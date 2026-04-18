"""Backtest engine — walk-forward, fee-aware, per-strategy PnL attribution.

Design:
  1. Load historical market snapshots (orderbook + trade tape) from
     data/historical/<sport>/. For v1 we use synthetic/replayed data for the
     shipped strategies and flag them as "synthetic" in the output.
  2. For each (date, market) tuple, ask every live strategy whether it would
     have fired. If yes, simulate the fill at best_ask + slippage, accrue
     mark-to-market, close at settlement.
  3. Walk-forward: strategy coefficients are only updated on seasons earlier
     than the current test window. No look-ahead.
  4. Produce per-strategy and overall metrics: hit rate, avg EV, Sharpe,
     max drawdown, profit factor, 95% CI on mean per-trade return via
     block bootstrap.

Important caveat documented loudly in the output: the historical Kalshi
orderbook data we have is thin (Kalshi's public tape starts mid-2024 for
most sports markets). A v1 backtest is therefore directionally useful but
NOT a claim of production-grade historical evidence.
"""
from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Iterable, Optional

log = logging.getLogger("backtest.engine")

# Project-local imports
try:
    from research.kalshi.fees import fee_cents
except ImportError:  # pragma: no cover — stub when module not on path
    def fee_cents(contracts: int, price: float, role: str = "taker") -> int:
        coef = 0.07 if role == "taker" else 0.0175
        return math.ceil(coef * contracts * price * (1.0 - price) * 100.0)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class MarketSnapshot:
    """Normalized snapshot at a point in time."""
    ts: float                 # unix seconds
    market_ticker: str        # Kalshi market key
    sport: str                # "mlb" | "nba" | "nfl"
    event_id: str             # game/event identifier
    yes_best_bid: float       # 0..1
    yes_best_ask: float       # 0..1
    depth_yes: int
    depth_no: int
    model_p_yes: float        # model prediction at this snapshot
    notes: dict = field(default_factory=dict)


@dataclass
class Trade:
    ts: float
    market_ticker: str
    sport: str
    strategy_id: str
    side: str                 # "yes" or "no"
    role: str                 # "maker" or "taker"
    entry_price: float
    contracts: int
    entry_fee_cents: int
    model_p_at_entry: float
    # filled at settlement / close:
    exit_ts: Optional[float] = None
    exit_price: Optional[float] = None
    exit_fee_cents: int = 0
    settled_outcome: Optional[bool] = None   # True => Yes wins
    pnl_cents: Optional[int] = None
    closed_reason: str = ""


@dataclass
class BacktestResult:
    strategy_id: str
    n_trades: int = 0
    hit_rate: float = 0.0
    avg_return_per_trade_pct: float = 0.0
    total_pnl_cents: int = 0
    sharpe_annualized: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    ci95_mean_return_pct: tuple[float, float] = (0.0, 0.0)
    synthetic_data: bool = True
    notes: str = ""


# ---------------------------------------------------------------------------
# Execution simulation
# ---------------------------------------------------------------------------
def simulate_entry(snapshot: MarketSnapshot,
                   side: str,
                   role: str,
                   contracts: int,
                   slippage_ticks: int = 1) -> tuple[float, int]:
    """Return (entry_price, fee_cents). Taker pays ask + 1 tick slippage."""
    tick = 0.01
    if side == "yes":
        raw = snapshot.yes_best_ask + slippage_ticks * tick if role == "taker" else snapshot.yes_best_ask - tick
    else:
        no_ask = 1.0 - snapshot.yes_best_bid
        raw = no_ask + slippage_ticks * tick if role == "taker" else no_ask - tick
    entry_price = max(0.01, min(0.99, raw))
    fee = fee_cents(contracts, entry_price, role=role)
    return entry_price, fee


def simulate_settlement(trade: Trade, outcome_yes: bool) -> Trade:
    """Close a trade at settlement. Kalshi pays $1 (100¢) per winning contract."""
    trade.settled_outcome = outcome_yes
    trade.exit_ts = trade.ts + 86400  # placeholder; real backtest carries actual ts
    trade.exit_price = 1.0 if outcome_yes else 0.0
    wins_yes = (trade.side == "yes" and outcome_yes) or \
               (trade.side == "no" and not outcome_yes)
    # No exit fee at settlement on Kalshi
    gross = 100 * trade.contracts if wins_yes else 0
    cost = int(trade.entry_price * 100 * trade.contracts)
    # Exact fee math: PnL = (1-entry)*C*100 - fee if win; -entry*C*100 - fee if lose
    trade.exit_fee_cents = 0
    if wins_yes:
        trade.pnl_cents = gross - cost - trade.entry_fee_cents
    else:
        trade.pnl_cents = 0 - cost - trade.entry_fee_cents
    trade.closed_reason = "settlement"
    return trade


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _compute_drawdown(pnl_stream_cents: list[int]) -> float:
    peak = 0
    running = 0
    max_dd = 0.0
    for p in pnl_stream_cents:
        running += p
        peak = max(peak, running)
        dd = (peak - running)
        if peak > 0:
            max_dd = max(max_dd, dd / max(peak, 1))
    return max_dd


def _sharpe(returns_pct: list[float], periods_per_year: int = 100) -> float:
    if len(returns_pct) < 2:
        return 0.0
    mean = sum(returns_pct) / len(returns_pct)
    var = sum((r - mean) ** 2 for r in returns_pct) / (len(returns_pct) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def _block_bootstrap_ci(returns: list[float], n_boot: int = 1000, block_size: int = 10,
                        seed: int = 0) -> tuple[float, float]:
    if len(returns) < 5:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(returns)
    means = []
    for _ in range(n_boot):
        sample = []
        while len(sample) < n:
            start = rng.randint(0, max(0, n - block_size))
            sample.extend(returns[start:start + block_size])
        sample = sample[:n]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------
def run_strategy(strategy_id: str,
                 snapshots: Iterable[MarketSnapshot],
                 outcomes: dict[str, bool],
                 entry_rule: Callable[[MarketSnapshot], Optional[dict]],
                 bankroll_cents: int = 1_000_000,
                 synthetic: bool = True) -> BacktestResult:
    """Run a single strategy's backtest.

    Parameters
    ----------
    entry_rule : callable
        Given a MarketSnapshot, return {"side": ..., "role": ..., "contracts": ...}
        to fire a trade, or None to skip.
    outcomes : dict
        event_id -> True if Yes won at settlement.
    """
    trades: list[Trade] = []
    for snap in snapshots:
        decision = entry_rule(snap)
        if decision is None:
            continue
        entry_price, fee = simulate_entry(
            snap, side=decision["side"], role=decision["role"],
            contracts=decision["contracts"],
        )
        t = Trade(
            ts=snap.ts,
            market_ticker=snap.market_ticker,
            sport=snap.sport,
            strategy_id=strategy_id,
            side=decision["side"],
            role=decision["role"],
            entry_price=entry_price,
            contracts=decision["contracts"],
            entry_fee_cents=fee,
            model_p_at_entry=snap.model_p_yes,
        )
        if snap.event_id in outcomes:
            t = simulate_settlement(t, outcomes[snap.event_id])
        trades.append(t)

    # Metrics
    settled = [t for t in trades if t.pnl_cents is not None]
    wins = [t for t in settled if t.pnl_cents > 0]
    losses = [t for t in settled if t.pnl_cents <= 0]
    total_pnl = sum(t.pnl_cents for t in settled)
    notional_per_trade = [
        max(1, int(t.entry_price * 100 * t.contracts)) for t in settled
    ]
    returns_pct = [
        (t.pnl_cents / notional_per_trade[i]) * 100
        for i, t in enumerate(settled)
    ]
    hit_rate = len(wins) / len(settled) if settled else 0.0
    avg_ret = sum(returns_pct) / len(returns_pct) if returns_pct else 0.0
    dd = _compute_drawdown([t.pnl_cents for t in settled])
    sharpe = _sharpe(returns_pct, periods_per_year=100)
    pf_num = sum(t.pnl_cents for t in wins)
    pf_den = abs(sum(t.pnl_cents for t in losses)) or 1
    profit_factor = pf_num / pf_den
    ci = _block_bootstrap_ci(returns_pct, n_boot=1000, block_size=10)

    return BacktestResult(
        strategy_id=strategy_id,
        n_trades=len(settled),
        hit_rate=hit_rate,
        avg_return_per_trade_pct=avg_ret,
        total_pnl_cents=int(total_pnl),
        sharpe_annualized=sharpe,
        max_drawdown_pct=dd,
        profit_factor=profit_factor,
        trades=settled,
        ci95_mean_return_pct=ci,
        synthetic_data=synthetic,
        notes=("Synthetic replay data — Kalshi public orderbook tape is thin "
               "pre-2024H2; directional only." if synthetic else ""),
    )


def save_result(result: BacktestResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize trades briefly
    serial = asdict(result)
    serial["trades"] = [asdict(t) for t in result.trades]
    path.write_text(json.dumps(serial, indent=2))
