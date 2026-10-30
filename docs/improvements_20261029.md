# Post-validation improvements — 29 October 2026

This is a conservative first improvement pass, using the existing Phase 8 recordings. No new camera movement, cloud request, camera configuration change, or calibration replacement was required. Phase 9 and standalone Pi migration have not started.

## Changes

The two-view estimator now checks its signed translation against three disjoint, interleaved subsets of the retained correspondences. Each subset needs at least 30 points and a recovered pose supported by at least 20 points and 60% of that subset. A direction more than 15 degrees from the full-fit direction rejects the displacement as `unstable_direction`. Insufficient subset evidence also rejects the displacement. These are engineering gates, not confidence intervals or an accuracy guarantee. Correspondences share the same scene and can share systematic errors.

The new CSV fields identify the estimator as `two-view-subset-check-v2` and expose `direction_spread_deg`. A zero spread on an early rejection means the check did not complete, not perfect agreement. CSV columns stay identical across accepted, waiting, and reset states.

The dashboard retains the last 20 nonempty disconnected path segments in gray. All segment origins overlap; gray segments are historical local sketches, not a reconstructed global path. The current segment remains green. No line joins separate segments. The feature counters now distinguish retained tracks, attempted tracks, new seeds, and total active points.

## Verification and limits

The repeatable offline replay verifies every JPEG against its recorded SHA-256, reuses recorded producer sessions/frame numbers/timestamps, and runs LK plus the updated estimator. OpenCV is seeded by frame index. Archived counts came from the original live run, so randomized solver differences can contribute to differences; this is not a strictly identical random-state A/B experiment. Offline timing excludes live network transport and display and does not establish new live FPS.

These same recordings informed development, so they are regression evidence rather than held-out accuracy validation. Existing raw frames, original reports, and the frozen Phase 8 summary are preserved.

Synthetic correspondence trials accept 9/10 known-motion cases (previously 10/10), with maximum accepted rotation error 1.3625 degrees and direction error 13.3446 degrees. The new gate deliberately trades availability for caution; the maximum accepted error has not improved. Stationary, pure rotation, planar translation, and 80%-outlier negative controls still reject translation. The rendered LK sequence retains four accepted poses.

Continuous position, metric scale, global loop closure, independent drift, and reliable rotation-only heading remain unresolved. The checkerboard reference still has planar-pose instability and shared-calibration bias. Rejecting a doubtful pose avoids inventing a unit displacement but does not recover the missing trajectory.

Artifacts: `results/reports/improvements-20261029-replay.json` and `results/reports/improvements-20261029-synthetic.json`.

Run the dashboard as usual with `./scripts/start_stream.ps1 -Dashboard`. No physical retest is required to use these changes. A later accuracy claim will require an improved pose/reference method and fresh controlled measurements.


For another offline replay, choose a new destination (existing reports are never overwritten):

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_improvements --output results/reports/NEW-replay.json
```

The full 56-test suite passes. The dashboard state transition is covered by an automated path-break regression; its revised layout has not been visually checked in a new live camera session.

## Recorded-data replay results

| Recording | Frames verified | Original accepted poses | Updated accepted poses |
|---|---:|---:|---:|
| stationary | 439 | 0 | 0 |
| horizontal | 886 | 1 | 1 |
| vertical | 891 | 2 | 0 |
| rotation | 1792 | 1 | 0 |
| low-light | 1793 | 0 | 0 |
| low-texture | 1791 | 0 | 0 |
| rapid-motion | 1791 | 1 | 1 |
| feature-loss | 1791 | 0 | 0 |
| interruption | 829 | 0 | 0 |
| repeat-path | 2690 | 9 | 4 |

All 14693 frames passed their recorded hash checks. The updated estimator rejects both vertical candidates and the rotation recording’s translation candidate; repeat-path accepted poses fall from nine to four. Horizontal and rapid-motion each retain one accepted pose. This is more conservative output, not evidence of improved metric accuracy or recovered continuity.

Mean geometry time, including frames waiting for baseline: stationary 0.000 ms, horizontal 0.017 ms, vertical 0.049 ms, rotation 0.022 ms, low-light 0.000 ms, low-texture 0.000 ms, rapid-motion 0.007 ms, feature-loss 0.000 ms, interruption 0.000 ms, repeat-path 0.062 ms. These offline values are not live end-to-end latency.
