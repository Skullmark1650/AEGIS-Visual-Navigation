# Phase 5 visual odometry results

Tested 2026-10-28 on the Windows laptop and IMX708 Raspberry Pi camera. The basic Phase 5 prototype is implemented and tested. Phase 6 has not started. Live pose accuracy, continuous trajectory accuracy, and deployment readiness are not established.

## Delivered behavior

The live pipeline combines existing forward/backward LK tracking with calibrated normalized point coordinates, persistent-ID anchor correspondences, robust essential-matrix estimation, cheirality-based relative pose recovery, rejection statuses, pose accumulation, and a live X/Z direction sketch. The reviewed Phase 4 calibration is required. Every received frame is checked for matching camera/focus/crop profile and resolution before odometry.

The sketch explicitly uses unit translation steps. Each step has independently unknown scale; it is not measured physical displacement or a globally scale-consistent trajectory. Failed motion estimates break the trajectory into separately initialized segments. Full relative rotations, translation directions, accumulated orientations, centers, segment numbers, support, parallax, and runtime are recorded in CSV; JSON contains summary statistics. See visual_odometry.md for conventions and thresholds.

## Final live measurement

Source: `results/reports/viewer-20261028-225332.json` and matching CSV, final 30-second launcher run using manual lens position 2.0, 640 x 480 at nominal 15 FPS, OpenCV 4.12.0. The display was inspected during the preceding odometry run; the final version uses the same display with stricter geometry gates.

| Measurement | Result |
|---|---:|
| Processed frames | 440 |
| First-to-last receive span | 29.203 s |
| Receive FPS | 15.0327 |
| Connection errors | 0 |
| Producer sequence gaps | 0 |
| Display queue skips | 8 |
| Complete processing mean | 18.970 ms |
| Complete processing p95 | 28.239 ms |
| Complete processing maximum | 56.946 ms |
| Geometry-estimation mean across all frames | 0.612 ms |
| CSV records verified | 440 |

Complete processing includes JPEG decode, LK, geometry, overlays, and telemetry, excluding Tk display scanout. Geometry timing excludes waiting frames' anchor bookkeeping and is zero on those frames; it is not the cost of an attempted essential-matrix solve. Display skips mean the GUI used its latest-frame queue; they are not producer frame loss.

| Odometry status | Frames |
|---|---:|
| Waiting for baseline | 368 |
| Accepted pose | 8 |
| Planar or rotation ambiguity | 25 |
| Insufficient pose support | 12 |
| Low parallax | 15 |
| Tracking quality reset | 11 |
| Startup reset | 1 |

The user was asked to translate the camera slowly sideways through a stationary scene. Live views included a predominantly planar brick wall. The motion was not instrumented or recorded against an external reference; accepted poses are algorithm outputs, not verified real-world correct poses. Low-motion periods did not add unit steps. No live translation distance, velocity, angular error, drift rate, ATE, or RPE is claimed.

## Synthetic ground-truth tests

Final reproducible artifact: `results/reports/phase5-baseline20-validation.json`. These tests project known synthetic 3D structure through the measured calibration; they are distinct from live measurements.

Ten nonplanar correspondence trials used 0.15-pixel Gaussian noise per coordinate and 15% random mismatches. All ten were accepted. Relative rotation error averaged 0.5276 degrees, maximum 1.3625 degrees. Signed translation-direction error averaged 3.8592 degrees, maximum 13.3446 degrees. Translation direction is compared directly with the known anchor-to-current translation vector, without sign flipping to conceal inversions.

The 36-frame rendered nonplanar sequence exercises actual Shi-Tomasi detection, LK, persistent IDs, anchor selection, calibrated geometry, and pose accumulation. Status counts were 25 baseline waits, five accepted estimates, three low-parallax rejections, two pose-support rejections, and one startup reset. On its five accepted estimates, rotation error averaged 0.3256 degrees (maximum 0.5838); translation-direction error averaged 2.1529 degrees (maximum 4.5744). Rejected frames are reported rather than excluded from the acceptance count. The patches are integer-rendered, synthetic textures with simplified appearance, not photorealistic camera images.

Negative controls produced these expected rejections:

| Synthetic condition | Result |
|---|---|
| Stationary camera | Low motion |
| Pure rotation | Planar or rotation ambiguity |
| Planar scene | Planar or rotation ambiguity |
| 80% mismatches | Insufficient pose support |
| Frame gap | Explicit new segment and zeroed center |

The earlier 8-pixel baseline allowed an incorrect rendered translation direction approaching a sign reversal. Final baseline 20 pixels and minimum parallax .75 degrees removed that failure in this sequence, with reduced acceptance. This is a diagnostic-driven gate change, not evidence that all direction flips are impossible.

All **36 automated tests passed** after final changes. New tests cover inverse pose composition, known synthetic motion with mismatches, degeneracy rejection, profile/review gates, invalid points, reset behavior, full rendered tracking, baseline waiting, and stable CSV columns across accepted and rejected states. An early live export exposed variable CSV fields when accepted poses first appeared; the schema was corrected, regression-tested, and the final 440-row export succeeded.

## Reproduction and artifacts

```powershell
./scripts/start_stream.ps1 -DurationSeconds 30 -OdometryCalibration results/calibration/phase4-reviewed-camera.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m laptop.verify_odometry --calibration results/calibration/phase4-reviewed-camera.json --output results/reports/new-phase5-validation.json
```

Use a fresh verification output name. The launcher generates timestamped transport/odometry JSON and CSV files. Calibration, captures, generated reports, and source hashes remain local under ignored data/results directories. Code and this measured summary are repository files.

## Limitations and next boundary

The implementation is basic two-view monocular odometry. It does not estimate consistent relative translation magnitude, maintain a landmark map, optimize multiple views, correct drift, recognize loop closures, or fuse another sensor. Consecutive normalized directions can distort a plotted path even under one arbitrary global scale. Segments reset on failure and must not be interpreted as a continuous position history. Conservative homography rejection can discard useful scenes; moving objects, rolling shutter, inaccurate calibration, blur, and repeated textures can still cause wrong estimates.

Pure rotation is rejected rather than solved by a dedicated rotation-only method. The physical calibration target's measured square size does not provide scale for arbitrary scenes. Real-world accuracy needs a separate controlled sequence with measured motion or reference poses; ATE/RPE would additionally require a defined alignment and justified scale model. The current sketch cannot support a valid metric trajectory-error claim.

Phase 5 implementation, synthetic validation, live runtime testing, and documentation are delivered. Further real-motion validation remains necessary before describing this as reliable navigation. No Phase 6 dashboard or autonomous control was added.
