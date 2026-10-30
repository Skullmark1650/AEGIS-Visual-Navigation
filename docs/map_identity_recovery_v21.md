# Incorrect map identity and covered-view recovery: v21 diagnosis

## Confirmed causes

Saved v2recording: first returned-map recovery1265uses keyframe634.61mapped board correspondences that pass old bidirectional LK checks disagree with fixed-board projection by47.63pxmedian (vector47.40,-2.93px). At1285the same61pairs are47.32pxwrong. This is direct evidence of wrong feature identity on repeated target structure, consistent with the~40mmmap offset, not just an inaccurate transport clock. The board reference is diagnostic only; it never enters the recovery code. Later source1361/1391matches atnetworkrecovery1665agree within .131/.039px, preserving an ALREADY incorrect map origin. Same ID, good reprojection and bidirectional cycle did not establish original scene identity.

At uncovered sample2515the archive contains frames1331/1361/1391aged1184/1154/1124frames. All exceed existing900frame limit. At2540the images have86/120/113old-LKmatches, but their age is ineligible. This confirms stale stationary archives as the later recovery blocker. Never extend timestamps of old images.

## Candidate

Experimental guided_map_candidate.py combines independently detected mutual SIFT .7ratio matches (>=90distinct2px-spaced matches), global homography proposal with2pxRANSAC and>=75%support, and old mapped-feature LK initialized by that proposal. Bidirectional LK retains patch<25, FB<1px, requires refined target<=2pxfrom global guide, finite in-bounds points. Original3Dpose checks, two-frame confirmation, same session/map/age restrictions and fresh point IDs remain. Reject unsupported/ambiguous guides; no fallback to the old possibly aliased LK.

The global guide is deliberately conservative in nonplanar or low-overlap views. It is not proof of zero translation or a replacement pose model; PnP still validates mapped3Dpoints afterward. At634->1265/1285only64/60distinct descriptor matches exist, with60.9%/43.3%homography support. The candidate rejects these recoveries instead of accepting the wrong old map. It does not secretly correct them with checkerboard coordinates.

Refresh the latest keyframe every30frames only from successfully supported current map observations, preserving earlier archive views and the900frame maximum since actual observation. This addresses long stationary holds while keeping stale/session invalidation.

## Primary replay

Full stateful paired replay verifies2831source JPEGhashes and maintains independent tracker state, including adopted mapped points. Baseline v8reports1109maptrackingframes/3recoveries/1initialization; candidate1376trackingframes/2recoveries/2initializations. Candidate rejects oldmap1return; a NEW map2initializes1364/90.266s fromanchor1254. Its origin/scale/heading are independent of rejectedmap1. Newheadingepoch3/root1254 is NOT originalheadingepoch1/root20. The path gap remains; no original trajectory/loop repair claim.

Candidate recovers map2at1665/110.328s after actual connection interruption and2540/168.657s after occlusion, staysmap2toend. Occlusion~1.672s after first sampled clearboard2515/166.985s (samplingbound~.2s). No position observations during blocked/resetframes2418-2510.

Newmap2reference comparison:785samples, one initial scale45.5552mm/unit from map2initial baseline, RMS .41260mm/max1.02484mm/last .10744mm. Two independently validated initial reference poses used, extraanchor1254added with strict same planar-reference guards. These are correlated same-camera/calibration values after one fitted scale; not independent metricaccuracy. Long holds dominate samplecount. No intermapalignment or completeA->B->Aloopscore. The original map remains unrecovered, so same-original-map requirement of that old path is not passed.

## Verification / continuation

83tests pass before any promotion, including known36pxtextured-shift matching, blank/wrong-scene rejection and periodic-checkerboard-only rejection. Archived replay/regression status and final deployment decision appended after completion. Productionv8currently unchanged. No camera/Pi/API/user movement. Original v2livefailure retained; developmentreplays do not turn it into a fresh acceptance pass. Phase8OPEN. NoPhase9orPi-onlymigration.

Artifacts: results/experiments/map-diagnosis-v21/{archive-and-matches,global-guide-diagnostics,unthresholded-guide-counts,candidate-preregistration,fresh-v2,new-map-review}.json; laptop/diagnose_map_identity.py, guided_map_candidate.py, probe_guided_map.py. Full-state controls saved regressions.json when finished.

## Final tested change and deployment

Promoted as default guided-map-recovery-v9 after paired full-state evidence across15086unique recordedframes and83passingtests. v8source frozen results/backups/improvements-v8/visual_odometry.py. New production matching helper laptop/map_correspondence.py is independent of experimental rotation modules. Diagnostic script explicitly loads the frozen v8source so old-failure reproduction remains possible. Main camera/stream/calibration settings unchanged. Live dashboard has NOT been reopened on v9; fresh acceptance remains required.

Full controls: stationary439,lowlight1793,lowtexture1791,featureloss1791,interruption829remainzero observed poses; oldrepeat2690retains one map and improves maptracking2182->2192,recovery1310/85.859s->1300/85.188s(.671searlier). Earlier fresh horizontal1879retains one map/one recovery but mappedframes1504->1494,recovery1175/76.875->1185/77.547s(.672slater); this availability tradeoff is documented. Fresh rotation1043unchanged22updates/same gaps. Current fresh2831rejects the false old map, correctly labels new map2, recovers it after both faults. Globalguide may conservatively reject nonplanar/low-texture/low-overlap views; that cost is preferable to an unsupported old-map position, not proof that all ambiguity is solved.

Production refactor preserves the tested prototype's matching and pose decisions. Greedy spatial deduplication was vectorized with exact output-array equality verified on a known shifted textured pair:1317matches unchanged, measured matching walltime5.946s->.318s on this laptop. That is a component benchmark, not liveFPS or end-to-end latency. Normal83test suite passed after installing/refactoring; standard odometry21tests also passed staged production before installation. Recovery work still costs processing time; measure actual v9live timing in fresh validation.

Phase8remainsOPEN. This change prevents the observed false return; it does not recover oldmap1or link map2toits origin. Fresh user movement is not requested in this software turn. Next is scoped fresh v9validation (stationary/mapestablishment/connection/coveredview) with explicit handling of a new map when old one is unavailable; user accepted rotation gaps, not arbitrary wrong position. Keep that limitation visible. NoPhase9/Pi-onlymigration. All raw evidence/failures/provenance retained.
