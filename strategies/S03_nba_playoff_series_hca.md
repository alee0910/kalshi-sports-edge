# S03 — NBA playoff series HCA alternation

## Thesis

Kalshi's "series-winner" contracts often reprice on single-game outcomes with
too much momentum bias: a Game-1 road win typically pushes the series price by
more than the game-level HCA swing justifies in a 2-2-1-1-1 format.

The mechanism: in 2-2-1-1-1, the higher seed has home court for games 1, 2, 5,
7. A road team's Game-1 win transfers ~0.08-0.12 expected series probability
*before* factoring that HCA re-alternates in games 3-4. Retail tends to over-
weight the single-game evidence and underweight the structural HCA.

We run `simulate_series` with updated per-game home/away win probabilities
after each game and compare the Monte-Carlo series probability to Kalshi's
live series contract. Fade when market deviates > 4% from model.

## Market selection

- NBA playoff series markets (Round 1 through Finals).
- Best-of-7 only (best-of-5 not currently a Kalshi product for NBA).
- Priced between 15¢ and 85¢ (avoid blowout illiquidity tails).

## Entry signal

After each completed game:
```
games_remaining_format = derive_remaining_games(series_state, format="2-2-1-1-1")
p_series_fair = simulate_series(
    per_game_home_wp = model.predict(home_advantage_applied=True),
    per_game_away_wp = model.predict(away_advantage_applied=True),
    series_state = current_state,
    n_sims = 100000,
)["p_home_series_win"]
edge = p_series_fair - kalshi_quote
if abs(edge) >= 0.04 and fee_adjusted_ev(...) > 2 * taker_fee:
    submit_order(side = "yes" if edge > 0 else "no", size = kelly_frac * k_opt)
```

`kelly_frac = 0.25`.

## Exit signal

- Re-enter or re-evaluate after each subsequent game.
- On series completion (settlement).
- If intra-game news changes per-game WP by > 0.05 (injury scratch) → reprice
  and optionally close.

## Sizing

0.25× Kelly. Per-series cap 2% bankroll across all positions on that series.

## Fee & slippage handling

Series markets trade at meaningful P*(1-P) (often 0.3-0.7), so taker fees are
material: `ceil(0.07 * 100 * 0.5 * 0.5) = 2¢` per contract at 50¢. Require
4¢ gross edge for 2¢ net target.

## Expected performance (backtest placeholder)

NBA playoffs produce ~15 best-of-7 series per year. Expected 2-3 reprice
opportunities per series = 30-45 trades/year. Per-trade EV target: 1.5-3%.

## Risks / failure modes

- **Series-level skill underestimated.** If one team has a matchup advantage
  that grows series-over-series (e.g. 3-PT defense travels), our per-game
  repeated-sim underestimates the advantage.
- **Correlated injury risk.** A starter injury in Game 1 affects all
  subsequent games; if our model doesn't instantly update per-game WPs, the
  series math is wrong.
- **Rest-and-travel interactions.** The 2-2-1-1-1 format means game 3 is
  often short-rest away for the lower seed; our NBA model's rest adjustment
  must handle this correctly (currently does).

## References

- /research/domain/nba_literature_review.md
- Kubatko, J., et al. (2007). "A Starting Point for Analyzing Basketball
  Statistics." *JQAS*.
- Dean Oliver, *Basketball on Paper* — HCA decomposition.
