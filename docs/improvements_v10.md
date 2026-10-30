# Retained map recovery v10

## Change

Recovery now keeps the larger distinct, geometrically verified PnP inlier set whenever it exceeds incidental tracker-seed associations, even when those associations already pass the50point minimum. Before,61seed coincidences caused134of195verified observations to be discarded. Afterward, the actively tracked inliers fell below the60needed to refresh a recovery keyframe, so a green map could outlive its recovery archive. The v10change fixes that retention decision, not the count/geometry gates.

Same independent descriptor guide, bidirectional LK/photometric/bounds gates, PnP/coverage/positive-depth/reprojection checks, two distinct-frame pose confirmation, session/age limits and fresh-ID adoption remain. All adopted points are CURRENT image measurements, not guessed historical flow. Larger set selection occurs only AFTER pose confirmation. Existing support floors are not reduced and old image timestamps are not extended. Newunitcase deliberately supplies61coincident seeds plus a larger verified cloud; it fails old behavior and passes new retention.84tests pass.

## Primary saved failing recording

Freshv9recording3722frames replayed with independent actual tracker states, verifying everyJPEGhash and profile. Frozenv9baseline retained2maps:61landmarks after network, subsequent inliers45-58, no stationaryrefresh after network, no coverrecovery, newmap2onreturn. V10retains195landmarks at same network-recovery frame1045, subsequent inliers minimum177,1756refresh-eligible frames, and recovers map1/root28at2935about1.688safter first sampledclearview. Sourceclear sample has~.21s sampling uncertainty. Network source-frame receipt-relative recovery1.453s unchanged; old actual livepose-ready1.750s is NOT a newv10live measurement. Replay timing is source-time evidence only.

V10has1initialization,2904map-tracking frames and2recoveries vsbaseline2initializations/2178tracking/1recovery. It keeps map1through the return toA, does not relabel a neworigin. Missing-motion gaps remain explicit. Two additional accepted frames2802/2803, inside v9's broader reset interval, were visually checked and still show partial cover with boardfeatures visible. No pose between2804and firstclearreference, including fullyblocked rawframe2850. Do not label all v9resetframes as fullyblocked ground truth.

Per-map initial scale stays31.0023mm/unit from the initial baseline, not a whole-trajectory fit:1696paired same-camera boardreference samples, RMS1.91236mm/max3.26233mm, final difference .50528mm. Local endpoint/peak ratio .11682. These include long holds, are correlated with same camera/calibration, and are NOT independent metric accuracy or proof ofzero drift. Original physical return was6.195mmfrominitial in the reference; the algorithm is not expected to fabricate a zero endpoint. This development footage is not fresh acceptance for v10.

## Evidence and reproduction

results/experiments/retained-landmarks-v22: preregistration.json; v9-baseline.py; fresh-v9.json and fresh-review.json; per-recording regression reports/index; finalsummary/hashes whencomplete. Baseline also results/backups/improvements-v9/visual_odometry.py. Scripts laptop/probe_retained_landmarks.py, probe_retained_regressions.py, review_retained_landmarks.py. Tests test_odometry.py contains new61seedcoincidence fixture. No camera/Pi/API/user movement used. Original failed livev9results remain unchanged.

Earlier-recording qualification is appended below once all cases complete. Phase8OPEN until scoped freshv10validation; noPhase9orPi-onlymigration. Do not keep repeating physical work without this offline qualification. No first-rotation-gap fix claimed; temporary rotation gaps remain accepted documented limitation.

## Completed earlier-recording qualification

17unique recordings/27059frames total, including3722frame primary case and16earlier recordings. Full original10condition study plus3recent recordings and3later trials replayed against frozenv9using real mutable tracker state. Every earlier recording retains exactly the same status counts, initialization frames/mapIDs, and recovery frames/mapIDs. Static/lowlight/lowtexture/featureloss/interruption negative controls remain zero position and rotation observations. Old repeated path remains2192maptrackingframes andmap1recovery1300/85.188s. Earlier covered-view trial remains1494maptrackingframes andmap1recovery1185/77.547s. Old/new rotation outcomes unchanged; no rotation-gap repair claimed.

The earlier false-map recording still rejects map1return and uses clearly separate map2, with network/cover recoveries1665/2540. Independent old-reference review gives same values asv9: earlier covered-view849samples2.34994mmRMS/3.49135max; wrong-maprecord's separate map2785samples .41260mmRMS/1.02484max. These are one-initial-scale correlated comparisons, not certified accuracy. The initial short wrong-maprecord map1segment remains4.406mmRMS/7.149max; the known40mmfalse reattachment remains rejected. No old/new origins silently connected.

Default retained-map-recovery-v10 is qualified for the next fresh test.84automated tests pass, including the new61coincidence regression. Source helpers/calibration/settings match frozenv9except the explicit core retention/version change. v9backup saved. Completed index, per-case fullreports, summary, reference reviews and hashes preserved. No live v10capture occurred, so prior failed freshv9trial is not reclassified as passed. Phase8stillOPENpending fresh validation ofv10with the same required fault/accuracy gates. No camera/API/user action in this software pass; noPhase9orPi-onlymigration.
