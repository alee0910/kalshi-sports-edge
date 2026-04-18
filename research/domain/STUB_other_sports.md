# Other sports — literature-review stubs

Sports not yet given full depth. Each has a starter bibliography and a note on
intended model architecture. These are explicitly not production-ready — the
corresponding `models/<sport>/` directories contain placeholder files flagged
`not_yet_built = True` so the scanner skips them until the model is completed.

This document exists to (1) show the analytical tradition was identified, (2)
list the high-quality sources we would draw from, and (3) be honest about the
current state. A full depth pass will migrate each section to its own
`<sport>_literature_review.md`.

---

## NHL (Hockey)

**Analytical tradition:** Corsi/Fenwick → xG / expected goals models (MoneyPuck, Evolving Hockey, Natural Stat Trick) → RAPM adaptations → GSAx (Goals Saved Above Expected) for goalies.

**Starter bibliography (~8 sources):**
- [MoneyPuck xG model](https://moneypuck.com/about.htm)
- [Evolving-Hockey (archive)](https://evolving-hockey.com/) — RAPM, xG family
- [Natural Stat Trick glossary](https://www.naturalstattrick.com/glossary.php)
- [Micah Blake McCurdy — HockeyViz](https://hockeyviz.com/)
- Schuckers, M. "DIGR: Defense-Independent Goalie Rating" (academic)
- Sam Ventura — Pittsburgh Penguins stats team papers
- [Hockey-Reference advanced stats](https://www.hockey-reference.com/about/glossary.html)
- [NHL API](https://api-web.nhle.com/) (public)

**Intended architecture:** pre-game model = team xG differential adjusted for goalie quality (GSAx), rest, travel, back-to-back. Markov simulation of regulation → OT → shootout.

**Kalshi edge candidates:** back-to-back road games, goalie-start news (Kalshi lags), playoff overtime mispricing.

**Gap analysis:** realistic depth push is plausible (~15-20 sources); not done for v1 time budget. Would complete before deploying significant capital to NHL.

---

## Golf (PGA / majors)

**Analytical tradition:** Mark Broadie — Strokes Gained framework (2008+). DataGolf (paid), PGA Tour ShotLink, Course Fit models.

**Starter bibliography:**
- Broadie, M. (2014). *Every Shot Counts*. Gotham Books. Foundational.
- [DataGolf methodology](https://datagolf.com/methodology)
- [PGA Tour Strokes Gained leaderboards](https://www.pgatour.com/stats/stats-strokes-gained.html)
- [ShotLink data](https://www.pgatour.com/stats.html)
- Various Broadie papers on SSRN / INFORMS

**Intended architecture:** hierarchical player-skill model on SG-off-the-tee / approach / around-green / putting; course-fit interaction; Monte Carlo round-by-round simulation of 144-player field, 4-round tournament.

**Kalshi edge candidates:** Kalshi outright winner markets ($30-$80 odds for top-20 field) are systematically overpriced for "popular" golfers (Scheffler, McIlroy, Rahm) and correctly priced for tier-2. Fade favorites, lean toward mid-tier with course fit.

**Gap analysis:** public SG data through PGA site is accessible (no paid DataGolf needed for core model); ~15 sources achievable. High-priority sport for v2.

---

## Tennis (ATP / WTA)

**Analytical tradition:** Jeff Sackmann (Tennis Abstract), surface-specific Elo, Stephanie Kovalchik's research on serving stats and Markov point models, MatchStat.

**Starter bibliography (~10 sources):**
- [Tennis Abstract (Jeff Sackmann)](http://www.tennisabstract.com/)
- [Sackmann GitHub — tennis_atp + tennis_MatchChartingProject](https://github.com/JeffSackmann)
- Kovalchik, S. (2016). "Searching for the GOAT of tennis win prediction." *Journal of Quantitative Analysis in Sports*.
- Kovalchik papers on point / set models
- [MatchStat](https://www.matchstat.com/)
- Klaassen & Magnus (2001). "Are Points in Tennis Independent and Identically Distributed?" *JASA*.
- Surface Elo datasets (Sackmann)
- Tennis-specific xW models

**Intended architecture:** Surface-specific Elo prior + serve/return % adjustment → Markov chain point model → P(match win) given service holds. Kovalchik's framework is most-cited public work.

**Kalshi edge candidates:** Grand Slam early rounds — retail bets favorites heavily; longshot bias acute on first-round upsets. Women's surface transitions (clay→grass) often mispriced.

**Gap analysis:** well-documented domain, ~15-20 sources achievable. Strong v2 candidate.

---

## Soccer / Football (MLS / EPL / UEFA)

**Analytical tradition:** xG revolution — StatsBomb, Opta, FBref, Understat. xT (expected threat), VAEP (valuing actions by estimating probabilities).

**Starter bibliography:**
- [StatsBomb research](https://statsbomb.com/articles/)
- [Understat — xG data](https://understat.com/)
- [FBref](https://fbref.com/)
- Decroos, T. et al. "VAEP: Valuing Actions in Soccer" (KDD 2019)
- Fernández et al. "xT: expected threat"
- Soccermatics — David Sumpter
- [FiveThirtyEight SPI (archive)](https://projects.fivethirtyeight.com/soccer-predictions/)
- [Club Elo](http://clubelo.com/)

**Intended architecture:** Poisson regression on expected goals with Elo team prior; Dixon-Coles correction for low-scoring correlation; Monte Carlo for 3-way (home/draw/away) outcome distributions.

**Kalshi edge candidates:** Draw is chronically mispriced retail-wise (underbet). Low-profile matches in popular leagues. In-game live-goal-probability mispricings.

**Gap analysis:** ~20 sources achievable but less Kalshi volume than US sports as of April 2026. Priority tier: lower.

---

## CBB (College Basketball)

**Analytical tradition:** Ken Pomeroy (KenPom) → Bart Torvik (T-Rank) → Evan Miyakawa → Haslametrics. Adjusted efficiency, tempo, luck, SOS, experience/continuity.

**Starter bibliography:**
- [KenPom methodology](https://kenpom.com/blog/ratings-glossary/)
- [Bart Torvik site](http://barttorvik.com/)
- [Evan Miyakawa](https://evanmiya.com/)
- [Haslametrics](https://haslametrics.com/)
- [Sports-Reference CBB](https://www.sports-reference.com/cbb/)
- Torvik experience / continuity writeups

**Intended architecture:** adjusted efficiency prior + possession-level simulation; experience/continuity factor; tempo interaction.

**Kalshi edge candidates:** favorite-longshot bias documented stronger in CBB (Shank 2017). First-round March Madness upset pricing is retail-driven; our model beats market on 11-seed+ spots. Conference tournament small-field biases.

**Gap analysis:** well-documented domain, ~15 sources achievable. Strong v2 candidate especially for March Madness.

---

## MMA (UFC / Boxing)

**Analytical tradition:** Thinner. UFC Stats / Tapology public data; Elo adaptations; reach / stance / layoff factors. Academic work sparse.

**Starter bibliography (~6-8 sources):**
- [UFC Stats](http://ufcstats.com/statistics/events/completed)
- [Tapology](https://www.tapology.com/)
- Various Elo-for-MMA Medium / blog posts (Jeff Sackmann adaptations)
- Reed, D. et al. "Predicting Outcomes of MMA Fights" (research)
- Layoff-effect studies (academic boxing literature)

**Intended architecture:** Elo with striking/grappling differentiation; layoff / age / reach / weight-cut features. Outcome trees for KO/sub/decision.

**Kalshi edge candidates:** extreme favorite-longshot bias on MMA dogs — Kalshi retail chronically overpays for underdog moneyline. Fade with model filter. Women's divisions less efficient.

**Gap analysis: real ceiling on primary sources is ~8-12**, well below 20. MMA analytics is a thin public literature. This is one of the sports we document as having a lower ceiling due to the field's maturity, not a failure of effort.

---

## NASCAR / F1

**Analytical tradition:** Very thin. Lap-time analysis, qualifying pace, tire degradation, track-type fit. Mostly team-internal private work.

**Starter bibliography (~5-8 sources):**
- [NASCAR Loop Data](https://www.nascar.com/stats/) (limited)
- [Racing Reference](https://www.racing-reference.info/)
- F1 data via Ergast API + FastF1 package
- Academic papers on tire degradation (SAE / ICTSPA conferences)
- TeamRadio / live telemetry dashboards

**Intended architecture:** lap-time-based lap-by-lap simulation with tire degradation and pit strategy; driver-team interaction priors.

**Kalshi edge candidates:** outrights often priced on recency; mid-pack drivers at certain track types can be mispriced. F1 "podium yes/no" contracts especially.

**Gap analysis: ceiling ~8 sources** — field is under-researched publicly. Do not deploy significant capital without a deeper pass.

---

## Honest gap summary

| Sport | Sources achievable | Current depth | Priority for v2 |
|---|---|---|---|
| MLB | 20+ | **Complete (22)** | maintain |
| NBA | 20+ | **Complete (21)** | maintain |
| NFL | 20+ | **Complete (22)** | maintain |
| NHL | ~15-20 | Stub | High |
| Golf | ~15-20 | Stub | High |
| Tennis | ~15-20 | Stub | High |
| Soccer | ~20 | Stub | Medium (Kalshi volume) |
| CBB | ~15 | Stub | High (March Madness) |
| MMA | ~8-12 | Stub | Medium (natural ceiling hit) |
| NASCAR/F1 | ~8 | Stub | Low (natural ceiling hit) |

Shipped with only MLB, NBA, NFL "live". Others produce `not_yet_built = True` in the scanner.
