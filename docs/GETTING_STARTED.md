# Set up a Pi and laptop

These steps target a new Raspberry Pi 5 + Camera Module 3 and a Windows laptop. Allow time for OS installation, dependency downloads, and physical camera calibration. Shell blocks are labeled by the computer where they run. You do not need Codex or a cloud API key to run the camera and local vision.

## 1. Assemble and install the Pi

With Pi power disconnected, attach the Camera Module 3 using a Pi 5 compatible CSI cable. Pi 5 uses smaller camera connectors than older boards. Follow the official [camera hardware instructions](https://www.raspberrypi.com/documentation/accessories/camera.html) for ribbon orientation; do not insert/remove the cable while powered.

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install Raspberry Pi OS 64-bit with its supported camera stack. The original prototype used a Debian 12 Bookworm environment. Newer OS versions may need separate verification. In Imager, set a username, hostname, Wi-Fi if needed, and enable SSH. Record your username; it need not be `pi`. Boot the Pi and connect the laptop to the same network.

On the Pi (local terminal or initial password SSH session):

```bash
sudo apt update
sudo apt install git python3-venv python3-picamera2 rpicam-apps
rpicam-hello --list-cameras
rpicam-still -n -o ~/camera-check.jpg
```

Expected: an IMX708 camera is listed and `camera-check.jpg` shows a recognizable scene. Inspect it on the Pi or copy it to the laptop. Close other camera applications before continuing. See the [official camera software guide](https://www.raspberrypi.com/documentation/accessories/camera-software.html) if your OS uses different package names.

## 2. Install laptop prerequisites

Install [Git for Windows](https://git-scm.com/downloads/win) and standalone [Python 3.12](https://www.python.org/downloads/windows/) with Tcl/Tk support and the Python launcher. Enable Windows OpenSSH Client in Optional Features if `ssh` is missing. In PowerShell:

```powershell
git --version
ssh -V
py -3.12 --version
py -3.12 -m tkinter
```

The last command should open a small Tk test window. Close it. In a folder you control, clone the public repository:

```powershell
git clone https://github.com/Skullmark1650/AEGIS-Visual-Navigation.git
cd AEGIS-Visual-Navigation
```

Alternatively use GitHub's Code → Download ZIP and extract it first. Create the environment from inside the repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r laptop/requirements.txt
.\.venv\Scripts\python.exe scripts/verify_environment.py --role laptop --output results/reports/windows-environment.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: environment report ends with `"passed": true`; tests pass. Vision tests require the laptop dependencies. No activation is necessary. The project uses Tk for windows and headless OpenCV for vision; do not replace it with a GUI OpenCV package unnecessarily.

## 3. Configure SSH access

Replace `YOUR_PI_USER` below with the username you created. If `raspberrypi.local` does not resolve, use the Pi's LAN IP from your router or `hostname -I` on the Pi.

```powershell
ssh YOUR_PI_USER@raspberrypi.local
```

Verify the host fingerprint against the Pi before accepting a new host key. Log out using `exit`. Generate a dedicated key on Windows (choose a passphrase and use an SSH agent if desired; do not overwrite an existing key):

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\aegis_pi_ed25519" -C "AEGIS laptop"
Get-Content "$env:USERPROFILE\.ssh\aegis_pi_ed25519.pub" | ssh YOUR_PI_USER@raspberrypi.local 'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys'
```

Add this block to `%USERPROFILE%\.ssh\config` with your username and address:

```sshconfig
Host aegis-pi
    HostName raspberrypi.local
    User YOUR_PI_USER
    IdentityFile ~/.ssh/aegis_pi_ed25519
    ServerAliveInterval 10
```

Test `ssh aegis-pi`. The launchers rely on this alias. Private keys remain outside the repository. Do not disable SSH host-key checking.

## 4. Install AEGIS on the Pi

For a repository downloaded on Windows, transfer just the runtime source without virtual environments or private data. In PowerShell, from the laptop repository:

```powershell
ssh aegis-pi 'mkdir -p ~/AEGIS'
scp -r pi configs scripts aegis-pi:~/AEGIS/
ssh aegis-pi
```

Then in the Pi shell:

```bash
cd ~/AEGIS
bash scripts/setup_pi.sh
.venv/bin/python scripts/verify_environment.py --role pi --output results/reports/pi-environment.json
.venv/bin/python pi/capture_test.py --output data/recordings/first-camera-check.jpg
exit
```

The Pi environment inherits OS camera packages using `--system-site-packages`. Do not pip-install replacements for libcamera/Picamera2. Capture refuses to overwrite files; choose a new filename on repeat runs.

## 5. Open the first live view

Back on the Windows laptop:

```powershell
.\scripts\start_stream.ps1 -Features none
```

Expected: a live image window. The Pi server binds to loopback; the launcher forwards laptop loopback port 8765 over SSH. No router port forwarding is needed. Close with **Q** or the window close button. If PowerShell blocks a script, use a process-only invocation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_stream.ps1 -Features none
```

This does not change machine-wide execution policy. After live video works, complete [calibration](CALIBRATION_GUIDE.md), then start `-Dashboard`.

## Troubleshooting

| Symptom | Check |
|---|---|
| SSH fails | Pi power/network, correct username/address, SSH enabled; try `ssh -v aegis-pi` |
| Camera missing | Power down, check correct connector/ribbon; test OS camera tools before AEGIS |
| Picamera2 import fails | Install OS package and recreate Pi venv with system packages |
| Tk import/display fails | Reinstall Python with Tcl/Tk; run desktop PowerShell, not a headless session |
| Port 8765 busy | Close the existing AEGIS viewer/tunnel; do not start two viewers |
| Calibration missing/mismatch | Complete your own calibration at the same resolution/focus; see calibration guide |
| Waiting for baseline | Slowly translate camera while viewing a fixed, textured scene with depth variation |
| Lost map/rotation gap | Hold a clear original scene steady; recovery is bounded and may fail |

If a launcher was forcibly interrupted, stop its camera server with `ssh aegis-pi 'cd ~/AEGIS && .venv/bin/python pi/stream_control.py stop'`. Check Task Manager for your own abandoned SSH forward only. Normal window closure performs cleanup automatically.
