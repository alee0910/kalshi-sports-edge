# Strategies

Each `.md` file in this directory is a complete strategy spec in the format
prescribed by Phase 3 of the project plan. The python file `registry.py`
enumerates the active strategies for the scanner (Phase 6) and the backtest
framework (Phase 4).

## Shipped strategies (v1)

| ID | Name | Sport(s) | Edge thesis (one line) | Kelly frac |
|---|---|---|---|---|
| S01 | `favorite_longshot_fade` | ALL | Kalshi retail overpays sub-20¢ longshots; fade sub-15¢ tails when model P < quote. | 0.25× |
| S02 | `mlb_starter_news` | MLB | First-price window after starter scratch/confirmation is slow; model re-prices in < 60s. | 0.30× |
| S03 | `nba_playoff_series_hca_alternation` | NBA | Series markets misprice HCA alternation in 2-2-1-1-1 vs. single-game HCA. | 0.25× |
| S04 | `nfl_weather_underreaction` | NFL | Wind > 18 mph and cold < 25°F in outdoor games → Kalshi total/ML under-adjusts vs. model. | 0.25× |
| S05 | `popular_team_futures_short` | MLB/NBA/NFL | Popular-team futures (LAD, NYY, BOS, LAL, DAL, KC, SF) run 2-6% over model pre-season. | 0.20× |
| S06 | `stale_reprice_arb` | ALL | After in-game news (TO, injury), Kalshi redraws spread over 30-120s. Our scanner catches lag. | 0.35× |

All strategies share:

- **Fee-aware EV rule.** Execute only if `edge × notional > 2 × taker_fee` (see
  `research/kalshi/fees.py`).
- **Kelly fraction.** Fractional Kelli with strategy-specific multiplier
  (above). Never use full Kelly. Cap per-contract position at 0.5% of bankroll.
- **Correlation cap.** Total exposure across a single sport slate capped at 8%
  of bankroll.
- **Hard stop.** If daily drawdown exceeds -3% of bankroll → halt new orders
  for 24h and flag for manual review.
- **Kalshi legality cutoff.** No orders placed from MA (state injunction); PR,
  GU, AS excluded. Reviewed monthly against the April 2026 CFTC rulemaking
  docket.

## File layout

Each strategy is one markdown file following the template in
[`_template.md`](./_template.md). `registry.py` is the canonical list the
scanner imports.

## Why only 6 strategies (not 10+)?

Per the project spec: 4-6 strategies is the target. Each one must be
independently defensible and independently backtested. A long list with 12
marginal strategies would be harder to monitor and more prone to p-hacking the
strategy set after-the-fact.

I picked 6 because:

1. S01 and S05 cover different time horizons of the same retail-behavior
   mispricing (intraday tails vs. futures-window popular-team premium).
2. S02 and S06 are both "reprice-lag" strategies but with genuinely different
   trigger events (news vs. in-game play).
3. S03 and S04 are the two structural mispricings most specific to their sport.
