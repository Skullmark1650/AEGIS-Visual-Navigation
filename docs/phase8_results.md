# Final prototype results

The final default is **retained-map-recovery-v10**. Phase 8 closed for agreed limited local-map prototype checks. Continuous global navigation, arbitrary-room robustness, independent metric accuracy and drone use remain unvalidated.

The final fresh series used two recordings with unchanged software and 4,988 source frames. Qualification before those captures used 84 automated tests and 27,059 saved frames. Original detailed reports preserve earlier failures and exclusions.

| Measurement | Reported result | Interpretation |
|---|---|---|
| Main receive rate | 14.689 FPS | Tested nominal 15 FPS profile |
| Stationary period | 20 s, 301 frames, no observed poses | Stationary observation did not fabricate motion |
| Intentional SSH-forward outage | 2.250 s | One transport error and 47-frame producer gap |
| Network recovery | 1.657 s after tunnel listening | Same supported local map recovered |
| Supported stationary hold | 78.375 s | Before covered-view test |
| Covered-view recovery | 1.797 s after first sampled clear frame | Same map recovered; about 0.21 s sampling uncertainty |
| Movement followup receive rate | 15.003 FPS | 1,096 frames, no transport gaps/errors |
| Movement followup map | Retained through return | A separate short successful trial |

The longer run lost its first map during outbound movement and established a new map **before** the two recovery tests. That second map recovered after the faults, then was lost again during return. Recovery success is not a claim that the whole route remained tracked.

The first nominal 50 mm movement had a camera-derived reference excursion of 66.813 mm, outside the frozen 40–60 mm execution range, and remains inconclusive. A separately preregistered movement repeat aligned the same camera-base point at marks 50 mm apart. Its camera-derived excursion was 57.138 mm and return offset 7.769 mm; endpoint orientation changed 2.428 degrees. It retained one map through return.

For 379 paired observations in that repeat, a single initial scale gave 2.778 mm RMS and 4.035 mm maximum comparison error. **These are correlated comparisons using the same camera and calibration, not independent millimeter accuracy.** The reference itself has uncertainty. A successful repeat does not erase the longer run's return failure.

Rotation gaps remain, monocular scale remains arbitrary without a valid external scale source, and new maps have independent origins. There is no independently measured global trajectory drift, loop closure, true-north heading, continuous pose availability, or flight validation.

For full reported context see [final series](phase8_v10_final_series.md), [v10 improvements](improvements_v10.md), and [archive availability](RESEARCH_ARCHIVE.md). Private source recordings and result manifests are not distributed in this publication snapshot, so these measurements cannot be independently reproduced from this repository alone.
