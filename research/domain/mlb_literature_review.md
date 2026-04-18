# MLB — Literature Review

_Target: ~20 primary sources. Achieved: 22. Status: complete for v1 model._

Goal: identify the frontier of baseball analytics for the purpose of estimating true win probabilities on Kalshi single-game, series, and futures contracts, distinguishing metrics with predictive value from those that are merely descriptive or outdated.

## 1. Analytical tradition

Baseball is the oldest and deepest-instrumented analytical tradition in sports. The modern arc: Bill James's *Baseball Abstracts* (1977-1988) → Tom Tango / MGL / Andrew Dolphin, *The Book* (2007) → Baseball Prospectus (1996+) → FanGraphs (2004+) → Statcast (2015+) → Stuff+/Pitching+/PitchingBot (2021+) → THE BATcast (2024+). The current frontier is pitch-level and batted-ball-level physical modeling blended with Bayesian hierarchical estimation of player skill.

Key practitioners whose work informs this review: Tom Tango, Bill James, Russell Carleton, Mitchel Lichtman (MGL), Jeff Zimmerman, Eno Sarris, Max Bay, Harry Pavlidis, Jeremy Greenhouse, Adam Salorio, Ethan Moore, Driveline Baseball R&D.

## 2. Frontier metrics (≥ 2023 consensus)

Organized by what they predict.

### 2.1 Hitter quality (predictive)

| Metric | Underlying signal | Stabilization N (PA) | Predictive r² vs. next-season wOBA |
|---|---|---|---|
| **xwOBA** (Statcast) | Batted-ball exit velocity + launch angle → expected wOBA per BBE | ~150-200 | ~0.22 |
| **wOBA** | Weighted runs-per-event linear weights | ~450 PA | ~0.19 |
| **wRC+** | Park + league-adjusted offensive runs vs. league avg (scaled to 100) | ~450 PA | ~0.20 |
| **BB%** | Walk rate | ~120 PA | ~0.55 (very stable) |
| **K%** | Strikeout rate | ~60 PA | ~0.65 (most stable skill) |
| **HR/FB%** | Homer rate on fly balls | ~300 PA | ~0.14 |
| **Barrel rate** (Statcast) | % of batted balls with EV ≥ 98 mph + optimal launch angle | ~50 BBE | high — good early-season signal |
| **Hard-hit rate** | % BBE with EV ≥ 95 mph | ~50 BBE | medium-high |

**Verdict for modeling:** prefer xwOBA + K% + BB% + barrel rate as core offensive inputs. wOBA alone is fine at full season. Early season, weight xwOBA higher because of faster stabilization.

Sources: [FanGraphs wOBA](https://library.fangraphs.com/offense/woba/), [xwOBA MLB glossary](https://www.mlb.com/glossary/statcast/expected-woba), [MLB Technology Blog xwOBA intro](https://technology.mlblogs.com/an-introduction-to-expected-weighted-on-base-average-xwoba-29d6070ba52b), [Russell Carleton stabilization rates (BP archive)](https://www.baseballprospectus.com/news/).

### 2.2 Pitcher quality (predictive) — frontier

The most important recent shift: **Stuff+ / Pitching+ / PitchingBot** eclipsed ERA, FIP, xFIP, SIERA as the predictive standard for pitchers.

| Metric | Underlying signal | Stabilization | Predictive power |
|---|---|---|---|
| **Stuff+** (FanGraphs, Driveline) | Pitch physics (velocity, spin, vertical/horizontal break, release point) → predicted run value per pitch | ~80 pitches | **Highest** of single-metric pitcher stats |
| **Pitching+** | Stuff+ + Location+ + count-state → holistic pitcher quality | ~150 pitches | Comparable to Stuff+; better on control-dependent types |
| **Location+** | Pitch location vs. count/batter-handedness run value | ~200 pitches | Weaker than Stuff+ alone; useful component |
| **PitchingBot** (FanGraphs) | Alt pitch model (Cameron Grove); two flavors | ~80 pitches | Roughly equivalent |
| **xFIP** | ERA estimator using league-average HR/FB | ~150 IP | Moderate |
| **SIERA** | More sophisticated ERA estimator | ~150 IP | Moderate |
| **DRA** (Baseball Prospectus) | Deserved Run Average, mixed model approach | Full season | Moderate-high but slow to compute |
| **ERA** | Runs allowed per 9 (luck-laden) | never really stabilizes | **Outdated. Avoid as primary input.** |
| **Pitcher Wins** | Win/loss record | N/A | **Uselessly noisy. Do not use.** |

**Verdict for modeling:** Stuff+ per-pitch-type as primary input, Pitching+ as secondary. SIERA as backup when Stuff+ unavailable (e.g., minor-league call-ups). Never use ERA as the dominant predictive signal; treat as outcome variable only.

Sources: [FanGraphs Stuff+ primer](https://library.fangraphs.com/pitching/stuff-location-and-pitching-primer/), [Stuff+ launch post](https://blogs.fangraphs.com/pitchingbot-and-stuff-pitch-modeling-are-now-on-fangraphs/), [Driveline updated methodology May 2024](https://www.drivelinebaseball.com/2024/05/revisiting-stuff-plus/), [Driveline original Dec 2021](https://www.drivelinebaseball.com/2021/12/what-is-stuff-quantifying-pitches-with-pitch-models/), [PitchingBot primer](https://library.fangraphs.com/pitching/pitchingbot-pitch-modeling-primer/), [Adam Salorio Stuff+ build](https://medium.com/@adamsalorio/introducing-my-stuff-model-2840f196cf01), [Baseball Prospectus "Updated Evaluation of Hitting and Pitching Metrics"](https://www.baseballprospectus.com/news/article/82426/prospectus-feature-an-updated-evaluation-of-hitting-and-pitching-including-stuff-metrics/), [FanGraphs "They don't make pitch models like they used to"](https://blogs.fangraphs.com/they-dont-make-pitch-models-like-they-used-to/), [THE BATcast launch](https://blogs.fangraphs.com/introducing-the-bat-x-for-pitchers-and-the-batcast-stuff-model/).

### 2.3 Defense (predictive)

| Metric | Source | Notes |
|---|---|---|
| **OAA** (Outs Above Average) | Statcast | Range-based; full outfielders; partial infielders. Current frontier. |
| **DRS** (Defensive Runs Saved) | Baseball Info Solutions | Older. Still widely used. |
| **UZR** (Ultimate Zone Rating) | FanGraphs (Mitchel Lichtman) | Older; higher noise. |
| **Catcher Framing Runs** | Statcast / Baseball Prospectus | Stable across years (r ≈ 0.6). ~0.135 runs per extra strike. |
| **Pop time** (catcher) | Statcast | Describes throws; less predictive of wins than framing. |

**Verdict:** Use OAA + catcher framing runs. DRS as secondary. Avoid UZR except long samples. Catcher framing is the single most overlooked team-level defensive input — a good framer is worth ~15 runs/year, roughly 1.5 wins.

Sources: [FanGraphs catcher defense library](https://library.fangraphs.com/defense/catcher-defense/), [FanGraphs framing launch](https://blogs.fangraphs.com/fangraphs-pitch-framing/), [Beyond the Box Score framing comparison](https://www.beyondtheboxscore.com/2019/3/25/18279548/framing-fangraphs-baseball-prospectus-statcorner-catchers-grandal-mathis-barnes-contreras-stassi), [Statcast framing leaderboard](https://baseballsavant.mlb.com/leaderboard/catcher-framing), [Ben Wiener expected strike difference](https://blog.benwiener.com/baseball/2024/08/31/expected-strike-diffence.html).

### 2.4 Team-level / game-context

| Metric | Use |
|---|---|
| **Park factors** (by batter/pitcher handedness, batted-ball type) | Adjust xwOBA and Stuff+ for venue |
| **Base-out run expectancy (RE24)** | In-game WP and simulation base |
| **Pythagenpat** (pythagenport with dynamic exponent) | Team win-rate from runs/allowed — baseline prior |
| **Weather** (temp, wind, humidity) | Affects HR rate; marginal but real |

Sources: [Tom Tango run expectancy framework](http://tangotiger.com/index.php/site/article/run-expectancy-by-the-24-base-out-states), [Wikipedia wOBA](https://en.wikipedia.org/wiki/WOBA).

## 3. Superseded / overrated metrics

Do NOT treat these as primary predictors:

- **Pitcher Wins / Losses** — luck-dominated; no predictive signal.
- **RBI** — highly park/lineup dependent.
- **Batting Average** — worse than OBP or wOBA for predicting runs.
- **Fielding Percentage** — doesn't account for range.
- **ERA** — heavy luck component via BABIP + sequence noise. Use SIERA / xFIP / Stuff+ instead.
- **Save / Hold** — bullpen usage artifact, not skill signal.

## 4. Stabilization / sample-size handbook

Drawn from Russell Carleton's foundational work on reliability. Do not train features on samples below these thresholds without explicit shrinkage toward prior.

| Statistic | N for r = 0.5 (half signal) |
|---|---|
| K% (batter or pitcher) | ~60 PA / BF |
| BB% | ~120 PA / BF |
| Barrel rate (Statcast) | ~50 BBE |
| Hard-hit rate | ~50 BBE |
| Stuff+ | ~80 pitches |
| GB% | ~150 BBE |
| BABIP (batter) | ~800 PA (!) |
| BABIP (pitcher) | ~2000+ BF (pitcher BABIP famously never stabilizes much) |
| wOBA | ~450 PA |
| Catcher framing | ~1000 chances |

**Implication for modeling:** for any in-season feature with N below the stabilization threshold, shrink to league mean or player's prior-season value with a weight proportional to N / (N + N_stabilize).

## 5. Monte Carlo simulation methodology

The state of the art for game-by-game win probability is:

1. **Plate appearance model**: given batter skill, pitcher skill, defender OAA, park, weather, count → distribution over PA outcomes {K, BB, HBP, 1B, 2B, 3B, HR, OUT-in-play}. Modern implementations use gradient-boosted trees (LightGBM, XGBoost) or neural nets over ~1M training PAs.
2. **Base-out state transition**: given PA outcome and base-out state, advance baserunners. Markov model based on empirical transition matrices.
3. **Simulation loop**: 5000–10000 simulated games per matchup to get P(home win) and run-distribution variance.
4. **Bayesian prior**: blend the per-game simulation with a team-level prior (Pythagenpat or log5-adjusted team strength) to handle cold-start early season.

Sources: [Swartz & Hui 2011 "Two-Stage Bayesian Model for MLB"](https://www.sfu.ca/~tswartz/papers/mlb.pdf), [Monte Carlo MLB GitHub](https://github.com/snoozle-software/monte-carlo-mlb), [MLB Prediction site methodology](https://mlbprediction.com/mlb-game-simulation-models.html), [Arxiv 2505.05120 Bayesian MLB simulation](https://arxiv.org/html/2505.05120v1), [Rishi Gundakaram Medium MC writeup](https://medium.com/@rishi.gundakaram/baseball-forecasting-using-monte-carlo-simulation-f789ba0abee2), [FullCountProps methodology](https://www.fullcountprops.com/methodology), [SharpAlpha MC intro](https://sharpalpha.substack.com/p/an-intro-to-monte-carlo-simulation), [Nick Faddis ML WP](https://medium.com/@nfadd/predicting-win-probability-for-mlb-games-with-machine-learning-a4c2ad993496).

## 6. Open-source implementations inventory

| Project | Language | License | Usefulness |
|---|---|---|---|
| [baseballr](https://github.com/BillPetti/baseballr) | R | MIT | Scrapes Statcast + MLB API. Best-in-class for pulling data. |
| [pybaseball](https://github.com/jldbc/pybaseball) | Python | MIT | Python port. Statcast download, Lahman, FanGraphs. **Primary dep for our pipeline.** |
| [baseball-datapull](various) | Python | N/A | Ad-hoc scrapers. Use pybaseball instead. |
| [snoozle-software/monte-carlo-mlb](https://github.com/snoozle-software/monte-carlo-mlb) | Python | MIT | Reference implementation for MC WP. |
| [MLB Stats API](https://statsapi.mlb.com/) | — | Free | Official live feed. No auth needed for basic use. |
| [Baseball Savant](https://baseballsavant.mlb.com/) | — | Free | Statcast leaderboards + game-level CSV exports. |

We will primarily use **pybaseball** + MLB Stats API for live data. Build Stuff+ replication against Savant pitch-level data.

## 7. Expected Kalshi-specific edge sources

Linking lit review findings to Phase 1 structural inefficiencies:

1. **Market priors on starting pitchers are often noisy** — markets anchor on ERA/W-L; we will use Stuff+ + Pitching+ rolling averages, which reprice pitcher quality faster after a hot/cold stretch.
2. **Lineup changes (late scratches) move Kalshi less than they should** — a backup catcher vs. starter can shift framing runs by 2-3 runs per game; a 5-star platoon matchup can shift team wOBA by 15+ points.
3. **Weather edges**: MLB outdoor venues with >15 mph out-to-RF winds move HR rate ~30%. Kalshi usually reprices late.
4. **Series Bayesian updates** frequently overreact (per Phase 1 doc section 6.5). Our model provides principled update size from log5 / pythag.
5. **Futures (division/pennant):** retail overweights popular teams (Yankees, Dodgers, Braves). Our model uses team-strength priors not affected by popularity.

## 8. Known blind spots

- **Injuries** — our data pipeline needs reliable injury feed. Free MLB injury data is imperfect; we may miss same-day scratches.
- **Bullpen usage** — workload modeling (recent back-to-back, piggyback patterns) is hard. Market sometimes has better info from beat reporters.
- **Umpire effects** — home-plate ump influences called strike zone, which interacts with Stuff+/framing. We will include ump as a feature but umpire metadata is sparse pre-first-pitch.
- **Cold-start early season** — before ~50 PAs of data, shrink heavily to priors. Avoid trading April games with low model confidence.

## 9. Bibliography

1. Tango, T., Lichtman, M., Dolphin, A. (2007). *The Book: Playing the Percentages in Baseball*. Potomac Books.
2. James, B. (annual). *Baseball Abstract* / *Bill James Handbook*.
3. Carleton, R. ["Stabilization Rates for MLB Offensive Statistics"](https://www.baseballprospectus.com/news/) (series, BP archive).
4. [FanGraphs wOBA library page](https://library.fangraphs.com/offense/woba/)
5. [Wikipedia — wOBA](https://en.wikipedia.org/wiki/WOBA)
6. [Baseball Prospectus — Siren Song of xwOBA for Pitchers](https://www.baseballprospectus.com/news/article/40026/prospectus-feature-siren-song-statcasts-expected-metrics/)
7. Sharpe, S. ["An Introduction to Expected Weighted On-Base Average"](https://technology.mlblogs.com/an-introduction-to-expected-weighted-on-base-average-xwoba-29d6070ba52b) MLB Technology Blog
8. [Statcast Expected Stats leaderboard](https://baseballsavant.mlb.com/leaderboard/expected_statistics)
9. Nestico, T. ["Modelling xwOBA with KNN"](https://medium.com/@thomasjamesnestico/modelling-xwoba-with-knn-9b004e93861a)
10. Salorio, A. ["Exploring Key Metrics and Methodology for Analyzing Offensive Performance"](https://adamsalorio.substack.com/p/exploring-key-metrics-and-methodology-2b7)
11. Salorio, A. ["Introducing My Stuff+ Model"](https://medium.com/@adamsalorio/introducing-my-stuff-model-2840f196cf01)
12. [FanGraphs Stuff+/Location+/Pitching+ primer](https://library.fangraphs.com/pitching/stuff-location-and-pitching-primer/)
13. [FanGraphs PitchingBot primer](https://library.fangraphs.com/pitching/pitchingbot-pitch-modeling-primer/)
14. [Driveline: What is Stuff+?](https://www.drivelinebaseball.com/2021/12/what-is-stuff-quantifying-pitches-with-pitch-models/)
15. [Driveline: Revisiting Stuff+ (May 2024)](https://www.drivelinebaseball.com/2024/05/revisiting-stuff-plus/)
16. [Baseball Prospectus — Updated Evaluation of Hitting and Pitching Metrics](https://www.baseballprospectus.com/news/article/82426/prospectus-feature-an-updated-evaluation-of-hitting-and-pitching-including-stuff-metrics/)
17. [FanGraphs — THE BATcast Stuff Model](https://blogs.fangraphs.com/introducing-the-bat-x-for-pitchers-and-the-batcast-stuff-model/)
18. [FanGraphs — catcher defense library](https://library.fangraphs.com/defense/catcher-defense/)
19. [MLB Glossary — Catcher Framing](https://www.mlb.com/glossary/statcast/catcher-framing)
20. Swartz, T.B., Hui, T.K. (2011). ["A Two-Stage Bayesian Model for MLB Winners"](https://www.sfu.ca/~tswartz/papers/mlb.pdf)
21. [Analyzing Baseball Data with R — framing chapter](https://beanumber.github.io/abdwr3e/07-framing.html)
22. Arxiv 2505.05120 — ["Simulating MLB Seasons using Bayesian Inference"](https://arxiv.org/html/2505.05120v1)
