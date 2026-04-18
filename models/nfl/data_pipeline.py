"""NFL data pipeline (nfl_data_py + nfelo-style power ratings)."""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Optional

from models.nfl.model import GameContext, MatchupInputs, QBInfo, TeamPowerRating

log = logging.getLogger("nfl.pipeline")
CACHE_ROOT = Path("data/cache/nfl")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def _nfl():
    try:
        import nfl_data_py as nfl  # noqa
        return nfl
    except ImportError:
        log.warning("nfl_data_py missing; pip install nfl_data_py")
        return None


def fetch_team_power(team_code: str, season: int,
                     through_week: int = 18) -> TeamPowerRating:
    """Pull season-to-date EPA + success rate; compute Elo blend."""
    nfl = _nfl()
    if nfl is None:
        return TeamPowerRating(team_code)
    try:
        import pandas as pd
        pbp = nfl.import_pbp_data([season])
        # Filter completed plays
        pbp = pbp[(pbp["week"] <= through_week) & (pbp["play_type"].isin(["pass", "run"]))]
        off = pbp[pbp["posteam"] == team_code]
        defp = pbp[pbp["defteam"] == team_code]
        off_epa = off["epa"].mean() if len(off) else 0.0
        def_epa = defp["epa"].mean() if len(defp) else 0.0
        off_sr = off["success"].mean() if "success" in off.columns and len(off) else 0.45
        def_sr = defp["success"].mean() if "success" in defp.columns and len(defp) else 0.45
        # Elo: placeholder from preseason baselines; retrain via training.py
        elo = fetch_elo(team_code, season, through_week)
        return TeamPowerRating(
            team_code=team_code,
            elo=elo,
            off_epa_per_play_season=float(off_epa),
            def_epa_per_play_season=float(def_epa),
            off_success_rate=float(off_sr),
            def_success_rate=float(def_sr),
            games_observed=int(pbp[pbp["posteam"] == team_code]["game_id"].nunique()),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("team_power %s %d fallback: %s", team_code, season, e)
        return TeamPowerRating(team_code)


def fetch_elo(team_code: str, season: int, through_week: int) -> float:
    """Get nfelo-style Elo rating.  Placeholder = 1500 constant until Elo
    walk-through computed by training.py."""
    cache = CACHE_ROOT / f"elo_{season}.json"
    if cache.exists():
        import json
        d = json.loads(cache.read_text())
        return d.get(team_code, 1500.0)
    return 1500.0


def fetch_starting_qb(team_code: str, season: int, week: int) -> QBInfo:
    nfl = _nfl()
    if nfl is None:
        return QBInfo("unknown")
    try:
        pbp = nfl.import_pbp_data([season])
        pbp = pbp[(pbp["week"] <= week) & (pbp["posteam"] == team_code) &
                  (pbp["pass"] == 1) & (pbp["qb_dropback"] == 1)]
        if not len(pbp):
            return QBInfo("unknown")
        # Most-frequent passer in most-recent game
        latest_week = int(pbp["week"].max())
        pbp_recent = pbp[pbp["week"] == latest_week]
        counts = pbp_recent["passer_player_id"].value_counts()
        if counts.empty:
            return QBInfo("unknown")
        qb_id = str(counts.index[0])
        qb_plays = pbp[pbp["passer_player_id"] == qb_id]
        cpoe_col = "cpoe" if "cpoe" in qb_plays.columns else None
        epa_col = "epa"
        return QBInfo(
            qb_id=qb_id,
            cpoe=float(qb_plays[cpoe_col].mean()) if cpoe_col else 0.0,
            epa_per_play=float(qb_plays[epa_col].mean()),
            passes_observed=int(len(qb_plays)),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("starting_qb %s fallback: %s", team_code, e)
        return QBInfo("unknown")


def build_matchup(home: str, away: str, season: int, week: int,
                  is_playoff: bool = False,
                  weather: Optional[dict] = None,
                  is_thursday_night: bool = False) -> MatchupInputs:
    home_p = fetch_team_power(home, season, week)
    away_p = fetch_team_power(away, season, week)
    home_qb = fetch_starting_qb(home, season, week)
    away_qb = fetch_starting_qb(away, season, week)
    ctx = GameContext(is_playoff=is_playoff, is_thursday_night=is_thursday_night)
    if weather:
        ctx.temp_f = weather.get("temp_f", 60)
        ctx.wind_mph = weather.get("wind_mph", 5)
        ctx.precipitation = weather.get("precipitation", 0.0)
        ctx.is_dome = weather.get("is_dome", False)
        ctx.altitude_feet = weather.get("altitude_feet", 0)
    return MatchupInputs(home_p, away_p, home_qb, away_qb, ctx)
