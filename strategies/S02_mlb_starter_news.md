# S02 — MLB starter news

## Thesis

Starting-pitcher identity is the largest single factor in an MLB moneyline.
The market moves ~25-40 cents when a confirmed starter is scratched / a
swingman is named. Kalshi's reprice window after such news has been observed
(via public orderbook snapshots and the Kalshi Discord archives) to lag
sharpbook reprices by roughly 30-180 seconds — partly because Kalshi's market
makers are more conservative with quote updates and partly because the news
has to percolate through retail eyeballs before the liquidity regenerates.

Our scanner polls team injury / lineup feeds (`mlb_data_py`, Rotowire scraper)
every 60s during the afternoon window (2-7 pm ET). On scratch detection we
immediately rerun the MLB model with the confirmed replacement starter and
place limit orders inside the current spread, attempting to make liquidity at
the updated theoretical.

## Market selection

- MLB single-game moneyline.
- Scheduled game within next 6 hours (i.e. starters already projected).
- Excludes: opener games where starter convention doesn't apply (flag via
  opener_expected bool from pipeline).

## Entry signal

```
if starter_scratch_detected (new_starter_id != last_seen_starter_id):
    new_pred = model.predict(matchup_with_new_starter)
    old_price = last_market_price
    implied_fair = new_pred.p_home_win
    edge = abs(implied_fair - old_price)
    if edge >= 0.04 and fee_adjusted_ev(...) > 2 * maker_fee:
        # Post maker order at theoretical + 1 tick buffer
        submit_limit(price = implied_fair ± buffer, size = kelly_frac * k_opt)
```

`kelly_frac = 0.30` (higher than baseline — thesis is time-limited).

## Exit signal

- Opposite-side fill or lapse to game start (auto-expiry).
- If Kalshi bid converges to our theoretical within ±2¢ → cancel remaining and
  hold existing position to settlement.
- If ≥ 15 minutes pass and no fill → cancel (signal stale).

## Sizing

0.30× Kelly. Per-contract cap 0.5% bankroll. Maximum 3 MLB starter-news
positions open simultaneously (correlation cap across daily MLB slate).

## Fee & slippage handling

Maker fee `ceil(0.0175 * C * P * (1-P))` — 4× cheaper than taker. Strategy
relies on maker fills; if no maker fill within 15min, abandon. Do NOT fall
through to taker at same price.

## Expected performance (backtest placeholder)

Edge per trade: 2-4¢ on a 40-60¢ market ≈ 4-7% of notional.
Trade frequency: ~60-120 trades per MLB season, conservatively.
Target Sharpe: 1.2-1.8 if reprice-lag thesis holds.

## Risks / failure modes

- **Kalshi MM learns.** If their quote engine eventually fires inside 10s
  after news, our lag-edge evaporates.
- **False scratches.** Rumor-level reports sometimes don't confirm; our
  replacement-starter input has to come from confirmed sources only.
- **Replacement starter data gap.** Rarely-used long relievers have noisy
  Stuff+ estimates; MLB model's shrinkage handles it but with wider CI.
- **Liquidity collapse post-news.** If both sides pull quotes, our maker
  orders stale at zero fill.

## References

- /research/domain/mlb_literature_review.md
- Kalshi community Discord + orderbook snapshots (informal evidence)
- The Book (Tango/Lichtman): starter effect ≈ 0.15 runs per start per
  quality-of-start tier.
