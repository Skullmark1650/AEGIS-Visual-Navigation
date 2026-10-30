# Longer temporal baseline experiment v17

## Outcome

Tested a single predefined longer view set542/574/620(5.203s span) from the saved fresh rotation recording, against the unchanged v16three-view gates. No accepted hypothesis; no production change. Landmark-recovery-v8 remains default and mapfix is intact. No camera, Pi/API calls or physical movement. Phase8OPEN, not advanced.

Preregistration copied the v16limits and froze the exact assessor hash before matching/fitting the new views. Frames chosen as start of the observed turn sequence, known first reset and later settled view. No reference-based branch selection or threshold sweep. All3JPEGhashes verified. As with earlier experiments, this is development footage, not held-out acceptance.

## Measurements

Compared with v16(554/560/574), cycle-consistent distinct tracks fall80to56; training/heldout53/27to37/19, below required90total/60train/30holdout. Best positive-depth fraction improves83.75%to92.86%, passing85%. Middle-view heldout median .19172to.24603px and95th1.25115to.38963px: both longer-view residual limits pass. But structure singular ratio .04855to.00742falls below .01, indicating a near-planar/weak-depth reconstruction under this model. Median parallax .13315to.19753deg remains below .5deg. Longer elapsed time did not create sufficient depth information. It trades shared overlap for a somewhat stronger baseline, and does not cross the required evidence gates.

The best branch is diagnostic only. Counts/folds do not meet minimums; no experimental acceptance, no heading bridge and no full candidate integration/replay. Rotation agreement fold checks not run after preliminary rejection. Low prediction residual alone is not an observable/unique3Dpose. Estimates are not metric, independent accuracy or proof that every possible method must fail.

## Controls

Unchanged assessor was rerun on controls with results saved under this experiment:240nonplanar ideal points accept exactly one hypothesis, endpoint rotation error .07548deg;240point single-plane motion and240point pure rotation reject; blank images yield0cycletracks.79production tests pass. These are component/unchanged-system checks, not a broad qualification of the exploratory model. No older/newer full-recording regressions were run because no candidate passed its primary case.

## Artifacts and continuation

results/experiments/rotation-v17/{preregistration,result,comparison,controls,hashes}.json and tracks.npz. Code laptop/probe_rotation_long_baseline.py refuses overwrite of completed result; laptop/verify_rotation_long_baseline.py saves controls separately from v16. Baseline v16outputs preserved. NEXT_SESSION.md updated.

Next decision should address the evidence/model limitation, not repeatedly lengthen time or reduce minimum tracks/parallax. Remaining options for software investigation: an orientation-specific multi-view uncertainty model (not a translation-dependent reconstruction), or explicit partial-tracking acceptance with unknown intervals and later reference recovery. A new estimator needs predefined orientation identifiability/error checks, negative controls and saved-data regression before promotion. More elapsed time alone has not repaired this interval, and there is no validated continuous-heading fix yet. No new physical test needed to review these options; initialized-map network and eventual fresh final validation remain pending. NoPhase9/Pi-onlymigration.
