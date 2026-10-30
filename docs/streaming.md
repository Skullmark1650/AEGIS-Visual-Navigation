# Phase 1 — live video streaming

Phase 2 update: the launcher now defaults to the paired feature overlay. Use
`-Features none` for the original Phase 1 video-only behavior. See
[feature detection](features.md) for detector parameters and tests.
Phase 3 adds `-Tracking` for live LK motion vectors and quality-checked tracks;
see [optical flow](optical_flow.md). It uses the same camera server and transport.

## Objective and implementation

Capture camera frames on the Pi, transmit them to Windows, display live video,
and record actual throughput and timing. HTTP/MJPEG is simple to inspect and
requires no broker, ROS, OpenCV, API subscription, or additional hardware.
The stream travels through an SSH forward; HTTP listens only on 127.0.0.1.

Files: `pi/camera_server.py` owns Picamera2 and HTTP; `pi/stream_control.py` manages
the project's server; `laptop/camera_client.py` receives and displays; configuration
is `configs/stream.json`; the Windows launcher is `scripts/start_stream.ps1`.
The source must be present on both machines before starting; the launcher does
not silently deploy local changes.

## Required software

Pi: OS Picamera2, libcamera, Python 3.11+, and Pillow. Keep the existing
`--system-site-packages` environment. Windows: project Python, Tk 8.6, OpenSSH,
and `Pillow==13.0.0` installed with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r laptop/requirements.txt
```

## Operate from Windows

From the repository, in Windows PowerShell:

```powershell
.\scripts\start_stream.ps1
```

The live viewer shows receive FPS, estimated delay with clock uncertainty,
received frames, producer sequence gaps, and connection errors. Close the viewer
or press Q to shut down. The launcher stops its SSH forward and asks the Pi
server to close its camera. Default duration is one hour; optional example:

```powershell
.\scripts\start_stream.ps1 -DurationSeconds 120
```

Each launch records uniquely named JSON and per-frame CSV under
`results/reports/viewer-<date-time>.*`. Tunnel and camera logs are local artifacts.
Existing reports are preserved. The camera does not record continuous video.

## Manual alternative

If PowerShell script execution is restricted, use three Windows terminals.
First start the Pi camera server (returns after launching in the background):

```powershell
ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py start'
```

Second, keep the SSH forward running:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8765:127.0.0.1:8765 aegis-pi
```

Third, run the viewer from the laptop repository:

```powershell
.\.venv\Scripts\python.exe laptop/camera_client.py --report results/reports/my-session.json
```

After closing the viewer, press Ctrl+C in the forwarding terminal and stop the Pi:

```powershell
ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py stop'
```

Do not disable PowerShell security policy just to use the launcher.

## Configuration

Edit `configs/stream.json` on the Pi, then stop/start the server. Current settings:
640 x 480 pixels, target 15 FPS, JPEG quality 80. Width, height, target FPS, and
quality are validated; FPS range is 1–30, quality 10–95. These are requested
settings, not promised throughput. The fixed frame-duration controls constrain
exposure time. Lower light may reduce image quality at the selected frame rate.
Default camera focus behavior is not a calibrated focus configuration.

If editing Windows files, copy the configuration explicitly:

```powershell
scp configs/stream.json aegis-pi:/home/YOUR_PI_USER/AEGIS/configs/stream.json
```

## Frame protocol and metrics

Each multipart part carries a length-bounded JPEG, producer session UUID,
monotonic frame ID within that session, raw libcamera SensorTimestamp,
its approximate Pi wall-clock mapping, and capture-to-JPEG-ready duration.
Picamera2's BGR888 format yields RGB bytes for Pillow; no channel swap is applied.

Receive FPS is `(received_count-1)/(last_arrival-first_arrival)`, using the laptop
monotonic clock. It excludes startup, includes outages within the receive interval,
and counts decoded frames, not display refreshes. Sequence gaps count skipped
producer frames; they do not measure TCP packet loss or pre-producer sensor loss.
A server restart changes session UUID and resets the frame-ID baseline.

Five HTTP clock exchanges estimate Pi-minus-laptop clock offset with the usual
two-way timestamp formula; the lowest RTT sample is retained. Half its RTT is
reported as a conservative communication uncertainty under stable clocks.
Clock probes repeat every 30 seconds independently of frame reception and on
reconnect. Unmodelled OS scheduling, timestamp mapping error, and clock drift can
add error. These probes do not discipline either device's clock.

Estimated delay = laptop receipt wall time + estimated clock offset - mapped
sensor timestamp. It includes sensor readout, JPEG encoding, transport, and any
buffering, but excludes JPEG decoding and physical display scanout. It is not a
precise one-way network latency measurement. Do not clamp negative estimates;
they can indicate offset uncertainty or clock changes. Capture-to-JPEG-ready
timing stays within the Pi clock domain and avoids cross-device clock offset.

## Test and acceptance

Windows, from repository:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe laptop/camera_client.py --headless --duration 65 --report results/reports/new-benchmark.json
.\.venv\Scripts\python.exe scripts/test_stream_recovery.py --report results/reports/new-recovery.json
```

Keep the Pi server and port-8765 SSH forward running for the throughput test.
The recovery test creates its own forward on port 8766, interrupts it for three
seconds, and checks that frames resume without restarting the receiver. It
does not disable Wi-Fi or prove recovery from every network failure mode.

Acceptance: real live viewer inspected; stable reception near the requested
15 FPS for the measured run; timing and frame gaps recorded; automatic reconnect
tested; clean camera shutdown demonstrated. See `phase1_results.md` for evidence.
Do not progress to Phase 2 until this phase is accepted.

## Troubleshooting and limits

- Port in use: close the prior launcher/forward; do not start overlapping launchers.
- Reconnecting: verify Pi server status and tunnel. Receiver retries after failures;
  a dead SSH process must be restarted (the recovery test does that explicitly).
- Camera busy: stop the streaming server before running the still-capture test.
- Camera exception: producer closes the camera and exits; inspect Pi
  `~/AEGIS/results/server.log`, fix the fault, and start again. A failed sensor
  is not silently replaced with simulated frames.
- Camera process management checks the saved PID against this repository's server
  command before stopping it. It does not kill arbitrary Python processes.
- Delay spikes: inspect clock uncertainty, Wi-Fi contention, and buffering before
  attributing the result to vision processing. More accurate latency validation
  needs stronger clock synchronization or an optical measurement experiment.
- JPEG/TCP is a prototype transport; sustained low-latency operation under
  congestion has not been established. Logs can grow; the viewer defaults to a
  bounded one-hour session. No metric here establishes navigation accuracy.

## Sources

- [Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Picamera2 request format definitions](https://github.com/raspberrypi/picamera2/blob/main/picamera2/request.py)
