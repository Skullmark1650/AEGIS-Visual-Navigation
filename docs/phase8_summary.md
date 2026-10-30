## Current final scoped verdict: Phase 8 complete for limited prototype

Read docs/phase8_v10_final_series.md. Frozenv10freshseries4988frames passesrequiredscopedcomponentgates:network1.657s,cover1.797safter78.375shold,same testmap/reference, stationary/observedpositionlimits,andseparatemeasuredmotionrepeat. Mainnominalmove66.813mm remainsinconclusive;outboundrestart/returnlossremainlimitations. Rotation/positiongaps,arbitraryscale/neworigins, noindependent/globalmetricqualification. Originalstrictergoalsremainunachievedasdocumented. Phase9/Pi-onlynotstarted. Liveallstopped; no required cameraactionnow. Earlierhistorybelowisretained,notcurrentstatus.

## Current software follow-up
See docs/improvements_v10.md: retained-landmark fix verified on27059savedframes/84tests; same-map covered recovery restored in development replay. Freshv9failure retained; Phase8OPENuntil freshv10validation. Rotationgaps remain accepted limitation.

## Latest freshv9assessment
See docs/phase8_v9_fresh_results.md. Frozenv9network recovery1.750s and per-map reference comparisons pass; long-hold covered-view recovery fails due insufficient retained inliers for keyframe refresh. Phase8OPEN. No further physical test until saved-data fix/control verification. Olderfailedtrials retained below.

## Fresh scoped validation update
See docs/phase8_connection_v2_results.md. Connection/reference recovery passed; position accuracy and physical occlusion recovery failed on current v8. Temporary rotation gaps accepted by user, other gates not waived. Phase8 OPEN; no further physical test requested before saved-data diagnosis.

# Phase 8 controlled validation summary

Ten-condition research validation series, not navigation qualification. Continuous pose reliability failed in motion cases; independent metric drift and angular/direction accuracy remain unavailable.

| Case | Frames | Receive FPS | Mean / p95 processing ms | LK consistency | Accepted poses |
|---|---:|---:|---:|---:|---:|
| stationary | 439 | 15.014 | 15.80 / 18.08 | 100.000% | 0 |
| horizontal | 886 | 15.008 | 15.57 / 18.57 | 99.737% | 1 |
| vertical | 891 | 15.005 | 15.99 / 19.29 | 99.879% | 2 |
| rotation | 1792 | 15.009 | 14.80 / 17.30 | 99.918% | 1 |
| low-light | 1793 | 15.012 | 14.35 / 17.06 | 99.546% | 0 |
| low-texture | 1791 | 15.007 | 14.86 / 17.67 | 67.528% | 0 |
| rapid-motion | 1791 | 15.005 | 15.07 / 17.33 | 99.995% | 1 |
| feature-loss | 1791 | 15.003 | 15.48 / 18.61 | 56.941% | 0 |
| interruption | 829 | 13.971 | 15.32 / 17.41 | 100.000% | 0 |
| repeat-path | 2690 | 15.007 | 15.33 / 18.53 | 99.958% | 9 |

Total verified frames in selected cases: 14693.

LK consistency is accepted/attempted image correspondences. Geometry-evaluation acceptance excludes waits/resets and is not ground-truth correctness. Reference comparisons share calibration and cannot establish independent accuracy.

Frozen estimator/calibration; manual motion confirmations, correlated board PnP, no independent continuous pose ground truth. UI countdown added during series.

See phase8_results.md for per-case references, recovery definitions, operator deviations, and final conclusions. All individual board-reference SVG traces remain in results/reports.
