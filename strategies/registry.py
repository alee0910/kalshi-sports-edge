"""Strategy registry — the canonical list the scanner and backtester import.

Each strategy is represented as a `Strategy` dataclass with the metadata the
execution layer needs. The actual entry/exit logic lives in
`core/strategy_engine.py` (Phase 6) and reads these specs as configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    sports: tuple[str, ...]
    kelly_fraction: float
    per_contract_cap_pct_bankroll: float
    per_slate_cap_pct_bankroll: float
    min_edge_over_fee_multiplier: float
    role_preference: str        # "maker" or "taker" or "either"
    price_band: tuple[float, float]  # (min_yes, max_yes) Kalshi price range
    time_horizon_days: int       # expected days position held
    thesis_summary: str
    # Phase 4 findings:
    min_edge_pp: float = 0.03   # minimum gross edge in probability points
    shadow_mode: bool = False   # if True, scanner logs would-be trades but does not submit


# NB: sports tuple items align with `models/<sport>/model.py` sport identifier.
STRATEGIES: tuple[Strategy, ...] = (
    Strategy(
        id="S01",
        name="favorite_longshot_fade",
        sports=("mlb", "nba", "nfl"),
        kelly_fraction=0.25,
        per_contract_cap_pct_bankroll=0.005,
        per_slate_cap_pct_bankroll=0.04,
        min_edge_over_fee_multiplier=2.0,
        role_preference="maker",      # v1.1: flipped from taker (Phase 4 finding)
        price_band=(0.04, 0.18),
        time_horizon_days=1,
        thesis_summary="Fade sub-20¢ longshots where model P < quote by 3+ pp.",
        min_edge_pp=0.03,             # v1.1: tightened from 0.02
        shadow_mode=False,
    ),
    Strategy(
        id="S02",
        name="mlb_starter_news",
        sports=("mlb",),
        kelly_fraction=0.30,
        per_contract_cap_pct_bankroll=0.005,
        per_slate_cap_pct_bankroll=0.03,
        min_edge_over_fee_multiplier=2.0,
        role_preference="maker",
        price_band=(0.15, 0.85),
        time_horizon_days=1,
        thesis_summary="Enter inside Kalshi reprice lag after starter confirmation/scratch.",
        min_edge_pp=0.03,
        shadow_mode=False,
    ),
    Strategy(
        id="S03",
        name="nba_playoff_series_hca_alternation",
        sports=("nba",),
        kelly_fraction=0.25,
        per_contract_cap_pct_bankroll=0.02,
        per_slate_cap_pct_bankroll=0.04,
        min_edge_over_fee_multiplier=2.0,
        role_preference="either",
        price_band=(0.15, 0.85),
        time_horizon_days=14,
        thesis_summary="Fade momentum overreaction on series markets post single-game outcome.",
        min_edge_pp=0.06,             # v1.1: tightened from 0.04
        shadow_mode=True,             # v1.1: shadow-mode until calibrated (Phase 4 finding)
    ),
    Strategy(
        id="S04",
        name="nfl_weather_underreaction",
        sports=("nfl",),
        kelly_fraction=0.25,
        per_contract_cap_pct_bankroll=0.006,
        per_slate_cap_pct_bankroll=0.02,
        min_edge_over_fee_multiplier=2.0,
        role_preference="either",
        price_band=(0.20, 0.80),
        time_horizon_days=1,
        thesis_summary="Exploit 4-8¢ Kalshi lag on severe outdoor weather updates.",
        min_edge_pp=0.03,
        shadow_mode=False,
    ),
    Strategy(
        id="S05",
        name="popular_team_futures_short",
        sports=("mlb", "nba", "nfl"),
        kelly_fraction=0.20,
        per_contract_cap_pct_bankroll=0.01,
        per_slate_cap_pct_bankroll=0.03,
        min_edge_over_fee_multiplier=2.0,
        role_preference="taker",
        price_band=(0.03, 0.30),
        time_horizon_days=60,
        thesis_summary="Buy No on popular-team season/championship futures carrying 2-6% premium.",
        min_edge_pp=0.03,             # v1.1: tightened from 0.02
        shadow_mode=True,             # v1.1: shadow-mode until calibrated
    ),
    Strategy(
        id="S06",
        name="stale_reprice_arb",
        sports=("mlb", "nba", "nfl"),
        kelly_fraction=0.35,
        per_contract_cap_pct_bankroll=0.003,
        per_slate_cap_pct_bankroll=0.03,   # v1.1: tightened from 0.05
        min_edge_over_fee_multiplier=2.0,
        role_preference="taker",
        price_band=(0.05, 0.95),
        time_horizon_days=0,
        thesis_summary="Arb 30-120s Kalshi lag after in-game scoring/injury events.",
        min_edge_pp=0.035,            # v1.1: tightened from 0.025
        shadow_mode=True,             # v1.1: shadow-mode until live lag data confirms edge
    ),
)


def by_id(sid: str) -> Strategy:
    for s in STRATEGIES:
        if s.id == sid:
            return s
    raise KeyError(sid)


def for_sport(sport: str) -> tuple[Strategy, ...]:
    return tuple(s for s in STRATEGIES if sport in s.sports)


# Global risk limits (apply across all strategies)
@dataclass(frozen=True)
class GlobalRisk:
    daily_drawdown_stop_pct: float = 0.03   # halt new orders if daily PnL <= -3%
    per_sport_exposure_cap_pct: float = 0.08
    portfolio_concentration_max_pct: float = 0.15
    jurisdiction_blocklist: tuple[str, ...] = ("MA",)   # MA injunction live as of April 2026


GLOBAL = GlobalRisk()
