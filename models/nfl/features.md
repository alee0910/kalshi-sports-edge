# NFL model — feature specification

Grounded in `/research/domain/nfl_literature_review.md`.

## Team ratings

| Feature | Source | Stabilization |
|---|---|---|
| `elo` (nfelo-style blended rating) | nfelo GitHub; replicated | preseason from prior year weighted 1/3 |
| `off_epa_per_play_season` | nflfastR / nfl_data_py | 3-5 games |
| `def_epa_per_play_season` | nflfastR / nfl_data_py | 6-8 games |
| `off_success_rate` | nflfastR | 4-6 games |
| `def_success_rate` | nflfastR | 6-8 games |

Weighting: offensive EPA counts 1.6× defensive EPA in team-quality prediction (nfelo empirical finding).

## QB features

| Feature | Source | Stabilization |
|---|---|---|
| `cpoe` (Completion % Over Expected) | NGS + nflfastR | ~250 throws |
| `epa_per_play` | nflfastR | ~150 throws |
| `is_starter` | Injury/depth chart scraper | real-time |
| `is_injury_replacement` | Roster update detection | real-time |

Rule: backup QB starting for the first time → subtract 4 points from team margin. If backup has ≥ 3 career starts with established metrics, use their actual CPOE/EPA (no additional penalty).

## Situational / context

| Feature | Source |
|---|---|
| `is_division_game`, `is_thursday_night`, `is_monday_night`, `is_playoff` | Schedule |
| `home_rest_days`, `away_rest_days` | Schedule |
| `temp_f`, `wind_mph`, `precipitation` | Weather API (OpenWeatherMap) — stadium lat/lon |
| `is_dome` | Stadium metadata |
| `altitude_feet` | Stadium metadata |
| `is_neutral_site` | Schedule (London/Mexico games) |

Weather rules:
- Dome: ignore weather
- Wind > 15 mph: each 5 mph above → 0.5 pts decrease in total, split by pass-dependence
- Temp < 32°F: 0.5 pts decrease in total
- Precipitation: 1 pt decrease per inch forecast

## Deliberately NOT using

- Raw yards per carry (heavily line/script dependent).
- QB wins.
- Passer rating (obsolete — replaced by EPA/CPOE).
- Turnover differential (too noisy within-season).
- Red zone TD % (small samples).
- Time of possession.

## Planned v2 upgrades

- PFF grades (requires paid access).
- Line play features (pressure rate, run-block win rate).
- Coaching change mid-season features.
- Special teams EPA (low weight but non-zero).
