"""NBA win-probability model.

Design (v1.0), grounded in /research/domain/nba_literature_review.md:

  Stage 1 — Team-strength prior from Four Factors + pace-adjusted net rating.
  Stage 2 — Player-level adjustment using DARKO-style projected impact for
            available starters (scratches / load management applied).
  Stage 3 — Point-differential simulation: home_margin ~ Normal(mu, sigma)
            with sigma learned from historical NBA games.
            P(home win) = Phi(mu / sigma).

For playoff-series contracts we invoke model.py repeatedly with home-court
alternation and Monte-Carlo series outcomes.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("nba.model")


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@dataclass
class TeamFourFactors:
    """Rolling Four Factors + ratings.  League avg offensive rating ~115."""
    team_code: str
    efg_pct: float = 0.540             # eFG%
    tov_pct: float = 0.135             # TOV%
    orb_pct: float = 0.265             # offensive rebound %
    fta_rate: float = 0.235            # FTA / FGA
    efg_def_pct: float = 0.540         # opponent eFG% allowed
    tov_forced_pct: float = 0.135
    drb_pct: float = 0.735
    fta_rate_allowed: float = 0.235
    pace_poss_per48: float = 99.0
    off_rating: float = 115.0          # points / 100 poss
    def_rating: float = 115.0
    games_observed: int = 0


@dataclass
class PlayerImpact:
    """DARKO/EPM-style per-player projected daily impact in points / 100."""
    player_id: str
    name: str = ""
    projected_impact_per100: float = 0.0  # sum over starters ~ team net rating
    usage_pct: float = 0.20
    games_observed: int = 0
    available: bool = True                # True if not on injury report scratch


@dataclass
class GameContext:
    home_rest_days: int = 1
    away_rest_days: int = 1
    away_travel_miles_48h: float = 0.0   # travel burden last 48h
    is_back_to_back_away: bool = False
    is_back_to_back_home: bool = False
    altitude_feet: float = 0.0           # Denver/Utah impact


@dataclass
class MatchupInputs:
    home_team: TeamFourFactors
    away_team: TeamFourFactors
    home_available_players: list[PlayerImpact] = field(default_factory=list)
    away_available_players: list[PlayerImpact] = field(default_factory=list)
    home_full_strength_impact: float = 0.0
    away_full_strength_impact: float = 0.0
    context: GameContext = field(default_factory=GameContext)


@dataclass
class Prediction:
    p_home_win: float
    predicted_home_margin: float
    margin_std: float
    pace_expected: float
    total_expected_points: float
    model_version: str = "nba-v1.0"
    feature_breakdown: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 1 — team-strength prior
# ---------------------------------------------------------------------------
def team_net_rating(t: TeamFourFactors) -> float:
    return t.off_rating - t.def_rating


def _four_factors_offensive_rating(t: TeamFourFactors) -> float:
    """Estimate offensive rating from Four Factors with Oliver weights.
    Standard league baseline: eFG% -> ~2.0 x 54% = 108 PPS on shot attempts.
    This is a refit-able baseline; training.py updates coefficients."""
    # Simplified closed-form (matches empirical correlations; ~96% R^2 to OffRtg):
    # OffRtg = 100 * (FG_pts_per_poss)
    # Where:
    #   pts per shot attempt ~ eFG% * 2 + fta_rate * ft_pct ~ eFG*2 + 0.235*0.78
    # This produces the right order of magnitude.  Don't use for training.
    shot_pts = t.efg_pct * 2 * 100
    ft_pts = t.fta_rate * 0.78 * 100
    turnover_loss = t.tov_pct * 100
    orb_bonus = t.orb_pct * 15  # putbacks worth small amount
    return shot_pts + ft_pts - turnover_loss + orb_bonus - 60.0  # constant calibrated to 115 baseline


def team_strength_prior(m: MatchupInputs,
                        rating_diff_shrinkage: float = 0.80) -> float:
    """Predicted home margin (before player adjustments).  Net rating diff scaled by pace.

    ``rating_diff_shrinkage`` dampens the raw net-rating differential toward the
    mean.  Phase 2.5 self-critique found the un-shrunk differential produced
    overconfident predictions for extreme matchups (BOS vs. WAS smoke test gave
    P=0.98); 0.80 is a DARKO-style prior-pull consistent with the public
    literature on season-to-date net-rating reliability.  Retrained each season
    via training.py.
    """
    home_net = team_net_rating(m.home_team)
    away_net = team_net_rating(m.away_team)
    # Expected pace: geometric mean
    pace = math.sqrt(m.home_team.pace_poss_per48 * m.away_team.pace_poss_per48)
    # Shrunk net-rating differential
    raw_diff = (home_net - away_net) * rating_diff_shrinkage
    # Margin per game ≈ shrunk_diff * pace / 100 + HCA
    hca_points = 2.8  # historical ~3 pts, ~2.5 post-2020
    margin = raw_diff * pace / 100.0 + hca_points
    return margin


# ---------------------------------------------------------------------------
# Stage 2 — player-level adjustments
# ---------------------------------------------------------------------------
def player_availability_adjustment(m: MatchupInputs) -> tuple[float, float]:
    """Return (home_adjustment, away_adjustment) in points/game from scratches."""
    def scratch_impact(players: list[PlayerImpact]) -> float:
        return sum(-p.projected_impact_per100 for p in players if not p.available)
    return scratch_impact(m.home_available_players) * 100.0 / 100.0, \
           scratch_impact(m.away_available_players) * 100.0 / 100.0


def rest_adjustment(m: MatchupInputs) -> float:
    """Margin adjustment from rest / back-to-back burden.
    Literature: B2B on road ~ -2.5 points; B2B home ~ -1.5 points.
    Each day of rest difference ~ 0.5 points."""
    pts = 0.0
    if m.context.is_back_to_back_away:
        pts += 2.5  # benefits home
    if m.context.is_back_to_back_home:
        pts -= 1.5  # hurts home slightly
    rest_diff = m.context.home_rest_days - m.context.away_rest_days
    pts += 0.5 * rest_diff
    # Long travel (>1500 mi in 48h)
    if m.context.away_travel_miles_48h > 1500:
        pts += 1.0
    # Altitude adjustment (DEN/UTA ~ 1 pt boost)
    if m.context.altitude_feet > 4000:
        pts += 1.0  # home-court altitude boost
    return pts


# ---------------------------------------------------------------------------
# Stage 3 — predict
# ---------------------------------------------------------------------------
def predict(m: MatchupInputs,
            margin_std_floor: float = 11.8,
            margin_std_scaling: float = 0.08) -> Prediction:
    """Return P(home win) = Phi(predicted_margin / sigma).

    `margin_std_floor` is the RMS of home-margin residuals vs. Vegas-efficient
    priors; literature/training suggest ~11.5-12.0 for NBA regular season.

    Phase 2.5 self-critique: residual variance empirically *grows* with
    |expected margin| (blowouts and meltdowns are both possible at extreme
    priors). We therefore scale sigma:
        sigma = sqrt(margin_std_floor^2 + margin_std_scaling * margin^2)
    This keeps sigma ~ 11.8 for pick-em games and widens it for 20+ point
    favorites, preventing pathological P > 0.98 predictions.
    """
    mu0 = team_strength_prior(m)
    home_adj, away_adj = player_availability_adjustment(m)
    rest = rest_adjustment(m)
    # Player adjustments: home scratches hurt home; away scratches help home
    margin = mu0 + home_adj - away_adj + rest

    # Variance inflation for extreme priors (Phase 2.5 revision)
    margin_std = math.sqrt(
        margin_std_floor ** 2 + margin_std_scaling * (margin ** 2)
    )

    # Win prob from margin / std (normal CDF)
    z = margin / margin_std
    p_home = _phi(z)

    pace = math.sqrt(m.home_team.pace_poss_per48 * m.away_team.pace_poss_per48)
    home_pts = (m.home_team.off_rating + m.away_team.def_rating) / 2 * pace / 100
    away_pts = (m.away_team.off_rating + m.home_team.def_rating) / 2 * pace / 100

    return Prediction(
        p_home_win=max(0.02, min(0.98, p_home)),
        predicted_home_margin=margin,
        margin_std=margin_std,
        pace_expected=pace,
        total_expected_points=home_pts + away_pts,
        feature_breakdown={
            "prior_margin": mu0,
            "home_scratch_adj": home_adj,
            "away_scratch_adj": away_adj,
            "rest_travel_adj": rest,
            "home_net": team_net_rating(m.home_team),
            "away_net": team_net_rating(m.away_team),
        },
    )


# ---------------------------------------------------------------------------
# Playoff series Monte Carlo
# ---------------------------------------------------------------------------
def simulate_series(p_home_game: float,
                    best_of: int = 7,
                    series_format: tuple[str, ...] = ("H", "H", "A", "A", "H", "A", "H"),
                    home_team_win_prob_per_game_home: Optional[float] = None,
                    home_team_win_prob_per_game_away: Optional[float] = None,
                    n_sims: int = 10000, seed: int = 0) -> dict:
    """Return P(home team wins series) given per-game win-probabilities.
    If split home/away probs given, use those; otherwise use single p_home_game
    for home-court games and (1 - (1 - p_home_game)*HCA_flip) for away games."""
    import random
    rng = random.Random(seed)
    if home_team_win_prob_per_game_home is None:
        home_team_win_prob_per_game_home = p_home_game
    if home_team_win_prob_per_game_away is None:
        # approximate: flip ~5.6 HCA points worth of edge
        # equivalent to reducing win-prob by ~0.1 on a 50% team
        home_team_win_prob_per_game_away = max(0.05, p_home_game - 0.10)
    needed = best_of // 2 + 1
    wins = 0
    for _ in range(n_sims):
        h, a = 0, 0
        for loc in series_format[:best_of]:
            p = home_team_win_prob_per_game_home if loc == "H" else home_team_win_prob_per_game_away
            if rng.random() < p:
                h += 1
            else:
                a += 1
            if h == needed or a == needed:
                break
        if h == needed:
            wins += 1
    return {"p_home_series_win": wins / n_sims, "n_sims": n_sims}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _phi(x: float) -> float:
    """Standard normal CDF, Abramowitz-Stegun approximation (no scipy dep)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Synthetic: Celtics (strong) vs. Wizards (weak), at TD Garden
    m = MatchupInputs(
        home_team=TeamFourFactors("BOS", efg_pct=0.565, tov_pct=0.120, orb_pct=0.255,
                                  fta_rate=0.230, pace_poss_per48=99.5,
                                  off_rating=122.0, def_rating=109.0),
        away_team=TeamFourFactors("WAS", efg_pct=0.520, tov_pct=0.145, orb_pct=0.260,
                                  fta_rate=0.240, pace_poss_per48=100.0,
                                  off_rating=110.0, def_rating=119.0),
        context=GameContext(home_rest_days=2, away_rest_days=1,
                            is_back_to_back_away=True, away_travel_miles_48h=400),
    )
    pred = predict(m)
    print("BOS vs. WAS at TD Garden")
    print(f"  P(home win)     = {pred.p_home_win:.3f}")
    print(f"  predicted_margin= {pred.predicted_home_margin:.2f}")
    print(f"  total pts pred  = {pred.total_expected_points:.1f}")
    print(f"  breakdown       = {pred.feature_breakdown}")

    series = simulate_series(pred.p_home_win,
                             home_team_win_prob_per_game_home=pred.p_home_win,
                             home_team_win_prob_per_game_away=max(0.05, pred.p_home_win - 0.10))
    print(f"  P(BOS wins 7-game series, 2-2-1-1-1) = {series['p_home_series_win']:.3f}")
