# Phase 2 measured results — 2026-10-28

Status: COMPLETE. Phase 3 has not started. Both live overlays were inspected in
a native Windows window; a separate timed viewer run, paired headless run,
controlled saved-image benchmark, unit tests, and recovery test were executed.

## Setup and comparison method

Existing Pi 5 / IMX708 stream: 640 x 480, target 15 FPS, JPEG quality 80 over
HTTP/MJPEG inside SSH. Laptop Python 3.12.14, Pillow 13.0.0, NumPy 2.2.6,
OpenCV 4.12.0 (wheel 4.12.0.88), one OpenCV CPU worker thread. No GPU or AI API.
Both detectors received the same grayscale image, and execution order alternated.
Feature budget 500; complete parameters are embedded in each report and saved in
`configs/features.json`. ORB descriptors were not computed. Timings include the
detection call and point conversion; grayscale, overlay, and transport are separate.
All live frames, including initialization outliers, are included in live summaries.

## Primary live viewer test

Requested 65 seconds; 966 frames across 64.265 seconds between
first and last receipt, completed 2026-10-28T23:33:25.030615+00:00.
The scene contained indoor brickwork, blinds, and furniture; it was not a
controlled lighting or camera-motion experiment. The final viewer was separately
inspected showing yellow Shi-Tomasi points, cyan ORB points, grid diagnostics,
counts, timings, and live connection statistics.

| Measurement | Shi-Tomasi | ORB |
| --- | ---: | ---: |
| Mean detection time (ms) | 8.214 | 3.081 |
| p95 detection time (ms) | 11.193 | 3.981 |
| Maximum detection time (ms) | 17.414 | 248.693 |
| Mean points/frame | 186.3 | 390.8 |
| Minimum points/frame | 153 | 359 |
| Maximum points/frame | 242 | 500 |
| Mean occupied cells out of 12 | 9.57 | 6.39 |
| No-feature frames | 0 | 0 |
| Warning frames | 0 | 0 |
| Detector error frames | 0 | 0 |

Receive FPS: **15.016**; completion throughput: 15.078 FPS.
Received producer sequence gaps: **0**; connection errors: **0**.
The display queue skipped 40 frames to show a fresh image; these are
counted separately from network/producer sequence gaps. Received FPS does not
measure physical display refresh rate.
Total decode/analysis/telemetry processing averaged 21.215 ms
(p95 25.778 ms); analysis including overlays averaged
18.325 ms (p95 22.688 ms).
ORB's largest detection-time outlier occurred on the first frame; it remains in
the summary. No causal attribution beyond its observed timing is assumed.
Receive and completion throughput use different first/last timestamp boundaries,
so their small difference is not evidence of extra frames or higher camera FPS.

ORB was faster in this run and returned more points, but its points occupied fewer
grid cells. Many points on repeated blind edges are not proof of stable or unique
landmarks. Neither point count nor grid coverage establishes detector accuracy,
repeatability, or tracking success. Shi-Tomasi remains a reasonable starting
candidate for Phase 3 sparse optical flow, to be evaluated there rather than
declared superior from these counts.

## Additional paired live run

A 65-second headless run received 970 frames at 15.009 FPS with no
producer sequence gaps or connection errors. A pre-existing video-only viewer
was also connected, and a short offline trial overlapped part of that run.
Shi-Tomasi averaged 3.808 ms and
ORB 1.825 ms; mean counts were
348.3 and 228.8.
ORB produced 8 warning frames (fewer than 30 points and/or low grid coverage).
Different scene contents and execution workloads prevent attributing differences
between the live runs to rendering alone. CPU frequency and background workload
were not controlled. These are measured trials, not universal speed rankings.

## Controlled saved-image tests

One real received image was saved, then benchmarked without a live detector client.
Five warmup calls per case/method were excluded, followed by 100 timed repetitions
per case/method with alternating order. Repeating a fixed frame measures timing
variability, not independent scene samples or accuracy. Darkening, blur, and
uniform gray are synthetic transformations and are explicitly labelled as such.

| Input | Shi points / occupied cells | ORB points / occupied cells | Shi mean / p95 ms | ORB mean / p95 ms |
| --- | ---: | ---: | ---: | ---: |
| Saved real image | 500 / 12 | 92 / 5 | 7.612 / 9.762 | 2.358 / 3.004 |
| Synthetic 20% intensity | 500 / 12 | 0 / 0 | 7.391 / 9.448 | 1.950 / 2.822 |
| Synthetic 21-pixel Gaussian blur | 139 / 12 | 18 / 3 | 7.015 / 8.944 | 2.118 / 3.080 |
| Synthetic uniform gray | 0 / 0 | 0 / 0 | 6.652 / 9.578 | 1.901 / 2.924 |

No OpenCV errors occurred in the offline benchmark. Uniform gray correctly gave
`no_features` for both detectors. ORB also reported `no_features` on the darkened
image and `low_count` on the blurred image. Shi-Tomasi retained 500 detections
on the darkened input because its score threshold is relative; this does not
validate real low-light robustness. Digital darkening does not model exposure,
noise, autofocus, or motion blur. The saved real image includes a person, so its
points are not assumed to be static navigation landmarks. The live scene changed
after this snapshot; do not compare its point counts to the later viewer as if
conditions were identical.

## Recovery and tests

With both detectors enabled, the recovery script interrupted its own SSH forward
for 3.031 seconds. Reception resumed with two connections;
maximum receive gap was 4.141 seconds, with
61 skipped producer frames and 2 expected connection errors.
Both detectors continued without detector exceptions. A separate live viewer
remained connected during this test. This simulates a transport interruption;
Wi-Fi loss, hardware failure, and the SSH process's own automatic restart are untested.

Windows: all 14 unit tests pass. Pi: eight transport/setup regression tests pass;
six laptop-only detector tests are skipped because Pi OpenCV is intentionally absent.
Tests cover blank input, textured point bounds, clustered spatial distribution,
invalid parameters, explicitly injected detector errors, same-array input,
alternating order, non-destructive overlays, and existing protocol checks.
The injection is a synthetic error-handling test, not a measured hardware fault.

## Evidence and reproducibility

- `results/reports/viewer-20261028-183218.json` and `.csv`: primary paired viewer run.
- `results/reports/phase2-live-comparison.json` and `.csv`: initial paired headless run.
- `results/reports/phase2-offline-final.json` and `.csv`: final fixed-image benchmark.
- `results/reports/phase2-recovery.json`, `.csv`, and `.log`: detection-enabled recovery.
- `results/reports/windows-phase2-packages.txt`: Windows dependency snapshot.
- `results/plots/phase2-final-overlays/`: real, synthetic-dark, synthetic-blur, and uniform overlays.
- `data/recordings/phase2-source.jpg`: local benchmark source image.

Source SHA-256: `6b930b32ca36c52becb7a9fa876c65a64109969e7e04bbe8e9b63e1fed1a1df7`.
Full parameters, version identifiers, counts, timings, grid bins, statuses, and
error messages are retained in the reports. Images and full telemetry remain
local and ignored by Git; this measured summary and reproduction instructions
are committed. See [feature guide](features.md) for commands and algorithm details.

Code, test design, documentation, and verification were AI-assisted by Codex.
The native feature window and saved overlay were visually inspected by Codex.
Independent human code review remains outstanding. No Phase 3 tracking, optical
flow, pose estimate, calibration, or navigation accuracy claim is included.
