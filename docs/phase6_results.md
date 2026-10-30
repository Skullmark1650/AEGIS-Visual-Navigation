# Phase 6 dashboard results

Tested 2026-10-28, America/Chicago. Phase 6 adds a laptop-operated Tk dashboard to the existing camera, LK tracking, and calibrated visual-odometry pipeline. No new runtime dependency or Pi desktop interaction is required. Phase 7 has not started.

## Requirements delivered

The dashboard displays live camera video, tracked points, motion vectors, an illustrative camera path, segment-relative orientation, tracking and pose status, feature counts, processing FPS, estimated transport delay with clock uncertainty, producer gaps, GUI queue skips, connection errors, and system warnings. Measured transport values, estimated pose values, and the illustrative unit-step path are explicitly distinguished.

The initial origin is not presented as an observed orientation. Held poses and stale images are not new measurements. The path is not a metric or globally scale-consistent trajectory. All Phase 5 limits remain applicable; adding a dashboard does not improve pose accuracy.

## Camera and interruption test

Artifact: `results/reports/viewer-20261028-231556.json` and matching CSV. The live dark dashboard was visually inspected with the actual Pi camera and matching reviewed calibration. All panels, counters, warnings, and the Stop control were visible.

| Measurement | Result |
|---|---:|
| Processed frames | 517 |
| Receive span | 39.047 s |
| Receive FPS including interruption | 13.2148 |
| Processing FPS including interruption | 13.2199 |
| Complete processing mean / p95 / max | 16.367 / 21.296 / 28.573 ms |
| Dashboard refresh count | 656 |
| Dashboard refresh mean / max | 4.427 / 41.584 ms |
| Accepted VO estimates | 6 |
| GUI queue skips | 9 |
| Connections | 2 |
| Connection errors | 1, deliberately induced timeout |
| Producer sequence gaps | 10 |
| Maximum receipt gap | 4.781 s |

The owned camera-server process was paused with SIGSTOP, then resumed with SIGCONT after approximately three seconds. The dashboard visibly showed STALE, zero FPS, and an explicit historical-image/pose warning. A timeout caused reconnection. The saved stream resumed and recorded one frame-gap reset rather than connecting a path across the outage. The aggregate FPS includes the deliberate interruption and must not be compared with an uninterrupted 15-FPS run without that qualification.

VO statuses: 428 waiting-baseline, 70 planar-or-rotation, six low-parallax, six accepted, five pose-support failures, one startup reset, and one frame-gap reset. Accepted estimates have no external motion ground truth; they demonstrate integration rather than verified navigation accuracy.

Dashboard refresh timing measures Python/Tk refresh callback work, including image preparation, canvas updates, and widget configuration. It excludes display scanout and deferred OS painting. Complete processing timing measures the receiver's decode/tracking/odometry/overlay work; it does not include dashboard refresh callback time. Dashboard statistics are the last callback snapshot available when the receiver writes its report.

## Final uninterrupted run and Stop control

Artifact: `results/reports/viewer-20261028-231710.json` and matching CSV. This run used the final dashboard source, including the origin/accepted-orientation distinction. It ended by clicking the dashboard's **Stop camera and close** button before its requested 90-second limit.

| Measurement | Result |
|---|---:|
| Frames / receive span | 982 / 65.343 s |
| Receive / processing FPS | 15.0131 / 15.0202 |
| Connection errors / producer gaps | 0 / 0 |
| GUI queue skips | 34 |
| Receiver processing mean / p95 / max | 17.834 / 29.670 / 110.113 ms |
| Dashboard refreshes | 1,071 |
| Dashboard callback mean / max | 5.221 / 20.070 ms |
| Accepted VO estimates | 51 |
| Tracking quality resets | 72 |

The scene/camera moved during the run. Other pose statuses were 652 waiting-baseline, 101 planar-or-rotation, 35 pose-support failures, 70 low-parallax rejections, and one startup reset. Frequent resets show why this remains a research prototype; 51 accepted outputs are not 51 independently verified correct poses. The dashboard continued displaying live video and warnings through degraded estimation.

The GUI closed, both report files were written, the laptop port forward stopped listening, and remote camera control reported **Server stopped**. This verifies laptop-only operation and cleanup through the actual Stop button, not only a timed exit.

## Automated checks and limitations

All 39 automated tests passed, including three dashboard telemetry tests and all prior camera, calibration, tracking, and odometry regressions. Stale-data and disconnect warning behavior were tested both with telemetry fixtures and the live interrupted camera. The final orientation wording was tightened to distinguish initialized origins from accepted estimates.

The dashboard refresh loop requests updates every 50 ms; that is a scheduling interval, not a claim of 20 displayed camera frames per second. The camera targets 15 FPS. A latest-image queue can skip GUI images; all processed pose records still feed the path. Timing measurements apply to this laptop and scene, not every machine or scene. Long runs retain the existing per-frame telemetry in memory; memory growth has not been endurance-tested.

For startup, shutdown, warning meanings, and calibration requirements, see dashboard.md. The source/artifact integrity manifest is `results/reports/phase6-source-hashes.json`. Generated machine reports remain local under ignored results paths.
