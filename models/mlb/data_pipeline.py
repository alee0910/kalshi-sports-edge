"""MLB data pipeline.

Pulls from:
- pybaseball (Statcast pitch-level, FanGraphs season stats)
- MLB Stats API (statsapi.mlb.com) for live lineups and schedule

Caches to /data/cache/mlb/.  Produces MatchupInputs for the model.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Optional

from models.mlb.model import (
    BullpenStats, GameContext, MatchupInputs, PitcherStats, TeamPrior, TeamSeasonStats
)

log = logging.getLogger("mlb.pipeline")

CACHE_ROOT = Path(os.environ.get("KALSHI_DATA_ROOT", "data/cache")) / "mlb"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# pybaseball helpers (optional import so repo works w/o install)
# ---------------------------------------------------------------------------
def _pb():
    try:
        import pybaseball  # noqa
        pybaseball.cache.enable()
        return pybaseball
    except ImportError:
        log.warning("pybaseball not installed; install with `pip install pybaseball` for full pipeline")
        return None


# ---------------------------------------------------------------------------
# Team season stats
# ---------------------------------------------------------------------------
def fetch_team_season_stats(team_code: str, season: int,
                            end_date: Optional[dt.date] = None) -> TeamSeasonStats:
    """Pull aggregate team offensive + defensive stats from FanGraphs/Statcast."""
    pb = _pb()
    if pb is None:
        return TeamSeasonStats(team_code)
    try:
        bat = pb.team_batting(season, season, league="all")
        row = bat[bat["Team"] == team_code].iloc[0]
        return TeamSeasonStats(
            team_code=team_code,
            xwoba_vs_LHP=row.get("xwOBA_L", row.get("xwOBA", 0.320)),
            xwoba_vs_RHP=row.get("xwOBA_R", row.get("xwOBA", 0.320)),
            wrc_plus=float(row.get("wRC+", 100.0)),
            k_rate=float(row.get("K%", 0.22)) if row.get("K%", 0.22) > 1 else float(row.get("K%", 0.22)) / 100,
            bb_rate=float(row.get("BB%", 0.085)) if row.get("BB%", 0.085) > 1 else float(row.get("BB%", 0.085)) / 100,
            barrel_rate=float(row.get("Barrel%", 0.075)) if row.get("Barrel%", 0.075) > 1 else float(row.get("Barrel%", 0.075)) / 100,
            pa_observed=int(row.get("PA", 0)),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("team_season_stats %s %d fallback: %s", team_code, season, e)
        return TeamSeasonStats(team_code)


# ---------------------------------------------------------------------------
# Pitcher stats — frontier: Stuff+ from Savant pitch-level
# ---------------------------------------------------------------------------
def fetch_pitcher_stats(pitcher_id: str, season: int,
                        end_date: Optional[dt.date] = None,
                        window_days: int = 45) -> PitcherStats:
    """Fetch pitcher-level Stuff+ + peripherals.  Fall back to SIERA if
    Stuff+ not yet computed (e.g. minor-league call-up)."""
    pb = _pb()
    if pb is None:
        return PitcherStats(pitcher_id)
    try:
        # pybaseball's fangraphs_pitching_leaderboards includes stuff+ when available
        df = pb.fangraphs_pitching_leaderboards(season, season, qual=0)
        row = df[df["playerid"].astype(str) == str(pitcher_id)]
        if row.empty:
            return PitcherStats(pitcher_id)
        r = row.iloc[0]
        return PitcherStats(
            pitcher_id=pitcher_id,
            stuff_plus=float(r.get("Stuff+", None)) if "Stuff+" in r else None,
            pitching_plus=float(r.get("Pitching+", None)) if "Pitching+" in r else None,
            siera=float(r.get("SIERA", 4.0)),
            xfip=float(r.get("xFIP", 4.0)),
            k_rate=float(r.get("K%", 22.0)) / 100.0 if r.get("K%", 22.0) > 1 else float(r.get("K%", 0.22)),
            bb_rate=float(r.get("BB%", 8.0)) / 100.0 if r.get("BB%", 8.0) > 1 else float(r.get("BB%", 0.08)),
            throws=str(r.get("Throws", "R")),
            pitches_observed=int(r.get("Pitches", 0)),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("pitcher_stats %s fallback: %s", pitcher_id, e)
        return PitcherStats(pitcher_id)


# ---------------------------------------------------------------------------
# Matchup builder — called by scanner
# ---------------------------------------------------------------------------
def build_matchup(home_team: str, away_team: str,
                  home_sp_id: str, away_sp_id: str,
                  game_date: dt.date,
                  park_factor: float = 1.00,
                  weather: Optional[dict] = None) -> MatchupInputs:
    season = game_date.year
    home_stats = fetch_team_season_stats(home_team, season, game_date)
    away_stats = fetch_team_season_stats(away_team, season, game_date)
    home_sp = fetch_pitcher_stats(home_sp_id, season, game_date)
    away_sp = fetch_pitcher_stats(away_sp_id, season, game_date)

    # Bullpen placeholder: average of team's non-starter innings-weighted stuff+
    # Production: compute from pitcher_ids list. For now, approximate with team-level.
    home_bullpen = BullpenStats(stuff_plus_weighted=None, siera_weighted=4.00)
    away_bullpen = BullpenStats(stuff_plus_weighted=None, siera_weighted=4.00)

    # Team priors (season-to-date run production)
    home_prior = fetch_team_prior(home_team, season, game_date)
    away_prior = fetch_team_prior(away_team, season, game_date)

    ctx = GameContext(park_factor=park_factor)
    if weather:
        ctx.temp_f = weather.get("temp_f", 70.0)
        ctx.wind_out_cf_mph = weather.get("wind_out_cf_mph", 0.0)
        ctx.humidity_pct = weather.get("humidity_pct", 50.0)

    return MatchupInputs(
        home_team=home_stats, away_team=away_stats,
        home_pitcher=home_sp, away_pitcher=away_sp,
        home_bullpen=home_bullpen, away_bullpen=away_bullpen,
        home_prior=home_prior, away_prior=away_prior,
        context=ctx,
    )


def fetch_team_prior(team_code: str, season: int, end_date: dt.date) -> TeamPrior:
    """Season-to-date runs scored/allowed and W-L for pythagenpat."""
    pb = _pb()
    if pb is None:
        return TeamPrior(runs_scored=400, runs_allowed=400, games_played=80)
    try:
        df = pb.team_pitching(season, season, league="all")
        row = df[df["Team"] == team_code].iloc[0]
        ra = int(row.get("R", 400))
        g = int(row.get("G", 80))
        bat = pb.team_batting(season, season, league="all")
        rs = int(bat[bat["Team"] == team_code].iloc[0].get("R", 400))
        return TeamPrior(runs_scored=rs, runs_allowed=ra, games_played=g)
    except Exception as e:  # noqa: BLE001
        log.warning("team_prior %s fallback: %s", team_code, e)
        return TeamPrior(runs_scored=400, runs_allowed=400, games_played=80)
