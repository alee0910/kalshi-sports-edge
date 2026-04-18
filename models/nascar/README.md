# NASCAR / F1 model — STUB

**Status:** `not_yet_built = True`. Do not deploy.

## Why stubbed

v1 ship scope focused on MLB, NBA, NFL (US-market Kalshi volume is concentrated
in those three). NASCAR / F1 is documented at the literature-review level but a
production-grade model has not been built.

## Research artifact

See [`research/domain/STUB_other_sports.md`](../../research/domain/STUB_other_sports.md)
for the starter bibliography, intended architecture, and Kalshi edge rationale.

## Intended architecture (v2)

Lap-time lap-by-lap sim with tire degradation + pit strategy; driver-team priors

## What needs to happen before going live

1. Migrate this sport's stub in `STUB_other_sports.md` to a full
   `research/domain/nascar_literature_review.md` (15-20 sources, the same
   depth as MLB/NBA/NFL).
2. Write `data_pipeline.py` with public data source.
3. Implement `model.py` (replacing this stub).
4. Add `training.py` walk-forward fit over `start-season ... end-season`
   with holdout validation.
5. Run Phase 2.5 self-critique; must earn at least **B-** to ship.
6. Flip `not_yet_built = False` and add the sport to `core/scanner.py`
   eligibility list.

## Scanner behaviour today

`core/scanner.py` imports `nascar.model` and checks `not_yet_built`
before evaluating any nascar market. If the flag is `True`, the market is
logged and skipped (no prediction, no edge, no order).
