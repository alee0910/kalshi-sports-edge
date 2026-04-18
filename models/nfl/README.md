# NFL model

## Approach (v1.0)

Blended power-rating + EPA model, grounded in `/research/domain/nfl_literature_review.md`:

1. **Stage 1 — Power-rating prior.** Blend of nfelo-style Elo (55%) and season-to-date EPA-derived margin (45%). EPA margin uses offensive-EPA weight 1.6× defensive (empirical, nfelo).
2. **Stage 2 — QB adjustment.** CPOE and EPA/play deltas for starting QBs. Backup-QB replacement: -4 points until backup has ≥ 3 career starts of sample.
3. **Stage 3 — Situational.** Thursday short-rest, rest-day difference, division, playoff, weather (wind > 15 mph, temp < 32°F, precipitation), altitude. Ignores weather if dome.
4. **Stage 4 — margin → win prob.** `P(home win) = Φ(margin / 13.5)` (regular season) or `/ 12.5` (playoff).

## Literature informing the model

- Burke — EPA, WP framework foundations
- Baldwin/Carl/Sharpe — nflfastR models; public EPA/WP/CP benchmarks
- Football Outsiders — DVOA methodology
- nfelo — WEPA, power-rating blend; found best public forecaster
- PFF — blends improve with grade data (paid)
- Open Source Football — WP model architecture
- Sabin Analytics — cautionary note on EPA predictability

## Known limitations (v1)

- No PFF grade data (paid); reduces line-play signal.
- Elo is stub at 1500 constant until training.py walk-through is run over multi-season data.
- Pass-dependence feature is constant; should vary by team.
- No coaching-change features.
- Special teams EPA ignored.
- Backup-QB penalty is constant; actual replacement quality has wide variance.

## Kalshi edge rationale

- Early-season retail overreaction (Weeks 1-3) → use heavy-shrinkage prior.
- QB injury → backup transitions often mispriced in first Kalshi reprice window.
- Weather-sensitive games (outdoor cold/wind) → market underweights effects.
- Popular-team futures (Cowboys, Chiefs, 49ers) overpriced throughout futures window.
- Thursday-night short-rest differential often lagged.

## Training

```
python models/nfl/training.py --start-season 2015 --end-season 2024 --holdout-season 2025
```

Requires `pip install nfl_data_py scikit-learn pandas numpy`.
Fits: Elo K + MoV multiplier, HCA, margin_std, QB adjustment scales, isotonic post-calibration.

## Inference

```python
from models.nfl.data_pipeline import build_matchup
from models.nfl.model import predict
m = build_matchup("KC", "DEN", season=2026, week=10,
                  weather={"temp_f": 28, "wind_mph": 18, "is_dome": False})
pred = predict(m)
```

## Target calibration

- Log loss ≤ 0.640 (market-beating by ~0.01)
- Brier ≤ 0.220
- 10-bucket reliability ±0.03
