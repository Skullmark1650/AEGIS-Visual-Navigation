# Controlled engineering validation

Phase 8 is in progress. Keep the measured 20 mm checkerboard fixed, planar, upright, and fully visible about 30–36 inches ahead of the camera. Include other stationary textured objects at different depths. Keep the calibrated focus, resolution, and crop unchanged. Mark camera positions A and B, 50 mm apart horizontally, using a ruler/tape. Camera rotations are relative to its initial pointing direction; ruler translation alone does not establish orientation ground truth.

## Run and replay

```powershell
./scripts/start_validation.ps1 -Experiment stationary -DurationSeconds 30
```

The launcher records original received JPEGs and hashes under a unique data/validation directory, saves per-frame transport/tracking/pose telemetry, then runs offline board-reference analysis. This adds disk/hash overhead to receiver timings. No AI request or image upload occurs. Different producer sessions appear in JPEG filenames. Existing recording directories and validation outputs are never overwritten.

Offline replay:

```powershell
.\.venv\Scripts\python.exe -m laptop.validation --recording data/validation/YOUR_RUN --output results/reports/YOUR_NEW_RESULT.json
```

Keep one producer session per run. The experiment manifest identifies the calibration and report files. Every raw frame hash and frame profile is checked. Reference estimation samples every 15 frames by default and additionally evaluates every accepted VO estimate and its recorded anchor. Pose comparison uses the exact anchor rather than incorrectly comparing adjacent frames to an anchored estimate.

## Physical protocol: guide one case at a time

1. Stationary: camera resting at A, untouched for 30 seconds; record any accidental movement.
2. Horizontal: hold A, slide camera slowly to B (50 mm right) without turning it, hold B, return to A, hold. Confirm actual ruler distances after the run.
3. Vertical: camera rises a measured 50 mm without turning, holds, then returns to its measured starting height. Arrange support before beginning.
4. Rotation: rotate about a marked pivot to a measured 10-degree heading and back, using an angle reference. Without a protractor/reference, label the angle operator-estimated. Pure rotation may be correctly rejected by this prototype.
5. Low light: camera stays fixed; reduce room lighting, hold, restore it. Record conditions; no calibrated lux measurement is implied.
6. Low texture: camera stays fixed; put a plain surface in view, hold, restore the original scene. This is a deliberately changed scene, not known camera motion.
7. Rapid camera motion: a brief faster movement and stop, followed by a stationary recovery period. No velocity accuracy without timed motion ground truth.
8. Temporary feature loss: with the camera fixed, block its view briefly without touching the lens, then uncover and hold still. Mark cover/uncover times for event-based recovery measurement.
9. Network/capture interruption: fixed camera; deliberately pause/resume the owned stream, record exact event times, verify stale warnings, reconnect and pose reset. A server pause is a capture/application interruption, not measured network packet loss.
10. Repeated path: three slow measured A-to-B-to-A cycles with endpoint holds; record each cycle. Assess output continuity and direction consistency. Do not interpret reset centers as zero drift.

Each recording needs operator notes: actual distances/angles and their measurement method, event times, fixed target confirmation, scene changes, and deviations. Planned motion is not evidence that the camera followed it. Stop between cases so conditions and frame ranges are unambiguous.

## Accuracy, drift, and recovery definitions

Board solvePnP uses the measured 20 mm squares and reviewed camera calibration. It is a correlated, image-derived reference, not independent tracking ground truth. Its own reprojection residual must be at most 1.5 pixels; missing/rejected targets produce no reference. Upright corner ordering is canonicalized; large in-plane board rotations and pose ambiguity remain limitations.

For accepted VO estimates with detectable anchor/current references, report angular rotation difference and signed translation-direction error. Direction is evaluated only when board-reference baseline is at least 10 mm to avoid unstable near-zero denominators. Reference endpoint displacement and orientation change are not VO metric accuracy. Reference spread during stationary capture helps characterize measurement noise, not an independent camera-motion truth.

Metric VO drift, scale error, ATE and RPE remain unavailable for the current independently normalized translation steps and reset segments. Document this limitation rather than invent a global metric trajectory or treat resets as successful loop closure. A known ruler displacement does not make each arbitrary VO step metric.

Tracking recovery requires at least 30 retained point matches on a non-reset frame; newly seeded points alone do not qualify. The analyzer reports delay from each reset to retained-track recovery and the next accepted pose separately. Missing recovery is null/censored, not zero. Delays from the physical uncover/resume event additionally require an event timestamp. A later accepted pose may be in a new segment and is not continuous navigation recovery.

Processing/receive FPS and receipt gaps come from timestamps. Capture-to-receipt delay includes clock uncertainty and excludes display scanout, so true end-to-end latency is not established. Laptop-process CPU is expressed as percent of one logical core (can exceed 100%); memory is working set/lifetime peak. Pi CPU/memory and endurance memory growth are not measured by this harness.
