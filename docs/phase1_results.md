# Phase 1 measured results — 2026-10-28

Status: COMPLETE after real hardware, viewer, recovery, and clean-stop checks.
Phase 2 has not started. These results describe the tested connection and scene,
not guaranteed performance across networks or environments.

## Configuration and method

Raspberry Pi 5 / IMX708, Python 3.11.2, Picamera2 0.3.31, OS Pillow 9.4.0;
Windows Python 3.12.14, Pillow 13.0.0, Tk 8.6. Requested capture: 640 x 480,
15 FPS, JPEG quality 80. HTTP/MJPEG was forwarded through the existing SSH
connection. Pi wlan0 was up; radio signal strength was not measured because
`iw` was unavailable. Indoor scene with a bright window; no controlled light
measurement or motion experiment was performed. Camera focus was not calibrated.

The final sustained headless run requested 65 seconds, completed at
2026-10-28T23:23:22.295333+00:00, and spanned 64.578 seconds between
first and last received frames. CSV preserves every decoded frame and timing.
Clock probes ran in a separate worker thread. The viewer and recovery tests
were separate runs. All frames came from the real camera; no simulated data.

| Final sustained measurement | Result |
| --- | ---: |
| Received/decoded frames | 970 |
| Receive FPS | 15.005 |
| Producer sequence gaps | 0 |
| Connection errors | 0 |
| JPEG payload throughput, excluding protocol overhead | 5.539 Mbit/s |
| Pi sensor-start to JPEG-ready mean / p95 | 15.193 / 15.828 ms |
| Laptop JPEG decode mean / p95 | 1.501 / 1.762 ms |
| Estimated sensor-start to laptop receipt mean / p95 | 50.406 / 58.615 ms |
| Estimated receipt delay maximum | 129.893 ms |
| Clock offset probe uncertainty, per sample | 31.84, 29.08, 28.55 ms |

The delay estimate has substantial clock uncertainty. It cannot establish precise
one-way network latency or physical camera-to-display latency. The uncertainty
is comparable to the reported mean; prefer the same-device capture timing for
conclusions that need millisecond precision. Frame receipt excludes decode and
display scanout. Offset assumptions and formulas are in [streaming](streaming.md).

## Viewer and reconnect evidence

A native Windows viewer was opened and inspected through a captured window state:
live image and changing frame counter were present. A separate 30-second viewer
run decoded 438 frames at 15.029 FPS with zero received
sequence gaps and zero connection errors. Its latest-image display queue skipped
4 frames to favor freshness. Receive FPS is not a measured
monitor refresh rate. The final launcher smoke test received 170 frames at 15.001 FPS over 11.266
seconds, with zero sequence gaps or connection errors, then stopped the camera
cleanly. One display-queue frame was skipped.

The final recovery test kept the Pi camera running and terminated only its own
SSH forward for 3.015 seconds.
The receiver established 2 connections, logged 2
connection failures, and resumed automatically without receiver restart.
Maximum gap between received frames: 4.250 seconds.
62 producer frame IDs were skipped across the outage.
This validates transport reconnection after forward restoration; it does not
prove Wi-Fi recovery, SSH process restart, or camera hardware fault recovery.

After the launcher stopped, a fresh still-capture test also succeeded (66,883-byte
JPEG), confirming that the camera was released for reuse.

All eight unit tests passed on both Windows and the Pi. Protocol tests cover
embedded boundary-like bytes, truncation, allocation bounds, and configuration.
Real integration tests separately establish camera/network operation.

## Artifacts and repeatability

Local ignored evidence in `results/reports/`:

- `phase1-final-sustained.json` and `.csv`: final throughput/timing run.
- `phase1-final-recovery.json`, `.csv`, and `.log`: final interruption test.
- `phase1-viewer.json` and `.csv`: inspected live-viewer run.
- `viewer-<timestamp>.json` and `.csv`: final launcher smoke test and later sessions.
- `windows-phase1-packages.txt`: laptop package snapshot.

A received frame is saved locally at `data/recordings/phase1-frame.jpg`.
Images, full logs, and per-frame CSV remain outside Git. This summary is committed.
Use [streaming instructions](streaming.md) to repeat tests with fresh report names.

## Development findings and limits

Initial runs achieved 15 FPS but exposed a receive pause during inline clock
recalibration. Moving calibration to a separate worker reduced that avoidable
backlog; it does not eliminate Wi-Fi jitter or TCP buffering. Earlier trial
artifacts remain available and are not presented as final results.

No benchmark at 30 FPS, congestion endurance test, accuracy measurement, camera
calibration, feature detection, or trajectory estimation has been performed.
These are Phase 1 engineering measurements, not navigation performance results.
Code, test design, documentation, and verification were AI-assisted by Codex;
independent human review remains outstanding.
