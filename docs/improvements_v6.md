# Phase 8 rotation gap work — v6 image re-matching

## Result

The newer rotation recording (`rotation-20261029-043945`) now keeps one heading reference through the turn and return, with no intermediate heading reset. It has 97 accepted rotation updates versus v5's 84. There are two total segment numbers (startup and the initial rotation-only transition), rather than v5's four; both retain the original orientation reference. This is intermittent measured orientation with baseline waits, not an orientation measurement at every received frame or an interpolated trajectory.

The older rotation recording (`rotation-20261029-031748`) improves from 63 to 74 rotation updates but still has one rejected interval. It is explicitly not counted as a complete heading reconstruction. Phase 8 is therefore not declared complete.

No camera, Pi stream, API request or new physical test was used. All original images, calibration, telemetry and operator notes are preserved. The previous source is frozen in `results/backups/improvements-v5/visual_odometry.py`; the new default is `rotation-rematch-v6` through the existing dashboard launcher.

## Diagnosis

In the newer test, v5's last trusted anchor before its break was frame 542. The ordinary tracked correspondences could not pass the rotation model at the reversal; repeated attempts against that anchor accumulated 86.79 pixels of movement by frame 563 and reset the heading. Essential-matrix subset rotations also disagreed, so accepting their average would not have been justified.

A fresh match of the actual frame-542 image to frame 543, using a larger local patch and stricter image-consistency checks, passes the original rotation geometry. The accepted median reprojection residual is .2477 pixels. The tracked-point estimates and the directly verified image matches are not equivalent evidence during that difficult frame. The change repairs correspondence quality instead of extrapolating a missing angle or relaxing homography branch ambiguity.

## Implemented fallback

Only after a rotation-only reference already exists, and ordinary accumulated movement is at least four pixels, a failed regular model can trigger a direct match to its recent anchor image. The anchor must be no more than 30 producer frames old (about two seconds at the configured 15 FPS).

The fallback uses 31-by-31 pyramidal LK patches, four pyramid levels, bidirectional matching, forward/backward error below .5 pixels and patch error below five. It also rejects out-of-image results. At least 60 matches and 70% of source points must survive those stricter image checks.

The cleaned pairs then pass exactly the existing rotation model: at least 90% homography support, broad image coverage, median bearing reprojection residual at most .4 pixels, at least 90% of residuals below one pixel, angular bounds, homography rotation-branch separation at most .3 degrees and turn greater than twice that ambiguity. Translation remains unknown. This is not a new relaxed geometric acceptance path.

Three updates in the newer recording use this fallback: frames 423, 534 and 543. They retain about 97.2%, 98.6% and 95.0% of source points, with median forward/backward errors .0049, .0049 and .0289 pixels. Accepted rotation-fit residuals are .1028, .1499 and .2477 pixels. The rest of its 97 updates use the regular path. The strict rematches take roughly 6–8 ms in the offline estimator on this laptop; live camera/network/display performance was not remeasured.

Anchor images are refreshed with their corresponding feature anchors. Session/gap handling and all existing map-loss/recovery semantics are preserved. CSV schemas add `rotation_method`, `rotation_retrack_ratio` and `rotation_retrack_fb_px` in every state. Local diagnostics count image-confirmed rematches rather than suggesting that missing motion was predicted.

## Heading comparison

The checkerboard is usable for 77 sampled reference poses in the newer recording. The v6 retained-heading trace differs by .1672 degrees RMS and .4784 degrees maximum from the shared-camera/calibration board reference. Final difference is .1759 degrees. The estimated endpoint turn magnitude is 2.1824 degrees versus the reference's 2.0969 degrees; neither is forced to zero or used to override the operator's approximate original-direction confirmation.

Long stationary holds dominate the 77 samples. Only FIVE usable reference samples fall within the first-to-last accepted-rotation update window (21.640–40.640 s); their RMS difference is .3361 degrees. The pattern leaves the image during much of the main turn, so that portion has no board score. This is not independent angular accuracy, a per-frame confidence interval, or proof of zero heading drift. Reference ambiguity/sensitivity checks remain active. The new reference review refuses to compare global heading after an unknown heading-epoch reset.

## Older unresolved interval

In the older run, trusted frame 1285 still cannot be carried through to the frame-1307 reset. The first later valid rotation is frame 1309 in a new local heading epoch. Direct matches with 15-, 21-, 31- and 41-pixel patches at sampled frames in the interval produced zero validated candidates under the same strict image/rotation checks. The bounded recent-anchor age is not the cause: the reset occurs only 22 producer frames after the trusted anchor.

The current observations/models do not justify bridging that interval. This is not proof that every possible multi-view or motion model would fail. More sophisticated model work or eventual additional validation may help, but a convenient homography branch or an essential matrix whose rotation subsets disagree is not accepted merely to remove the visible gap. An experimental two-plane disambiguation probe also failed its support/distinctness checks; it was not installed in the production estimator.

## Regression

All 70 automated tests pass. New image-domain tests recover a known camera turn despite deliberately corrupted point tracks and reject pure planar image slides, blank images and stale anchors. Existing 70 planar-slide controls, map replenishment, recovery confirmation, schema and gap-safe path tests continue to pass.

Known synthetic translation remains 10/10 accepted, maximum direction error 2.849 degrees and rotation error .5255 degrees. Twenty known pure-turn pairs remain accepted, and the idealized continuous turn/return retains its heading without a reset. These are synthetic controls, not hardware accuracy validation.

The complete original ten-case study (14,693 raw frames) was hash-verified and replayed against v5 with identical LK inputs and per-frame OpenCV seeds. The recent stationary/horizontal/rotation recordings preserve integrity evidence for another 2,891 frames, totaling 17,584 unique recorded frames.

| Original recording | Frames | v5 rotation updates | v6 rotation updates | v6 mapped poses | v6 old-map recoveries |
|---|---:|---:|---:|---:|---:|
| stationary | 439 | 0 | 0 | 0 | 0 |
| horizontal | 886 | 9 | 9 | 515 | 0 |
| vertical | 891 | 6 | 16 | 435 | 0 |
| rotation | 1792 | 63 | 74 | 0 | 0 |
| low-light | 1793 | 0 | 0 | 0 | 0 |
| low-texture | 1791 | 0 | 0 | 0 | 0 |
| rapid-motion | 1791 | 0 | 0 | 1315 | 0 |
| feature-loss | 1791 | 0 | 0 | 0 | 0 |
| interruption | 829 | 0 | 0 | 0 | 0 |
| repeat-path | 2690 | 0 | 0 | 2182 | 1 |

Stationary, lighting-change, low-texture, feature-loss and interruption negatives remain at zero observed pose updates. The newer horizontal return retains one initialization and 898 consecutive map poses. Repeated-path map recovery remains unchanged: one initialization, 2,182 map poses, one recovery of the original map and an explicit unseen gap. The older vertical case has more accepted orientation updates, but its frontal reference is still unsuitable for an independent accuracy claim.

## Remaining scope

The newer test's heading break is fixed on replay; the older difficult interval remains unknown. The implementation has not been tested live in this pass, and these same recordings informed development, so they are not held-out validation. Phase 8 remains open pending remaining reliability work and eventual fresh end-to-end validation of the final software. No new physical test is needed now. No Phase 9 or Pi-only migration has begun. Calibration/focus/profile remain unchanged.

## Artifacts

- `v6-rotation-verified.json`: paired newer rotation trace.
- `v6-heading-reference-verified.json`: validity-gated heading reference, with the motion-window limitation.
- `v6-older-rotation-candidate.json`, `v6-older-gap-review.json`: unresolved older case and diagnostics.
- `v6-horizontal-verified.json`, `v6-stationary-verified.json`: preserved newer controls.
- `v6-full-study-verified.json`: paired full original study and estimator hashes.
- `v6-regression-verified.json`: synthetic controls.
- `v6-final-source-hashes.json`: final source/tests/docs and selected report hashes.

Reports live under `results/reports`. All outputs refuse overwrite. Reproduce the newer comparison with an unused destination:

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_cached --recording data/validation/rotation-20261029-043945 --cache results/cache/rotation-043945.npz --baseline results/backups/improvements-v5/visual_odometry.py --output results/reports/NEW-rotation.json
```
