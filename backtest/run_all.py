"""Top-level backtest runner for all 6 v1 strategies on synthetic data.

Output: backtest/results/summary.json + per-strategy result JSON files.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from dataclasses import asdict
from pathlib import Path

from backtest.engine import (
    MarketSnapshot, Trade, BacktestResult,
    run_strategy, save_result,
)
from backtest.synthetic_data import (
    favorite_longshot_snapshots,
    mlb_starter_news_snapshots,
    nba_series_hca_snapshots,
    nfl_weather_snapshots,
    popular_team_futures_snapshots,
    stale_reprice_snapshots,
)

log = logging.getLogger("backtest.run_all")
RESULT_DIR = Path("backtest/results")


# ---------------------------------------------------------------------------
# Entry rules
# ---------------------------------------------------------------------------
def kelly_contracts(edge: float, odds: float, bankroll_cents: int,
                    fraction: float, per_contract_cap_pct: float) -> int:
    """Very-simplified Kelly sizing for discrete-payout binary bets.
    f* = edge / odds where odds = payout / stake. For Yes: payout = 1 - price.
    """
    if odds <= 0:
        return 0
    f_star = edge / odds
    size_cents = max(0, fraction * f_star * bankroll_cents)
    size_cents = min(size_cents, per_contract_cap_pct * bankroll_cents)
    # Convert to contracts @ $0.01-per-cent granularity; clamp to at least 1
    price_cents = max(1, int(round(odds * 100)))  # placeholder
    contracts = int(size_cents / max(price_cents, 1))
    return max(1, min(contracts, 500))


def flb_entry_rule(snap: MarketSnapshot):
    quote = snap.yes_best_ask
    if not (0.04 <= quote <= 0.18):
        return None
    if snap.model_p_yes >= quote - 0.02:
        return None
    # Buy No → equivalent to shorting Yes
    odds = snap.yes_best_ask  # cost of entering Yes = quote; for No side, stake = (1-bid)
    edge = (quote - snap.model_p_yes)
    contracts = kelly_contracts(edge=edge, odds=1 - (1 - snap.yes_best_bid),
                                bankroll_cents=1_000_000,
                                fraction=0.25, per_contract_cap_pct=0.005)
    return {"side": "no", "role": "taker", "contracts": contracts}


def mlb_starter_rule(snap: MarketSnapshot):
    market = (snap.yes_best_bid + snap.yes_best_ask) / 2
    edge = snap.model_p_yes - market
    if abs(edge) < 0.03:
        return None
    side = "yes" if edge > 0 else "no"
    contracts = kelly_contracts(edge=abs(edge), odds=0.5,
                                bankroll_cents=1_000_000,
                                fraction=0.30, per_contract_cap_pct=0.005)
    return {"side": side, "role": "maker", "contracts": contracts}


def nba_series_rule(snap: MarketSnapshot):
    market = (snap.yes_best_bid + snap.yes_best_ask) / 2
    edge = snap.model_p_yes - market
    if abs(edge) < 0.04:
        return None
    side = "yes" if edge > 0 else "no"
    contracts = kelly_contracts(edge=abs(edge), odds=0.5,
                                bankroll_cents=1_000_000,
                                fraction=0.25, per_contract_cap_pct=0.02)
    return {"side": side, "role": "taker", "contracts": contracts}


def nfl_weather_rule(snap: MarketSnapshot):
    market = (snap.yes_best_bid + snap.yes_best_ask) / 2
    edge = snap.model_p_yes - market
    if abs(edge) < 0.025:
        return None
    side = "yes" if edge > 0 else "no"
    contracts = kelly_contracts(edge=abs(edge), odds=0.5,
                                bankroll_cents=1_000_000,
                                fraction=0.25, per_contract_cap_pct=0.006)
    return {"side": side, "role": "taker", "contracts": contracts}


def popular_team_rule(snap: MarketSnapshot):
    if not snap.notes.get("is_popular_team"):
        return None
    market = snap.yes_best_ask
    if snap.model_p_yes >= market - 0.02:
        return None
    contracts = kelly_contracts(edge=market - snap.model_p_yes,
                                odds=1 - snap.yes_best_bid,
                                bankroll_cents=1_000_000,
                                fraction=0.20, per_contract_cap_pct=0.01)
    return {"side": "no", "role": "taker", "contracts": contracts}


def stale_reprice_rule(snap: MarketSnapshot):
    market = (snap.yes_best_bid + snap.yes_best_ask) / 2
    edge = snap.model_p_yes - market
    if abs(edge) < 0.025:
        return None
    side = "yes" if edge > 0 else "no"
    contracts = kelly_contracts(edge=abs(edge), odds=0.5,
                                bankroll_cents=1_000_000,
                                fraction=0.35, per_contract_cap_pct=0.003)
    return {"side": side, "role": "taker", "contracts": contracts}


STRATEGIES = [
    ("S01", favorite_longshot_snapshots, flb_entry_rule),
    ("S02", mlb_starter_news_snapshots, mlb_starter_rule),
    ("S03", nba_series_hca_snapshots, nba_series_rule),
    ("S04", nfl_weather_snapshots, nfl_weather_rule),
    ("S05", popular_team_futures_snapshots, popular_team_rule),
    ("S06", stale_reprice_snapshots, stale_reprice_rule),
]


def main():
    logging.basicConfig(level=logging.INFO)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for sid, gen, rule in STRATEGIES:
        snaps, outcomes = gen()
        result = run_strategy(sid, snaps, outcomes, rule, synthetic=True)
        out_path = RESULT_DIR / f"{sid}.json"
        save_result(result, out_path)
        summary.append({
            "strategy_id": sid,
            "n_trades": result.n_trades,
            "hit_rate": round(result.hit_rate, 4),
            "avg_return_per_trade_pct": round(result.avg_return_per_trade_pct, 3),
            "total_pnl_cents": result.total_pnl_cents,
            "sharpe_annualized": round(result.sharpe_annualized, 3),
            "max_drawdown_pct": round(result.max_drawdown_pct, 4),
            "profit_factor": round(result.profit_factor, 3),
            "ci95_mean_return_pct": [round(x, 3) for x in result.ci95_mean_return_pct],
        })
        log.info("%s: %d trades, hit=%.2f%%, pnl=%d¢, sharpe=%.2f, PF=%.2f",
                 sid, result.n_trades, 100 * result.hit_rate,
                 result.total_pnl_cents, result.sharpe_annualized,
                 result.profit_factor)
    (RESULT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
