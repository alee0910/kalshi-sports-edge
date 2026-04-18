# S06 — Stale-reprice arbitrage (in-game events)

## Thesis

Kalshi's in-game win-probability contracts reprice continuously but with a
lag behind live-event feeds. Key events — TD/FG scoring, HR/extra-base
hit, turnovers, lead changes, injury timeouts — cause a latency window of
~15-120 seconds between the event hitting a fast live data feed (MLB Gameday,
ESPN GameCast, nflfastR live, NBA Play-by-play feed) and the Kalshi quote
converging.

Our scanner polls MLB/NBA/NFL live-event feeds at 2s cadence. On event
detection it immediately recomputes the model's in-game win probability and
compares against the current Kalshi quote. If the lag exceeds 2.5 cents we
submit a taker order, expecting to close at fair within 60 seconds.

## Market selection

- MLB in-game moneyline (games currently in innings 4-9).
- NBA in-game moneyline (2nd half).
- NFL in-game moneyline (Q2 onward).
- Excludes: settling markets (< 2 minutes to decision).

## Entry signal

```
on_event_detected(game_id, event_type):
    in_game_state = live_state_after_event()
    p_fair = in_game_model.win_probability(in_game_state)
    p_market = kalshi_last_trade
    if (p_fair - p_market) >= 0.025 and fee_adjusted_ev(...) > 2 * taker_fee:
        # Taker on the correct side, small size for rapid fill
        submit_taker(side="yes", size = kelly_frac * k_opt, price = best_ask)
    elif (p_market - p_fair) >= 0.025:
        submit_taker(side="no", size = kelly_frac * k_opt, price = 100 - best_bid)
```

`kelly_frac = 0.35` — this is the highest-conviction strategy in the book;
it's pure speed/latency edge, not a thesis about persistent bias.

## Exit signal

- Mid-position: close when Kalshi quote converges within 1¢ of our fair
  (partial close 50%, hold other 50% to settlement).
- If market moves against us by 4¢+ without new information → close (our
  model was wrong about the event magnitude).
- At settlement.

## Sizing

0.35× Kelly but with **strict per-event cap** of 0.3% of bankroll; these
trades are high-frequency and position size must not spiral.

## Fee & slippage handling

Fee at P=0.5 is ~1.75¢ taker. Require 2.5¢ gross edge for ≈ 0.75¢ net after
fee and 1-tick slippage. Strategy is sensitive to slippage — use best_ask for
small sizes, avoid sweeping the book.

## Expected performance (backtest placeholder)

High frequency: ~10-40 qualifying events per MLB/NBA/NFL day during season.
Small per-trade edge (~1% of notional after fees). Annual target: 1-3% of
bankroll if in-game model is well-calibrated and Kalshi MM latency remains
~30-60s.

## Risks / failure modes

- **Kalshi MM speed improves.** Every quarter we should measure the lag
  distribution and downsize if median lag falls below 20s.
- **Event classification errors.** A missed scorer attribution (e.g. credited
  to wrong player) could flip our model in the wrong direction; cross-check
  feeds before trusting.
- **In-game model accuracy.** MLB/NBA/NFL in-game models are less mature
  than pregame. Phase 7 must report in-game calibration separately.
- **Review-overturns.** A TD ruled on field then overturned → we've made a
  bet on an event that reversed. Either wait 30s post-score for confirmation
  or accept this tail risk.
- **Execution bleed.** At 10-40 trades/day × 75-125 days/yr per sport, small
  slippage errors compound.

## References

- /research/domain/nfl_literature_review.md (Burke on in-game WP)
- /research/domain/nba_literature_review.md (Oliver possessions)
- /research/domain/mlb_literature_review.md (run expectancy matrices)
- nflfastR in-game WP model documentation.
