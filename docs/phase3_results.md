# Phase 3 measured results — 2026-10-28

Status: COMPLETE. Phase 4 has not started. Pyramidal Lucas–Kanade tracking,
quality checks, motion vectors, feature renewal, and interruption resets were
implemented and exercised on synthetic data and the real Pi camera feed.

## Configuration and method

Pi 5 / IMX708: 640 x 480, target 15 FPS, JPEG quality 80, existing SSH/MJPEG
transport. Windows: Python 3.12.14, OpenCV 4.12.0 (wheel 4.12.0.88),
NumPy 2.2.6, Pillow 13.0.0, one OpenCV CPU worker thread. No new Pi package.
Configuration: 300-point budget, Shi-Tomasi 0.01 quality and 10-pixel spacing,
21 x 21 LK window, pyramid levels 0–3, 30 iterations, epsilon 0.01, minimum
eigenvalue 0.0001, forward/backward patch-error limit 25, consistency limit
1 pixel, maximum pair displacement 80 pixels. Full settings are in every report
and `configs/tracking.json`. Tracking is a separate mode from detector comparison.

## Primary live viewer run

Requested 65 seconds; received 965 frames over 64.250 seconds between
first/last JPEG receipt, completed 2026-10-28T23:45:02.128675+00:00. The indoor scene
contained a moving foreground hand/person as well as walls and blinds. It was
not a controlled camera-motion or stationary-scene experiment. The native viewer
was visually inspected with active vectors, endpoints, point counts, and quality
status. Arrows were explicitly displayed at 3x actual image displacement.

| Measurement | Observed result |
| --- | ---: |
| Receive FPS | 15.004 |
| Received frames | 965 |
| Producer sequence gaps / connection errors | 0 / 0 |
| Display queue skips | 4 |
| Attempted / accepted correspondences | 231,641 / 228,054 |
| Weighted consistency-acceptance rate | 98.451% |
| Mean accepted tracks per received frame, including initial zero | 236.33 |
| Mean active point count | 240.27 |
| Initial seed / later top-up features | 300 / 3502 |
| Later top-up events | 34 |
| Mean flow magnitude (pixels per observed pair) | 1.561 |
| LK and filtering mean / p95 (ms) | 7.206 / 9.799 |
| Tracker total, excluding drawing, mean / p95 (ms) | 8.737 / 11.965 |
| Decode + tracker + drawing/telemetry mean / p95 (ms) | 14.795 / 19.649 |
| Mean accepted forward–backward residual (mean of frame means, px) | 0.02652 |

Status frames: {'initializing': 1, 'tracking': 956, 'degraded': 8}. Reset reasons: {'startup': 1}.
Disjoint rejections: forward 890, backward 275,
consistency 2413, excessive displacement 9;
no tracking exceptions were recorded. Rejection totals equal attempted minus
accepted correspondences. Display queue skips are distinct from received gaps.
Summary replacement totals include initial seeding; the table separates it using
per-frame CSV. Average flow magnitude and residual are frame averages, while
acceptance rate uses correspondence-weighted totals.

The acceptance percentage is a configured consistency metric, **not ground-truth
accuracy**. Repeated textures, moving objects, and consistent incorrect matches
can survive these checks. No real-world correspondence labels, camera pose,
distance, scale, velocity, or navigation accuracy were measured.

## Known synthetic image motion

One real received image was transformed into eight 20-frame sequences with
simulated 15-FPS capture timestamps. These are image-plane transformations,
not physical camera translations or rotations. Each sequence uses a fresh tracker.
No warmup frames were discarded. Endpoint errors below use accepted adjacent-frame
correspondences only; rejected features are reflected in the acceptance rate.
The seven predefined checks passed; the rapid-motion trial is exploratory.

| Synthetic case | Accepted / attempted | Acceptance | Median / p95 endpoint error (px) | Mean flow magnitude (px/pair) |
| --- | ---: | ---: | ---: | ---: |
| Identical stationary image | 5700 / 5700 | 100.00% | 0.00000 / 0.00000 | 0.000 |
| Horizontal +2 px/frame | 5256 / 5297 | 99.23% | 0.00115 / 0.00348 | 2.003 |
| Vertical +2 px/frame | 5353 / 5382 | 99.46% | 0.00120 / 0.00327 | 2.001 |
| In-plane 0.4 deg/frame | 5340 / 5365 | 99.53% | 0.02860 / 0.06784 | 1.515 |
| Exploratory +15 px/frame | 4242 / 4560 | 93.03% | 0.00186 / 0.00378 | 14.999 |
| 75% image occluded, then restored | 3844 / 4185 | 91.85% | N/A | 0.000 |
| Uniform image, then restored | 3900 / 4200 | 92.86% | N/A | 0.000 |
| Ten frame IDs skipped | 5400 / 5400 | 100.00% | N/A | 0.000 |

Identical frames produced zero flow. Horizontal/vertical translation produced
near-uniform 2-pixel displacements in the requested directions; synthetic rotation
produced a spatially varying field. RMS spread around the mean vector was
0.035 px for horizontal translation,
0.015 px for vertical translation, and
1.431 px for in-plane rotation. This illustrates
controlled image patterns; it does not classify general 3D camera motion.
Integer-shift, brightness-preserving synthetic inputs are easier than real
blurred/low-light motion, so their very small errors are not field accuracy claims.

Complete texture loss gave zero accepted tracks on its first blank frame.
When texture returned, 300 new points were seeded without fabricating vectors;
the next frame verified 300 tracks. Recovery therefore took one subsequent
observed frame in this synthetic case. Partial occlusion triggered quality-based
reinitialization/replacement and resumed tracking after restoration. A timestamp
gap reseeded without extrapolating motion across missing frames. Overall survival
ratios in these sequences exclude frames with no points to attempt; the loss
and reset events are not hidden by those percentages.

An additional seeded 320 x 240 random-texture translation diagnostic accepted
125/300 (41.67%), with retained median endpoint error
0.000301 px. Its below-threshold survival triggered a quality reset.
Large backward-pass rejections on that finite small texture illustrate the
sensitivity to image size, pyramid scale, and patch content. The initial unit
test assumption of >80% survival was replaced with an accepted-correspondence
error/accounting check after this diagnosis; the production gates were not relaxed.
This diagnostic is retained alongside the successful real-image transform trials.

## Replacement, interruption, and launcher checks

The replacement unit test occluded a small image region, retained surviving IDs,
added new unique IDs without resetting the survivors, respected the feature cap,
and checked that replacement points remained outside retained-point mask regions.
The deliberate backward-match inconsistency test rejected the altered returns;
an injected LK exception produced an explicit error and fresh seeds. These are
synthetic software tests, not physical fault measurements.

The real transport recovery test held its owned SSH forward down for 3.031 seconds.
The maximum receive gap was 4.234 seconds; the receiver established
2 connections and logged 2 expected connection errors, with
62 missing producer frame IDs. The tracker recorded one `frame_gap` reset,
seeded the returning image, and resumed valid pairs on subsequent frames. No
motion was reported over the outage. This tests a restored forward, not Wi-Fi
failure, camera failure, or automatic restart of a dead SSH process.

A final 12-second launcher smoke test (`viewer-20261028-184813.json`) received
170 frames at 15.042 FPS, with zero received gaps or connection errors.
Its status log included 1 quality-triggered reset and
7 later non-reset top-ups, and no LK exceptions. The camera
stopped cleanly when the timed viewer closed. This also exercised the final
error-bucket and initial-seed/top-up summary bookkeeping.

Windows: all 22 unit tests pass. Pi: eight setup/transport regressions pass;
14 optional laptop vision tests explicitly skip because Pi OpenCV is absent.
The Pi capture software and OS camera dependencies were not changed.

## Evidence and limitations

- `results/reports/phase3-live-viewer.json` and `.csv`: primary 65-second live viewer run.
- `results/reports/phase3-synthetic-final.json` and `.csv`: controlled motion/loss tests.
- `results/reports/phase3-recovery.json`, `.csv`, `.log`: real interruption/reset evidence.
- `results/reports/phase3-noise-diagnostic.json`: challenging small random-texture case.
- `results/reports/viewer-20261028-184813.json` and corresponding CSV: final launcher smoke test.
- `results/reports/windows-phase3-packages.txt`: environment snapshot.
- `results/plots/phase3-synthetic-final/`: motion, loss, and recovery overlays.
- `data/recordings/phase3-source.jpg`: local real-image source for synthetic tests.

Source SHA-256: `5a832800b2adb2dda9c7d69b8eb77801b5fcb7715c7fbbe2920e89ac9eddd491`.
Full telemetry and images remain local and ignored by Git. This measured summary
and [operating/mathematical guide](optical_flow.md) are committed. An earlier
headless trial (`phase3-live-headless.json`) logged nine refusals because the
server/forward had not yet started, then received 614 frames at 15.020 FPS over
40.813 seconds. It is startup/retry evidence, not the clean primary trial.
A short synthetic benchmark overlapped the beginning of the primary viewer test;
background CPU workload was not otherwise controlled. A low-jitter long-duration
guarantee, physical motion ground truth, robustness across lighting, and pose/scale
accuracy remain untested. No calibration or Phase 4 implementation was added.

Code, tests, documentation, debugging, and command execution were AI-assisted by
Codex. The live vector viewer and saved synthetic overlay were visually inspected.
Independent human review remains outstanding.
