# NBA model

## Approach (v1.0)

Margin-based win probability, grounded in `/research/domain/nba_literature_review.md`:

1. **Stage 1 — Team strength prior.** Four-Factors-derived ratings + pace → expected possessions. Home margin = (home_net − away_net) × pace/100 + HCA.
2. **Stage 2 — Availability & rest adjustments.** Subtract DARKO/EPM impact of scratched starters. Back-to-back and travel adjustments.
3. **Stage 3 — Win prob via margin distribution.** `P(home win) = Φ(margin / σ)` where σ ≈ 11.8 points (to be refit in training).

## Literature informing the model

- Dean Oliver Four Factors (2004, refit arxiv 2305.13032)
- DARKO / EPM / LEBRON player impact metrics (RAPM-based)
- Pace-adjusted net rating as ground truth of team strength
- Gelman's "model the point differential" (Statmodeling)
- NBA HCA post-2020 ~2.5-3.0 pts (was ~3.5 pre-pandemic)

## Known limitations (v1) — will be revisited in Phase 2.5 critique

- **Margin prediction currently too confident** for large net-rating differences. Need to dampen rating-differential scaling (rating_diff_scale coefficient < 1.0) or inflate σ for high-variance inputs.
- No shot-quality / xeFG layer yet. Recent-form shooting luck not separated from true shot selection.
- Back-to-back penalty applied as constant; should vary by team (deep-bench teams absorb better).
- No official refereeing crew feature.
- Player impact uses a single aggregate "projected_impact_per100"; production needs DARKO daily feed.
- No possession-level model (pace + efficiency is abstract).

## Kalshi edge rationale

- Rest / travel / B2B: retail markets systematically under-adjust.
- Load management (star scratches): Kalshi lags Twitter by 1-5 min.
- Popular-team futures: Lakers/Warriors priced richer than model.
- Altitude (Denver, Utah): underweighted in most markets.

## Training

```
python models/nba/training.py --start-season 2019 --end-season 2024 --holdout-season 2025
```

Requires `pip install nba_api scikit-learn pandas numpy`. Fits HCA, margin_std, rating-diff scale, rest-day coefficients, isotonic post-calibration.

## Inference

```python
from datetime import date
from models.nba.data_pipeline import build_matchup
from models.nba.model import predict, simulate_series

m = build_matchup("BOS", "MIL", game_date=date(2026, 5, 14), home_rest=2, away_rest=1)
pred = predict(m)
series = simulate_series(pred.p_home_win)
```

## Target calibration

- OOS log loss ≤ 0.660 (beats spread-implied by ~0.01)
- Brier ≤ 0.225
- 10-bucket reliability within ±0.03 diagonal
