"""NBA data pipeline.

Primary sources:
- nba_api (https://github.com/swar/nba_api) for schedules, play-by-play, team stats
- DARKO data via apanalytics Shiny app scrape / daily CSV dump
- EPM from dunksandthrees.com
- Official NBA Injury Report PDF (for scratches / load management)
"""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Optional

from models.nba.model import (
    GameContext, MatchupInputs, PlayerImpact, TeamFourFactors
)

log = logging.getLogger("nba.pipeline")
CACHE_ROOT = Path("data/cache/nba")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def _nba_api():
    try:
        import nba_api  # noqa
        return nba_api
    except ImportError:
        log.warning("nba_api missing; `pip install nba_api` for full pipeline")
        return None


def fetch_team_four_factors(team_code: str, season: str = "2025-26",
                            as_of: Optional[dt.date] = None) -> TeamFourFactors:
    """Pull season-to-date Four Factors + ratings for a team."""
    api = _nba_api()
    if api is None:
        return TeamFourFactors(team_code)
    try:
        from nba_api.stats.endpoints import leaguedashteamstats
        df = leaguedashteamstats.LeagueDashTeamStats(
            season=season, measure_type_detailed_defense="Advanced"
        ).get_data_frames()[0]
        row = df[df["TEAM_ABBREVIATION"] == team_code].iloc[0]
        # Four factors from leaguedashteamstats
        df_ff = leaguedashteamstats.LeagueDashTeamStats(
            season=season, measure_type_detailed_defense="Four Factors"
        ).get_data_frames()[0]
        ff = df_ff[df_ff["TEAM_ABBREVIATION"] == team_code].iloc[0]
        return TeamFourFactors(
            team_code=team_code,
            efg_pct=float(ff.get("EFG_PCT", 0.54)),
            tov_pct=float(ff.get("TM_TOV_PCT", 13.5)) / 100.0 if ff.get("TM_TOV_PCT", 0.135) > 1 else float(ff.get("TM_TOV_PCT", 0.135)),
            orb_pct=float(ff.get("OREB_PCT", 0.265)),
            fta_rate=float(ff.get("FTA_RATE", 0.235)),
            efg_def_pct=float(ff.get("OPP_EFG_PCT", 0.54)),
            pace_poss_per48=float(row.get("PACE", 99.0)),
            off_rating=float(row.get("OFF_RATING", 115.0)),
            def_rating=float(row.get("DEF_RATING", 115.0)),
            games_observed=int(row.get("GP", 0)),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("four_factors %s fallback: %s", team_code, e)
        return TeamFourFactors(team_code)


def fetch_darko_impacts(as_of: dt.date) -> dict[str, PlayerImpact]:
    """Return mapping of player_id -> DARKO DPM projections.
    Scrapes apanalytics Shiny app CSV if available; otherwise returns empty."""
    # Placeholder.  In production we cache a daily CSV snapshot committed to
    # /data/historical/nba/darko/YYYY-MM-DD.csv via a separate scheduled job.
    path = CACHE_ROOT / "darko" / f"{as_of.isoformat()}.csv"
    if not path.exists():
        log.info("DARKO snapshot not cached for %s; returning empty", as_of)
        return {}
    try:
        import pandas as pd
        df = pd.read_csv(path)
        out = {}
        for _, r in df.iterrows():
            pid = str(r.get("player_id", r.get("nba_id", "")))
            out[pid] = PlayerImpact(
                player_id=pid,
                name=str(r.get("name", "")),
                projected_impact_per100=float(r.get("DPM", 0.0)),
                usage_pct=float(r.get("usage", 20.0)) / 100.0 if r.get("usage", 0.20) > 1 else float(r.get("usage", 0.20)),
                games_observed=int(r.get("games", 0)),
            )
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("darko read failed: %s", e)
        return {}


def fetch_injury_report(as_of: dt.date) -> set[str]:
    """Return set of player IDs marked OUT on NBA official injury report.
    Stub — production implementation scrapes NBA Injury Report PDF."""
    return set()


def build_matchup(home: str, away: str,
                  game_date: dt.date,
                  home_rest: int = 2, away_rest: int = 2,
                  home_b2b: bool = False, away_b2b: bool = False,
                  travel_miles_away: float = 0.0,
                  altitude: float = 0.0) -> MatchupInputs:
    home_ff = fetch_team_four_factors(home)
    away_ff = fetch_team_four_factors(away)
    darko = fetch_darko_impacts(game_date)
    out = fetch_injury_report(game_date)
    # Attach availability — scanner fills in actual player_ids for each team roster
    return MatchupInputs(
        home_team=home_ff, away_team=away_ff,
        context=GameContext(home_rest_days=home_rest, away_rest_days=away_rest,
                            is_back_to_back_home=home_b2b, is_back_to_back_away=away_b2b,
                            away_travel_miles_48h=travel_miles_away,
                            altitude_feet=altitude),
    )
