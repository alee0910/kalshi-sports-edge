# College Basketball model — STUB

**Status:** `not_yet_built = True`. Do not deploy.

## Why stubbed

v1 ship scope focused on MLB, NBA, NFL (US-market Kalshi volume is concentrated
in those three). College Basketball is documented at the literature-review level but a
production-grade model has not been built.

## Research artifact

See [`research/domain/STUB_other_sports.md`](../../research/domain/STUB_other_sports.md)
for the starter bibliography, intended architecture, and Kalshi edge rationale.

## Intended architecture (v2)

KenPom-style adjusted efficiency + possession sim; experience/continuity factor

## What needs to happen before going live

1. Migrate this sport's stub in `STUB_other_sports.md` to a full
   `research/domain/cbb_literature_review.md` (15-20 sources, the same
   depth as MLB/NBA/NFL).
2. Write `data_pipeline.py` with public data source.
3. Implement `model.py` (replacing this stub).
4. Add `training.py` walk-forward fit over `start-season ... end-season`
   with holdout validation.
5. Run Phase 2.5 self-critique; must earn at least **B-** to ship.
6. Flip `not_yet_built = False` and add the sport to `core/scanner.py`
   eligibility list.

## Scanner behaviour today

`core/scanner.py` imports `cbb.model` and checks `not_yet_built`
before evaluating any cbb market. If the flag is `True`, the market is
logged and skipped (no prediction, no edge, no order).
