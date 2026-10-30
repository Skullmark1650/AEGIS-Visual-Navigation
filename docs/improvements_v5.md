# Phase 8 rotation and local-map recovery — v5

## Outcome

Default estimator `rotation-recovery-v5` improves the recent turn recording from 21 to 84 accepted rotation-only updates and reduces the number of pose segments from eight to four. Full heading continuity is still not demonstrated: the recording has a remaining reset during the turn/return, and the target leaves the image during part of that motion. No certified real-world angular error or heading closure is available.

The original repeated-path recording now recovers its previous map rather than initializing a differently scaled replacement. Map loss is recorded at frame 1281 (elapsed 83.922 s); recovery confirms at frame 1310 (85.859 s): 1.937 s after the estimator reset. Map ID 1, its origin and its arbitrary scale are reused. The missing interval remains a separate path segment, not a reconstructed movement. V4 had two map initializations and no old-map recovery; v5 has one initialization, 2,182 map poses, one confirmed recovery and 39 triangulated new tracked IDs.

All 68 automated tests pass. The complete 14,693-frame original study and 2,891 recent frames retain integrity-check evidence; no new camera recording, Pi operation, cloud request or user movement was needed. Original files/reports remain intact; v4 source is frozen in `results/backups/improvements-v4/visual_odometry.py`.

## Rotation changes

Two-view translation initialization still requires twelve pixels of median anchor movement. Rotation has its own probe from four pixels, so a slow turn need not wait for translation-sized image displacement. It still requires broad coverage, at least 60 correspondences, 90% homography support, median bearing reprojection residual at most .4 pixels, at least 90% of residuals below one pixel, and a turn between .05 and 20 degrees.

Rather than a fixed homography singular-spread cutoff alone, the estimator decomposes all admissible homography rotation branches. Their maximum angular separation must be no more than .3 degrees, and the estimated turn must exceed twice that separation. It never chooses a convenient large-ambiguity branch to fill a gap. This is a model-ambiguity gate, not a confidence interval or proof that translation is zero. The singular spread and branch separation are logged for diagnosis.

The recent turn remains in two observed orientation stretches (four total segments including unknown/reset states). The dominant stretch captures much more of the motion; segments cannot be summed into a trusted total turn. The old rotation recording improves from ten to 63 rotation updates. Extra acceptance is availability evidence, not independent accuracy validation.

## Map longevity

After a well-supported low-residual PnP pose (median residual below .3 pixels, at least 85% support), new tracker IDs can be seeded in the existing map. Two known map poses supply triangulation without introducing a new arbitrary scale. Seeds must span at least five frames, .1 map units and .75 degrees of ray parallax; both reprojections must be within .5 pixels, with positive bounded depth. Seeds expire after 150 producer frames. Inactive IDs are pruned, keeping the active set bounded by the tracker.

The repeated-path run adds 39 mapped IDs. The recent horizontal run adds 47 while preserving its 898 consecutive map poses and full recorded return. Synthetic tests verify that new IDs recover known 3D coordinates in the same scale and continue tracking after the original mapped IDs disappear.

## Recovery after loss

Up to three image/3D keyframes are retained for the current map. After loss, bidirectional pyramidal LK rematches frozen keyframe points to the current image; PnP and LM refinement then estimate pose against their original 3D coordinates. Recovery requires at least 60 good LK matches, at least 40 PnP inliers and 70% support, broad image coverage, median map reprojection error no more than .5 pixels, positive depth and at least 50 one-to-one tracker associations within .75 pixels.

Two distinct current frames must agree within .2 map units and two degrees before recovery is accepted. A repeated call on the same frame cannot confirm itself. Each candidate is limited to two map units and 20 degrees from a saved keyframe. Checks run every five producer frames; keyframes older than 900 producer frames are excluded. Session, resolution and nonmonotonic-frame changes invalidate keyframes. This is bounded local visual recovery, not global place recognition or recovery from arbitrary movement.

The first candidate is `relocalizing`, with no observed pose. `relocalized` restores the map ID/origin/scale and starts a new observed segment at the recovered position. The dashboard preserves that segment origin so it cannot draw a fictitious line from zero through the unseen interval. Subsequent poses return to `map_tracking`. Map ID, segment origin, added-ID counts and rotation ambiguity are present in the fixed CSV schema; diagnostics and summaries explain the distinctions.

Point reassociation uses vectorized distances and unique nearest matches. In the saved-video ID-reset experiment, confirmation frames took 7.5 and 6.8 ms in the estimator on this laptop (an earlier loop implementation took roughly 131 and 134 ms). These are offline timings during regression work, not a new live camera/display FPS benchmark. Update timings now include rotation probes, anchor matching, replenishment and recovery work.

## Paired recent-recording and fault checks

- Stationary: 214 frames, zero new poses in both versions.
- Horizontal: 1,336 frames, unchanged one initialization plus 898 map poses, no loss. Shared-camera board comparison after one initial scale alignment: 1.250 mm RMS / 2.317 mm maximum across 61 samples, versus v4's 1.164 / 2.281 mm. This small change is not an accuracy improvement; reference perturbation sensitivity was already around 2.3 mm. End position differs from the reference by .865 mm under the fitted scale. No independent millimeter accuracy is claimed.
- Rotation: 1,341 frames, 21 -> 84 rotation-only updates, eight -> four segments, no invented translation/map initialization.
- Tracker-ID reset injected into the unmodified horizontal video at frame 650: map 1 confirms again at frame 660, .672 s later, with 887 normal mapped poses plus one recovered pose. V4 starts a new map instead. This simulates tracker-state loss; it is not a physical camera outage or occlusion experiment.
- Original repeated path: genuine recorded PnP loss, recovered map 1 after 1.937 s, without changing scale. Four tentative candidates precede confirmation. Timing is reset-relative, not a measured physical uncover event.

## Full original-study regression

Every raw JPEG was checked against its original SHA-256 again. Candidate and v4 baseline use the same LK correspondences and per-frame OpenCV seed. Cached replays also decode keyframes through the same RGB-to-gray path as the live tracker. The final selected reports record matching estimator source hashes.

| Recording | Frames | Rotation-only | Map poses | Confirmed old-map recovery |
|---|---:|---:|---:|---:|
| stationary | 439 | 0 | 0 | 0 |
| horizontal | 886 | 9 | 515 | 0 |
| vertical | 891 | 6 | 435 | 0 |
| rotation | 1792 | 63 | 0 | 0 |
| low-light | 1793 | 0 | 0 | 0 |
| low-texture | 1791 | 0 | 0 | 0 |
| rapid-motion | 1791 | 0 | 1315 | 0 |
| feature-loss | 1791 | 0 | 0 | 0 |
| interruption | 829 | 0 | 0 | 0 |
| repeat-path | 2690 | 0 | 2182 | 1 |

Stationary, lighting, low-texture, feature-loss and interruption recordings remain at zero observed pose updates. These negative recordings did not initialize a map: they do not prove robustness of an already-initialized map under every lighting change or physical occlusion. The old vertical run has tentative recovery candidates but does not confirm recovery; it eventually initializes a different map. No unsupported old-origin continuity is claimed there.

## Automated/synthetic evidence

All 68 tests pass, including known-scale map replenishment, original-ID disappearance, return-to-origin PnP with outliers, blank/unrelated image rejection, two-frame confirmation, same-frame rejection, session invalidation, gap-safe path origins, stable schemas and 70 planar-slide controls (including 4–12-pixel motions).

Known nonplanar translation remains 10/10 accepted, maximum direction error 2.849 degrees and rotation error .5255 degrees. Pure-turn projections remain 20/20 accepted with .00731-degree maximum error. A new 121-frame known turn/return produces 60 rotation updates without an intermediate heading reset: maximum orientation error .1723 degrees and final error .00085 degrees. Stationary, planar and 80%-outlier translation controls remain rejected. These synthetic inputs do not reproduce exposure changes, rolling shutter, scene dynamics or hardware noise.

## Remaining Phase 8 work

Real turn continuity still has a gap. Local recovery is verified for the saved repeated-path loss and controlled tracker-state injection, not arbitrary viewpoint/scene changes. There is no global place-recognition system, bundle adjustment, loop-closure optimizer, IMU fusion or independent metric scale. Recovered origin/scale does not reconstruct motion during a gap or prove zero drift.

Phase 8 remains open pending remaining rotation reliability and eventual fresh end-to-end validation of the final software. No further physical test is needed now. Pi-only migration and Phase 9 have not started. Camera focus/profile/calibration are unchanged, and the live dashboard has not been opened in this offline pass.

## Artifacts

- `results/reports/v5-full-study-verified.json`: paired original-study replay and source hashes.
- `v5-rotation-verified.json`, `v5-horizontal-verified.json`, `v5-stationary-verified.json`: paired recent tests.
- `v5-repeat-verified.json`: exact loss/recovery events and map IDs.
- `v5-reset-verified.json`: explicitly labeled simulated tracker reset on real video.
- `v5-horizontal-reference.json`: correlated reference comparison (same trajectory as the selected horizontal replay).
- `v5-regression-verified.json`: synthetic controls and turn sequence.
- `v5-final-source-hashes.json`: final source/test/report and selected artifact hashes.

The dashboard launcher is unchanged: `./scripts/start_stream.ps1 -Dashboard`. To repeat the injected-reset experiment, choose an unused destination:

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_cached --recording data/validation/horizontal-20261029-043504 --cache results/cache/horizontal-043504.npz --baseline results/backups/improvements-v4/visual_odometry.py --inject-reset-frame 650 --output results/reports/NEW-reset.json
```
