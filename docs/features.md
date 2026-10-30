# Phase 2 — Shi-Tomasi and ORB detection

## Purpose

Find distinctive image locations before attempting to track them in Phase 3.
The Windows viewer can show Shi-Tomasi in yellow, ORB in cyan, or both side by
side on the same image. These are new detections each frame in this comparison
mode; it has no persistent point identities. Stateful tracking is now available
in the separate [Phase 3 optical-flow mode](optical_flow.md). Neither mode estimates pose.

`laptop/feature_detector.py` contains detector configuration, detection, grid
statistics, and overlays independently of the network. `laptop/camera_client.py`
adds live execution and CSV/JSON metrics. `configs/features.json` controls the
parameters. `laptop/benchmark_features.py` runs the same detectors on saved images.
The Pi camera server and its OS-managed camera packages are unchanged.

## Dependencies and live operation

Windows PowerShell, from this repository:

```powershell
.\.venv\Scripts\python.exe -m pip install -r laptop/requirements.txt
.\scripts\start_stream.ps1 -Features both
```

The launcher defaults to `both`; use `-Features shi-tomasi`, `-Features orb`, or
`-Features none` for a single detector or the original video-only viewer. Close
the existing launcher/viewer before launching another. Q or closing the window
stops the viewer, SSH forward, and camera. The side-by-side view is 1280 x 480
plus a status band; each detector sees the original 640 x 480 frame.

Windows dependencies are pinned: Pillow 13.0.0, NumPy 2.2.6, OpenCV headless
4.12.0.88. Headless OpenCV provides image algorithms; Tk remains responsible for
the visible window, avoiding a second GUI toolkit. OpenCV is configured for one
CPU worker thread. No GPU processing or API service is used.

For manual operation, start the server and SSH forward as described in
[streaming](streaming.md), then run on Windows:

```powershell
.\.venv\Scripts\python.exe laptop/camera_client.py --features both --duration 65 --report results/reports/new-features.json --snapshot data/recordings/new-source.jpg
```

Snapshots preserve the RGB source image rather than its feature overlay. Generated
images and telemetry are ignored by Git. Each report name must be new.

## What makes a feature useful?

A corner has intensity variation in two independent directions. A flat patch
has little variation; an edge mainly varies across one direction, leaving motion
along the edge ambiguous. The local image-gradient matrix summarizes this:

`M = sum_over_patch([[Ix*Ix, Ix*Iy], [Ix*Iy, Iy*Iy]])`.

Shi-Tomasi uses the smaller eigenvalue of M as a corner score. If both eigenvalues
are large, the patch changes in both directions. OpenCV's `goodFeaturesToTrack`
applies a score threshold relative to the strongest corner, nonmaximum suppression,
minimum spacing, and a maximum count. A detected corner is a candidate for tracking,
not evidence that it will remain visible or match correctly over time.

ORB detects FAST corners across an image pyramid, ranks them using its configured
Harris score, and estimates keypoint orientations. In later work ORB can also
compute rotated BRIEF descriptors for matching. This phase calls `ORB.detect`
only; descriptor extraction is deliberately excluded from its timing comparison.

Lighting affects contrast, exposure, sensor noise, and motion blur. Low texture,
blur, saturation, and uniform walls can leave few distinctive points. More points
can also mean more weak/noisy points. A moving person can provide many corners
without being a useful static navigation landmark. No semantic filtering is done.

## Parameters and spatial distribution

Both detectors request at most 500 points. These settings are not equivalent
operating thresholds and do not guarantee comparable localization or repeatability.

| Parameter | Default | Effect |
| --- | ---: | --- |
| Shi-Tomasi qualityLevel | 0.01 | Lower accepts weaker corners relative to the strongest response |
| Shi-Tomasi minDistance | 10 px | Larger separates detections more strongly |
| Shi-Tomasi blockSize | 7 px | Gradient neighborhood size changes noise/structure response |
| ORB fastThreshold | 20 | Lower accepts smaller absolute contrast differences |
| ORB scaleFactor / nlevels | 1.2 / 8 | Controls pyramid scale sampling and compute cost |
| ORB edgeThreshold / patchSize | 31 / 31 px | Restricts border detections and orientation patch support |

A 4-column by 3-row grid logs all 12 cell counts, occupied-cell count, and
coverage (occupied cells / 12). Coverage measures spread, not uniformity, optical
flow observability, or navigation quality. The header covers the top image strip
for legibility; metrics use the full underlying image, including that strip.

Configurable warning rules: fewer than 30 features gives `low_count`; below 25%
grid coverage gives `poor_coverage`; zero detections gives `no_features`.
OpenCV exceptions give `error` with a logged explanation, distinct from texture
loss. The first applicable status is shown; counts and grid values remain logged.
Thresholds are engineering diagnostics, not calibrated failure probabilities.

## Measurement definitions

Both methods receive the identical uint8 grayscale array on each compared frame.
Execution order alternates by frame to reduce systematic warm-cache advantage.
`detect_ms` includes the detector call and conversion to an N-by-2 point array;
it excludes grayscale conversion, grid metrics, drawing, JPEG decode, descriptors,
and network time. Every live frame is included, including initialization outliers.

`analysis_ms` covers common grayscale conversion, both detections, grid metrics,
and overlay rendering when enabled. `processing_ms` starts before JPEG decode and
ends after analysis/telemetry assembly. Neither includes physical display scanout.
Reports separately record receive FPS and completion throughput; these are not
unconstrained detector FPS benchmarks. Existing delay estimates retain the clock
uncertainty described in the streaming guide.

Per-frame CSV adds detector counts, processing time, grid counts, coverage, status,
and error strings. Summary JSON records parameters and library versions, timing
statistics, feature count ranges, no-feature frames, warning frames, and errors.
No-feature frames are expected behavior in unsuitable scenes, not software crashes.

## Reproducible tests without the Pi

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m laptop.benchmark_features --image data/recordings/new-source.jpg --repeats 100 --report results/reports/new-offline.json --overlays results/plots/new-overlays
.\.venv\Scripts\python.exe scripts/test_stream_recovery.py --features both --report results/reports/new-feature-recovery.json
```

The offline benchmark uses a real saved image plus explicitly synthetic variants:
20% intensity, Gaussian blur with a 21-pixel kernel, and uniform gray. It runs five
warmup calls per case/method, then 100 timed calls each, alternating order. These
repetitions measure runtime on fixed inputs, not 100 independent scenes. Synthetic
darkening does not reproduce camera auto-exposure, photon noise, or physical low
light. Uniform gray is a controlled low-texture input, not a real wall experiment.
The original source hash is saved for reproducibility; the image remains local.
The recovery test requires the real Pi server to be running and creates its own
SSH forward. It interrupts that forward, then checks reception resumes with both
detectors enabled. It does not disconnect Wi-Fi or validate hardware fault recovery.

Unit tests cover blank input, textured input and point bounds, clustered grid
distribution, invalid parameters, an injected OpenCV failure, identical shared
input, and alternating order. Pi regression tests skip laptop-only detector tests
when OpenCV is absent; the Pi need not install the laptop vision environment.

## Acceptance and troubleshooting

Acceptance: both live overlays are visible on a textured indoor scene; actual
counts/distributions/timings are recorded on common frames; unsuitable input and
detector errors are distinguished; tests and results are documented. See
[measured results](phase2_results.md). Stop at Phase 2 before adding tracking.

- No points: inspect lighting, blur, texture, and thresholds. Do not label an
  empty image a successful navigation observation.
- Shi-Tomasi reaches 500 often: it is capped; the scene may support additional
  candidates. Raising the cap changes both timing and density.
- Dark-image Shi-Tomasi counts stay high: its threshold is relative; this does
  not show immunity to darkness or guarantee that detections are stable.
- ORB points cluster or avoid borders: inspect its pyramid, FAST threshold, and
  edge exclusion. More detections alone do not establish a better detector.
- Video-only mode works but detection does not: install the pinned laptop
  requirements using the project's Windows Python, not the Pi's interpreter.
- Slow viewer: inspect detector p95, total analysis time, display skips, and
  network metrics separately before changing stream settings.

## Sources

- [OpenCV Shi-Tomasi tutorial](https://docs.opencv.org/4.12.0/d4/d8c/tutorial_py_shi_tomasi.html)
- [OpenCV ORB tutorial](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
- [OpenCV ORB API](https://docs.opencv.org/4.x/db/d95/classcv_1_1ORB.html)
