# Three-view rotation observability probe v16

## Outcome

Production remains landmark-recovery-v8, with the map-recovery fix intact. An isolated three-view geometric prototype was implemented and tested using saved first-gap images554/560/574. It does not safely resolve the gap and is NOT promoted. No camera/Pi/API calls, production edits or user movement.79production tests pass; separate prototype controls described below. Phase8OPEN, not advanced toPhase9.

## Method and limits recorded before acquisition of results

preregistration.json locks the3views,90minimum unique cycle tracks, deterministic held-out split (source feature index order modulo3: one third holdout),60training/30holdout minimums,85%positive-depth support, middle-view heldout median<=.5px/p95<=1px, median parallax>=.5deg, structure singular min/max>=.01 and rotation agreement across3trainingfolds<=.15deg. These are experimental engineering gates, not certified observability/confidence limits. No limits were loosened to accept the measured result.

Mutual SIFT .7ratio matches are cycle-consistent through all3images, with2pxseparation in every view. End-view essential proposals use ONLY training correspondences, consider all4physical hypotheses, and triangulate points. The middle pose is obtained by robust PnP/refinement using ONLY training points. Held-out points are triangulated using their endpoint images under the training-derived endpoint model; middle-image prediction is then checked without using their middle observations during fitting. Thus it is a held-out middle-view prediction, NOT a wholly independent3view reconstruction or ground truth. No board coordinates/pose enter estimation or branch selection. No SciPy dependency added; this is endpoint initialization+third-view validation, not joint bundle adjustment or a production multi-view optimizer.

For a preliminary pass only,3independent preassigned training subsets refit endpoint E and compare data-selected positive-depth rotations against the full training solution. A missing/weak fold rejects. No branch is chosen by checkerboard agreement. All hypotheses and failed gates remain in output.

## Saved first-gap measurement

80unique cycle tracks, below90.53training/27heldout also below60/30. Two pose branches have zero positive depth; the reversed sign has16.25%; the best branch83.75%in both endpoint/middle views, below85%. Median heldout middle prediction .19172px looks good, but95thpercentile1.25115px exceeds1px. Estimated structure spread .04855 passes .01. Median parallax .13315deg falls well below .5deg. No hypothesis passes; fold checks are deliberately not executed after preliminary rejection. Good median fit must not hide weak depth or tail errors.

A preliminary diagnostic file is retained separately; final result.json includes explicit experimental rejection after fold-validation code was added. Views were selected from previously inspected development footage; even preregistered limits here do not make it a held-out final test. No full1043frame integration/replay or broader older-recording regressions were performed because this primary interval does not meet its acceptance gates.

## Prototype controls

240idealized nonplanar3Dpoints under known3view rotation/translation with .02px Gaussian image noise: exactly one accepted hypothesis, endpoint rotation error .07548deg. This verifies the pipeline can pass a sufficiently supported ideal case; it does not predict hardware accuracy. Corresponding240point single-plane motion rejects;240point pure rotation rejects the translation-dependent model; blank images yield zero cycle tracks. These are component controls, not full system negative-control qualification.79normal unit/integration tests pass with unchanged production. Controls and full hypothesis metrics saved in controls.json.

## Artifacts and next work

laptop/rotation_multiview_probe.py, verify_rotation_multiview.py; results/experiments/rotation-v16/preregistration.json, tracks.npz, preliminary-result.json, result.json, controls.json, hashes.json. Main probe currently overwrites result/tracks at its fixed experimental path; copy it/use fresh filenames before a new trial. Original raw frames/provenance remain intact. NEXT_SESSION.md updated.

This result supports conservative rejection of the current small-baseline three-view reconstruction. It does not prove that no method can recover heading, or that all saved views lack useful depth. Next meaningful investigation is whether a longer, independently matched temporal baseline with sufficient shared tracks improves parallax while respecting session/reference boundaries. Predefine a small fixed view set and limits before running; do not choose the board-favored answer or sweep until something passes. Any successful observability probe needs independent feature folds, wrong-scene/planar controls, full saved-data regression and eventual fresh validation before promotion. If overlap/depth remain insufficient, retain unknown motion and later reference recovery rather than guessing a continuous path. No additional physical test is needed for that saved-data investigation. Network testing and eventual fresh final validation remain pending; noPi-onlymigration.
