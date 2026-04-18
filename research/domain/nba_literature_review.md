# NBA — Literature Review

_Target: ~20 primary sources. Achieved: 21. Status: complete for v1 model._

## 1. Analytical tradition

The APBRmetrics community formalized in the late 1990s / early 2000s. Key lineage: Dean Oliver, *Basketball on Paper* (2004) — the Four Factors → Daryl Morey and the MIT Sloan Sports Analytics Conference era (2006+) → advanced plus-minus (APM → RAPM → BPM → LEBRON → DARKO → EPM) → Second Spectrum / SportVU / Hawk-Eye player-tracking era (2013+) → modern Bayesian + tracking-data fusion.

Core practitioners/platforms: Dean Oliver, Kostya Medvedovsky (DARKO), Ben Taylor (Thinking Basketball), Krishna Narsu (LEBRON), Taylor Snarr (EPM), Seth Partnow, Ben Falk (Cleaning the Glass), Ken Pomeroy (college-level but influential), NBA Second Spectrum, ShotQuality.com, Basketball Reference, FiveThirtyEight (RAPTOR, now retired).

## 2. Frontier metrics

### 2.1 Team efficiency / Four Factors (Oliver, 2004)

Dean Oliver's Four Factors explain ~96% of variance in team wins in modern era:

| Factor | Formula | Weight (Oliver) |
|---|---|---|
| **eFG%** (shooting) | (FGM + 0.5 × 3PM) / FGA | 40% |
| **TOV%** (turnovers) | TOV / (FGA + 0.44 × FTA + TOV) | 25% |
| **ORB%** (offensive rebounding) | ORB / (ORB + Opp_DRB) | 20% |
| **FTA Rate** | FTA / FGA | 15% |

**TS% (True Shooting %)** is the preferred offensive-efficiency scalar since it folds FT and 3PT into one: `PTS / (2 × (FGA + 0.44 × FTA))`.

Sources: [Arxiv 2305.13032 "Four Factors Revisited"](https://arxiv.org/abs/2305.13032), [Basketball-Reference Four Factors](https://www.basketball-reference.com/about/factors.html), [Chris Gunther "Revisiting the Four Factors"](https://chartinghoops.substack.com/p/revisiting-the-four-factors), [Cleaning the Glass Four Factors guide](https://cleaningtheglass.com/stats/guide/league_four_factors), [Statathlon Four Factors](https://statathlon.com/four-factors-basketball-success/).

### 2.2 Player impact metrics — RAPM family (frontier)

All modern catch-all metrics are RAPM-derivatives:

| Metric | What it adds to RAPM | Predictive ranking (per NBA execs survey) |
|---|---|---|
| **DARKO (DPM)** | Time-decay RAPM + box score + age/experience curves; outputs daily updating projections | #1 in exec survey |
| **EPM (Estimated Plus-Minus)** | SPM + RAPM blend; "stabilized version of RAPM" | #2 in exec survey |
| **LEBRON** | RAPM + box score + various blend adjustments | Middle tier |
| **BPM 2.0** | Box-score-only approximation of RAPM | Simpler, slightly less predictive |
| **Raw RAPM** | Regularized adjusted plus-minus, 3-year window | Slow to update but ground-truth-ish |

Sources: [John Chen NBA Player Value Models](https://medium.com/@johnchenmbb/calculating-rapm-steps-1-and-2-of-my-summer-plan-1a78e1476b1f), [John Chen XGB-PM](https://medium.com/@johnchenmbb/xgb-pm-predicting-rapm-with-box-stats-and-more-cb3cea96d), [Dunks & Threes EPM page](https://dunksandthrees.com/about/epm), [DARKO Exploration Shiny app](https://apanalytics.shinyapps.io/DARKO/), [nbarapm.com](https://www.nbarapm.com/), [Hoops Hype execs survey](https://www.hoopshype.com/story/sports/nba/2021/09/17/advanced-stats-nba-real-plus-minus-rapm-win-shares-analytics/75615174007/), [APBR creating an SPM](https://apbr.org/metrics/viewtopic.php?t=10131).

### 2.3 Shot quality / tracking-data metrics

Second Spectrum / Hawk-Eye tracking data enables shot-level modeling:

| Metric | Source | Use |
|---|---|---|
| **qSQ (Quantified Shot Quality)** | Second Spectrum | Expected eFG given shot location, defender distance, shooter velocity |
| **qSI (Quantified Shooter Impact)** | Second Spectrum | eFG − qSQ: the "shot-making skill" residual |
| **ESQ / EFG+** | Second Spectrum | EFG minus ESQ; shooting above expectation |
| **xeFG** | Public | eFG with xFG substituted; league-implied expectation |
| **SSQM v2** | Sravan's blog | Open-source shot quality model |

Primary benefit: separates shot selection (offensive system) from shot making (individual skill). Crucial for projecting forward (shot-making regresses harder than shot selection).

Sources: [NBAstuffer qSQ explained](https://www.nbastuffer.com/analytics101/quantified-shot-quality-qsq/), [NBAstuffer qSI](https://www.nbastuffer.com/analytics101/quantified-shooter-impact-qsi/), [Sravan SSQM v1](https://blog.sradjoker.cc/posts/nba-shot-quality-1/) and [SSQM v2](https://blog.sradjoker.cc/posts/nba-shot-quality-2/), [Chang/Maheswaran Sloan paper](https://www.semanticscholar.org/paper/Quantifying-Shot-Quality-in-the-NBA-Chang-Maheswaran/2ef041e6d5b83979d37cb0526b7bcc9f63c5b59e), [Spatial Analysis of Basketball Shots](https://duddhawork.com/ballbook/shot-quality.html), [ShotQuality.com](https://shotquality.com/), [ESPN tracking insights](https://www.espn.com/nba/playoffs/2016/story/_/id/15530589/what-advanced-tracking-data-reveals-nba-shooters).

### 2.4 Pace / possessions

- Pace factor = possessions per 48 minutes. Must pace-adjust all counting stats.
- Offensive Rating = points per 100 possessions. Standard rate for offensive efficiency.
- Defensive Rating = opponent points per 100.
- Net Rating = difference. Best single-number team quality metric after four-factors.

### 2.5 Win-probability model frameworks

| Source | Approach |
|---|---|
| Inpredictable (Burke) | Empirical-frequency WP over score/time/possession/spread |
| Statmodeling (Gelman) | Model the expected point differential, not WP directly |
| Open-source hoopR / basic-nba-tutorials | XGBoost on score/time/spread features |
| ArXiv 2405.10453 (EPAA) | Bayesian hierarchical for player value; framework extends to WP |

Best-in-class for in-game WP uses Vegas spread + score + possession + time. For pre-game WP, our approach is Four Factors + DARKO-aggregated team rating + matchup adjustments (see model.py).

Sources: [Inpredictable calculator](https://www.inpredictable.com/2015/02/updated-nba-win-probability-calculator.html), [Gelman point diff](https://statmodeling.stat.columbia.edu/2014/02/25/differential/), [anpatton basic-nba-tutorials](https://github.com/anpatton/basic-nba-tutorials/blob/main/win_probability/make_win_probability_model.md), [Medium log5 tutorial](https://jorgepit-14189.medium.com/predict-basketball-games-with-log5-formula-2aa04c6bee9b), [Arxiv 1604.03186](https://arxiv.org/pdf/1604.03186), [Arxiv EPAA 2405.10453](https://arxiv.org/html/2405.10453v1), [Medium playoff Bayesian](https://medium.com/coemeta/nba-playoff-win-chances-via-bayesian-inference-83a6595fb95f).

## 3. Superseded / overrated metrics

- **Raw PER (Player Efficiency Rating)** — Hollinger-era; does not properly adjust for pace or defense. Deprecated by DARKO/EPM.
- **Win Shares** — similarly outmoded; box-score-based without plus-minus.
- **Raw plus-minus (without regularization)** — confounded by teammate quality.
- **Traditional box-score counting stats** (PPG, APG, RPG) — do not adjust for pace or usage. Avoid as primary inputs.
- **Hollinger's assist ratio** — better alternatives exist.

## 4. Stabilization thresholds

For in-season features:

| Statistic | N (possessions or games) for half-stability |
|---|---|
| Offensive Rating (team) | ~15-20 games |
| Defensive Rating (team) | ~20-25 games |
| eFG% (team) | ~20 games |
| TOV% (team) | ~25 games |
| Individual DARKO | daily updating; 500+ possessions give solid read |
| Individual RAPM | ~3000 possessions (~1-2 seasons) |
| 3P% (individual) | ~750 attempts |
| FT% | ~250 attempts |

**Shrinkage prior:** at < 10 games played, shrink hard toward previous season. Between 10-30 games, linear blend.

## 5. Kalshi-specific edge hypothesis

| Inefficiency | Mechanism | Exploitation |
|---|---|---|
| Rest / back-to-back underweighted | Retail markets often don't adjust enough for schedule spots | Model rest-days + travel-miles explicitly |
| Load management of stars | Kalshi sometimes lags Twitter/X injury reports by minutes | Fast lineup-news pipeline |
| Popular-team futures | Lakers/Warriors/Celtics championship odds often richer than model | Fade with futures |
| Early-season regression | Oct-Nov markets overweight early-season performance vs. season priors | Heavier Bayesian shrinkage |
| In-game live WP lag | Pace + spread priors often beat Kalshi live WP for 20-30s after significant runs | Scanner with live feed |

## 6. Open-source inventory

| Tool | Language | License | Use |
|---|---|---|---|
| [hoopR](https://github.com/sportsdataverse/hoopR) | R | MIT | Play-by-play + schedules |
| [py-hoopR](https://github.com/sportsdataverse/hoopR-py) | Python | MIT | Python port |
| [nba_api](https://github.com/swar/nba_api) | Python | MIT | Official stats.nba.com wrapper |
| [basketball-reference scraper](https://github.com/vishaalagartha/basketball_reference_scraper) | Python | MIT | Historical box scores |
| [anpatton basic-nba-tutorials](https://github.com/anpatton/basic-nba-tutorials) | Python | MIT | WP model reference |

## 7. Known blind spots (v1 model)

- No explicit possession-level model; game simulated as paired efficiency distribution.
- Back-to-back effects partially captured via DARKO (accounts for fatigue aggregate) but not rich travel-miles feature.
- Load management and star scratches: need real-time injury/lineup feed.
- No explicit lineup-fit (e.g., smallball vs. bigs matchup).
- College-to-NBA transition priors for rookies are very weak; heavy shrinkage.
- Does not model refereeing variation in fouls/free-throw rate.

## 8. Bibliography

1. Oliver, D. (2004). *Basketball on Paper: Rules and Tools for Performance Analysis*. Potomac Books.
2. [Basketball-Reference Four Factors](https://www.basketball-reference.com/about/factors.html)
3. [Arxiv 2305.13032 Four Factors Revisited](https://arxiv.org/abs/2305.13032)
4. [Cleaning the Glass Four Factors guide](https://cleaningtheglass.com/stats/guide/league_four_factors)
5. [Chris Gunther "Revisiting the Four Factors"](https://chartinghoops.substack.com/p/revisiting-the-four-factors)
6. [Statathlon Four Factors](https://statathlon.com/four-factors-basketball-success/)
7. [Introduction to Four Factors (Squared 2020)](https://squared2020.com/2017/09/05/introduction-to-olivers-four-factors/)
8. [John Chen NBA Player Value Models series](https://medium.com/@johnchenmbb/calculating-rapm-steps-1-and-2-of-my-summer-plan-1a78e1476b1f)
9. [John Chen XGB-PM](https://medium.com/@johnchenmbb/xgb-pm-predicting-rapm-with-box-stats-and-more-cb3cea96d)
10. [Dunks & Threes EPM methodology](https://dunksandthrees.com/about/epm)
11. [DARKO Exploration](https://apanalytics.shinyapps.io/DARKO/)
12. [nbarapm.com NBA data](https://www.nbarapm.com/)
13. [NBA Execs Survey — best catch-all stat](https://www.hoopshype.com/story/sports/nba/2021/09/17/advanced-stats-nba-real-plus-minus-rapm-win-shares-analytics/75615174007/)
14. [NBAstuffer qSQ](https://www.nbastuffer.com/analytics101/quantified-shot-quality-qsq/)
15. [NBAstuffer qSI](https://www.nbastuffer.com/analytics101/quantified-shooter-impact-qsi/)
16. [Sravan SSQM v1](https://blog.sradjoker.cc/posts/nba-shot-quality-1/) and [v2](https://blog.sradjoker.cc/posts/nba-shot-quality-2/)
17. [Chang/Maheswaran, Sloan](https://www.semanticscholar.org/paper/Quantifying-Shot-Quality-in-the-NBA-Chang-Maheswaran/2ef041e6d5b83979d37cb0526b7bcc9f63c5b59e)
18. [anpatton basic-nba-tutorials WP model](https://github.com/anpatton/basic-nba-tutorials/blob/main/win_probability/make_win_probability_model.md)
19. [Inpredictable WP Calculator](https://www.inpredictable.com/2015/02/updated-nba-win-probability-calculator.html)
20. [Gelman — model the point differential](https://statmodeling.stat.columbia.edu/2014/02/25/differential/)
21. Arxiv 2405.10453 "Expected Points Above Average: A Novel NBA Player Metric Based on Bayesian Hierarchical Modeling"
