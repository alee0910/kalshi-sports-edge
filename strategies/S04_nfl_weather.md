# S04 — NFL outdoor-weather under-adjustment

## Thesis

The NFL betting market has historically under-adjusted for extreme outdoor
weather. Multiple studies (Sharp Football Analysis 2019-2023 wind data;
Football Outsiders weather splits; Open Source Football game-level regressions
on wind/temp/precip) show:

- **Wind > 15 mph** compresses scoring; dropoff is roughly 0.5 pts per 5 mph
  above 15. Pass-heavy teams drop more than rush-heavy teams.
- **Temperature < 32°F** reduces total by ~1 point even without wind (ball
  grip, kicking).
- **Precipitation** of ≥ 0.5" during-game expected → -1 pt per inch forecast.

Kalshi's NFL-outcome market makers largely inherit consensus Vegas odds; when
the forecast updates sharply in the 24h before kickoff, we've observed
4-8-cent reprice lags. Our scanner re-pulls OpenWeatherMap at 12h, 6h, 3h,
and 1h before kickoff and flags any material change.

The strategy is moneyline-side, not total-side: when weather changes are
severe, the underdog's implied win probability rises (lower totals reduce
scoring variance, which *compresses* win-probability; this sounds backwards
but empirically the smaller absolute margins mean more variance relative to
expected margin, giving the underdog more realization probability).

## Market selection

- NFL regular-season and playoff single-game moneyline markets.
- Outdoor stadiums only (skip dome via `context.is_dome`).
- Forecast wind > 18 mph OR temperature < 25°F OR precipitation > 0.7"
  projected.

## Entry signal

```
weather_t = pull_openweathermap(stadium)
pred_new = model.predict(matchup_with_weather(weather_t))
pred_old = last_prediction_without_update
if abs(pred_new.p_home_win - pred_old.p_home_win) >= 0.03 \
   and kalshi_quote_has_not_moved_at_same_rate():
    side = "yes" if pred_new.p_home_win > kalshi_home_quote else "no"
    submit_order(size = kelly_frac * k_opt)
```

`kelly_frac = 0.25`.

## Exit signal

- Settlement.
- If weather forecast converges back to baseline → close half.

## Sizing

0.25× Kelly. Per-game cap 0.6% bankroll.

## Fee & slippage handling

NFL moneyline contracts tend to trade 0.30-0.70 where fees are highest
(~1.5¢ taker at P=0.5). Require 4¢ gross edge for 2.5¢ net.

## Expected performance (backtest placeholder)

Estimated 15-25 qualifying weather games per NFL season (outdoor + severe
weather). Per-trade edge target: 2.5-5%. Annual expected return: 0.5-1.5% of
bankroll from this strategy alone (intentionally small; this is a tail
strategy).

## Risks / failure modes

- **Weather data errors.** OpenWeatherMap stadium-specific forecasts have
  ±3 mph wind error bars. Use multi-source consensus (NOAA + OWM) before
  deciding.
- **Backward-looking thesis.** Kalshi MMs may now explicitly incorporate
  weather feeds (they've added features in 2025-26); persistence of the edge
  is uncertain.
- **Coaching adjustment.** Teams alter gameplans for wind; my model's wind
  penalty is team-agnostic. A wind-veteran like Buffalo's Allen loses less
  than a short-timer QB; model doesn't capture this yet.

## References

- /research/domain/nfl_literature_review.md
- Weekly Sharpe (2020) — "Wind as a Predictor of NFL Totals" blog series.
- Burke, Brian — Advanced NFL Stats weather splits archive.
- Baldwin, Ben — nflfastR maintainers: weather features in WP model.
