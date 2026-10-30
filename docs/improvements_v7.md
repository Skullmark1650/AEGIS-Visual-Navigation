# Older rotation interval: heading-reference recovery v7

## Outcome

The older recording now automatically reacquires its original local heading reference after the difficult interval. It no longer finishes permanently referenced to the arbitrary heading created by the reset. This is recovery of an orientation reference, NOT reconstruction of the blurred frames, a continuous angular trajectory through them, or a position fix.

In `rotation-20261029-031748`, the last accepted original-reference orientation is frame 1285 (84.203 s). The reset occurs at frame 1307 (85.672 s). Three verified clear-frame observations at 1375, 1385 and 1395 confirm recovery at frame 1395 (91.547 s), restoring heading epoch 1 and its original reference frame 31. Recovery takes 5.875 s after the reset, or 7.344 s after the last accepted original-reference observation. An earlier tentative match at frame 1335 expires before the confirmation group.

The 88 frames from reset until recovery remain tagged with a different local heading epoch. They are not silently reinterpreted as observations in the original reference. Translation remains unobserved, no map or metric position is created, and the path remains disconnected. The final original-heading reference is restored, but missing rotation/velocity samples are not filled.

Default version is `heading-recovery-v7`. All 74 automated tests pass; the full original-study replay and newer tests preserve the existing good cases. No Pi/camera operation, external API request, new image capture or user movement was needed. Original recordings/calibration/notes remain intact; v6 is frozen under `results/backups/improvements-v6/visual_odometry.py`.

## Why a new recovery path was needed

Raw frames 1285, 1286 and 1290 were visually checked. Frame 1286 has pronounced motion blur. Earlier direct-match experiments retain only about 18–36% of source points at that frame, far below the strict 70% requirement. Later clear views can contain translation as well as rotation; forcing them into the pure-rotation image model is not justified.

A candidate that tried to use partial orientation estimates to carry the entire interval was not promoted: subsequent geometry became unstable and could trigger unwanted new translation/map interpretations. The production solution preserves v6's tracking decisions and instead verifies a later reappearance of the original view. Experimental sources/reports are retained separately.

## Implementation

Up to three heading keyframes retain a grayscale image, image points, a measured local camera-to-world rotation, producer session, heading epoch and reference frame. The first reference is preserved alongside two later views. Only observations in that same trusted epoch extend the archive.

After a heading-epoch reset, and only when no active 3D map is being tracked, recovery checks an earlier view every five producer frames. The reference must be in the same producer session and image shape and no more than 1,800 producer frames old (about two minutes at the configured 15 FPS). Session, resolution and nonmonotonic-frame changes invalidate old references. Existing 3D-map recovery has priority.

Fresh 21-pixel/four-level bidirectional LK requires at least 90 matches and 70% of source points, patch error below five, forward/backward error below .5 pixels and valid image coordinates. It uses the saved images rather than extrapolated motion or long-lived point IDs.

A uniquely supported pure-rotation model can use the unchanged homography/bearing gates. Otherwise, a separate epipolar model observes orientation while discarding translation. It requires:

- At least 90 RANSAC-supported pairs and 85% support.
- Rejection of an almost exact single homography, since it does not identify general 3D epipolar geometry.
- A normalized eight-point design with smallest/next-smallest singular ratio no more than .5 and next-smallest/largest ratio at least .0004.
- At least 10% image coverage, 60 positive-depth pose supports and 85% pose support, with a rotation between .1 and 20 degrees.
- Three validation folds defined before full-fit inlier selection, each with at least 20 pose supports and 80% support; all subset rotations must agree with the full rotation within .15 degrees.

These are conservative engineering identifiability checks, not a formal observability proof, statistical confidence interval or independent angle measurement. RANSAC/all-inlier refitting uses the existing .5-pixel epipolar threshold. The translation vector is deliberately not exposed as an observation.

Three distinct current frames within a 30-producer-frame window must each agree with the current candidate heading within .2 degrees. They need not be consecutive; rejected frames contribute no confirmation. The same frame cannot confirm itself. On acceptance the latest measured orientation is used, not a predicted/interpolated angle or an average of different camera times.

New statuses distinguish `heading_relocalizing` (no accepted recovery) and `heading_relocalized` (orientation only). The latter restores the old heading epoch/reference, starts a new observed segment and leaves position unknown. Heading epoch serials remain unique for subsequent resets even after restoring an earlier epoch. Map keyframes also preserve their heading epoch so map recovery cannot mislabel its orientation frame.

CSV/diagnostics record heading epochs/reference frames, epipolar residual, subset rotation spread and identifiability ratios. The dashboard explicitly says that position and motion through the gap remain unknown. Reference-review tooling compares only headings in the original epoch and recognizes a verified return to it, rather than treating a reset to identity as zero drift.

## Measured older-recording recovery

The confirming frame has 257 positive-depth pose supports out of 270 strict image matches (95.19% support). Median epipolar residual is .3245 pixels; subset rotation spread .0618 degrees; design null ratio .3126 and rank ratio .000748. Its heading epoch/reference are restored to 1 / frame 31, with `translation_observed=false`.

The existing 74 normal rotation observations are preserved; three tentative recovery events and one confirmation are added. This is not a higher rotation-count claim used to disguise the gap. The last original-reference observation, reset and confirmation times are separately recorded in `v7-recovery-review.json`.

The stricter checkerboard reference review accepts ZERO reference poses in this older recording, including its initial reference. The mostly frontal target remains ambiguous or sensitive under those gates. Consequently no RMS angular accuracy or measured old-run heading drift is reported. Matching an earlier legacy board-fit number would not make it independent ground truth. The recovered orientation is model-verified software evidence, not certified physical accuracy.

## Regression and controls

All 74 tests pass. New tests cover three-frame heading confirmation, duplicate-frame rejection, blank/unrelated images, different producer sessions, stale references, planar slides, unique epoch serials and orientation-only UI behavior. The new epipolar recovery model rejects all 80 synthetic planar controls across four noise levels. In the corresponding 80 nonplanar trials it accepts 29 and rejects 51; maximum accepted angular error is .1314 degrees. This availability tradeoff and idealized projected inputs do not predict hardware accuracy.

Existing synthetic translation remains 10/10 accepted with maximum direction error 2.849 degrees and rotation error .5255 degrees. Pure-turn and continuous-turn synthetic controls remain unchanged.

The newer rotation recording retains all 97 updates without an intermediate heading reset. The newer horizontal return retains 898 map poses, and the newer stationary run still adds no pose updates. Full original-study regression checks all 14,693 raw-image hashes; the recent 2,891 frames retain their integrity evidence, totaling 17,584 unique recorded frames.

| Original recording | Frames | Normal rotation updates | Heading recoveries | Map poses | Map recoveries |
|---|---:|---:|---:|---:|---:|
| stationary | 439 | 0 | 0 | 0 | 0 |
| horizontal | 886 | 9 | 0 | 515 | 0 |
| vertical | 891 | 16 | 0 | 435 | 0 |
| rotation | 1792 | 74 | 1 | 0 | 0 |
| low-light | 1793 | 0 | 0 | 0 | 0 |
| low-texture | 1791 | 0 | 0 | 0 | 0 |
| rapid-motion | 1791 | 0 | 0 | 1315 | 0 |
| feature-loss | 1791 | 0 | 0 | 0 | 0 |
| interruption | 829 | 0 | 0 | 0 | 0 |
| repeat-path | 2690 | 0 | 0 | 2182 | 1 |

Stationary, lighting-change, low-texture, feature-loss and interruption controls remain at zero observed pose updates. Repeated-path map recovery is unchanged: one initialization, 2,182 map poses and recovery of the same map with an explicit unseen gap. This does not establish recovery from every physical occlusion, scene change or arbitrary viewpoint.

## Remaining scope

This pass handles the older recording's permanent loss of heading reference; it does not recover every rotation sample during motion blur. Relocalization requires overlapping clear views, sufficient static 3D evidence or a validated pure-rotation model, and three consistent observations within the bounded window. It can fail conservatively. It is not global place recognition, true-north heading, bundle adjustment, inertial fusion or metric position recovery.

Phase 8 remains open for eventual fresh end-to-end validation of the final software and explicitly scoped accuracy/drift claims. Saved recordings used during development are not held-out validation. No additional physical test is needed now. Camera profile/focus/calibration, Phase 9 and Pi-only migration are unchanged. The v7 live dashboard has not been opened in this offline pass.

## Artifacts and reproduction

Under `results/reports`:

- `v7-older-final.json`, `v7-recovery-review.json`: paired old recording, epochs and recovery timing.
- `v7-older-reference-reviewed.json`: reference rejection and original-epoch bookkeeping; no invented error score.
- `v7-full-study-final.json`: full paired regression with main/helper source hashes.
- `v7-newer-final.json`, `v7-horizontal-final.json`, `v7-stationary-final.json`: newer controls.
- `v7-regression-final.json`, `v7-geometry-controls.json`: projected geometry controls.
- `v7-final-source-hashes.json`: final source/test/docs and selected artifact hashes.

The normal launcher remains `./scripts/start_stream.ps1 -Dashboard`. Repeat the older replay with a new output filename:

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_cached --recording data/validation/rotation-20261029-031748 --cache results/cache/rotation-031748.npz --baseline results/backups/improvements-v6/visual_odometry.py --output results/reports/NEW-old-rotation.json
```
