# Rotation spatial/depth diagnosis and refined-match experiment v15

## Outcome

Production remains landmark-recovery-v8, recovered-landmark fix intact. Saved first-gap descriptor pairs were examined spatially and under all four essential-pose hypotheses. A separate subpixel-refined descriptor candidate was tested on the1043frame recording; it did not improve original-reference continuity and is not promoted. No camera/Pi/API use or new physical movement. All79production automated tests pass.

## Pose and spatial evidence

Source554to560/570/574 uses138/127/110mutual descriptor pairs. For all-inlier essential fits, positive-depth counts across the four hypotheses (before the existing1000unit depth cap) are[0,0,26,96], [0,0,30,83], [0,0,13,81]. Under the depth cap these become[0,0,14,77], [0,0,13,68], [0,0,9,74]. Raw robust five-point fits also split support: best bounded counts93,79,77. No tested branch reaches85%of the full correspondence pool. Thus neither switching signs nor removing the distant-depth cap repairs the required support. The distance cap is in arbitrary baseline units, not meters. Positive-depth disagreement is not proof that every rejected point is an outlier.

A4x3grid records positive and rejected epipolar-inlier support for each hypothesis. Rejections occupy several cells, including upper/middle/right/lower regions; they are not confined to one isolated cell. The target board, brick wall, seat and window are at differing depths and have repeated structure. Counts alone cannot establish which points are physically wrong, moving or near-infinite, and no region was masked based on the answer.

Using same-camera board reference for DIAGNOSIS ONLY, the all-inlier branch with greatest bounded support differs by .0683deg at560and .1009deg at574;570was not a selected reference. Close agreement with a correlated reference is not permission to bypass the support/ambiguity checks. No board answer enters the candidate, no reference-favored branch chosen.

## Subpixel candidate

Starting from predefined mutual SIFT .7ratio matches and2pixel source/target deduplication, refine destination positions with a21px local zero-pyramid LK search initialized by the descriptor pair. Require forward/backward status and patch error<25in both directions (existing ordinary LK bound), backward displacement<.5px, destination adjustment<=2px, finite in-bounds points, >=90retained correspondences. No image warp, translated path or board geometry is used. Unchanged pure-rotation/nonplanar rank/subset/cheirality checks still decide acceptance. This is an experimental matching change, not a proven safety equivalence from identical numerical gates.

Paired full recording replay verifies source hashes/cache/config/calibration provenance. Candidate17rotation updates vs22baseline; one fallback878after the original-reference gap. Original-heading availability remains64.9089%; same-original-reference RMS .573690deg and maximum4.556115deg unchanged. Original first gap is unresolved. Candidate REJECTED FOR PROMOTION; isolated update counts are not a success criterion.

Three additional experimental controls: blank and unrelated random-texture views yield no refined matches; an ideal planar10px slide yields1333matches but is rejected by the nonplanar orientation-only model. These controls test only the specific matcher/orientation component, not the full candidate's false-positive rate. Broader archived negative/older/newer replays were not repeated after the primary case failed; production unchanged and79production tests pass. Earlier rejected trials remain preserved.

## Artifacts and next work

laptop/diagnose_rotation_spatial.py; rotation_refined_candidate.py; probe_rotation_refined.py; review_rotation_refined.py. Results in results/experiments/rotation-v15: spatial-hypotheses.json, fresh-rotation.json, comparison.json, controls.json, hashes.json. Existing image/retention diagnostics and v8baseline preserved. Probe refuses overwrite; choose a new output for new experiments.

Next should be an observability assessment across several independently observed views, rather than another arbitrary match threshold. Determine whether a multi-view nonplanar pose model can resolve the first interval without using checkerboard coordinates or supplying unobserved headings. Prototype separately, require held-out feature/reprojection checks and planar/wrong-scene controls before full replay; if insufficient evidence remains, report unknown motion and recover later. A multi-view model is a more substantive estimator change, not a verified fix yet. Never infer rotation merely from the reference agreement or smooth across resets. Saved data suffice for development; no additional user movement is currently needed. Phase8OPEN, network/fresh final validation pending; noPhase9orPi-onlymigration.
