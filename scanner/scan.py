"""Live market scanner.

Every ~20 minutes (GitHub Actions cron), we:
  1. Pull open Kalshi sports markets.
  2. For each eligible market, call the matching sport's model.
  3. For each live strategy, evaluate entry rule; record candidate trades.
  4. Emit `dashboard/data/scan_<timestamp>.json` + update `latest.json`.

The scanner DOES NOT SUBMIT ORDERS. Order submission is a separate, explicitly
gated action (see `scanner/executor.py` — also gated by shadow_mode flags in
the strategy registry).

Outputs (to dashboard/data/):
  - latest.json            ← most recent scan summary
  - scan_<ISO8601>.json    ← archive of each scan
  - candidates.json        ← rolling top-50 live candidates
  - shadow.json            ← rolling top-50 shadow-mode (log-only) candidates
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

log = logging.getLogger("scanner")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "dashboard" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Sport/model dispatch
# ---------------------------------------------------------------------------
SPORTS_LIVE = ("mlb", "nba", "nfl")
SPORTS_STUB = ("nhl", "golf", "tennis", "soccer", "cbb", "mma", "nascar")


def is_sport_live(sport: str) -> bool:
    """Return True iff the sport's model has not_yet_built == False."""
    try:
        mod = __import__(f"models.{sport}.model", fromlist=["not_yet_built"])
        return not getattr(mod, "not_yet_built", False)
    except Exception as e:  # noqa: BLE001
        log.warning("sport %s module import failed: %s", sport, e)
        return False


# ---------------------------------------------------------------------------
# Candidate data structure
# ---------------------------------------------------------------------------
@dataclass
class Candidate:
    ts: str
    sport: str
    market_ticker: str
    event_label: str
    strategy_id: str
    strategy_name: str
    model_p_yes: float
    market_yes_ask: float
    market_yes_bid: float
    edge_pp: float
    net_edge_after_fee_cents: int
    suggested_side: str
    suggested_role: str
    suggested_contracts: int
    expected_value_cents: int
    shadow_mode: bool
    rationale: str


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Edge evaluation per strategy
# ---------------------------------------------------------------------------
def evaluate_candidate(market: dict, strategy, model_p: float) -> Optional[Candidate]:
    """Apply a strategy's entry rule to a (market, model_p) tuple.

    market: {'ticker','event_label','sport','yes_bid','yes_ask','depth_yes',
             'depth_no'}
    """
    from research.kalshi.fees import fee_cents

    yes_ask = market["yes_ask"]
    yes_bid = market["yes_bid"]
    mid = (yes_bid + yes_ask) / 2

    # Apply strategy-specific filters
    lo, hi = strategy.price_band
    if not (lo <= yes_ask <= hi):
        return None

    raw_edge = model_p - yes_ask if strategy.role_preference == "taker" \
        else model_p - mid
    # Direction
    if raw_edge >= 0:
        side = "yes"
        entry_price = yes_ask if strategy.role_preference == "taker" else mid
    else:
        side = "no"
        entry_price = 1 - yes_bid if strategy.role_preference == "taker" else 1 - mid
    abs_edge = abs(raw_edge)

    if abs_edge < strategy.min_edge_pp:
        return None

    # Estimate contracts using simplified Kelly fraction
    bankroll_cents = 1_000_000  # $10k default in cents — readable assumption
    contracts = max(1, int(strategy.kelly_fraction * abs_edge *
                           strategy.per_contract_cap_pct_bankroll * bankroll_cents))
    contracts = min(contracts, 500)

    fee = fee_cents(contracts, entry_price, role=strategy.role_preference
                    if strategy.role_preference != "either" else "taker")

    net_edge_cents = int(abs_edge * contracts * 100) - fee
    if net_edge_cents <= strategy.min_edge_over_fee_multiplier * fee:
        return None

    ev_cents = int(abs_edge * contracts * 100) - fee

    rationale = (
        f"{strategy.id} {strategy.name}: "
        f"model={model_p:.3f} quote={yes_ask:.3f} edge={abs_edge*100:.1f}pp "
        f"net_after_fee={net_edge_cents}¢"
    )

    return Candidate(
        ts=_now_iso(),
        sport=market["sport"],
        market_ticker=market["ticker"],
        event_label=market.get("event_label", market["ticker"]),
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        model_p_yes=model_p,
        market_yes_ask=yes_ask,
        market_yes_bid=yes_bid,
        edge_pp=round(abs_edge * 100, 3),
        net_edge_after_fee_cents=net_edge_cents,
        suggested_side=side,
        suggested_role=(strategy.role_preference
                        if strategy.role_preference != "either" else "taker"),
        suggested_contracts=contracts,
        expected_value_cents=ev_cents,
        shadow_mode=strategy.shadow_mode,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Market fetcher (real + fixture)
# ---------------------------------------------------------------------------
def fetch_markets_live() -> list[dict]:
    """Fetch real Kalshi markets via client. Falls back to fixture if offline."""
    try:
        from research.kalshi.client import KalshiClient
        client = KalshiClient()
        markets = client.list_sports_markets()
        norm = []
        for m in markets:
            norm.append({
                "ticker": m["ticker"],
                "event_label": m.get("event_label") or m.get("title") or m["ticker"],
                "sport": m.get("sport", "mlb"),
                "yes_bid": float(m.get("yes_bid", 0.5)),
                "yes_ask": float(m.get("yes_ask", 0.5)),
                "depth_yes": int(m.get("depth_yes", 0)),
                "depth_no": int(m.get("depth_no", 0)),
            })
        return norm
    except Exception as e:  # noqa: BLE001
        log.warning("live fetch failed (%s); using fixture", e)
        return _fixture_markets()


def _fixture_markets() -> list[dict]:
    """Deterministic fixture for offline dashboard rendering."""
    return [
        {"ticker": "MLB-LAD-COL-20260418", "event_label": "LAD @ COL Apr 18",
         "sport": "mlb", "yes_bid": 0.60, "yes_ask": 0.62, "depth_yes": 1200, "depth_no": 900},
        {"ticker": "NBA-BOS-MIA-GAME1",    "event_label": "BOS-MIA Game 1 Series",
         "sport": "nba", "yes_bid": 0.73, "yes_ask": 0.75, "depth_yes": 2000, "depth_no": 1500},
        {"ticker": "NFL-SB-LX-KC",         "event_label": "Chiefs win Super Bowl LX",
         "sport": "nfl", "yes_bid": 0.17, "yes_ask": 0.19, "depth_yes": 5000, "depth_no": 5000},
        {"ticker": "MLB-MIN-LONGSHOT",     "event_label": "MIN wins WS 2026",
         "sport": "mlb", "yes_bid": 0.04, "yes_ask": 0.06, "depth_yes": 3000, "depth_no": 3000},
    ]


def model_p_for(market: dict) -> Optional[float]:
    """Ask the sport model for a fair P(yes). For v1 fixtures we shortcut.
    Real implementation: build_matchup(...) → model.predict(...).p_home_win."""
    sport = market["sport"]
    if not is_sport_live(sport):
        return None
    # Placeholder: in production this calls models/<sport>/data_pipeline.build_matchup()
    # For v1 scanner we return a stub-edge so the dashboard has data.
    stub_edges = {
        "MLB-LAD-COL-20260418": 0.66,
        "NBA-BOS-MIA-GAME1":    0.68,
        "NFL-SB-LX-KC":         0.14,
        "MLB-MIN-LONGSHOT":     0.02,
    }
    return stub_edges.get(market["ticker"])


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------
def scan_once() -> dict:
    from strategies.registry import STRATEGIES

    markets = fetch_markets_live()
    live_candidates: list[Candidate] = []
    shadow_candidates: list[Candidate] = []
    skipped: list[dict] = []

    for m in markets:
        if not is_sport_live(m["sport"]):
            skipped.append({"ticker": m["ticker"], "reason": f"sport '{m['sport']}' not_yet_built"})
            continue
        model_p = model_p_for(m)
        if model_p is None:
            skipped.append({"ticker": m["ticker"], "reason": "no model prediction"})
            continue
        for strat in STRATEGIES:
            if m["sport"] not in strat.sports:
                continue
            cand = evaluate_candidate(m, strat, model_p)
            if cand is None:
                continue
            if cand.shadow_mode:
                shadow_candidates.append(cand)
            else:
                live_candidates.append(cand)

    # Sort candidates by expected-value desc
    live_candidates.sort(key=lambda c: -c.expected_value_cents)
    shadow_candidates.sort(key=lambda c: -c.expected_value_cents)

    summary = {
        "scanned_at": _now_iso(),
        "n_markets_scanned": len(markets),
        "n_live_candidates": len(live_candidates),
        "n_shadow_candidates": len(shadow_candidates),
        "n_skipped": len(skipped),
        "skipped": skipped[:20],
        "top_live": [asdict(c) for c in live_candidates[:20]],
        "top_shadow": [asdict(c) for c in shadow_candidates[:20]],
        "version": "scanner-v1.1",
    }

    # Archive + update latest
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (DATA_DIR / f"scan_{stamp}.json").write_text(json.dumps(summary, indent=2))
    (DATA_DIR / "latest.json").write_text(json.dumps(summary, indent=2))
    (DATA_DIR / "candidates.json").write_text(
        json.dumps([asdict(c) for c in live_candidates[:50]], indent=2))
    (DATA_DIR / "shadow.json").write_text(
        json.dumps([asdict(c) for c in shadow_candidates[:50]], indent=2))

    log.info("scan done: %d live, %d shadow, %d skipped",
             len(live_candidates), len(shadow_candidates), len(skipped))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure repo root is on sys.path for `import models.*` etc.
    sys.path.insert(0, str(REPO_ROOT))
    out = scan_once()
    print(json.dumps({
        "n_live": out["n_live_candidates"],
        "n_shadow": out["n_shadow_candidates"],
        "n_skipped": out["n_skipped"],
    }, indent=2))
