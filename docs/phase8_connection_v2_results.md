# Phase 8 fresh connection interruption test and blocking findings

## User-authorized scope

User accepts temporary rotation gaps as a documented research-prototype limitation. v2scope/requirements and frozen v8sources recorded in results/reports/phase8-v2-current.json and the pointed preregistration.json before fresh acquisition. Prior v1failed/inconclusive results remain. Rotation acceptance does not waive position accuracy or map recovery checks, and no continuous/metric/GPS-denied qualification is implied.

## Fresh recording

data/validation/prototype-v2-20261029-172000 contains2831rawframes, one producer session, two laptop connections,14.758receivedFPS overall. All raw hashes verified by offline analyzer;1283usable boardreference samples. Planned outage causes one connection error and a single47producer-frame gap. No additional sequence gaps; dashboard stale-feed behavior remains under existing tests.

Operator confirms camera A->B nominal50mm, then B->A, target fixed. Initial outbound map1initializes634/41.610s but loses at659/43.282s. No fault issued until return/recovery; map1reacquires1265/83.672s, loses briefly1277/84.469s and reacquires1285/85.000s. Those unexpected losses remain in evidence. Do not count all waiting periods as valid position tracking.

## Actual connection interruption: PASS for connection/reference recovery

Only the controller-owned laptopSSHforward is terminated; Pi producer remains running. Forward closes22:21:58.409578UTC, new forward listens22:22:00.650388UTC:2.24081s unavailability. Camera/target stationary at A. Receiver detects the broken connection, reconnects, resets tracks on the actual producer gap at1655/109.735s, and reacquires map1at1665/110.328s with headingepoch1/root20. Approximate1.558s from listening to mapped receipt, well within5s. Timing is reconstructed from sidecarUTC minus rowelapsed; includes processing/write timing uncertainty (~.1s allowance), not an exactlatency/zero-clock-uncertainty claim. Producer session/map/reference retained. One intentionally induced error/gap is excluded only for the fault gate.

This passes transport and same-reference reacquisition, NOT accurate position restoration; pre-existing positional error is a separate failure below.

## Stationary and execution checks

Initial20s contains301receivedframes, zero observed pose updates, mean-LK-flow95th .02587px (<.25).101usable boardreferences, maximum center deviation .560mm. Boardreference maximum excursion59.048mm and endpoint4.510mm, consistent with prescribed40-60mm excursion/<=10mmreturn limits. Reference endpoint rotation1.310deg indicates some unintended turn. Boardreference uses the same camera/calibration and is correlated, not independent truth.

## Required checks that FAILED

After connection test, operator fully covers view~5s without moving camera at A, then restores scene. Tracking resets at2418/160.563s; full-board samples disappear2416->2515. Clear full-board sample2515/166.985s, but productionv8never recovers its map by recording end. Occlusion recovery FAILS, unlike earlier short-hold development recording.

Position comparison uses one INITIAL map baseline scale19.40448mm/unit, not a full-trajectory fit.741paired v8map samples: correlatedRMS39.942mm, max41.705mm, last paired40.446mm. Pre-first-loss634-658 has16samples RMS4.406/max7.149mm; returned-map1285-1654 RMS40.502mm and afternetwork1665-2417 RMS40.307mm. Therefore the large offset already exists before the deliberate connection interruption. Same mapID and low PnPresidual do not prove correct scene correspondence/origin. Repeated checkerboard aliases are a possible cause to investigate, not yet established. No zero-drift or valid global loop claim. These measured misses exceed5mmRMS/10mmmax limits; accepting rotation gaps does not make them pass.

## Targeted offline follow-up

Experimental map_refresh_candidate.py updates the latest recovery image every30frames during a supported stationary map observation, preserving the same900frame age cap and existing pose/confirmation gates; earlier diverse archive views retained. This is a fresh measured keyframe, not extending stale image timestamps. On paired full-state replay of THIS recording, it recovers map1at2540/168.657s,1.672s after the sampled clear view (sampling bound~.2s), and stays mapped to end. Network recovery timing unchanged. Candidate1466maptrackingframes/4recoveries vsv8 1109/3; same initial map/reset history preserved. This supports investigation of stale stationary archives. Exact archive-age diagnostic at loss has not been logged; do not assert unique cause solely from the improvement.

Candidate does NOT fix positional offset:861paired samples RMS40.098/max41.705mm. It is not promoted as a validated navigation fix. Two keyframe-refresh tests plus existing suite total81passingtests. Offline regression results saved separately when complete; same developer footage is not fresh acceptance.

## Status and next work

Phase8remainsOPEN. Connection interruption task is complete with the scoped success above; fresh occlusion and position accuracy failed. User does not need more movement now. Diagnose correspondence/pose ambiguity around the first returned-map recovery, harden map correctness, and assess stationary archive refresh using saved data. No new continuous-rotation work required under accepted limitedscope. Only after actual fixes and appropriate controls should a short fresh validation be requested. Do not repeat unchanged desk tests or mark complete merely because map IDs return.

Receiver/ownedSSHforward/Pi stream stopped cleanly; cleanup_finished logged. Pi left powered, no shutdown requested. Candidate and baseline data in results/experiments/map-refresh-v20. Fresh raw/report/analysis/events pointed by phase8-v2-current.json. No API calls. NoPhase9orPi-onlymigration.

## Completed offline regression follow-up

Paired full-state replay covers 15086unique recorded frames including the fresh v2trial. Negative stationary/light/texture/feature-loss/interruption controls unchanged with no pose observations. Old repeated path retains2182maptracking andone recovery. Earlier fresh horizontal retainsone map/one recovery but mappedframes1504->1494; tentative recoveries2->4, a small recovery-delay regression explicitly retained. Fresh rotation remains22updates/same gaps. Candidate remains experimental, not promoted: fixing archival recovery alone does not resolve the40mmposition mismatch. All sources, raw records and final reports saved.
