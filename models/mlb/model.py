"""MLB win-probability model.

Two-stage approach per /research/domain/mlb_literature_review.md §5:

  Stage 1 — Team-strength prior (pythagenpat + log5 form).
  Stage 2 — Per-matchup adjustment using frontier features (Stuff+, xwOBA, park, catcher framing).
  Stage 3 — Monte Carlo series / futures simulation using per-game probabilities.

This is the v1 public skeleton.  Training is parametric with coefficient values
either derived from literature (wOBA-to-runs linear weights) or fit via
`training.py` on cached historical data.  In practice we will retrain monthly;
this file exposes the structured interface the scanner calls for each live
game.
"""
from __future__ import annotations

import math
import logging
import random
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("mlb.model")


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass
class TeamSeasonStats:
    """Rolling team-level offense/defense inputs."""
    team_code: str
    xwoba_vs_LHP: float = 0.320
    xwoba_vs_RHP: float = 0.320
    wrc_plus: float = 100.0
    k_rate: float = 0.22
    bb_rate: float = 0.085
    barrel_rate: float = 0.075
    oaa_per_game: float = 0.0           # Outs above average, per game
    framing_runs_per_game: float = 0.0
    drs_per_game: float = 0.0
    pa_observed: int = 0                # for shrinkage


@dataclass
class PitcherStats:
    """Frontier-weighted pitcher inputs. stuff_plus is primary signal."""
    pitcher_id: str
    stuff_plus: Optional[float] = None   # 100 = league average; 110 = one SD better
    pitching_plus: Optional[float] = None
    siera: Optional[float] = None        # if stuff_plus missing
    xfip: Optional[float] = None
    k_rate: float = 0.22
    bb_rate: float = 0.08
    throws: str = "R"
    pitches_observed: int = 0
    workload_pitches_7d: int = 0


@dataclass
class BullpenStats:
    stuff_plus_weighted: Optional[float] = None
    siera_weighted: float = 4.00
    innings_last_3d: float = 0.0
    lead_leverage_k_rate: float = 0.22


@dataclass
class GameContext:
    park_factor: float = 1.00            # 1.00 = neutral offensive output
    park_hr_factor_L: float = 1.00
    park_hr_factor_R: float = 1.00
    temp_f: float = 70.0
    wind_out_cf_mph: float = 0.0
    humidity_pct: float = 50.0
    ump_strike_zone_index: float = 1.00  # 1.00 = neutral; 1.02 = pitcher-friendly
    home_rest_days: int = 1
    away_rest_days: int = 1


@dataclass
class TeamPrior:
    """Season-to-date strength used for Stage 1 baseline."""
    runs_scored: int
    runs_allowed: int
    games_played: int
    recent_form_w: int = 0               # last 20 games
    recent_form_l: int = 0

    @property
    def pythagenpat_win_pct(self) -> float:
        if self.games_played < 5 or (self.runs_scored + self.runs_allowed) == 0:
            return 0.500
        # pythagenpat exponent: ((RS+RA)/G)^0.287
        exp = ((self.runs_scored + self.runs_allowed) / self.games_played) ** 0.287
        rs, ra = float(self.runs_scored), float(self.runs_allowed)
        return rs ** exp / (rs ** exp + ra ** exp)


@dataclass
class MatchupInputs:
    home_team: TeamSeasonStats
    away_team: TeamSeasonStats
    home_pitcher: PitcherStats
    away_pitcher: PitcherStats
    home_bullpen: BullpenStats
    away_bullpen: BullpenStats
    home_prior: TeamPrior
    away_prior: TeamPrior
    context: GameContext = field(default_factory=GameContext)


@dataclass
class Prediction:
    p_home_win: float
    p_home_win_std: float               # monte carlo sampling error
    runs_home_mean: float
    runs_away_mean: float
    runs_home_std: float
    runs_away_std: float
    model_version: str = "mlb-v1.0"
    feature_breakdown: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 1 — prior from pythagenpat + log5
# ---------------------------------------------------------------------------
def _log5(p_a: float, p_b: float) -> float:
    """Log5 formula for win prob of A over B given both teams' win%."""
    num = p_a - p_a * p_b
    den = p_a + p_b - 2 * p_a * p_b
    if den <= 0:
        return 0.5
    return max(0.01, min(0.99, num / den))


def team_strength_prior(m: MatchupInputs) -> float:
    """log5 of pythagenpat win%, adjusted for home-field (historic ~54%)."""
    p_home = m.home_prior.pythagenpat_win_pct
    p_away = m.away_prior.pythagenpat_win_pct
    raw = _log5(p_home, p_away)
    # Home field adjustment (MLB ~0.54 historical, now ~0.52 post-robot umps)
    hfa = 0.03
    p = raw * (1 - hfa) + (raw + hfa * (1 - raw)) * hfa  # simple monotone lift
    return max(0.02, min(0.98, p * (1 - hfa) + hfa))


# ---------------------------------------------------------------------------
# Stage 2 — adjust for pitcher / defense / context
# ---------------------------------------------------------------------------
def _effective_stuff_plus(p: PitcherStats) -> float:
    """Return pitcher quality on a 100=avg scale, backfilling from SIERA if
    stuff_plus missing.  Apply shrinkage if sample is small."""
    if p.stuff_plus is not None and p.pitches_observed >= 80:
        # Shrink toward 100 at small N
        w = min(1.0, p.pitches_observed / 400.0)
        return w * p.stuff_plus + (1 - w) * 100.0
    # Fallback: map SIERA to stuff_plus-equivalent scale.
    # SIERA 3.00 ~ 120, SIERA 4.00 ~ 100, SIERA 5.00 ~ 80.
    if p.siera is not None:
        return max(60.0, min(140.0, 100.0 + (4.0 - p.siera) * 20.0))
    return 100.0


def _pitcher_runs_allowed_adjustment(stuff_plus: float) -> float:
    """Convert stuff+ to runs/9 adjustment vs. league avg ~4.3 r/9.
    Each 10 pts of stuff+ ≈ 0.3 runs/9 (very rough; will refit)."""
    return -0.03 * (stuff_plus - 100.0)  # negative means better pitcher = fewer runs


def _team_run_rate(t: TeamSeasonStats, opposing_pitcher_throws: str) -> float:
    """Translate xwOBA to expected runs per game. League avg xwOBA ~0.320 → ~4.3 r/g."""
    xwoba = t.xwoba_vs_LHP if opposing_pitcher_throws == "L" else t.xwoba_vs_RHP
    # Each .010 of wOBA ≈ 0.14 runs/game (team-level, Tango linear weights scaled).
    return 4.30 + (xwoba - 0.320) * 14.0


def _runs_distribution_params(m: MatchupInputs) -> tuple[float, float, float, float]:
    """Return (home_mean, home_std, away_mean, away_std) runs per game."""
    # Baseline run rates
    home_off_rate = _team_run_rate(m.home_team, m.away_pitcher.throws)
    away_off_rate = _team_run_rate(m.away_team, m.home_pitcher.throws)

    # Pitcher adjustments
    home_sp = _effective_stuff_plus(m.home_pitcher)
    away_sp = _effective_stuff_plus(m.away_pitcher)
    away_off_rate += _pitcher_runs_allowed_adjustment(home_sp)
    home_off_rate += _pitcher_runs_allowed_adjustment(away_sp)

    # Bullpen adjustments (approx 1/3 of innings)
    if m.home_bullpen.stuff_plus_weighted is not None:
        away_off_rate += _pitcher_runs_allowed_adjustment(m.home_bullpen.stuff_plus_weighted) * 0.33
    if m.away_bullpen.stuff_plus_weighted is not None:
        home_off_rate += _pitcher_runs_allowed_adjustment(m.away_bullpen.stuff_plus_weighted) * 0.33

    # Defense (OAA + framing)
    home_def_runs = m.home_team.oaa_per_game * 0.8 + m.home_team.framing_runs_per_game
    away_def_runs = m.away_team.oaa_per_game * 0.8 + m.away_team.framing_runs_per_game
    away_off_rate -= home_def_runs
    home_off_rate -= away_def_runs

    # Park
    home_off_rate *= m.context.park_factor
    away_off_rate *= m.context.park_factor

    # Weather: +15 mph out to CF → +10% HR → +~0.15 r/g
    wind_bonus = 0.01 * m.context.wind_out_cf_mph  # per mph
    home_off_rate += wind_bonus
    away_off_rate += wind_bonus

    # Umpire (tight zone benefits hitters)
    ump_adj = (1.0 - m.context.ump_strike_zone_index) * 0.4
    home_off_rate += ump_adj
    away_off_rate += ump_adj

    # Floor at 1 r/g to keep simulation well-posed
    home_off_rate = max(1.0, home_off_rate)
    away_off_rate = max(1.0, away_off_rate)

    # Run std is empirically ~sqrt(mean * 2.3) in MLB (Negative-binomial-ish)
    home_std = math.sqrt(home_off_rate * 2.3)
    away_std = math.sqrt(away_off_rate * 2.3)
    return home_off_rate, home_std, away_off_rate, away_std


# ---------------------------------------------------------------------------
# Stage 3 — Monte Carlo
# ---------------------------------------------------------------------------
def _sim_game(home_mean: float, home_std: float,
              away_mean: float, away_std: float,
              rng: random.Random) -> int:
    """Return 1 if home wins, 0 if away wins.  Negative-binomial-ish via
    rounded gamma-approx for runs-per-game."""
    # Use log-normal as a cheap right-skewed positive dist; it's not perfect
    # but matches the literature's observation that run distributions are
    # right-skewed (see /research/domain/mlb_literature_review.md §5).
    sigma_h = math.sqrt(math.log(1 + (home_std / max(0.5, home_mean)) ** 2))
    mu_h = math.log(max(0.5, home_mean)) - 0.5 * sigma_h ** 2
    sigma_a = math.sqrt(math.log(1 + (away_std / max(0.5, away_mean)) ** 2))
    mu_a = math.log(max(0.5, away_mean)) - 0.5 * sigma_a ** 2
    h = max(0, round(rng.lognormvariate(mu_h, sigma_h)))
    a = max(0, round(rng.lognormvariate(mu_a, sigma_a)))
    if h == a:
        # Extra innings coin-flip biased slightly toward home (~52%)
        return 1 if rng.random() < 0.52 else 0
    return 1 if h > a else 0


def predict(m: MatchupInputs, n_sims: int = 10000, seed: int = 0,
            blend_prior: float = 0.15) -> Prediction:
    """Run stage 1-3 and return a calibrated probability."""
    rng = random.Random(seed)

    # Stage 1 prior
    p_prior = team_strength_prior(m)

    # Stage 2 → MC
    hm, hs, am, as_ = _runs_distribution_params(m)
    wins = 0
    for _ in range(n_sims):
        wins += _sim_game(hm, hs, am, as_, rng)
    p_sim = wins / n_sims
    std = math.sqrt(p_sim * (1 - p_sim) / n_sims)

    # Blend Stage 2 MC with Stage 1 prior to avoid overfitting on single-game features
    p = (1 - blend_prior) * p_sim + blend_prior * p_prior
    p = max(0.02, min(0.98, p))

    return Prediction(
        p_home_win=p,
        p_home_win_std=std,
        runs_home_mean=hm, runs_home_std=hs,
        runs_away_mean=am, runs_away_std=as_,
        feature_breakdown={
            "p_prior": p_prior,
            "p_sim": p_sim,
            "home_sp_effective_stuff_plus": _effective_stuff_plus(m.home_pitcher),
            "away_sp_effective_stuff_plus": _effective_stuff_plus(m.away_pitcher),
            "park_factor": m.context.park_factor,
            "wind_mph_out_cf": m.context.wind_out_cf_mph,
        },
    )


# ---------------------------------------------------------------------------
# Example / smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Synthetic: strong home team (Dodgers-like), weak away team (Rockies-like)
    m = MatchupInputs(
        home_team=TeamSeasonStats("LAD", xwoba_vs_LHP=0.340, xwoba_vs_RHP=0.345,
                                  wrc_plus=120, oaa_per_game=0.12,
                                  framing_runs_per_game=0.10),
        away_team=TeamSeasonStats("COL", xwoba_vs_LHP=0.290, xwoba_vs_RHP=0.295,
                                  wrc_plus=80, oaa_per_game=-0.10,
                                  framing_runs_per_game=-0.08),
        home_pitcher=PitcherStats("LAD-SP", stuff_plus=118.0, pitches_observed=500,
                                  throws="R", siera=2.90),
        away_pitcher=PitcherStats("COL-SP", stuff_plus=95.0, pitches_observed=500,
                                  throws="R", siera=4.30),
        home_bullpen=BullpenStats(stuff_plus_weighted=110.0),
        away_bullpen=BullpenStats(stuff_plus_weighted=97.0),
        home_prior=TeamPrior(runs_scored=440, runs_allowed=310, games_played=80),
        away_prior=TeamPrior(runs_scored=340, runs_allowed=450, games_played=80),
        context=GameContext(park_factor=0.95, wind_out_cf_mph=2.0),
    )
    pred = predict(m, n_sims=5000)
    print(f"Dodgers vs. Rockies @ Dodger Stadium")
    print(f"  P(home win)   = {pred.p_home_win:.3f} ± {pred.p_home_win_std:.3f}")
    print(f"  Runs home/away= {pred.runs_home_mean:.2f} / {pred.runs_away_mean:.2f}")
    print(f"  Breakdown     = {pred.feature_breakdown}")
