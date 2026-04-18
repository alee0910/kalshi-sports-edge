# NFL — Literature Review

_Target: ~20 primary sources. Achieved: 22. Status: complete for v1 model._

## 1. Analytical tradition

Modern NFL analytics is the youngest of the "big three" but the fastest-moving. Lineage: Brian Burke's Advanced Football Analytics (2008+) pioneering EPA/WP → Football Outsiders (Aaron Schatz) with DVOA/DYAR → nflfastR and the Open Source Football community (Ben Baldwin, Sebastian Carl, Lee Sharpe, 2019+) → PFF expanding → the EPA + CPOE standard → nfelo and WEPA blends.

Practitioners: Ben Baldwin, Brian Burke, Aaron Schatz, Mike Beuoy, Sam Hoppen, Bill Connelly (also CBB), Josh Hermsmeyer, PFF analytics team, nfelo / Robby Greer, Next Gen Stats team.

Football Outsiders shut down in 2023, with DVOA archived at FTN Fantasy. This is a gap in contemporary output but the public-data nflfastR ecosystem has largely superseded FO's role.

## 2. Frontier metrics

### 2.1 Play-level — EPA / CPOE / success rate

| Metric | Description | Predictive weight |
|---|---|---|
| **EPA/play** | Expected points added per play; difference in pre/post-play expected-points state | Highest single-number predictor of team quality |
| **Success rate** | % plays gaining ≥ 40% of yards-to-go on 1st, 60% on 2nd, 100% on 3rd/4th | Complementary to EPA (EPA rewards big plays, SR rewards consistency) |
| **CPOE** (Completion % Over Expected) | QB completion rate minus expected given throw difficulty | Better QB-evaluation than raw completion % |
| **EPA + CPOE composite** | Blend of EPA/play and CPOE | Standard QB quality signal |
| **xPass** | Probability play is pass given state | Tags plays as successful or not relative to expectation |
| **xYAC** | Expected yards after catch given throw location | Isolates receiver skill |

Key empirical weighting from nfelo/nflfastR community: **offensive EPA weight = 1.6, defensive EPA weight = 1.0** for predicting next-game net EPA. Offensive efficiency is substantially more stable than defensive.

Sources: [Open Source Football nflfastR models](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/), [NFL Operations](https://operations.nfl.com/gameday/analytics/stats-articles/), [Advanced Football Analytics EPA](http://www.advancedfootballanalytics.com/2010/01/expected-points-ep-and-expected-points.html), [Sabin Analytics — Slow down using EPA](https://sabinanalytics.com/blog/2024/01:05:slow-down-using-epa-for-everything/), [PFF betting 101](https://www.pff.com/news/bet-nfl-bet-terms-metrics-game-script-handicapping-success-rate-epa), [nfelo EPA tiers](https://www.nfeloapp.com/nfl-power-ratings/nfl-epa-tiers/), [nfelo what is EPA](https://www.nfeloapp.com/analysis/expected-points-added-epa-nfl/), [Action Network EPA explainer](https://www.actionnetwork.com/education/what-is-epa-how-expected-points-added-advanced-metric-can-help-you-with-football-betting), [Best Ball Stats EPA](https://bestballstats.com/expected-points-added-a-full-explanation/), [Covers advanced metrics](https://www.covers.com/nfl/key-advanced-metrics-betting-tips).

### 2.2 Team-adjusted — DVOA / DYAR / WEPA

- **DVOA** (Defense-adjusted Value Over Average): play-level success vs. league avg, adjusted for down, distance, and opponent. A team with +10% DVOA is 10% better than average.
- **DYAR**: DVOA scaled to replacement-level and expressed as yardage.
- **WEPA** (weighted EPA): nfelo's proprietary EPA with opponent adjustment and game-situation weighting. Empirical finding: WEPA beats DVOA and PFF in predictive power; blend of WEPA + PD + PFF best.

Sources: [Football Outsiders DVOA methods](https://www.footballoutsiders.com/info/methods), [FO DYAR](https://www.footballoutsiders.com/help/article/dyar), [FTN DVOA explainer](https://ftnfantasy.com/nfl/dvoa-explainer), [nfelo What's the Best NFL Game Grade (WEPA)](https://www.nfeloapp.com/analysis/whats-the-best-nfl-game-grade/), [PFF grades](https://www.pff.com/grades).

### 2.3 Next Gen Stats tracking data

| Metric | Use |
|---|---|
| Air yards, completion probability | QB evaluation |
| Passer score (NGS) | All-in-one QB rating |
| Tackle rate, expected tackle | Run D |
| Coverage schemes, separation | WR / CB |
| Time to throw, pressure rate | Offensive line / QB aggression |

NGS data is mostly public-facing on nfl.com; deeper tracking data requires paid access.

Sources: [NGS Passing Score](https://www.nfl.com/news/next-gen-stats-intro-to-passing-score-metric), [PFF Advanced Coverage Grade](https://www.pff.com/news/nfl-advanced-coverage-grade).

### 2.4 Elo / power ratings

| Source | Notes |
|---|---|
| **538 NFL Elo** | Classic Elo with QB-adjusted ratings; retired 2023 but archived |
| **nfelo** | Blended Elo + market + EPA model; open-source; considered SOTA public power rating |
| **Sagarin** | Old-school computer ranking; still referenced |
| **Massey** | Similar; mostly academic |

Practical: use nfelo power ratings (or replicate) as team-strength prior.

Sources: [nfelo power ratings](https://www.nfeloapp.com/nfl-power-ratings/), [PFF NFL site](https://www.pff.com/nfl).

### 2.5 Win-probability models

- nflfastR's WP model is XGBoost trained on play-level data; used throughout public analytics.
- Pre-game WP blends: Elo + market spread + CPOE-adjusted QB projection.
- nfelo's pregame model is currently the benchmark public.

Sources: [Open Source Football nflfastR WP](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/), [Open Source Football blog](https://opensourcefootball.com/).

## 3. Superseded / overrated metrics

- **QB Passer Rating (traditional 0-158.3 scale)** — obsolete. Use EPA/CPOE.
- **Total yards** — context-free.
- **Yards per carry (rushing)** — heavily influenced by line play and game-script, not isolated RB quality. Use rushing EPA and success rate.
- **Turnover differential** — mostly noise; TO luck regresses hard.
- **Red zone TD %** — small samples; bring big-year-to-year variation.
- **Time of possession** — outcome, not input.
- **QB wins** — does not isolate QB contribution.

## 4. Stabilization

| Statistic | Games for ~50% stability |
|---|---|
| Off EPA/play (team) | 3-5 games |
| Def EPA/play (team) | 6-8 games |
| Off success rate | 4-6 games |
| QB CPOE | 6-8 games (~250 throws) |
| DVOA | 6-8 games |
| Turnover differential | never really stabilizes within a season |
| Red zone TD % | never within-season |

Shrinkage strategy: for weeks 1-3, lean heavily on preseason power ratings + Vegas implied quality. Weeks 4-8, linear blend. Weeks 9+, season-to-date with prior blend ~10%.

## 5. Kalshi edge hypothesis

| Inefficiency | Mechanism | Exploitation |
|---|---|---|
| Early-season mispricing | Markets overreact to Week 1-2 noise | Use nfelo-style stable power prior with heavy shrinkage; fade recency |
| QB-injury premium | Starter → backup repricing often overshoots or undershoots | Know QB-EPA deltas; fast lineup-news pipe |
| Weather-sensitive contracts | Outdoor cold-weather games: market underprices weather impact on passing | Include weather as feature |
| Divisional rematch bias | Retail overweights divisional familiarity; actual effect minor | Fade |
| Popular-team Super Bowl futures | Cowboys / 49ers / Chiefs futures overpriced | Fade season-long |
| Home favorites on Thursday-night | Short rest favors home slightly more; sometimes lagged | Model short rest explicitly |

## 6. Open-source implementations

| Tool | Language | License | Use |
|---|---|---|---|
| [nflfastR](https://github.com/nflverse/nflfastR) | R | MIT | Core play-by-play + EPA/WP/CP models |
| [nflreadr](https://github.com/nflverse/nflreadr) | R | MIT | Data access layer |
| [nfl_data_py](https://github.com/cooperdff/nfl_data_py) | Python | MIT | Python port of nflfastR data |
| [nflverse](https://github.com/nflverse) | R/Python | Various MIT | Umbrella project |
| [nfelo](https://github.com/greerreNFL/nfelo) | Python | MIT | Power ratings + market blend |
| [sumer-nfl](https://sumersports.com/) | — | proprietary | commercial research |

Our pipeline: `nfl_data_py` for historical play-by-play and schedules; replicate nfelo-style power ratings in Python.

## 7. Known blind spots (v1 model)

- Offensive line quality is hard to isolate without PFF grades (paid).
- Coaching-staff mid-season changes not modeled.
- Divisional rematch history effects unclear.
- Special teams mostly ignored (ST EPA exists but noisy).
- QB-specific backup-QB priors for rare starter injuries are thin.
- Stadium-specific weather patterns (Lambeau wind, Mile High altitude) only folded via generic weather features.

## 8. Bibliography

1. Burke, B. (2010). ["Expected Points (EP) and Expected Points Added (EPA) Explained"](http://www.advancedfootballanalytics.com/2010/01/expected-points-ep-and-expected-points.html)
2. Baldwin, B., Carl, S., Sharpe, L. (2020+). nflfastR. [GitHub](https://github.com/nflverse/nflfastR).
3. [Open Source Football EP/WP/CP Models](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/)
4. [Open Source Football blog archive](https://opensourcefootball.com/)
5. [nflfastR getting started](https://nflfastr.com/articles/nflfastR.html)
6. [nfl_data_py README](https://github.com/cooperdff/nfl_data_py)
7. Schatz, A. et al. Football Outsiders: [DVOA methodology](https://www.footballoutsiders.com/info/methods) / [DYAR](https://www.footballoutsiders.com/help/article/dyar) / [stats](https://www.footballoutsiders.com/stats/nfl) / [Wikipedia entry](https://en.wikipedia.org/wiki/Football_Outsiders) / [glossary](https://www.footballoutsiders.com/info/glossary)
8. [FTN Fantasy DVOA explainer](https://ftnfantasy.com/nfl/dvoa-explainer)
9. [nfelo — EPA tiers](https://www.nfeloapp.com/nfl-power-ratings/nfl-epa-tiers/) and [EPA intro](https://www.nfeloapp.com/analysis/expected-points-added-epa-nfl/)
10. [nfelo — Best NFL Game Grade (WEPA)](https://www.nfeloapp.com/analysis/whats-the-best-nfl-game-grade/)
11. [nfelo power ratings page](https://www.nfeloapp.com/nfl-power-ratings/)
12. [Sabin Analytics — Slow Down Using EPA](https://sabinanalytics.com/blog/2024/01:05:slow-down-using-epa-for-everything/)
13. [PFF — Betting 101 metrics](https://www.pff.com/news/bet-nfl-bet-terms-metrics-game-script-handicapping-success-rate-epa)
14. [PFF — Advanced Coverage Grade](https://www.pff.com/news/nfl-advanced-coverage-grade)
15. [PFF Player Grades](https://www.pff.com/grades)
16. [PFF college→pro receiving grade correlation](https://www.pff.com/news/draft-pff-receiving-grades-predicting-ncaa-to-nfl)
17. [Daily Norseman — Analyzing PFF Grading](https://www.dailynorseman.com/2024/7/20/24198640/analyzing-nfl-analytics-pff-grading)
18. [Pro Football Focus Wikipedia](https://en.wikipedia.org/wiki/Pro_Football_Focus)
19. [NGS — Intro to Passing Score](https://www.nfl.com/news/next-gen-stats-intro-to-passing-score-metric)
20. [SumerSports — NFL Advanced Stats](https://sumersports.com/the-zone/nfl-advanced-stats/)
21. [Action Network — EPA explainer](https://www.actionnetwork.com/education/what-is-epa-how-expected-points-added-advanced-metric-can-help-you-with-football-betting)
22. [Best Ball Stats — EPA full explanation](https://bestballstats.com/expected-points-added-a-full-explanation/)
