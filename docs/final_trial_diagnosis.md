# Fresh final-trial diagnosis (v7 unchanged)

## Outcome

Investigated both saved fresh trials with integrity-checked LK caches. Replayed 1,879 horizontal and 1,043 rotation frames (2,922 total) with the unchanged heading-recovery-v7 estimator. Offline status counts reproduce the live CSVs exactly for both recordings. All 76 automated tests pass. No camera, Pi stream, API or physical movement used. Production estimator/tracker/calibration/acceptance limits remain unchanged. These development recordings are no longer held-out evidence for any future tuned candidate.

## Physical occlusion: association bottleneck, then expiry

Horizontal initial map1 is lost when view is blocked. At clear recorded frame1200 (about78.53s), frozen map keyframe360 yields97 valid bidirectional LK matches and88 PnP inliers, median reprojection residual .410px. Keyframe390 yields102 LK matches,100 PnP inliers and .473px residual. Both pass existing pose geometry, coverage, positive depth and bounded motion checks. However only11 and12 respectively associate one-to-one with freshly selected tracker points within the existing .75px radius; recovery requires50 associations. It therefore rejects a geometrically supported old-map match before its two-frame confirmation stage. This is not simply absence of scene overlap or failure of PnP.

The recovery archive holds frames330/360/390. During the long stationary hold, remember_map does not refresh a keyframe without .2 map-unit motion or5deg change. Frame1200 is still within900-frame age limits; by1300 all three archive entries exceed that limit. Diagnostic PnP probes at1300/1400 intentionally bypass the age filter to explain what evidence remains, and are NOT eligible production recovery events. They do not establish a recovery pass. Map2 later clears the old archive; no origin/scale bridge is valid.

Targeted implementation direction: retain verified recovered map-image points as actual tracked landmarks, rather than depending on coincidence with newly seeded corners; use unique IDs, unchanged geometry and repeated-frame confirmation. Another bounded improvement is refreshing an eligible stationary keyframe without evicting useful diverse views. Do not enlarge the association radius, fabricate landmark identities, extend expiry without tests, or infer position from heading-only recovery. Any implementation needs real-state replay because frozen LK caches would ignore newly inserted tracker points. Required controls include blank/wrong scenes, full physical occlusion, stale/session/resolution invalidation and retention of one map ID with an explicit path gap.

## Rotation: geometry mismatch, not missing features

At reset574 (36.813s), anchor554 retains239 correspondences. Recomputed calibrated homography support is82.4% (required90%); pure-rotation median residual1.342px (limit .4), only27.6% under1px (required90%); admissible homography rotation branch spread .926deg (limit .3).

At reset892 (58.016s), anchor861 retains253 correspondences: homography support56.9%; pure-rotation median residual3.280px;7.1% under1px; branch spread2.123deg. These offline probes recompute robust fits and explain the rejected pair; they are not independent physical truth or exact internal live RANSAC diagnostics.

The measured checkerboard reference already found22.792mm displacement, beyond the15mm pivot protocol. Mixed translation/depth and/or correspondence errors are plausible contributors; the fit statistics alone cannot uniquely attribute their cause. Both pairs substantially violate multiple pure-rotation guards, while translation geometry is also rejected for low parallax/support. Resetting to an explicitly different epoch preserves uncertainty. Forcing these pairs through a rotation model is unjustified. Original heading recovers at frame940/61.204s, but missing samples stay unknown.

Targeted direction: investigate an orientation-only, nonplanar epipolar observation during active tracking, with the same rank/subset identifiability checks already used for heading recovery. If not identifiable, report unavailable orientation and later recovery. Do not force planar/low-parallax pairs or integrate uncertain translation. Current frame940 recovery establishes reference reacquisition, not continuous heading through frames574-939.

## Evidence and next work

- results/reports/v8-horizontal-diagnostic.json: replay, source/cache provenance and per-keyframe rejection counts.
- results/reports/v8-rotation-baseline.json: complete integrity-checked rotation replay.
- results/reports/v8-rotation-gap-diagnostics.json: two rejected-pair measurements.
- laptop/diagnose_final.py: horizontal diagnostic reproduction (uses unchanged production subclass; does not alter decisions).
- results/cache/final-horizontal-redo.npz and final-rotation.npz plus provenance JSON: verified LK evidence.
- results/backups/improvements-v7/visual_odometry.py: frozen source copy.

This investigation adds a concrete diagnosis, not a promoted estimator fix or new acceptance pass. Next implement and test a separate candidate for recovered-map feature continuity, then compare rotation orientation-only options without weakening gates. Use saved footage first; no new user movement needed now. Final validation restarts under a new version after any promoted estimator/tracker change. Phase8 remains OPEN: stationary PASS, same-map occlusion recovery FAIL, rotation protocol INCONCLUSIVE, network recovery untested. No Phase9 or Pi-only migration.
