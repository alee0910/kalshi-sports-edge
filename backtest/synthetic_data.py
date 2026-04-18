"""Synthetic Kalshi-style market data generator for backtests.

This is NOT a historical replay. Its job is to produce a distribution of
snapshots that respects the mispricing theses in each strategy spec, so the
backtester can measure whether the entry rules extract edge AFTER fees and
slippage. If the entry rule loses money on synthetic data engineered to
match the thesis, the rule is broken. If it wins on synthetic data, that's a
necessary-but-not-sufficient check — Phase 7 calibration on live/historical
data is the final arbiter.

Each scenario is documented inline with the effect size drawn from the
literature review cited in the matching strategy spec.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator

from backtest.engine import MarketSnapshot


# ---------------------------------------------------------------------------
# Thesis-calibrated scenarios
# ---------------------------------------------------------------------------
def favorite_longshot_snapshots(n: int = 2000, seed: int = 1) -> tuple[list[MarketSnapshot], dict[str, bool]]:
    """S01: sub-20¢ longshots where empirical P < quoted P by ~2-4% on avg.

    Literature (Becker 2025): 72M-trade FLB — Yes prices in 4-18¢ band show a
    ~2-3% overpricing vs. realized frequency.
    """
    rng = random.Random(seed)
    snaps = []
    outcomes = {}
    for i in range(n):
        quoted = rng.uniform(0.04, 0.18)
        true_p = max(0.005, quoted - rng.uniform(0.015, 0.035))  # systematic ~2-3.5% over
        event_id = f"flb_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 3600,
            market_ticker=f"MLB-FLB-{i}",
            sport=rng.choice(["mlb", "nba", "nfl"]),
            event_id=event_id,
            yes_best_bid=max(0.01, quoted - 0.01),
            yes_best_ask=min(0.99, quoted + 0.01),
            depth_yes=rng.randint(500, 5000),
            depth_no=rng.randint(500, 5000),
            model_p_yes=true_p,
        ))
        outcomes[event_id] = rng.random() < true_p
    return snaps, outcomes


def mlb_starter_news_snapshots(n: int = 300, seed: int = 2):
    """S02: reprice-lag window — market still at old equilibrium, model at new fair."""
    rng = random.Random(seed)
    snaps = []
    outcomes = {}
    for i in range(n):
        market = rng.uniform(0.30, 0.70)
        # Model's new fair is 4-10¢ off the market (starter news hasn't been
        # absorbed yet). Sign is random.
        direction = rng.choice([-1, 1])
        fair = max(0.05, min(0.95, market + direction * rng.uniform(0.04, 0.09)))
        event_id = f"mlb_starter_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 21600,
            market_ticker=f"MLB-{i}",
            sport="mlb",
            event_id=event_id,
            yes_best_bid=market - 0.01,
            yes_best_ask=market + 0.01,
            depth_yes=rng.randint(200, 2000),
            depth_no=rng.randint(200, 2000),
            model_p_yes=fair,
        ))
        outcomes[event_id] = rng.random() < fair
    return snaps, outcomes


def nba_series_hca_snapshots(n: int = 120, seed: int = 3):
    """S03: series markets with ~4-7% overreaction to single-game outcomes."""
    rng = random.Random(seed)
    snaps, outcomes = [], {}
    for i in range(n):
        market = rng.uniform(0.25, 0.75)
        direction = rng.choice([-1, 1])   # retail over-extrapolates single game
        # We believe the series fair is *less* extreme than market (fade momentum)
        fair = market - direction * rng.uniform(0.04, 0.07)
        fair = max(0.08, min(0.92, fair))
        event_id = f"nba_series_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 86400,
            market_ticker=f"NBA-SERIES-{i}",
            sport="nba",
            event_id=event_id,
            yes_best_bid=market - 0.01,
            yes_best_ask=market + 0.01,
            depth_yes=rng.randint(500, 3000),
            depth_no=rng.randint(500, 3000),
            model_p_yes=fair,
        ))
        outcomes[event_id] = rng.random() < fair
    return snaps, outcomes


def nfl_weather_snapshots(n: int = 80, seed: int = 4):
    """S04: weather-driven edge in outdoor games."""
    rng = random.Random(seed)
    snaps, outcomes = [], {}
    for i in range(n):
        market = rng.uniform(0.30, 0.70)
        # Model adjusts for weather, market lagging → 3-5¢ edge
        fair = market + rng.choice([-1, 1]) * rng.uniform(0.03, 0.05)
        fair = max(0.1, min(0.9, fair))
        event_id = f"nfl_wx_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 86400,
            market_ticker=f"NFL-WX-{i}",
            sport="nfl",
            event_id=event_id,
            yes_best_bid=market - 0.01,
            yes_best_ask=market + 0.01,
            depth_yes=rng.randint(300, 2500),
            depth_no=rng.randint(300, 2500),
            model_p_yes=fair,
        ))
        outcomes[event_id] = rng.random() < fair
    return snaps, outcomes


def popular_team_futures_snapshots(n: int = 40, seed: int = 5):
    """S05: popular-team championship futures w/ 2-6% premium."""
    rng = random.Random(seed)
    snaps, outcomes = [], {}
    for i in range(n):
        quoted = rng.uniform(0.05, 0.25)
        # Model says fair is 2-5% less than quoted (popular team premium)
        fair = max(0.02, quoted - rng.uniform(0.025, 0.05))
        event_id = f"futures_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 86400 * 7,
            market_ticker=f"CHAMP-{i}",
            sport=rng.choice(["mlb", "nba", "nfl"]),
            event_id=event_id,
            yes_best_bid=quoted - 0.01,
            yes_best_ask=quoted + 0.01,
            depth_yes=rng.randint(1000, 10000),
            depth_no=rng.randint(1000, 10000),
            model_p_yes=fair,
            notes={"is_popular_team": True},
        ))
        outcomes[event_id] = rng.random() < fair
    return snaps, outcomes


def stale_reprice_snapshots(n: int = 1500, seed: int = 6):
    """S06: in-game stale-reprice — 2.5-5¢ edge window."""
    rng = random.Random(seed)
    snaps, outcomes = [], {}
    for i in range(n):
        market = rng.uniform(0.20, 0.80)
        direction = rng.choice([-1, 1])
        fair = max(0.05, min(0.95, market + direction * rng.uniform(0.025, 0.05)))
        event_id = f"reprice_{i}"
        snaps.append(MarketSnapshot(
            ts=1_700_000_000 + i * 60,
            market_ticker=f"INGAME-{i}",
            sport=rng.choice(["mlb", "nba", "nfl"]),
            event_id=event_id,
            yes_best_bid=market - 0.01,
            yes_best_ask=market + 0.01,
            depth_yes=rng.randint(200, 1500),
            depth_no=rng.randint(200, 1500),
            model_p_yes=fair,
        ))
        outcomes[event_id] = rng.random() < fair
    return snaps, outcomes
