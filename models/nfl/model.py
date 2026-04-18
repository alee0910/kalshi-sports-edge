"""NFL win-probability model.

Design (v1.0), grounded in /research/domain/nfl_literature_review.md:

  Stage 1 — nfelo-style power rating (Elo blend with EPA + market).
  Stage 2 — QB-adjusted: CPOE + EPA deltas for starting QBs; backup-QB penalty.
  Stage 3 — Situational: weather, short rest, divisional, home field.
  Stage 4 — Margin distribution → P(home win) via normal CDF.

Key empirical finding (nfelo, Open Source Football): weight offensive EPA
1.6× defensive EPA when computing forward-looking team quality.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("nfl.model")


@dataclass
class TeamPowerRating:
    """Elo-style rating with EPA components."""
    team_code: str
    elo: float = 1500.0
    off_epa_per_play_season: float = 0.0   # points / play
    def_epa_per_play_season: float = 0.0
    off_success_rate: float = 0.45
    def_success_rate: float = 0.45
    starting_qb_cpoe: float = 0.0          # %
    starting_qb_epa_play: float = 0.0
    games_observed: int = 0


@dataclass
class QBInfo:
    qb_id: str
    name: str = ""
    cpoe: float = 0.0
    epa_per_play: float = 0.0
    passes_observed: int = 0
    is_starter: bool = True
    is_injury_replacement: bool = False


@dataclass
class GameContext:
    is_division_game: bool = False
    is_thursday_night: bool = False
    is_monday_night: bool = False
    is_playoff: bool = False
    is_neutral_site: bool = False
    home_rest_days: int = 7
    away_rest_days: int = 7
    temp_f: float = 60.0
    wind_mph: float = 5.0
    precipitation: float = 0.0  # inches expected
    altitude_feet: float = 0.0
    is_dome: bool = False


@dataclass
class MatchupInputs:
    home_team: TeamPowerRating
    away_team: TeamPowerRating
    home_qb: QBInfo
    away_qb: QBInfo
    context: GameContext = field(default_factory=GameContext)


@dataclass
class Prediction:
    p_home_win: float
    predicted_home_margin: float
    margin_std: float
    total_expected_points: float
    model_version: str = "nfl-v1.0"
    feature_breakdown: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 1 — Elo / EPA prior
# ---------------------------------------------------------------------------
def _elo_expected_margin(home_elo: float, away_elo: float,
                         hca: float = 2.0) -> float:
    """Classic Elo-to-margin: margin_points ≈ (rating_diff / 25) + HCA."""
    return (home_elo - away_elo) / 25.0 + hca


def _epa_based_margin(home: TeamPowerRating, away: TeamPowerRating) -> float:
    """Margin from weighted EPA using nfelo's 1.6-offense/1.0-defense weights.
    An average game has ~65 plays/side.  EPA units are points, so margin =
    (home off − away def) × 1.6 + (home def − away off) × 1.0 ... no,
    more precisely: marginPts ≈ 65 × (home_off_epa - away_def_epa) +
                              65 × (away_off_epa - home_def_epa) × -1.
    """
    home_off_vs_away_def = home.off_epa_per_play_season - away.def_epa_per_play_season
    away_off_vs_home_def = away.off_epa_per_play_season - home.def_epa_per_play_season
    home_margin_est = 65.0 * (1.6 * home_off_vs_away_def / 2.6) + 65.0 * (-1.0 * away_off_vs_home_def / 2.6)
    return home_margin_est


# ---------------------------------------------------------------------------
# Stage 2 — QB adjustments
# ---------------------------------------------------------------------------
def _qb_adjustment(home_qb: QBInfo, away_qb: QBInfo) -> float:
    """Return home_margin points attributable to QB differential.
    Backup-QB penalty: 3-6 pts depending on whether the replacement has
    meaningful NFL sample."""
    def qb_quality_score(qb: QBInfo) -> float:
        if qb.passes_observed < 50:
            # no sample; return team priors
            return 0.0
        # CPOE in % -> each 1% of CPOE ~ 0.5 pts/game
        # EPA/play -> each 0.05 EPA/play ~ 1 pt/game
        return qb.cpoe * 0.5 + qb.epa_per_play * 20.0

    home_q = qb_quality_score(home_qb)
    away_q = qb_quality_score(away_qb)
    # Backup-QB penalty on top
    if home_qb.is_injury_replacement:
        home_q -= 4.0
    if away_qb.is_injury_replacement:
        away_q -= 4.0
    return home_q - away_q


# ---------------------------------------------------------------------------
# Stage 3 — situational
# ---------------------------------------------------------------------------
def _situational_adjustment(m: MatchupInputs) -> float:
    pts = 0.0
    ctx = m.context
    # Short rest (Thursday) favors slightly home, slightly more hurt road
    if ctx.is_thursday_night:
        pts += 0.5
    # Rest-day difference
    rest_diff = ctx.home_rest_days - ctx.away_rest_days
    pts += 0.3 * rest_diff
    # Playoff games → home-field matters less (better teams, closer matchups)
    if ctx.is_playoff:
        pts -= 0.5
    # Weather
    if not ctx.is_dome:
        # Wind > 15 mph suppresses passing by ~ 0.5 pts per 5mph over threshold
        if ctx.wind_mph > 15:
            pts -= (ctx.wind_mph - 15) * 0.1 * _relative_pass_dependence(m)
        # Cold temps (<32F) suppress scoring slightly
        if ctx.temp_f < 32:
            pts -= 0.5
        # Precipitation reduces scoring ~ 1 pt per inch
        pts -= ctx.precipitation * 1.0
    # Altitude
    if ctx.altitude_feet > 4000 and not ctx.is_neutral_site:
        pts += 0.5
    return pts


def _relative_pass_dependence(m: MatchupInputs) -> float:
    """Return 1.0 for "average" passing teams; higher for pass-heavy offenses.
    Used to scale weather-impact on pass-heavy vs. run-heavy teams."""
    # crude: based on off_success_rate and off_epa; placeholder
    return 1.0


# ---------------------------------------------------------------------------
# Stage 4 — predict
# ---------------------------------------------------------------------------
def predict(m: MatchupInputs, margin_std: float = 13.5) -> Prediction:
    """NFL margin std historically ~13.5 pts.  Slightly tighter in playoffs."""
    elo_m = _elo_expected_margin(m.home_team.elo, m.away_team.elo)
    epa_m = _epa_based_margin(m.home_team, m.away_team)
    # Blend elo-derived margin and EPA-derived margin; elo is more stable early
    # season, EPA is more responsive to current form.
    base_margin = 0.55 * elo_m + 0.45 * epa_m
    qb_adj = _qb_adjustment(m.home_qb, m.away_qb)
    sit_adj = _situational_adjustment(m)
    margin = base_margin + qb_adj + sit_adj

    z = margin / margin_std
    p = _phi(z)
    p = max(0.02, min(0.98, p))

    # Rough total-points estimate via off/def EPA aggregates
    total_epa = (m.home_team.off_epa_per_play_season + m.away_team.off_epa_per_play_season
                 - m.home_team.def_epa_per_play_season - m.away_team.def_epa_per_play_season)
    total_pts = 43.0 + total_epa * 30  # league avg total ~43.5

    return Prediction(
        p_home_win=p,
        predicted_home_margin=margin,
        margin_std=margin_std,
        total_expected_points=total_pts,
        feature_breakdown={
            "elo_margin": elo_m,
            "epa_margin": epa_m,
            "qb_adj": qb_adj,
            "situational_adj": sit_adj,
            "home_elo": m.home_team.elo,
            "away_elo": m.away_team.elo,
        },
    )


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


# ---------------------------------------------------------------------------
# Playoff Monte Carlo (single-elim tournament)
# ---------------------------------------------------------------------------
def simulate_playoff_tournament(bracket: list[dict], n_sims: int = 10000, seed: int = 0) -> dict:
    """bracket: list of rounds; each round is list of matchup descriptors with
    indices into a teams array and per-matchup p_home_win values.

    Returns championship probability per team."""
    import random
    rng = random.Random(seed)
    # This is a scaffold; in practice, build a function that takes the full
    # bracket structure (AFC/NFC seeded) and simulates each round.
    return {"n_sims": n_sims, "note": "bracket simulation TODO — plugs into simulate_series for series sports"}


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    m = MatchupInputs(
        home_team=TeamPowerRating("KC", elo=1660.0, off_epa_per_play_season=0.12,
                                  def_epa_per_play_season=-0.02,
                                  off_success_rate=0.50, def_success_rate=0.42),
        away_team=TeamPowerRating("DEN", elo=1480.0, off_epa_per_play_season=0.02,
                                  def_epa_per_play_season=0.01,
                                  off_success_rate=0.44, def_success_rate=0.46),
        home_qb=QBInfo("mahomes", "Mahomes", cpoe=4.5, epa_per_play=0.22, passes_observed=500),
        away_qb=QBInfo("DEN_QB", "Backup", cpoe=-1.0, epa_per_play=-0.03, passes_observed=80),
        context=GameContext(is_division_game=True, temp_f=28, wind_mph=18, precipitation=0.2),
    )
    pred = predict(m)
    print("KC vs. DEN @ Arrowhead, cold & windy")
    print(f"  P(home win) = {pred.p_home_win:.3f}")
    print(f"  margin      = {pred.predicted_home_margin:.2f}")
    print(f"  total pts   = {pred.total_expected_points:.1f}")
    print(f"  breakdown   = {pred.feature_breakdown}")
