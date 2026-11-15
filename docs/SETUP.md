# Setup

## Local

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-scanner.txt
# optional, for full MLB/NBA/NFL data + training:
pip install nfl_data_py mlb_data_py nba_api scikit-learn pandas numpy

# Run the scanner once
python -m scanner.scan

# Run the full backtest
python -m backtest.run_all

# Refresh calibration
python -m calibration.refresh
```

`PYTHONPATH` should be the repo root; the top-level `Makefile` (or plain
`python -m …` from the repo root) handles this.

## Kalshi API credentials

Set an environment variable before running the scanner:

```bash
export KALSHI_API_KEY="your-key-here"
```

The scanner falls back to deterministic fixture data when `KALSHI_API_KEY`
is absent or unreachable — useful for local dashboard development.

## Strava API credentials

1. Create an app at <https://www.strava.com/settings/api>. Set
   **Authorization Callback Domain** to `localhost`.
2. Export the app's credentials:

   ```bash
   export STRAVA_CLIENT_ID="12345"
   export STRAVA_CLIENT_SECRET="..."
   ```
3. Run the one-time OAuth flow (opens a URL, you paste back the redirect):

   ```bash
   python -m integrations.strava auth
   ```
   Tokens are saved to `secrets/strava_token.json` (gitignored). The client
   refreshes the 6-hour access token automatically and persists rotated
   refresh tokens.
4. Verify: `python -m integrations.strava whoami` /
   `python -m integrations.strava activities -n 5`.

For CI, add `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` and
`STRAVA_REFRESH_TOKEN` as Actions secrets. Rate limits are 200 requests /
15 min and 2,000 / day by default; the client backs off on 429s.

## GitHub Pages deployment

1. Push the repo to GitHub (see below for the PAT push).
2. In **Settings → Pages**: source = **GitHub Actions**.
3. In **Settings → Secrets and variables → Actions**: add secret
   `KALSHI_API_KEY`.
4. The two workflows run automatically:
   - `pages.yml` deploys `dashboard/` on every push to `main`.
   - `scanner.yml` runs every 20 minutes + daily calibration at 08:00 UTC.

## Pushing to a fresh private repo (first push)

Run these once, from the repo root, replacing `alee0910`:

```bash
git init -b main
git add .
git commit -m "kalshi-sports-edge v1 (MLB/NBA/NFL live, 7 sports stubbed)"
git remote add origin https://YOUR_PAT@github.com/alee0910/kalshi-sports-edge.git
git push -u origin main
```

Then revoke the PAT URL from `.git/config` (`git remote set-url origin
https://github.com/alee0910/kalshi-sports-edge.git`) so the token stops
living on disk.

## Training models (optional, local only)

Training scripts need historical data and are designed to run locally,
not in CI (CI has no data-source credentials or meaningful storage).

```bash
# MLB
python models/mlb/training.py --start-season 2018 --end-season 2025 --holdout-season 2026
# NBA
python models/nba/training.py --start-season 2019 --end-season 2024 --holdout-season 2025
# NFL
python models/nfl/training.py --start-season 2015 --end-season 2024 --holdout-season 2025
```

Each writes `models/<sport>/coefs.json` which the scanner loads at runtime.

## Risk controls

Before going live with real capital:

- Confirm `strategies/registry.py::GLOBAL.jurisdiction_blocklist` matches
  current Kalshi legal status (check [docs/DISCLAIMER.md](DISCLAIMER.md)).
- Confirm every strategy you intend to run shows `shadow_mode=False`.
- Verify `scanner/scan.py` is writing `candidates.json` under
  `dashboard/data/` and the dashboard is rendering them correctly.
- Read `docs/RUNBOOK.md` for the daily on-call checklist.

Never increase Kelly fractions above the values in `registry.py` without
first running a revised backtest and Phase 2.5-style self-critique.
