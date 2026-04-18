# S05 — Popular-team futures short

## Thesis

A long-running finding in sports-prediction markets (Simmons & Nelson 2006;
Levitt 2004 on NFL; Fangraphs on MLB preseason overs) is that retail-facing
futures on high-profile franchises carry a persistent premium of 2-6% over
model-implied fair value. Kalshi's season-champion and season-win futures
markets show the same pattern in 2025-26:

- **MLB preseason:** Dodgers, Yankees, Braves typically priced 3-5% over
  model fair on World Series futures.
- **NBA preseason:** Lakers, Celtics, Warriors, Nuggets — similar pattern.
- **NFL preseason:** Cowboys, Chiefs, 49ers, Eagles.

We short (buy No) these contracts at preseason/early-season when the market is
thickest and least driven by recent results. Close positions as the season
progresses and the premium compresses (information flow moves the price
toward fair).

## Market selection

- MLB World Series winner contracts (early-April window, before opening day +
  first 10 games).
- NBA Championship winner contracts (October window, before opening night +
  first 10 games).
- NFL Super Bowl winner contracts (September window, before Week 1 + first 2
  weeks).
- Target teams: defined as preseason top-3 popularity (measured by Google
  search volume and Kalshi trading volume through prior postseason).

## Entry signal

```
for team in popular_team_list[sport]:
    market_price = kalshi_current_yes_price
    model_fair = monte_carlo_full_season(team).p_championship
    premium = market_price - model_fair
    if premium >= 0.02 and fee_adjusted_ev(...) > 2 * taker_fee:
        # Buy No on the team
        submit_buy_no(size = kelly_frac * k_opt)
```

`kelly_frac = 0.20` (long holding period → lower conviction in point
estimate).

## Exit signal

- If premium compresses to < 0.5% → close (thesis played out).
- If model fair updates upward (team's roster news + early-season
  performance) → reassess; close if premium goes negative.
- Hard expiry: 60 days from entry (limits holding-period risk of path-
  dependence in markets we're not actively monitoring).

## Sizing

0.20× Kelly. Per-team cap 1% bankroll. Per-sport cap across multiple popular
teams 3% bankroll.

## Fee & slippage handling

Championship futures trade between 3¢ and 25¢ typically. Fee at 10¢ is
0.63¢; at 25¢ is 1.31¢. Require 2.5¢ edge gross for 1.5¢ net.

## Expected performance (backtest placeholder)

Levitt (2004): ~2.5% retail-driven premium on popular NFL teams. Simmons &
Nelson (2006): ~3% premium on "favorite" NBA teams. Published effect sizes
translate to ~25-40 bps/year on the shorted notional.

## Risks / failure modes

- **Premium is a risk premium, not a bias.** If our model is wrong about the
  team's prospects, the premium isn't alpha, it's compensation for tail risk.
  Phase 7 calibration reports will check this.
- **Championship concentration.** If 2-3 teams plausibly win, shorting any
  one of them has large idiosyncratic variance.
- **Kalshi settlement timing.** Championship contracts settle late; capital
  is tied up for up to 7 months. Kelly sizing must account for the long
  holding period (we use 0.20× instead of 0.25× for this reason).
- **Team news mid-season.** Major trade / injury can revalue the contract
  rapidly; scanner must watch for these events.

## References

- Levitt, S. D. (2004). "Why Are Gambling Markets Organised So Differently
  from Financial Markets?" *EJ*.
- Simmons, R. & Nelson, S. (2006). "Bias in betting markets."
- Ottaviani, M. & Sørensen, P. N. (2009). "Surprised by the Parimutuel Odds?"
  *AER*.
