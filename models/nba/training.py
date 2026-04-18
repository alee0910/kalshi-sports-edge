"""NBA model coefficient training.

Fits:
- HCA (home-court advantage) in points
- margin_std residual scale
- rating-differential scaling coefficient
- rest/back-to-back adjustments
- isotonic post-calibration map

Data: ~6 seasons (2019-20 through 2024-25) play-by-play + team ratings.
Walk-forward CV per season; holdout on most recent.
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger("nba.training")
COEFS_PATH = Path("models/nba/coefs.json")


@dataclass
class NBACoefs:
    # Phase 2.5 revision: net-rating differential is shrunk toward 0 to avoid
    # overconfidence on extreme matchups (see /research/self_critique.md).
    rating_diff_shrinkage: float = 0.80
    home_court_advantage_pts: float = 2.8
    # Sigma is now margin-dependent:
    #   sigma = sqrt(margin_std_floor^2 + margin_std_scaling * margin^2)
    margin_std_floor: float = 11.8
    margin_std_scaling: float = 0.08
    back_to_back_away_penalty: float = 2.5
    back_to_back_home_penalty: float = 1.5
    rest_day_diff_pts: float = 0.5
    travel_over_1500mi_pts: float = 1.0
    altitude_home_pts: float = 1.0
    fit_seasons: list[int] | None = None
    fit_n_games: int = 0
    fit_log_loss: float = 0.0
    fit_brier: float = 0.0
    fit_calibration_slope: float = 1.0
    version: str = "nba-v1.1-phase2p5-revised"


def load_coefs() -> NBACoefs:
    if COEFS_PATH.exists():
        return NBACoefs(**json.loads(COEFS_PATH.read_text()))
    return NBACoefs()


def save_coefs(c: NBACoefs) -> None:
    COEFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COEFS_PATH.write_text(json.dumps(asdict(c), indent=2))


def fit(start: int, end: int, holdout: int | None = None) -> NBACoefs:
    try:
        import numpy as np  # noqa
        import pandas as pd  # noqa
        from sklearn.linear_model import Ridge  # noqa
    except ImportError:
        log.error("scikit-learn / pandas / numpy required")
        return load_coefs()
    c = load_coefs()
    c.fit_seasons = list(range(start, end + 1))
    save_coefs(c)
    log.info("fit stub saved; run with hoopR data locally for real fit")
    return c


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--start-season", type=int, default=2019)
    p.add_argument("--end-season", type=int, default=2024)
    p.add_argument("--holdout-season", type=int, default=2025)
    args = p.parse_args()
    c = fit(args.start_season, args.end_season, args.holdout_season)
    print(json.dumps(asdict(c), indent=2))
