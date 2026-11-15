"""Strava API v3 client with OAuth2 refresh-token handling.

Strava access tokens expire after ~6 hours, so this client stores a long-lived
refresh token and mints access tokens on demand. Strava may rotate the refresh
token on any refresh; the newest one is written back to the token file.

Credentials come from environment variables (never committed):
  STRAVA_CLIENT_ID      - from https://www.strava.com/settings/api
  STRAVA_CLIENT_SECRET  - same page
  STRAVA_REFRESH_TOKEN  - from the one-time OAuth flow (see __main__.py)
  STRAVA_TOKEN_FILE     - optional; default secrets/strava_token.json
                          (gitignored). Takes precedence over
                          STRAVA_REFRESH_TOKEN once it exists.

References
----------
- https://developers.strava.com/docs/authentication/
- https://developers.strava.com/docs/reference/
- https://developers.strava.com/docs/rate-limits/
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Iterator, Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

log = logging.getLogger("strava.client")

API_BASE = "https://www.strava.com/api/v3"
AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEFAULT_TOKEN_FILE = Path("secrets/strava_token.json")
DEFAULT_SCOPES = ("read", "activity:read_all", "profile:read_all")
USER_AGENT = "kalshi-sports-edge/0.1"


class StravaAuthError(RuntimeError):
    pass


def _require_requests() -> None:
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests")


def authorize_url(client_id: str, redirect_uri: str = "http://localhost/exchange_token",
                  scopes: tuple[str, ...] = DEFAULT_SCOPES) -> str:
    """URL the athlete opens to grant access. Strava redirects to
    ``redirect_uri?code=...``; the redirect host must match the
    "Authorization Callback Domain" in your Strava app settings."""
    q = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "force",
        "scope": ",".join(scopes),
    }
    return f"{AUTHORIZE_URL}?{urlencode(q)}"


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Trade a one-time authorization code for access + refresh tokens."""
    _require_requests()
    r = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }, timeout=20)
    if r.status_code != 200:
        raise StravaAuthError(f"code exchange failed: {r.status_code} {r.text}")
    return r.json()


class StravaClient:
    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 refresh_token: Optional[str] = None,
                 token_file: Optional[os.PathLike | str] = None,
                 session: Optional["requests.Session"] = None):
        _require_requests()
        self.client_id = client_id or os.environ.get("STRAVA_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("STRAVA_CLIENT_SECRET")
        if not (self.client_id and self.client_secret):
            raise StravaAuthError("STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set")
        self.token_file = Path(token_file or os.environ.get("STRAVA_TOKEN_FILE")
                               or DEFAULT_TOKEN_FILE)
        self._token: dict[str, Any] = self._load_token()
        if refresh_token:
            self._token["refresh_token"] = refresh_token
        elif "refresh_token" not in self._token and os.environ.get("STRAVA_REFRESH_TOKEN"):
            self._token["refresh_token"] = os.environ["STRAVA_REFRESH_TOKEN"]
        if "refresh_token" not in self._token:
            raise StravaAuthError(
                "No refresh token. Run `python -m integrations.strava auth` first "
                "or set STRAVA_REFRESH_TOKEN.")
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/json",
                                     "User-Agent": USER_AGENT})
        self.rate_limit: dict[str, str] = {}

    # ------------------------------------------------------------------
    # token management
    # ------------------------------------------------------------------
    def _load_token(self) -> dict:
        try:
            return json.loads(self.token_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_token(self) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(self._token, indent=2))
        try:
            os.chmod(self.token_file, 0o600)
        except OSError:  # pragma: no cover
            pass

    def _refresh(self) -> None:
        r = self.session.post(TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._token["refresh_token"],
        }, timeout=20)
        if r.status_code != 200:
            raise StravaAuthError(f"token refresh failed: {r.status_code} {r.text}")
        body = r.json()
        self._token.update({k: body[k] for k in
                            ("access_token", "refresh_token", "expires_at") if k in body})
        self._save_token()
        log.info("refreshed Strava access token (expires_at=%s)", self._token.get("expires_at"))

    def access_token(self) -> str:
        # refresh a minute early to avoid racing expiry
        if not self._token.get("access_token") or \
                self._token.get("expires_at", 0) - 60 <= time.time():
            self._refresh()
        return self._token["access_token"]

    # ------------------------------------------------------------------
    # core HTTP
    # ------------------------------------------------------------------
    def _get(self, path: str, params: Optional[dict] = None, max_retries: int = 3) -> Any:
        url = f"{API_BASE}{path}"
        for attempt in range(max_retries + 1):
            r = self.session.get(url, params=params, timeout=30, headers={
                "Authorization": f"Bearer {self.access_token()}"})
            self.rate_limit = {k: v for k, v in r.headers.items()
                               if k.lower().startswith(("x-ratelimit", "x-readratelimit"))}
            if r.status_code == 401 and attempt == 0:
                self._token.pop("access_token", None)  # force refresh, retry once
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if attempt == max_retries:
                    break
                # Strava windows reset on 15-minute boundaries
                wait = 900 - (time.time() % 900) + 1 if r.status_code == 429 else 2 ** attempt
                log.warning("Strava %s on %s; sleeping %.0fs", r.status_code, path, wait)
                time.sleep(wait)
                continue
            break
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # endpoints
    # ------------------------------------------------------------------
    def athlete(self) -> dict:
        return self._get("/athlete")

    def athlete_stats(self, athlete_id: Optional[int] = None) -> dict:
        athlete_id = athlete_id or self.athlete()["id"]
        return self._get(f"/athletes/{athlete_id}/stats")

    def activities(self, after: Optional[int] = None, before: Optional[int] = None,
                   per_page: int = 100, limit: Optional[int] = None) -> Iterator[dict]:
        """Yield the athlete's activities (newest first), paging automatically.
        ``after``/``before`` are Unix epoch seconds."""
        page, n = 1, 0
        while True:
            params = {"page": page, "per_page": per_page}
            if after is not None:
                params["after"] = after
            if before is not None:
                params["before"] = before
            batch = self._get("/athlete/activities", params)
            if not batch:
                return
            for a in batch:
                yield a
                n += 1
                if limit is not None and n >= limit:
                    return
            page += 1

    def activity(self, activity_id: int, include_all_efforts: bool = False) -> dict:
        return self._get(f"/activities/{activity_id}",
                         {"include_all_efforts": str(include_all_efforts).lower()})

    def activity_streams(self, activity_id: int,
                         keys: tuple[str, ...] = ("time", "distance", "heartrate",
                                                  "watts", "altitude", "latlng")) -> dict:
        return self._get(f"/activities/{activity_id}/streams",
                         {"keys": ",".join(keys), "key_by_type": "true"})
