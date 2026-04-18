# kalshi-sports-edge

**Research-only** system for identifying mispricings in Kalshi's sports event
contracts. Covers MLB, NBA, and NFL in v1; NHL, golf, tennis, soccer, college
basketball, MMA, and NASCAR/F1 have literature stubs and placeholder models.

This is **not investment advice**. Read [docs/DISCLAIMER.md](docs/DISCLAIMER.md)
before anything else.

## What this is

Eight-phase system per the original design brief:

0. **Scaffolded repo** — clean directory structure, consistent imports.
1. **Kalshi microstructure research** — fee math, contract taxonomy, liquidity
   profile, 20-source bibliography. See `research/kalshi/`.
2. **Domain research & models per sport**
   - MLB, NBA, NFL fully built: literature review (~20 sources each), feature
     spec, dataclass model, training harness, data pipeline.
   - Other seven sports: literature stubs + placeholder models with
     `not_yet_built = True`.
3. **Six strategy specs** (`strategies/S01..S06_*.md`) + `registry.py` —
   everything fee-aware, Kelly-sized, with correlation caps and jurisdiction
   blocklist.
4. **Backtest framework** (`backtest/`) — fee-aware walk-forward engine
   with literature-calibrated synthetic snapshots. Phase 4 findings are in
   `backtest/FINDINGS.md`; three of six strategies enter v1.1 **shadow mode**
   pending live-data calibration.
5. **Live dashboard** (`dashboard/`) — static GitHub Pages site with three
   tabs: Live candidates, Backtest, Calibration.
6. **Scanner + GitHub Actions** — `.github/workflows/scanner.yml` runs every
   20 minutes, writes candidate lists to `dashboard/data/latest.json`.
7. **Calibration loop** (`calibration/`) — daily 08:00 UTC cron aggregates
   the rolling 30-day scan window against Kalshi settlements, emits
   reliability curves per strategy and per sport.
8. **This README + SETUP + DISCLAIMER + LICENSE.**

## Ten-second repo map

```
research/
  kalshi/          microstructure.md, fees.py, client.py
  domain/          mlb_literature_review.md, nba_*, nfl_*, STUB_other_sports.md
  self_critique.md Phase 2.5 grades & revisions
models/
  mlb/, nba/, nfl/     # data_pipeline.py, features.md, model.py, training.py, README.md
  nhl/, golf/, tennis/, soccer/, cbb/, mma/, nascar/   # stubs, not_yet_built=True
strategies/
  S01_favorite_longshot_fade.md   ...  S06_stale_reprice_arb.md
  registry.py                              # canonical Strategy dataclasses
backtest/
  engine.py  synthetic_data.py  run_all.py  FINDINGS.md  results/
scanner/
  scan.py                                  # the thing the cron runs
calibration/
  refresh.py                               # nightly reliability refresh
dashboard/
  index.html  style.css  app.js
  data/latest.json  data/backtest_summary.json  data/calibration.json
.github/workflows/
  scanner.yml   pages.yml
docs/
  DISCLAIMER.md  SETUP.md  RUNBOOK.md
```

## Verdict so far

- MLB/NBA/NFL models implement the mainstream sabermetric/analytics canon
  (EPA/CPOE/Stuff+/Four Factors/DARKO) to the depth that's credibly
  achievable from public data. The NBA model was revised in Phase 2.5 for
  overconfidence on extreme matchups.
- Synthetic backtest suggests only **S02 (MLB starter news)** is clearly
  profitable post-fee in v1. S01 and S04 are marginal. S03/S05/S06 are in
  shadow mode until live data confirms the edge.
- Dashboard deploys at `https://alee0910.github.io/kalshi-sports-edge/`
  once GitHub Pages is enabled for the repo.

## Start here

- [`docs/SETUP.md`](docs/SETUP.md) — how to run this locally and deploy the
  live scanner.
- [`docs/DISCLAIMER.md`](docs/DISCLAIMER.md) — legal, jurisdictional,
  risk-of-ruin.
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — on-call playbook when the scanner
  breaks or when calibration drifts.
- [`research/self_critique.md`](research/self_critique.md) — honest
  Phase 2.5 grading of each model.
- [`backtest/FINDINGS.md`](backtest/FINDINGS.md) — the backtest reality
  check.
