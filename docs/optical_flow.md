# Phase 3 — sparse Lucas–Kanade optical flow

## What is implemented

Windows tracks Shi-Tomasi features between received camera images using pyramidal
Lucas–Kanade (LK), verifies matches in both directions, rejects poor candidates,
and replenishes features when needed. The viewer shows accepted motion vectors,
current endpoints, and newly seeded points. It does not estimate camera pose,
translation scale, physical speed, or a trajectory.

Files: `laptop/optical_flow.py` contains the reusable stateful tracker;
`configs/tracking.json` controls its settings; `laptop/camera_client.py` integrates
tracking and telemetry; `laptop/benchmark_flow.py` creates controlled image-plane
tests. Tests are in `tests/test_optical_flow.py`. The Pi capture server is unchanged.
Phase 2 detection comparisons remain available as a separate mode.

## Start on Windows

From this repository in PowerShell, after closing any prior stream launcher:

```powershell
.\scripts\start_stream.ps1 -Tracking
```

Q or closing the viewer stops the camera and SSH forward when using the launcher.
For a timed session:

```powershell
.\scripts\start_stream.ps1 -Tracking -DurationSeconds 65
```

If script execution is restricted, use the manual server/tunnel commands in
[streaming](streaming.md), then run:

```powershell
.\.venv\Scripts\python.exe laptop/camera_client.py --tracking --duration 65 --report results/reports/new-flow.json
```

`--tracking` and `--features both/shi-tomasi/orb` are separate modes. Tracking
seeds its own Shi-Tomasi points. `--features none` is the client default; the
launcher selects it automatically when `-Tracking` is supplied. Existing pinned
laptop OpenCV/NumPy/Pillow dependencies suffice; no new Pi package is needed.

## Overlay interpretation

- Green arrows: accepted previous-to-current image displacement.
- Yellow points: accepted current endpoints.
- Cyan rings: newly seeded features, with no claimed previous correspondence.
- Arrows are drawn at **3× displacement for visibility** by default. This is
  explicitly labelled on the image; all reported measurements remain unscaled.

The status band reports tracking status, accepted/attempted correspondences,
active points, replacement count, processing time, frame rate, network gaps,
and connection failures. Small arrows can be indistinguishable from dots when
the scene is still. The header obscures the upper image strip for readability;
tracking operates on the full underlying image.

## Why optical flow works, and when it fails

Brightness constancy approximates a scene patch as retaining intensity while it
moves: `I(x+dx, y+dy, t+dt) ≈ I(x,y,t)`. A first-order expansion gives
`Ix*dx + Iy*dy + It*dt ≈ 0`. Ix/Iy are spatial image gradients; It describes
change over time. One pixel provides one equation for two displacement unknowns
(the aperture problem). Lucas–Kanade fits a common displacement to a small
neighborhood by least squares, using the same gradient matrix that motivates
corner detection. A well-conditioned patch has variation in two directions.

The approximation assumes small motion at the working scale, locally similar
motion, sufficiently distinctive texture, and approximate intensity constancy.
Image pyramids solve coarse-to-fine so larger full-resolution motions appear
smaller at coarse levels. `pyramid_max_level=3` permits levels 0–3 (four scales).
Iteration stops at a configured count or small update. Pyramids do not guarantee
tracking under arbitrary motion, repeated textures, blur, exposure changes,
rolling shutter, or occlusion. Coarse levels can also lose distinctive structure.

Optical flow is apparent **image motion**. Foreground objects, camera translation,
camera rotation, depth variation, and illumination changes can all contribute.
A uniform image translation and an in-plane image rotation give different
synthetic vector fields, but general 3D camera translation does not imply one
constant vector. Optical flow alone does not uniquely separate translation,
rotation, and moving objects. A moving hand in the inspected live scene produced
vectors without establishing any camera movement.

## Quality checks and feature replacement

Each attempted correspondence must pass all gates:

1. Forward LK succeeds, returns finite coordinates, stays inside the image, and
   has a patch error at most 25 (OpenCV's default mean absolute patch difference).
2. Backward LK succeeds with finite coordinates and the same patch-error limit.
3. The backward point returns within 1 pixel of its previous position (L2 norm).
4. Accepted displacement is at most 80 pixels per observed image pair.

Rejection counters are disjoint and sum with accepted count to attempted count.
A successful forward–backward check is a consistency test, not proof of correct
matching; symmetric mistakes in repeated texture can survive it. OpenCV errors
are logged separately from a blank/no-feature scene; an exception rejects the
whole attempted set into a separate error bucket.

If fewer than 30 correspondences survive or acceptance falls below 50%, the old
feature set is discarded and the current image is seeded again. Otherwise valid
survivors retain their IDs. Top-up is attempted if active count is below 120,
4×3 grid coverage is below 25%, or 30 frames have elapsed since detection.
Shi-Tomasi uses a mask excluding a 10-pixel radius around retained points and
adds up to the 300-point budget. New IDs increase monotonically, including after
resets. Redetection can find zero new corners; a detection attempt is distinct
from a replacement event with actual added points.

New points never count as accepted previous/current correspondences and are not
given zero-length motion vectors. After full texture loss, recovery first seeds
new points; tracking resumes only when a later frame verifies their displacement.
Accepted pairs on a low-quality frame remain diagnostic observations even when
their IDs are not retained for the next frame.
Summary totals for new features/replacement events include the first seed frame;
initial seed and later non-reset top-up counts are also separated explicitly.

The tracker reinitializes on producer-session or image-size change, nonmonotonic
frame/time input, more than two missing producer frame IDs, or capture interval
above 0.3 seconds. The interval uses Pi sensor timestamps, so it does not depend
on laptop/Pi wall-clock synchronization. It does not bridge long interruptions.

## Measurements and definitions

CSV adds `flow_*` columns for attempted/accepted tracks, success ratio, active and
new features, status, rejection reasons, frame interval, flow magnitudes,
median horizontal/vertical displacement, forward–backward residual, spatial
variation, coverage, processing time, and reset reason. JSON records all parameters
and versions with aggregate metrics and status/reset counts.

`weighted_success_ratio = total accepted / total attempted`. Initialization and
empty-feature frames have no denominator and a null per-frame ratio. They are
still reported through statuses and reset counters. This is **acceptance under
configured checks**, not a physical accuracy percentage or landmark identity
ground truth. Track replenishment is reported separately.

Flow magnitude is pixels per observed pair, not meters or calibrated velocity.
Capture intervals are recorded because frame gaps change temporal spacing.
`flow_spread_px` is RMS variation around the mean accepted vector, useful for
inspecting spatially varying motion but not a motion-type classifier.

`flow_ms` covers forward/backward LK and correspondence filtering; `renewal_ms`
covers the optional mask/detection/addition work; `total_ms` includes grayscale,
flow, replacement, bookkeeping, and metrics, **excluding overlay drawing**.
The client's `processing_ms` additionally includes JPEG decode, optional drawing,
and telemetry assembly, ending before Tk display. Throughput and physical display
refresh are different quantities. Existing network-delay estimates retain their
documented clock uncertainty and are not used in LK matching.

## Repeatable verification

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m laptop.benchmark_flow --image data/recordings/phase3-source.jpg --report results/reports/new-flow-synthetic.json --overlays results/plots/new-flow-synthetic
.\.venv\Scripts\python.exe scripts/test_stream_recovery.py --tracking --report results/reports/new-flow-recovery.json
```

The synthetic benchmark requires a textured saved image and creates stationary,
horizontal/vertical 2-pixel steps, 0.4-degree in-plane rotation steps, exploratory
15-pixel steps, partial occlusion, complete texture loss, and a timestamp/frame
gap. It applies known transforms to one real camera image. These are synthetic
image-plane tests, not physical camera translations or rotations.

Pairwise endpoint error compares accepted points to the known next-image mapping.
Rejected candidates do not receive an endpoint error; survival is reported
alongside error to avoid presenting a small error as complete tracking success.
There is no ground truth for live tracking. Integer-shift synthetic images are
much easier than real low-light, blurred, rolling-shutter motion. Each sequence
has 20 frames at simulated 15 FPS; offline execution time is measured independently
of that simulated capture rate. Every frame, including initialization, is timed.

The recovery test interrupts only its own SSH forward, restores it after about
three seconds, and checks that the receiver resumes **and the tracker reports a
frame-gap reset**. It does not disconnect Wi-Fi or test camera hardware faults.

Tests cover known translation error, stationary behavior, full loss/reseeding,
periodic renewal preserving survivors, unique IDs, timestamp/session/resolution
resets, deliberately inconsistent backward matches, invalid inputs, and injected
LK exceptions. Optional laptop tests skip on the Pi, where OpenCV is absent.

## Troubleshooting and remaining work

- Many rejections: inspect forward, backward, and consistency counters; texture,
  motion, image size/pyramid levels, patch-error limits, and exposure all matter.
  Relaxing a gate may increase survival while admitting wrong correspondences.
- Few new points: a low-texture image cannot supply features; point budget is a
  cap rather than a promised count. Repeated replacement attempts are recorded.
- Flow changes during a stationary-camera test: moving objects and sensor/image
  changes can cause flow. Live optical flow is not a calibrated camera velocity.
- Long interruption: reinitialization is intentional; no displacement is inferred
  across the missing interval. Start the SSH forward again if its process exited.
- Calibration, consistent focus, relative pose, metric scale, and navigation
  accuracy remain future phases. No phase-4 calibration code is included here.

See [measured results](phase3_results.md) for actual evidence and limitations.

## Sources

- [OpenCV optical-flow tutorial](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)
- [OpenCV LK API](https://docs.opencv.org/4.7.0/dc/d6b/group__video__track.html)
- [Official forward–backward example](https://github.com/opencv/opencv/blob/4.x/samples/python/lk_track.py)
