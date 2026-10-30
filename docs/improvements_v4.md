# Phase 8 software improvements — local-map v4

## Result

The saved horizontal return is now tracked. After one supported initial step, the estimator fits 898 successive poses against a temporary 3D map, continuing through the outbound stop and return without a reset. The previous version accepted one isolated step and never estimated the return. Turn tracking improves from two to 21 rotation-only updates in the recent recording, but still has eight separate orientation/position segments; complete turn/return continuity is not demonstrated.

This was an offline session. No camera/server was started, no API request was made, and no new physical test was required. All original JPEGs, telemetry, operator confirmations and reports are preserved. The new default is `local-map-v4`; the previous source is saved under `results/backups/improvements-v3/visual_odometry.py`.

## Diagnosis and changes

The horizontal return reached only 19.554 pixels of median anchor displacement; v3 required 20 before trying geometry. Lowering that prerequisite to 12 alone did not recover the return: repeated weak pairs also consumed the retry allowance and two-view depth/direction remained poorly conditioned. The final system waits for at least one pixel of new image movement between retries and allows sixteen deferred attempts; a seventeenth failure or insufficient retained matches breaks the segment. Stationary waiting does not consume the allowance.

Essential estimation now refits all RANSAC inliers with normalized eight-point geometry, enforces the essential singular-value constraint and checks Sampson support. The RANSAC/Sampson threshold is .5 pixels, stricter than the previous one pixel. At least 90% of initial support must survive the refit, otherwise it falls back to the RANSAC solution. Parallax, support and subset direction-agreement requirements remain in force.

A well-supported movement can initialize a small nonplanar 3D map, using triangulated retained feature IDs. It needs at least 50 landmarks with positive depth, reprojection/parallax checks and 3D conditioning. The map starts its own local origin and scale rather than mixing older independent unit steps into a supposedly consistent trajectory. PnP plus LM refinement then estimates absolute pose in those local units. It requires at least 40 inliers, 70% support, at least 10% image coverage, median reprojection residual no more than .5 pixels, positive depth and bounded per-frame movement/rotation.

Mapped poses use `map_tracking`; they are pose observations, not independent unit movement events. Landmarks are not replenished yet. Too few mapped IDs, a failed map pose, a tracking reset or a stream gap breaks continuity; no global relocalization or invented bridge is added. The dashboard, CSV, JSON summary, validation and local diagnostics distinguish local-map scale from independent unit-step fallback.

Rotation-compatible homography shape tolerance increases from .0025 to .005 normalized singular spread, retaining the .4-pixel median bearing-fit residual, 90% support, coverage and angular gates. Forty automated planar-slide controls remain rejected as rotation. Rotation-compatible motion still cannot prove zero translation in every distant or planar scene.

## Recent recordings: paired v3/v4 replay

All 2,891 recent raw frames were hash-verified while building the LK caches; checksummed cache metadata includes the recording CSV, LK source and configuration. Each estimator receives identical retained points and per-frame random seed. Cache files are decoded once into memory per replay; they do not alter the source recordings.

- Stationary: 214 frames, zero pose updates in either version.
- Horizontal: 1,336 frames. V3: one step. V4: one initialization plus 898 map poses in one local map, no map loss. The map contains 271 landmarks; maximum map-fit median reprojection residual .310 pixels. The final position is near the start but is not forced to zero.
- Rotation: 1,341 frames. V3: two rotation-only updates. V4: 21 updates, no accepted translation or map initialization. Remaining rejected intervals still divide the pose into eight segments. Their rotations cannot be summed into a certified full turn or heading closure.

The horizontal map is compared against 61 usable tilted-board samples after ONE scale alignment to the initial accepted baseline: 29.719 mm per local unit. Subsequent samples have 1.164 mm RMS / 2.281 mm maximum center difference. Final center difference is .720 mm and orientation difference .0958 degrees. The map endpoint is approximately [8.664, -.270, .108] mm under that reference-derived scale, versus reference [8.063, -.627, -.063] mm. These are shared-camera/shared-calibration comparisons with assumed board geometry and a reference-fitted scale, not independent millimeter VO accuracy or a deployed metric-distance capability. Reference perturbation sensitivity was already around 2.3 mm in this recording. The initial alignment sample is included in the 61 comparisons.

This does not claim a zero-drift return: the physical return was operator-confirmed, the reference endpoint was about 8.1 mm from its start, and the map retains that nonzero residual. No loop-closure optimization is present.

## Frozen ten-condition regression

All 14,693 original-study raw frames passed their recorded hashes again. No new pose updates appear in stationary, low-light, low-texture, full feature-loss or network-interruption recordings. Moving recordings can now contain mapped poses; an accepted initialization and a map observation must not be interpreted as equivalent unit steps.

| Recording | Frames | Initial/fallback steps | Map poses | Rotation-only | Map losses |
|---|---:|---:|---:|---:|---:|
| stationary | 439 | 0 | 0 | 0 | 0 |
| horizontal | 886 | 1 | 515 | 3 | 0 |
| vertical | 891 | 1 | 19 | 1 | 1 |
| rotation | 1792 | 0 | 0 | 10 | 0 |
| low-light | 1793 | 0 | 0 | 0 | 0 |
| low-texture | 1791 | 0 | 0 | 0 | 0 |
| rapid-motion | 1791 | 1 | 1315 | 0 | 0 |
| feature-loss | 1791 | 0 | 0 | 0 | 0 |
| interruption | 829 | 0 | 0 | 0 | 0 |
| repeat-path | 2690 | 2 | 2146 | 0 | 1 |

The repeated-path case follows 2,146 map poses but loses one map; the vertical case follows 19 map poses before loss. Global continuity across those losses is unavailable. The old frontal-board reference remains unsuitable for independent accuracy scoring. All 17,584 recorded frames across original and recent tests have integrity-check evidence; these are development/regression data, not a held-out validation set.

## Automated and synthetic checks

All 64 tests pass, including return-to-origin PnP with injected image outliers, map loss/gap behavior, stable telemetry schema, same-anchor retry semantics, path/scale labels and 40 planar-slide rotation controls. The deliberately uncertain-direction fixture now uses a short noisy baseline: the old longer-baseline fixture becomes stable after all-inlier refinement and should not be required to fail.

Known nonplanar translation projections accept 10/10 trials, with maximum accepted direction error 2.849 degrees and rotation error .5255 degrees (v3: 9/10, 13.345 and 1.362 degrees). All 20 pure-turn projections accept orientation only, maximum angular error .00731 degrees. Stationary, planar translation and 80%-outlier negative controls still reject translation. Synthetic results do not establish real-camera accuracy. Rendered tests exercise the initial tracking/map pipeline; the separate known-3D return test checks mapped position and scale consistency.

## Remaining work before closing Phase 8

The missed horizontal return is resolved in this recording. Remaining priorities are incomplete rotation continuity, retaining/extending a map as feature IDs age, and explicitly scoped recovery after map loss. The system still lacks global relocalization, loop closure, bundle adjustment, sensor fusion and independent metric scale. A later fresh validation of the final software will be needed before claiming Phase 8 tracking reliability; no further physical test is needed for the current offline work. Phase 9 and Pi-only migration have not started.

The live dashboard has not been opened with v4 during this pass. Its state/label logic is covered by tests, but camera/network/display performance was not remeasured. Existing stream/calibration profile and focus settings are unchanged.

## Saved artifacts and resume

- `results/reports/v4-horizontal-final.json`, `v4-horizontal-map-reference.json`: exact paired replay and local map/reference trace.
- `results/reports/v4-rotation-final.json`, `v4-stationary-final.json`: paired recent tests.
- `results/reports/v4-full-study-replay.json`: paired ten-case regression and source hashes.
- `results/reports/v4-regression-final.json`: synthetic controls.
- `results/reports/v4-final-source-hashes.json`: final implementation/test/report snapshot.
- `results/cache/*.npz` and matching JSON: integrity-checked LK replay caches. Experimental candidate reports are preserved separately.

Start the dashboard as usual: `./scripts/start_stream.ps1 -Dashboard`. For another cached replay choose an unused report path:

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_cached --recording data/validation/horizontal-20261029-043504 --cache results/cache/horizontal-043504.npz --baseline results/backups/improvements-v3/visual_odometry.py --output results/reports/NEW-replay.json
```
