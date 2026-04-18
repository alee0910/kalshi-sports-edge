# MLB model — feature specification

Grounded in `/research/domain/mlb_literature_review.md`. Each feature cited with its literature justification and stabilization threshold.

## Offensive features (per-team, vs. pitcher handedness)

| Feature | Source | Stabilization | Shrinkage target |
|---|---|---|---|
| `team_xwoba_vs_LHP` / `vs_RHP` | Statcast per PA aggregated over rolling 30-day window | ~400 PA team-level | League mean by handedness split |
| `team_wrc_plus` | FanGraphs rolling 60-day | ~450 PA | 100 (league-average) |
| `team_bb_rate` | Rolling 30-day | ~1200 PA team | League mean |
| `team_k_rate` | Rolling 30-day | ~600 PA team | League mean |
| `team_barrel_rate` | Statcast rolling 30-day | ~200 BBE team | League mean |
| `lineup_xwoba_sum` | Sum of projected lineup 9's individual xwOBA vs. starter's handedness | — | Individual-level priors |

## Pitcher features (starter + bullpen aggregate)

| Feature | Source | Stabilization | Why |
|---|---|---|---|
| `sp_stuff_plus` | FanGraphs / replicated from Savant pitch-level | ~80 pitches | **Frontier. Primary pitcher input.** |
| `sp_pitching_plus` | FanGraphs | ~150 pitches | Includes location + command |
| `sp_siera` | FanGraphs | ~150 IP | Secondary ERA estimator |
| `sp_xfip` | FanGraphs | ~150 IP | Tertiary |
| `sp_k_rate` | Rolling 5-start | ~40 BF | Stable skill |
| `sp_bb_rate` | Rolling 5-start | ~80 BF | Stable skill |
| `sp_workload_index` | Pitches-last-7d / innings-last-30d | N/A | Fatigue proxy |
| `bp_stuff_plus_weighted` | Likely-used relievers weighted by recent usage | ~80 pitches per RP | Bullpen depth |
| `bp_siera` | Weighted bullpen SIERA | ~50 IP per RP | Redundant but robust |

## Defense

| Feature | Source | Why |
|---|---|---|
| `team_oaa_per_game` | Statcast Outs Above Average rate | Range/defense |
| `catcher_framing_runs_rate` | Statcast framing runs per 100 chances | ~0.135 runs per extra strike |
| `team_drs_rate` | Baseball Info Solutions DRS per 27 | Historical defense |

## Context

| Feature | Source |
|---|---|
| `park_factor_overall` | FanGraphs 5-year park factor |
| `park_factor_hr_L/R` | Savant HR park factor by batter handedness |
| `weather_temp_f` | National Weather Service or paid feed (OpenWeather) |
| `weather_wind_speed_mph` | Component vector to CF |
| `weather_humidity_pct` | Affects ball carry |
| `ump_called_strike_pct_pitcher_friendly_index` | Retrosheet / public umpire data |
| `rest_days_home`, `rest_days_away` | Schedule-derived |
| `travel_last_48h_miles_away` | Schedule-derived |

## Time-of-year priors

- `season_progress_pct` = fraction of regular season elapsed. Used to scale shrinkage weight.
- Early season (< 30 games played): weight of current-season stats = season_progress / (season_progress + 0.2); rest goes to prior-season projection.

## Justification — why THIS set

Based on literature:
1. Offense: xwOBA + wRC+ (stable, predictive of runs, lit. supported).
2. Pitcher: Stuff+ + Pitching+ as primary. ERA explicitly omitted — it's an outcome, not a predictor. FIP/xFIP kept as backstops for pitchers with <80 pitches of Stuff+ data.
3. Catcher framing is the single most overlooked input in public betting markets per our Phase 1 research.
4. Weather and park are Kalshi-retail blind spots — beat reporters often cover but market reacts slowly.
5. No traditional stats (W-L, ERA alone, RBI, BA). Deliberately.

## Not-yet-incorporated frontier items (TODO)

- Seam-shifted wake features (FanGraphs SSW, 2023-)
- Pitch mirroring / tunneling metrics
- Batter swing decision metrics (chase rate modelled vs. zone)
- Opponent-adjusted Stuff+ (some pitchers' stuff plays up/down vs. specific lineups)

These are planned for v2 model.
