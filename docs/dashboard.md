# Live navigation dashboard

Start from the laptop repository in PowerShell:

```powershell
./scripts/start_stream.ps1 -Dashboard
```

The launcher starts the Pi camera remotely, opens the SSH forward, loads the reviewed Phase 4 calibration, and enables optical flow and visual odometry. No Pi desktop interaction is needed. Use `-DurationSeconds 60` for a timed demonstration or `-OdometryCalibration path/to/reviewed.json` for another reviewed calibration with matching camera settings.

The dashboard uses the existing Tk installation, with no new dependencies. Resize its window to fit the screen. Stop camera and close, Q, or the window close control ends the viewer and lets the launcher close its owned SSH tunnel and camera server. Reports are saved automatically under timestamped `results/reports/viewer-*.json` and matching CSV paths.

## Displays

The left panel contains the live raw camera image, tracked features, and motion vectors enlarged 3x for visibility. Geometry uses calibration-corrected point coordinates, even though the displayed image is raw.

The right panel shows tracking state, active and retained feature counts, odometry state, inlier support, parallax, and processing FPS over the most recent 30 processed frames. Orientation is an estimated ZYX Euler decomposition of the segment's camera-to-world rotation: X roll, Y pitch, Z yaw in degrees. Before any accepted pose, it says that the segment is only an initialized origin. Between estimates the orientation is held; it is not an inertial heading measurement. Euler angles can be ambiguous near a singularity.

The path plot shows X/Z camera centers from accepted estimates in the current segment, labeled illustrative unit steps. Independently unknown translation magnitudes prevent interpretation as physical distance, speed, or a globally scale-consistent path. The viewport rescales automatically and failure resets start a new segment. Plot updates consume all processed telemetry, even when the image queue skips a displayed frame.

Capture-to-receipt delay is an estimate including clock-probe uncertainty; it is not a ping time or end-to-end display latency. Producer sequence gaps, GUI queue skips, and connection errors are separate measured counters. They should not be combined or called TCP packet loss.

System warnings show disconnection, stale data, rejected/waiting odometry, and scale limitations. After 1.5 seconds without a displayed frame, the dashboard marks the feed STALE and displays zero FPS; the last image and estimates are explicitly historical. Recovery resumes the feed, and a tracking gap resets the odometry segment. A pose rejection does not mean transport failed.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Dashboard tests check processing-rate arithmetic, gap counting, empty startup, stale status, and reconnect warnings. Live layout, interruption/recovery, report output, and shutdown were exercised with the actual camera. See phase6_results.md for measured results and timing definitions.
