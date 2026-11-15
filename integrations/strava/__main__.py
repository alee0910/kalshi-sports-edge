"""Strava CLI.

  python -m integrations.strava auth            # one-time OAuth setup
  python -m integrations.strava whoami          # verify the connection
  python -m integrations.strava activities -n 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

from .client import (DEFAULT_TOKEN_FILE, StravaClient, authorize_url, exchange_code)


def _creds() -> tuple[str, str]:
    cid, secret = os.environ.get("STRAVA_CLIENT_ID"), os.environ.get("STRAVA_CLIENT_SECRET")
    if not (cid and secret):
        sys.exit("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET "
                 "(https://www.strava.com/settings/api)")
    return cid, secret


def cmd_auth(args: argparse.Namespace) -> None:
    cid, secret = _creds()
    print("1. Open this URL, log in, and click Authorize:\n")
    print("   " + authorize_url(cid))
    print("\n2. You'll land on a localhost page that fails to load — that's expected.")
    pasted = input("   Paste the full URL (or just the code) here: ").strip()
    code = parse_qs(urlparse(pasted).query).get("code", [pasted])[0]
    tok = exchange_code(cid, secret, code)
    path = DEFAULT_TOKEN_FILE if not os.environ.get("STRAVA_TOKEN_FILE") \
        else os.environ["STRAVA_TOKEN_FILE"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({k: tok[k] for k in ("access_token", "refresh_token", "expires_at")}, f, indent=2)
    os.chmod(path, 0o600)
    who = tok.get("athlete", {})
    print(f"\nConnected as {who.get('firstname', '?')} {who.get('lastname', '')}. "
          f"Tokens saved to {path}")
    print("For CI, store the refresh_token from that file as STRAVA_REFRESH_TOKEN.")


def cmd_whoami(args: argparse.Namespace) -> None:
    a = StravaClient().athlete()
    print(f"{a['firstname']} {a['lastname']} (id {a['id']})")


def cmd_activities(args: argparse.Namespace) -> None:
    for a in StravaClient().activities(limit=args.n):
        print(f"{a['start_date_local'][:10]}  {a['sport_type']:<12} "
              f"{a['distance'] / 1000:7.2f} km  {a['moving_time'] // 60:4d} min  {a['name']}")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m integrations.strava")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(fn=cmd_auth)
    sub.add_parser("whoami").set_defaults(fn=cmd_whoami)
    act = sub.add_parser("activities")
    act.add_argument("-n", type=int, default=10)
    act.set_defaults(fn=cmd_activities)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
