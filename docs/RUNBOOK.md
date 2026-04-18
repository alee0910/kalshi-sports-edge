# Runbook

Daily on-call checklist and common failure modes.

## Morning checklist

1. **Dashboard check.** Open the Pages URL. Confirm `Last scan` timestamp
   is within the last 30 minutes during active hours (or within 60 if
   overnight).
2. **Live vs shadow split.** On the Live tab, confirm the number of live
   candidates is not abnormally high (e.g. >30 means a probable model or
   market-feed error).
3. **Calibration tab.** If `warming_up=true`, no action needed — the
   system hasn't accumulated 30 settled samples yet. Once past the warm-up
   window, flag any strategy whose `log_loss > 0.70` for a week running.
4. **GitHub Actions.** Check the last `scanner.yml` run went green. If the
   last 3 runs are red, freeze live trading and investigate.

## Common failures

### Scanner's `live fetch failed`

Visible in GitHub Actions logs as `ProxyError` or `401 Unauthorized`.
- `401`: the Kalshi API key has been rotated or is invalid. Update the
  `KALSHI_API_KEY` repo secret; the next cron run picks it up.
- `ProxyError` / `DNS`: transient; the scanner falls back to fixtures and
  writes a valid `latest.json`. No action needed unless 3+ runs are affected.

### Dashboard shows no data

Check `dashboard/data/latest.json` is present on `main`. If not:
- The scanner workflow might not have permission to push back. Confirm
  `permissions: contents: write` is still in `scanner.yml`.
- Pages deploy might be stuck; trigger `pages.yml` manually via
  **Actions → Deploy dashboard to GitHub Pages → Run workflow**.

### Model returns `not_yet_built`-style error for MLB/NBA/NFL

This should be impossible for v1 sports. Check that `training.py` has been
run locally and `models/<sport>/coefs.json` was committed. The data
pipeline falls back to `1500` baseline Elo / `115.0` league ORtg if coefs
are missing; that's a degraded but non-erroring state.

### Unexpected live candidate explosion

If Live tab suddenly shows 50+ candidates:
- A market-data feed error is the most likely cause (stale bids mis-read).
  Cross-check a sample candidate against Kalshi's web UI.
- If the feed is correct, our model just produced an outlier. Verify
  `calibration.json` hasn't flipped for the relevant sport; if it has,
  revert to the prior model checkpoint.

## Manual kill switch

To stop the scanner immediately:
```
Actions → Kalshi scanner → Disable workflow
```
To stop **all** automation (scanner + pages):
```
Actions → (top-right ⋯) → Disable all workflows
```
Re-enable after the fix. The repo's last published state will persist on
Pages until the next successful deploy.

## Scheduled reviews

- **Weekly:** 15-minute look at calibration reliability curves. Any bucket
  where realized rate diverges from model_p by >10pp is a yellow flag;
  >15pp is a red flag and triggers a strategy-level revision cycle.
- **Monthly:** Review `strategies/registry.py::GLOBAL.jurisdiction_blocklist`
  against Kalshi's current legal status page. Update the docs/DISCLAIMER
  accordingly.
- **Quarterly:** Re-run Phase 2.5 self-critique on each live model. Any
  model dropping below B- requires revision before next quarter.
