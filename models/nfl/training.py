"""NFL training. Walk-forward Elo + coefficient refit.

Fits:
- Elo K-factor (margin-of-victory multiplier)
- Initial ratings and QB-adjustment scale
- HCA in points (currently ~2.0)
- margin_std (residual)
- isotonic post-calibration
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger("nfl.training")
COEFS_PATH = Path("models/nfl/coefs.json")


@dataclass
class NFLCoefs:
    elo_k_factor: float = 20.0
    elo_mov_multiplier_a: float = 2.2
    elo_mov_multiplier_b: float = 0.001
    off_epa_weight: float = 1.6
    def_epa_weight: float = 1.0
    home_court_advantage_pts: float = 2.0
    margin_std_regular: float = 13.5
    margin_std_playoff: float = 12.5
    backup_qb_penalty_pts: float = 4.0
    cpoe_pt_per_pct: float = 0.5
    qb_epa_pt_per_0p05: float = 1.0
    wind_mph_threshold: float = 15.0
    temp_threshold_f: float = 32.0
    fit_log_loss: float = 0.0
    fit_brier: float = 0.0
    fit_calibration_slope: float = 1.0
    version: str = "nfl-v1.0-priors"


def load_coefs() -> NFLCoefs:
    if COEFS_PATH.exists():
        return NFLCoefs(**json.loads(COEFS_PATH.read_text()))
    return NFLCoefs()


def save_coefs(c: NFLCoefs) -> None:
    COEFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COEFS_PATH.write_text(json.dumps(asdict(c), indent=2))


def fit(start: int, end: int, holdout: int | None = None) -> NFLCoefs:
    try:
        import numpy as np  # noqa
        import pandas as pd  # noqa
        from sklearn.isotonic import IsotonicRegression  # noqa
    except ImportError:
        log.error("need numpy/pandas/sklearn")
        return load_coefs()
    log.info("fit stub — pull nfl_data_py seasons %d..%d and run Elo walk", start, end)
    c = load_coefs()
    save_coefs(c)
    return c


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--start-season", type=int, default=2015)
    p.add_argument("--end-season", type=int, default=2024)
    p.add_argument("--holdout-season", type=int, default=2025)
    args = p.parse_args()
    c = fit(args.start_season, args.end_season, args.holdout_season)
    print(json.dumps(asdict(c), indent=2))
