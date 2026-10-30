# Continued rotation investigation: v10/v11 experiments

Production remains landmark-recovery-v8; no estimator, tracker, calibration or acceptance limit changed. Recovered-landmark fix remains installed. Saved fresh rotation recording1043frames was replayed against v8 twice, with integrity-checked tracking cache and raw-image provenance. This is development footage, not new held-out acceptance.

V10 tries fresh strict bidirectional image matches before the existing nonplanar orientation-only model, only in active rotation fallback, at most30producer frames from anchor. Existing >=90matches/70%retention, patch/FB, coverage, rank/null, subset, pose and geometry gates unchanged. Translation discarded. Result18rotation observations versus22baseline, no original-heading availability improvement. This candidate is NOT promoted.

V11 independently changes trusted heading view archive selection from minimum5degrees to1degree, retaining the same30frame spacing and3view cap, with first reference preserved. All observation/recovery gates unchanged. Result matches baseline status counts and original-heading availability; no demonstrated benefit, NOT promoted. This tests a bounded archive choice, not weakening geometric acceptance.

Both experiments retain64.9089%original-reference availability, .573690degrees RMS and4.556115degrees max correlated same-reference error. An endpoint recovery is not continuity. Full per-candidate epoch changes and error comparisons are in comparison.json. No increased availability/accuracy claim. Long stationary holds influence all-sample errors; these are same-camera/calibration diagnostics, not independent angular truth.

## Rejection diagnostics

Strict direct match probe at554->560 retains201matches with98.0%epipolar inliers, but normalized-design null ratio .7286 exceeds .5: the apparent essential fit is not sufficiently unique. At554->570 and574, the strict correspondence helper rejects (returned None: fewer than90good matches OR under70%retention; zero in diagnostic JSON denotes rejected set, not literally zero matches).

At861->880 there are255strict image pairs,92.16%epipolar inliers,217positive-depth supports; rank/null gates pass, but independent subset rotations disagree by .6784degrees (limit .15). More matches and a low residual cannot override that instability. At861->890, the strict correspondence helper rejects. Frame892 is31frames from anchor and fails both the30frame age scope and strict pair check. Diagnostic probes beyond age are explanation only, not eligible candidate observations. Probe robust fits seed RNG by current frame; they need not reproduce live random samples exactly.

This narrows the unresolved gaps to poor direct correspondence retention and orientation identifiability/subset inconsistency in mixed motion, rather than lack of a code path to call essential geometry. Do not relax null/subset/match gates or stitch identity-reset headings into one path. No safe improvement demonstrated in these trials.

## Validation and continuation

79automated tests pass. Broader old/new rotation or negative-control replays were not repeated for failed candidates because neither passes primary improvement criteria; no production change needs regression promotion. No Pi connection, camera, API or physical motion requested. Experiments and production hashes saved. Phase8 remains OPEN, including mixed-motion rotation gaps, initialized-map network test and eventual fresh final validation.

Next bounded analysis: record exact strict-match rejection counts and photometric/forward-backward distributions around554->570/574 and861->890, then test a better-supported recent image anchor without assuming its unobserved orientation. Evaluate against original-reference availability and moving-window error. If the image geometry remains non-identifiable, retain explicit unknown intervals; a software change must not invent their rotation. Use saved data first. v8 remains the normal live default.

Artifacts: laptop/rotation_image_candidate.py, probe_rotation_image.py, diagnose_rotation_image.py; laptop/rotation_archive_candidate.py, probe_rotation_archive.py; results/experiments/rotation-v10/{fresh-rotation,comparison,gate-diagnostics}.json and rotation-v11/{fresh-rotation,comparison}.json. Previous v9 retained separately. Probe outputs refuse overwriting completed experiments; use new filenames for new candidates.
