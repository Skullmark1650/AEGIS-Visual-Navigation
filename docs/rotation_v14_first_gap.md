# First rotation gap: descriptor experiment v14

Production remains landmark-recovery-v8, including the recovered-landmark fix. No camera, Pi connection, API or user movement used. This was one bounded saved-footage experiment, not an acceptance rerun.

## Image inspection and matching

Viewed raw554and574. The earlier trusted source is visibly softer; later image is sharper and scene framing changes. Full-frame Laplacian variance100.63vs146.06and medians124vs119 are descriptive, not calibrated blur/exposure estimates; image content changes confound these statistics. Cannot uniquely attribute mismatch to exposure or blur. Earlier strict LK diagnostics retain16/17of263pairs at570/574.

Candidate: independent SIFT descriptors(2000feature cap), mutual nearest matching in both directions with .7ratio test, two-pixel spacing in both images to avoid duplicate octave/orientation features, minimum90matches. Only recent same-anchor images<=30frames in active rotation fallback, ordinary existing path first. Existing calibrated homography/pure-rotation and identifiable nonplanar orientation gates unchanged. No translation output or spatial interpolation. This is a different correspondence model, so geometry thresholds alone do not establish equal false-positive rates.

554->560gets138distinct pairs;554->570gets127;554->574gets110. Diagnostic seeded essential fits have88.4%,89.0%,85.5%epipolar inlier support, but only77/138(55.8%),68/127(53.5%),74/110(67.3%)positive-depth pose supports, below85%required. Null ratios .4794,.4914,.4804 and rank ratios .000941,.001201,.001039pass their respective gates; valid-pose support then fails. Repeated pattern errors, low-baseline ambiguity or motion-model mismatch can contribute; these statistics alone do not identify a unique cause. Diagnostic RANSAC fits are seeded by frame and not asserted identical to every live random sample. No failed pair forced through.

## Paired replay outcome

All1043source frames integrity-checked via cache provenance. Descriptor candidate19rotation updates vs22baseline; fallback estimates881and909occur after the first original-reference gap. Original-heading availability remains64.9089%; same-original-reference correlated RMS .573690deg and max4.556115deg unchanged. No primary improvement. REJECTED FOR PROMOTION. Production is unchanged; standalone experimental modules are not imported by the normal launcher. No full old/new/negative candidate regression is justified before a primary gain.79existing automated tests pass; they validate unchanged production, not a qualification of this rejected candidate.

The first gap is not resolved merely by adding another matcher. Good image matches must also identify a consistent physical orientation. Neither the software resets nor eventual heading recovery reconstructs missing rotation. Same-camera board reference is not independent angular truth, and long holds affect reported RMS. Phase8remainsOPEN; noPhase9orPi-onlymigration.

## Saved artifacts and continuation

- laptop/rotation_descriptor_candidate.py, probe_rotation_descriptor.py, review_rotation_descriptor.py
- results/experiments/rotation-v14/fresh-rotation.json, comparison.json, image-diagnostics.json, gate-diagnostics.json, hashes.json
- Raw image hashes checked for diagnostic frames; full replay includes cache/source/calibration provenance.

Next investigation should quantify spatial distribution and positive-depth ambiguity of these127/110descriptor pairs, compare alternative essential-pose hypotheses against the correlated board-derived motion for diagnosis only, and check whether a small number of moving/repeated-pattern clusters dominates. Do not select the board-favored branch in the estimator, relax85%support, or tune to a reference answer. Any new general outlier model must be predefined and earn primary improvement plus negative/older/newer regression before promotion. Saved data suffices; no additional physical test is currently needed. Preserve all rejected v9-v14experiments to avoid repeating them.
