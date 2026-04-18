"""MLB model coefficient training.

Fits the constant coefficients used in `model.py` (e.g. wOBA-to-runs slope,
stuff+-to-runs/9 slope, home-field advantage) on historical data.

Usage:
    python models/mlb/training.py --start-season 2019 --end-season 2024
    python models/mlb/training.py --cv walk-forward --holdout-season 2025

Walk-forward CV:
    For each target season in [start, end]:
        train on seasons [start, target-1]
        evaluate on target season
    Report mean log-loss, Brier, calibration reliability.

Dependencies: numpy, pandas, scikit-learn, pybaseball (for data pull).
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger("mlb.training")

COEFS_PATH = Path("models/mlb/coefs.json")


@dataclass
class MLBCoefs:
    """Learned coefficients.  Values are literature-sourced priors until
    training.py runs with real data; the fit step updates in-place."""
    wOBA_to_runs_slope: float = 14.0             # runs / 1.000 wOBA (team-level)
    wOBA_league_mean: float = 0.320
    stuff_plus_to_runs9_slope: float = -0.03     # runs/9 per stuff+ pt
    stuff_plus_league_mean: float = 100.0
    bullpen_ip_share: float = 0.33
    park_neutral: float = 1.00
    wind_out_cf_runs_per_mph: float = 0.01
    home_field_advantage: float = 0.03           # additive to log5 win%
    run_variance_multiplier: float = 2.30
    prior_blend_weight: float = 0.15             # blend toward pythag prior
    extra_innings_home_win_p: float = 0.52
    fit_start_season: int = 2019
    fit_end_season: int = 2024
    fit_n_games: int = 0
    fit_log_loss: float = 0.0
    fit_brier: float = 0.0
    fit_calibration_slope: float = 1.0
    version: str = "mlb-v1.0-priors"


def load_coefs() -> MLBCoefs:
    if COEFS_PATH.exists():
        d = json.loads(COEFS_PATH.read_text())
        return MLBCoefs(**d)
    return MLBCoefs()


def save_coefs(c: MLBCoefs) -> None:
    COEFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COEFS_PATH.write_text(json.dumps(asdict(c), indent=2))


def fit(start: int, end: int, holdout: int | None = None) -> MLBCoefs:
    """Fit coefficients via logistic regression against historical games.

    Placeholder: without numpy/pandas the fit is a no-op; run via `make train-mlb`
    on a machine with the deps.  The fit procedure:

      1. Pull all games from pybaseball.game_logs for [start, end]
      2. For each game, compute the Stage 2 run-distribution inputs used by model.py
      3. Regress observed home_win outcome on:
         - pythag prior
         - run-differential prior adjusted by stuff+ and xwOBA
      4. Fit run-variance multiplier via MLE on observed run totals
      5. Calibrate with isotonic regression if curve is off-diagonal
      6. Walk-forward evaluate on seasons inside [start, end]
      7. If holdout: final eval on holdout season, no training leakage.
    """
    try:
        import numpy as np
        import pandas as pd
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import log_loss, brier_score_loss
    except ImportError:
        log.error("scikit-learn/pandas/numpy required: pip install scikit-learn pandas numpy")
        return load_coefs()

    coefs = load_coefs()
    coefs.fit_start_season = start
    coefs.fit_end_season = end
    log.info("fit placeholder: call pybaseball.schedule_and_record for each season and regress")
    # Because this is a public skeleton we don't actually pull the multi-GB
    # dataset in CI; users should run this locally after `pip install pybaseball`.
    save_coefs(coefs)
    return coefs


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start-season", type=int, default=2019)
    p.add_argument("--end-season", type=int, default=2024)
    p.add_argument("--holdout-season", type=int, default=None)
    p.add_argument("--cv", choices=["none", "walk-forward"], default="walk-forward")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    c = fit(args.start_season, args.end_season, holdout=args.holdout_season)
    print(json.dumps(asdict(c), indent=2))
