# S01 — Favorite-longshot fade (sub-20¢ tails)

## Thesis

On Kalshi sports markets, the favorite-longshot bias (FLB) documented by
Becker (2025)'s 72M-trade analysis shows contracts priced below 20¢ are
systematically overpriced by retail relative to outcome frequency. The bias is
strongest in the 3¢-15¢ range and in single-game / single-player markets (as
opposed to multi-event correlated futures). The effect persists because:

1. Kalshi's UI makes small absolute payoffs look attractive (lottery-ticket
   framing).
2. Shorting on Kalshi is via buying the No side and requires explicit thinking
   about the other leg; retail gravitates to Yes buys on longshots.
3. Arb flow is thin on sub-liquidity markets where fees are highest relative
   to edge.

The strategy is to sell (or buy No on) contracts trading at 4¢-18¢ when our
model's implied probability is at least 2 percentage points below the quote.

## Market selection

- All Kalshi sports markets (MLB/NBA/NFL for v1; others when `not_yet_built`
  flips).
- Pre-settlement only (intraday and pregame).
- Minimum notional liquidity: 1,000 contracts open interest on the No side.
- Excludes: Playoff Champion futures < 30 days to event (too few data points
  for our model to have edge over consensus after media coverage).

## Entry signal

```
if 0.04 <= Yes_price <= 0.18 and model_p <= Yes_price - 0.02
   and fee_adjusted_ev(model_p, Yes_price, role="taker") > 2 * taker_fee
   and orderbook_no_side_depth >= 1000:
   submit_buy_no(size = kelly_frac * bankroll * kelly_size, price = No_best_ask)
```

where `kelly_frac = 0.25` and `kelly_size` is the standard Kelly for the spread.

## Exit signal

- At market settlement (primary).
- If Yes_price drops ≥ 40% from entry → close half position (partial profit
  lock).
- If model probability revises upward beyond the quote (delta ≥ 0.03) → close
  position.

## Sizing

Quarter Kelly. Cap per-contract at 0.5% of bankroll. Cap total sub-20¢ fade
exposure at 4% of bankroll across all simultaneous positions (correlation
cap).

## Fee & slippage handling

Taker fee at entry: `ceil(0.07 * C * P * (1-P))`. At P=0.10, fee is ~0.63¢ per
contract. Required edge: at least 2¢ after fee. Assume 1-tick slippage on the
No ask.

## Expected performance (backtest placeholder)

Target from Becker (2025) meta-analysis: +1.5% to +3.0% edge per dollar
notional, before fees. After fees (which are brutal on sub-20¢), net target
+0.3% to +0.8%. Hit rate expected ~86% (longshots fail 90%+ of time).

## Risks / failure modes

- **Fee wall.** Taker fees scale with P*(1-P); at P=0.10 the fee is ~7% of the
  edge, which compresses EV. Maker-only variant should be tested in v2.
- **Adverse selection.** If we're taking liquidity from a sharp maker, we're
  on the wrong side of their model.
- **Correlated tails.** Many longshots resolve together (underdog-heavy slate
  days). A 3% daily drawdown is possible even on a +EV portfolio.
- **FLB attenuation.** Becker's data runs through 2025. If market maturity
  compresses FLB, strategy edge decays; monitor with Phase 7 calibration
  reports.

## References

- Becker, J. (2025). "Favorite-Longshot Bias on Kalshi." 72M-trade retail flow
  study. [jbecker.dev](https://jbecker.dev/)
- Snowberg, E. & Wolfers, J. (2010). "Explaining the Favorite-Long Shot
  Bias." *JPE*.
- Williams, L. V. & Paton, D. (1997). "Why Is There a Favourite-Longshot Bias
  in British Racetrack Betting Markets?" *EJ*.
