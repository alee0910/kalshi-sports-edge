# MLB model

## Approach (v1.0)

Three-stage win-probability model, grounded in `/research/domain/mlb_literature_review.md`:

1. **Stage 1 — Pythagenpat prior.** Season-to-date runs scored/allowed converted to a team win% via pythagenpat (Davenport-style dynamic exponent), then combined via log5 with home-field advantage. Serves as a strong cold-start / stabilizer.
2. **Stage 2 — Matchup-specific run-distribution estimation.** Starts from team xwOBA (handedness-split) → expected runs/game, then adjusts for starter Stuff+, bullpen Stuff+, team OAA + catcher framing, park factor, weather, umpire tendency.
3. **Stage 3 — Monte Carlo (10,000 sims).** Simulate home/away runs from right-skewed lognormal and count home wins. Output P(home win) with sampling std error.

Final output: `P = (1-w) * P_sim + w * P_prior` with `w = 0.15` (blend weight), shrinking to prior to avoid overfitting on noisy game-level features.

## Literature informing the model

| Feature | Source |
|---|---|
| xwOBA as offense baseline | FanGraphs wOBA library, MLB xwOBA glossary, Carleton stabilization rates |
| Stuff+ / Pitching+ as primary pitcher signal | Driveline (2021, 2024), FanGraphs primer, BP "Updated Evaluation" |
| Catcher framing | FanGraphs catcher defense library; 0.135 runs per extra strike (Statcast) |
| Pythagenpat exponent | Dolphin/Davenport: `((RS+RA)/G) ^ 0.287` |
| Log5 blending | Bill James original |
| Monte Carlo approach | Swartz/Hui 2011; SharpAlpha MC intro |
| Right-skewed run dist | `/research/domain/mlb_literature_review.md` §5; confirmed in arxiv 2505.05120 |

## Known limitations (v1)

- No lineup-card awareness at the individual-player level. Currently team-aggregate xwOBA; a meaningful upgrade would sum 9 projected starters' individual xwOBA vs. pitcher handedness.
- Bullpen is single-number aggregate; does not account for which relievers are rested.
- Umpire data for pre-first-pitch is sparse; we use league-average if unknown.
- Stuff+ shrinkage is linear; should be Bayesian hierarchical.
- No seam-shifted wake or tunneling features yet (FanGraphs SSW is 2023+).
- Weather is modeled only as wind-out-CF; temp/humidity influence is folded into park factor in practice.

## Kalshi-specific edge rationale

1. Markets anchor on ERA / W-L for pitcher priors; we anchor on Stuff+.  Difference is largest early-season and after a 3-start hot/cold stretch.
2. Late-scratch catcher / back-up catcher changes are underpriced by retail; framing can move a team's expected runs allowed by 0.2-0.4 r/g.
3. Weather repricing at Kalshi lags live wind forecasts by minutes-to-hours.
4. Team-popularity bias in futures: our prior is based on Pythagenpat, not fanbase size.

## How to train

```
python models/mlb/training.py --start-season 2019 --end-season 2024 --holdout-season 2025
```

Requires `pip install pybaseball scikit-learn pandas numpy`.  Fits:
- wOBA→runs slope
- Stuff+→runs/9 slope
- home-field advantage
- run variance multiplier
- isotonic post-calibration map

Saves `models/mlb/coefs.json`.

## How to run inference

```python
from datetime import date
from models.mlb.data_pipeline import build_matchup
from models.mlb.model import predict

m = build_matchup("LAD", "COL", home_sp_id="477132", away_sp_id="642528",
                  game_date=date(2026, 5, 14), park_factor=0.95)
pred = predict(m)
print(f"P(LAD win) = {pred.p_home_win:.3f}")
```

## Output quality targets

- Out-of-sample log loss target: ≤ 0.670 (beating market implied-prob baseline by ~0.02)
- Brier score target: ≤ 0.235
- Calibration: reliability diagram within ±0.03 of diagonal for all 10 deciles
- See `/research/calibration/` for monthly reports once the model is in live operation
