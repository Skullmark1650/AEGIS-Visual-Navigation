# Fresh v9 validation: required covered-view recovery failed

## Scope and provenance

Frozen guided-map-recovery-v9tested live under preregistered phase8-v9-fresh-v3limited local-map prototype protocol. User accepts temporary rotation gaps, not incorrect position or failed required map recovery. Original failures retained. Source hashes verified unchanged through capture. No code tuned during the trial. Raw recording: data/validation/v9-fresh-20261029-190444. Control,events,preflight,CSV/report and finalanalysis pointed by results/reports/phase8-v9-fresh-current.json.

## Confirmed operational results

3722receivedframes,14.8136FPS overall,2connections. One planned connection error and one47producer-frame gap; no other sequence gaps. Initial20s:301frames,zero observedpose updates, mean-LK-flow95th .02721px (<.25). Targetpreflight and atBboardreference valid/unambiguous.

Operator confirms nominal50mmA->B and returnB->A, fixed target, camera keptstill during faults. Map1initializes702/45.719s, headingepoch1/root28. After actual ownedSSHforward interruption, map1and sameheading recover1045/68.672s. Forwardunavailable2.438s; pose-ready recovery1.750s from forwardlistening on same-host monotonic clock. Network recovery PASS (<5s). No inferred sidecarUTC latency needed.

Supported stationary hold logged79.562s (>65). At covercue map1stilltracking. Last observedmap1pose2801/185.625s; reset2802/185.703s. Operator confirms fullcover~5s, restores while holdingB. Map1neverreturns; featuretrackingresumes without position. Returning toAinitializes NEWmap2at3659/247.015s, epoch108/root3643. This is a new origin/scale, not recovery or loop closure. Required covered-view recovery FAIL. NoPhase8completion. Full-position/reference analysis appended once complete; do not count unscored requirements as passed.

## Diagnostic finding, frozen code unchanged

After networkrecovery1045,195PnPinliers were verified but only61landmarks retained through nearby tracker-seed association. Subsequent active poses consistently use fewerthan60inliers:1045-1427sampled382maptrackingframes range51-56;1427-2600sampled1174range46-58;2600-2801sampled202range45-49. remember_map receives onlyPnPinliers and requires>=60, so the new stationary-refresh path cannot execute. Latest map1trackingframe even eligible forrefresh is987/64.719s; even akeyframe storedthen wouldexpireby1887. Alloldmap1archives must be expired wellbefore cover/restoration. This is a count-bound proof, not an asserted exact archive snapshot.

Nearby healthyimages2801/2780/2750to restored3109 have230/225/227unique descriptor matches with97.8%/99.1%/98.2%homography support. These are representative views, not asserted exact archiveframes, and support scene restoration/overlap. Actual raw2801and3109were visually checked: fullboardpresent, no grossscenechange. No blaming user execution for a map that stayedactive without maintaining eligible recovery evidence.

Likely targeted follow-up: retain more of the195verified mapcorrespondences when reconnecting instead of relying primarily on61coincident tracker seeds, while keeping unique IDs, geometry, same-map confirmation and fresh-image/age gates. Preserve enough real observed points for refreshing; do not lower thresholds or merely extendoldtimestamps. Test offline on this record plus earlierwrongmap/recovery/controlcases before a newversion. This is proposed, not implemented/promoted in this freshvalidation turn.

## Cleanup

Receivercompletednormally, ownedforward/Pistreamstoppedcleanly, cleanup_finishedlogged. Allrawdata/events/frozenhashes saved. No additionalcamera movement requested now. NoPhase9orPi-onlymigration. Phase8OPEN on requiredcovered-view failure, regardless of documentedrotationgaps or networksuccess.

## Completed reference/position assessment

All3722rawJPEGhashes verified.1934usable checkerboard reference samples;35rejected samples include deliberate occlusion. Maximum reference excursion51.962mm and final displacement6.195mm (limits40-60and<=10), endpoint rotation .130deg. Stationary101reference samples: maximum center radius .403mm and rotation .04096deg, within5mm/.5deg limits.

Map1:1360paired observations, one INITIAL baseline scale31.0023mm/unit, correlatedRMS1.76435mm/max3.26233mm. Map2:93paired observations, separately initialized scale14.7322mm/unit,RMS1.39507mm/max1.96170mm. Both satisfy observed-map5mmRMS/10mmmax criteria. These include long holds, use same camera/calibration, and are NOT independent metric accuracy. Map2cannot be aligned/stitched to map1to claim global loop closure, drift or covered-view recovery. No return of the earlier40mmfalse-map position was observed in the scored map segments.

Finalverdict: network,stationary,execution and observed per-map comparison checks PASS; required SAME-map covered-view recovery FAILS. Phase8remainsOPEN. Sources remained frozen. Do not reclassify newmap2as recoveredmap1or change the gates after seeing the failure. No code fix installed during this trial. Next saved-data task: preserve more verified recovered landmarks after network reconnection, retaining geometry/unique-ID/confirmation requirements, then replay all relevant controls before another fresh test. No more camera movements requested now.
