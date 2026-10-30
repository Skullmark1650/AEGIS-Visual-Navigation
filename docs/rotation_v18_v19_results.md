# Orientation-only multi-view investigation v18 and pending brightness check v19

## Outcome

The orientation-specific multi-view model was built and tested on two fixed saved view sets and synthetic controls. Neither saved set passes. The pending brightness candidate was also checked against full local-reference errors and older/newer rotation footage; it fails its predeclared local-error requirement. Neither is promoted. Production remains landmark-recovery-v8, map-recovery fix intact. All79production automated tests pass. No camera/Pi/API/user movement used.

## V18: orientation without accepted translation

This is a new research model, not relaxation of production pose gates. Essential fits estimate orientation while discarding translation and do not accept position from cheirality. Each edge requires>=90mutual descriptor matches,85%inlier support, normalized design null<=.5/rank>=.0004, a unique admissible rotation below20deg,3complementary trainingfolds with heldout epipolar95th<=1px and rotation spread<=.15deg. Every edge of the3view triangle must pass and composed-vs-direct rotation difference<=.2deg. No averaging rejected edges, no board-based branch choice. Small-turn scope and these engineering gates are not a formal confidence bound. Fixed-view limits/model recorded before running each set.

Saved554/560/574:138/168/110matches across edges. First edge fold spread .068deg but rank/null gate fails in at least one fold; middle edge spread .551deg plus heldout and identifiability rejection; direct edge spread .050deg but low support/heldout errors. Rotation cycle .550deg exceeds .2. Diagnostic cycle is printed even though edges rejected; it is NOT an accepted pose. Saved542/574/620: outer two edges fail90match requirement; middle edge190matches but .335degfold spread and heldout/identifiability rejection. No accepted original-heading bridge.

Pair-level geometry controls:40planar and40nonplanar trials,10seeds at0/.05/.2/.5pxnoise. All40planar reject;21/40nonplanar accept, maximum accepted rotation error .04970deg. Full3view controls:20planar and20nonplanar trials,5seeds across same noise levels. All20planar reject;10/20nonplanar accept, maximum accepted end-rotation error .02532deg. Thus a well-supported ideal orientation-only case can pass without requiring observable translation, but current saved gap fails. These synthetic controls do not predict real-camera accuracy or certify false-positive rates.

## V19: qualify earlier brightness local benefit

Candidate is unchanged v13global-median correction, frozen before follow-up. Scope explicitly second local reset, no first-gap success claim. Preregistered local epoch2 comparison required RMS<=.5deg and max<=1deg across ALL available reference samples, including stale held orientation. Actual134samples RMS .66970deg/max3.36875deg, so candidate fails. Baseline110samples RMS .76017/max3.88035; different epoch lengths mean these aggregate scores are not a matched-sample accuracy improvement. The earlier isolated .133deg sample was insufficient evidence.

Paired older rotation1792frames:73candidate vs74baseline rotation observations, same one original-heading recovery. Newer1341frames:98vs97observations, no new position/map, but this small count gain does not overcome fresh local-error failure. Full status counts/reference availability in regression-summary.json and complete replays. Negative/full-state map regressions from the pending qualification list were deliberately not run once mandatory error gate failed; candidate cannot be promoted. No changes to v8 tracking or its prior physical-occlusion replay evidence.

## Artifacts and continuation

laptop/rotation_orientation_ensemble.py, probe_rotation_orientation.py, probe_rotation_orientation_long.py, verify_orientation_ensemble.py, verify_orientation_three_view.py. results/experiments/rotation-v18/{preregistration,long-preregistration,result,long-result,geometry-controls,three-view-controls}.json. Pairfit andfold details retained. laptop/probe_brightness_regression.py; results/experiments/rotation-v19/{preregistration,fresh-local-error,older,newer,regression-summary}.json. New tracking caches v19-older/newer with provenance. Hash ledger and NEXT_SESSION saved.

The queued bounded software branches are now tested: active E fallback, strict image re-matching, denser/recent observed archives, brightness correction, descriptors/refinement,3Dthreeview reconstruction, longer temporal baseline, and orientation-only fold/cycle model. None provides a qualified continuous original-heading repair for the first gap. Do not restart these experiments unchanged or keep lowering thresholds until the known answer fits.

Next is a scope/architecture decision rather than another named threshold experiment: retain explicit unknown intervals and later reference recovery, or undertake a separately designed multi-frame optimizer/uncertainty estimator with proper independent validation. No claim that all algorithms are impossible, only that this tested path is exhausted. Rotation remains a documented limitation; initialized-map network test and eventual fresh validation remain. Phase8OPEN,noPhase9orPi-onlymigration. No new physical action needed to review findings. If user requests further development, start with the documented failed gates and a substantive model proposal, not another duplicate sweep.
