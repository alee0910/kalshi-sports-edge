# NBA model — feature specification

Grounded in `/research/domain/nba_literature_review.md`.

## Team (Four Factors + ratings)

| Feature | Source | Stabilization |
|---|---|---|
| `efg_pct` offense + defense | nba_api / basketball-reference | ~20 games |
| `tov_pct` offense + forced | nba_api | ~25 games |
| `orb_pct`, `drb_pct` | nba_api | ~20 games |
| `fta_rate`, `fta_rate_allowed` | nba_api | ~20 games |
| `off_rating`, `def_rating` (per 100 poss) | nba_api | ~20 games |
| `pace_poss_per48` | nba_api | ~15 games |

## Player impact

| Feature | Source | Stabilization |
|---|---|---|
| `projected_impact_per100` per player | DARKO (scraped from apanalytics Shiny), EPM (Dunks & Threes API), LEBRON | DARKO updates daily |
| `available` flag | Twitter/X lineup-news scraper + NBA Injury Report | real-time |
| `usage_pct` | nba_api | ~15 games |

Rule: when a starting-level player (≥ +1.5 DARKO DPM) is OUT, subtract ~75% of their per-100 impact from team rating to reflect backup replacement (not league-average).

## Context

| Feature | Source |
|---|---|
| `home_rest_days`, `away_rest_days` | Schedule |
| `is_back_to_back_home/away` | Derived |
| `away_travel_miles_48h` | Airport-distance lookup |
| `altitude_feet` | Venue metadata |

## NOT using (deliberately)

- PER (Player Efficiency Rating) — deprecated.
- Raw plus-minus without regularization.
- Win Shares — box-score-only.
- Traditional counting stats (PPG/APG/RPG) without pace-adjustment.

## Pending upgrades (v2)

- Shot quality (qSQ/xeFG) for recent-form offensive adjustment.
- Lineup-fit features (big-vs-smallball matchup index).
- Referee-crew tendency (fouls/FTs per game).
- Playoff experience premium (rookie-heavy teams decay in postseason).
