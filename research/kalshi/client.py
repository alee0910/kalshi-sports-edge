"""Kalshi REST + WebSocket client wrapper for sports event contracts.

Minimal-dep HTTP client around the public Kalshi Trade API v2/v3. Handles:
- API-key auth (Ed25519 or legacy email/password login flow) via env vars
- Market discovery, orderbook depth, fills, positions
- Rate-limit-aware retries
- Pagination for list endpoints

Credentials are pulled from environment variables only; never committed:
  KALSHI_API_KEY   - API key ID (UUID-form)
  KALSHI_API_SECRET - Ed25519 private key in PEM (optional, for signed endpoints)
  KALSHI_ENV       - 'prod' (default) or 'demo'

References
----------
- https://trading-api.readme.io/
- https://kalshi.com/api
"""
from __future__ import annotations

import os
import time
import base64
import logging
from dataclasses import dataclass
from typing import Any, Iterator, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

log = logging.getLogger("kalshi.client")

PROD_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"


@dataclass
class KalshiMarket:
    ticker: str
    event_ticker: str
    series_ticker: str
    subtitle: str
    yes_bid: Optional[float]  # dollars
    yes_ask: Optional[float]
    no_bid: Optional[float]
    no_ask: Optional[float]
    last_price: Optional[float]
    volume: int
    open_interest: int
    status: str              # 'active', 'closed', 'settled'
    close_time: Optional[str]
    category: Optional[str]
    raw: dict


class KalshiClient:
    def __init__(self, api_key: Optional[str] = None, env: str = "prod",
                 session: Optional["requests.Session"] = None):
        if requests is None:
            raise RuntimeError("requests not installed; pip install requests")
        self.api_key = api_key or os.environ.get("KALSHI_API_KEY")
        if not self.api_key:
            log.warning("No KALSHI_API_KEY set; some endpoints will fail")
        self.base = PROD_BASE if env == "prod" else DEMO_BASE
        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "kalshi-sports-edge/0.1",
        })
        if self.api_key:
            # Kalshi supports a simple bearer-token header for API-key auth
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        self._rate_limit_remaining = 100
        self._rate_limit_reset = 0.0

    # ------------------------------------------------------------------
    # core HTTP
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, params: dict | None = None,
                 json: dict | None = None, retries: int = 3) -> Any:
        url = f"{self.base}{path}"
        for attempt in range(retries):
            # Polite cooldown if we know we're rate-limited
            if self._rate_limit_remaining < 3 and time.time() < self._rate_limit_reset:
                sleep_for = self._rate_limit_reset - time.time() + 0.2
                log.info("rate-limit cooldown: sleeping %.2fs", sleep_for)
                time.sleep(max(0.0, sleep_for))
            r = self.session.request(method, url, params=params, json=json, timeout=20)
            # Track rate-limit headers if present
            if "X-RateLimit-Remaining" in r.headers:
                self._rate_limit_remaining = int(r.headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in r.headers:
                try:
                    self._rate_limit_reset = float(r.headers["X-RateLimit-Reset"])
                except ValueError:
                    pass
            if r.status_code == 429:
                wait = min(2 ** attempt, 8)
                log.warning("429 rate-limited; retry in %ds", wait)
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                wait = min(2 ** attempt, 8)
                log.warning("%d server error; retry in %ds", r.status_code, wait)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise KalshiAPIError(r.status_code, r.text, path)
            return r.json() if r.text else {}
        raise KalshiAPIError(r.status_code, r.text, path)

    # ------------------------------------------------------------------
    # markets
    # ------------------------------------------------------------------
    def list_markets(self, series_ticker: Optional[str] = None,
                     event_ticker: Optional[str] = None,
                     status: str = "open",
                     limit: int = 200) -> Iterator[KalshiMarket]:
        """Iterate markets with automatic cursor pagination."""
        cursor = None
        while True:
            params: dict[str, Any] = {"limit": limit, "status": status}
            if series_ticker:
                params["series_ticker"] = series_ticker
            if event_ticker:
                params["event_ticker"] = event_ticker
            if cursor:
                params["cursor"] = cursor
            data = self._request("GET", "/markets", params=params)
            for m in data.get("markets", []):
                yield _market_from_json(m)
            cursor = data.get("cursor")
            if not cursor:
                break

    def list_sports_markets(self, status: str = "open") -> list[KalshiMarket]:
        """Filter to sports categories. Kalshi uses series_ticker prefixes roughly:
        KXNBA, KXNFL, KXMLB, KXNHL, KXPGA, KXATP, KXWTA, KXUFC, KXNASCAR.
        Exact prefixes shift; we match on category field when possible.
        """
        sports_series_prefixes = (
            "KXNBA", "KXNFL", "KXMLB", "KXNHL",
            "KXPGA", "KXATP", "KXWTA", "KXUFC",
            "KXNCAAF", "KXNCAAB", "KXF1", "KXNASCAR",
            "KXMLS", "KXEPL", "KXUEFA",
        )
        out = []
        for m in self.list_markets(status=status):
            cat = (m.category or "").lower()
            if cat == "sports" or m.series_ticker.startswith(sports_series_prefixes):
                out.append(m)
        return out

    def get_market(self, ticker: str) -> KalshiMarket:
        data = self._request("GET", f"/markets/{ticker}")
        return _market_from_json(data["market"])

    def orderbook(self, ticker: str, depth: int = 10) -> dict:
        return self._request("GET", f"/markets/{ticker}/orderbook", params={"depth": depth})

    def trades(self, ticker: str, limit: int = 200, min_ts: Optional[int] = None,
               max_ts: Optional[int] = None) -> Iterator[dict]:
        cursor = None
        while True:
            params: dict[str, Any] = {"ticker": ticker, "limit": limit}
            if min_ts:
                params["min_ts"] = min_ts
            if max_ts:
                params["max_ts"] = max_ts
            if cursor:
                params["cursor"] = cursor
            data = self._request("GET", "/markets/trades", params=params)
            for t in data.get("trades", []):
                yield t
            cursor = data.get("cursor")
            if not cursor:
                break

    # ------------------------------------------------------------------
    # portfolio (requires signed auth)
    # ------------------------------------------------------------------
    def get_balance(self) -> dict:
        return self._request("GET", "/portfolio/balance")

    def get_positions(self) -> list[dict]:
        out, cursor = [], None
        while True:
            params: dict[str, Any] = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            data = self._request("GET", "/portfolio/positions", params=params)
            out.extend(data.get("market_positions", []))
            cursor = data.get("cursor")
            if not cursor:
                break
        return out


class KalshiAPIError(Exception):
    def __init__(self, status: int, body: str, path: str):
        super().__init__(f"Kalshi API error {status} on {path}: {body[:200]}")
        self.status = status
        self.body = body
        self.path = path


def _market_from_json(m: dict) -> KalshiMarket:
    def f(k: str) -> Optional[float]:
        v = m.get(k)
        return v / 100.0 if isinstance(v, (int, float)) else None  # API returns cents
    return KalshiMarket(
        ticker=m.get("ticker", ""),
        event_ticker=m.get("event_ticker", ""),
        series_ticker=m.get("series_ticker", ""),
        subtitle=m.get("subtitle", ""),
        yes_bid=f("yes_bid"),
        yes_ask=f("yes_ask"),
        no_bid=f("no_bid"),
        no_ask=f("no_ask"),
        last_price=f("last_price"),
        volume=m.get("volume", 0),
        open_interest=m.get("open_interest", 0),
        status=m.get("status", ""),
        close_time=m.get("close_time"),
        category=m.get("category"),
        raw=m,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    c = KalshiClient()
    mkts = c.list_sports_markets(status="open")
    print(f"found {len(mkts)} open sports markets")
    for m in mkts[:5]:
        print(f"  {m.ticker:30s} yes_ask={m.yes_ask} vol={m.volume} oi={m.open_interest}")
