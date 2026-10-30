# PROJECT: AEGIS — AI-Enhanced GPS-Denied Visual Navigation System

## 1. Project Overview

**Project Name:** AEGIS (Autonomous Estimation, Guidance, and Intelligent Sensing)

**Project Type:** Computer Vision, Robotics, Aerospace Engineering, Edge Computing, and Artificial Intelligence

**Primary Objective:**

Design, develop, test, and document a camera-based navigation system capable of estimating its own motion and trajectory without GPS, using a Raspberry Pi 5, Raspberry Pi Camera Module 3, and a Windows laptop.

The system must progressively evolve from basic camera capture and optical flow into a functioning monocular visual-odometry system with live trajectory visualization, uncertainty estimation, and optional AI-assisted environmental analysis.

The project should demonstrate proficiency in:

- Python software engineering
- Raspberry Pi hardware integration
- Computer vision and image processing
- Optical flow and feature tracking
- Camera calibration
- Linear algebra and 3D geometry
- Visual odometry and motion estimation
- Machine learning and AI integration
- OpenAI and Anthropic Claude APIs
- Edge computing and distributed systems
- Real-time data processing
- Engineering validation and experimental design
- Git, GitHub, documentation, and reproducible development

This is intended to become a serious engineering portfolio project suitable for demonstrating technical proficiency to aerospace engineering professors, research teams, and potential employers.

The project should prioritize technical correctness, measurable performance, and working software over flashy but unreliable demonstrations.

---

# 2. My Background and Available Hardware

I am an undergraduate aerospace engineering student at the University of Kansas.

I have experience with engineering mathematics, physics, MATLAB, and some programming, but I want detailed guidance when implementing unfamiliar software architectures, computer vision algorithms, and AI systems.

### Available hardware

**Raspberry Pi 5**
- Runs Raspberry Pi OS, exact version to be verified.
- Has Raspberry Pi Connect configured and working.
- Can be accessed remotely from my laptop.
- Has Wi-Fi connectivity.
- Has no additional sensors, motor controllers, or robotics hardware.

**Raspberry Pi Camera Module 3**
- 12-megapixel Sony IMX708 image sensor.
- Autofocus capability.
- Connected to the Raspberry Pi through its CSI camera interface.
- Can capture images and video.

**Main laptop**
- Windows operating system.
- Intel Xeon processor.
- NVIDIA RTX A2000 GPU.
- Used for software development, visualization, AI processing, and computationally intensive operations.

**Additional resources**
- Internet access.
- Python and freely available open-source libraries.
- OpenAI and/or Anthropic APIs if configured.
- GitHub for version control and documentation.

### Hardware constraints

Do not assume I own an IMU, GPS receiver, LiDAR, depth camera, drone, robot, motor, display, or any other additional equipment.

The first working version must use only the equipment listed above.

Any additional hardware should be optional and clearly identified as a future upgrade.

---

# 3. Your Role as the AI Development Assistant

Act as a multidisciplinary engineering development team consisting of:

1. Senior Python Software Engineer
2. Computer Vision and Visual Odometry Engineer
3. Robotics and Navigation Engineer
4. Aerospace Guidance, Navigation, and Control Engineer
5. Machine Learning Engineer
6. Raspberry Pi and Linux Systems Engineer
7. Technical Documentation and Testing Engineer

Your responsibility is to guide the project from initial setup to a fully documented and validated prototype.

### Working requirements

- Provide detailed, technically correct instructions.
- Explain the purpose of major components and algorithms.
- Generate complete, functional code rather than isolated snippets when implementing files.
- Clearly state which computer executes each command.
- Identify file paths and required dependencies.
- Prefer modular, maintainable software architecture.
- Include error handling, logging, and configuration management.
- Never claim a feature works without testing evidence.
- Do not invent benchmark results, hardware capabilities, or experimental measurements.
- Ask for necessary environment information before making platform-specific assumptions.
- Distinguish established engineering methods from experimental AI capabilities.
- Avoid unnecessary paid services.
- Prefer local processing when practical.
- Never expose API keys or credentials in source code.
- Avoid making large architectural changes without explaining the reason.
- Maintain a clear record of development progress, outstanding problems, and next steps.

When I encounter errors, help diagnose their underlying cause rather than repeatedly suggesting random fixes.

When implementing a feature, provide a way to test that feature before continuing.

---

# 4. Target System Architecture

The project will use a distributed architecture with two primary computing devices.

## Raspberry Pi 5 — Edge Sensing Node

Responsibilities:

- Interface with Camera Module 3.
- Capture video frames.
- Timestamp captured frames.
- Apply optional image preprocessing.
- Stream camera frames to the laptop.
- Record raw or compressed image data.
- Monitor camera and system health.
- Support configurable resolution and frame rate.
- Recover gracefully from temporary network interruptions.

Primary technologies:

- Python
- Picamera2
- libcamera
- NumPy
- OpenCV where compatible
- Network communication using an appropriate transport protocol

## Windows Laptop — Navigation Processing Node

Responsibilities:

- Receive camera frames.
- Perform camera calibration and image undistortion.
- Detect and track visual features.
- Calculate optical flow.
- Estimate relative camera motion.
- Accumulate trajectory estimates.
- Visualize tracking and navigation results.
- Save telemetry and experimental logs.
- Run machine learning models where useful.
- Integrate optional AI analysis through OpenAI or Claude.

Primary technologies:

- Python
- OpenCV
- NumPy
- SciPy
- Matplotlib or another suitable visualization framework
- PyTorch or ONNX Runtime when justified
- OpenAI and Anthropic SDKs for optional AI features

### Communication

Both devices should initially operate on the same local Wi-Fi network.

The communication system should support:

- Frame identifiers
- Capture timestamps
- Frame transmission
- Detection of dropped frames
- Latency measurements
- Connection recovery
- Adjustable video quality

Prefer a simple and reliable implementation initially, such as an HTTP/MJPEG stream or another appropriately justified solution.

Do not introduce ROS 2, complex message brokers, or distributed orchestration until the simpler architecture is working and there is a demonstrated reason to upgrade.

---

# 5. Development Roadmap

The project must be implemented in phases.

Each phase should have:

- Objectives
- Required software
- Files to create or modify
- Implementation instructions
- Expected behavior
- Test procedures
- Acceptance criteria
- Common failure cases
- Documentation requirements

Do not proceed to the next phase until the current phase is working or I explicitly authorize moving forward.

## PHASE 0 — Environment Setup and Verification

Objectives:

1. Verify Raspberry Pi OS version and architecture.
2. Verify Python version.
3. Verify Camera Module 3 connectivity.
4. Verify the laptop's Python environment.
5. Verify network connectivity.
6. Establish a Git repository.
7. Configure a convenient remote development workflow.

Recommended workflow:

- VS Code on Windows.
- Remote SSH to Raspberry Pi.
- Separate Python environments for Pi and Windows.
- Raspberry Pi Connect for graphical troubleshooting.
- Git for version control.

Important: Raspberry Pi Connect is already configured and working.

Use Raspberry Pi OS-supported installation methods for Picamera2 and libcamera. Do not assume installing Picamera2 into an arbitrary pip environment is reliable.

Verify camera operation using the supported `rpicam-*` utilities or equivalent tools for the installed OS version.

Deliverables:

- Working development environments.
- Verified camera capture.
- Git repository.
- Initial README.
- Dependency documentation.
- Environment verification script.

Acceptance criteria:

The Pi successfully captures and saves an image from Camera Module 3.

The laptop can access the Pi remotely and run development commands.

## PHASE 1 — Live Camera Streaming

Objective:

Transmit live camera video from the Pi to the laptop.

Requirements:

- Capture frames using Picamera2.
- Provide adjustable capture resolution.
- Provide configurable target FPS.
- Stream video across the local network.
- Display received video on the laptop.
- Measure received FPS and transmission latency.
- Handle connection failures.

Initial target:

640 × 480 resolution at approximately 15–30 FPS, depending on measured performance.

Deliverables:

- Raspberry Pi camera server.
- Windows camera client.
- Configuration files.
- FPS and latency monitoring.
- Basic logging.

Acceptance criteria:

The laptop displays a stable live video feed from the Raspberry Pi.

Measured performance is documented rather than assumed.

## PHASE 2 — Feature Detection

Objective:

Identify distinctive visual features in incoming camera frames.

Implement and compare appropriate methods, beginning with:

- Shi-Tomasi corner detection
- ORB feature detection

Explain:

- What makes a feature trackable.
- Why corners are often useful.
- How lighting affects feature detection.
- Why low-texture surfaces cause problems.
- How feature detector parameters affect performance.

Visualize detected features as colored markers on the live video.

Track and log:

- Number of detected features.
- Feature distribution across the image.
- Detection processing time.
- Detection failures.

Acceptance criteria:

The system reliably detects and displays visual features in a textured indoor environment.

## PHASE 3 — Optical Flow Tracking

Objective:

Track how visual features move between consecutive frames.

Begin with pyramidal Lucas-Kanade sparse optical flow.

Implement:

- Previous-frame storage.
- Feature tracking between frames.
- Optical flow vector visualization.
- Tracking quality checks.
- Feature replacement when tracking quality declines.
- Forward-backward consistency checks where useful.

Explain the underlying mathematical concepts, including:

- Image intensity constancy.
- Spatial image gradients.
- Temporal image gradients.
- Optical flow constraints.
- Lucas-Kanade assumptions.
- Image pyramids.

Record:

- Number of successfully tracked features.
- Tracking success percentage.
- Average optical flow magnitude.
- Processing time.
- Dropped-frame statistics.

Acceptance criteria:

When the camera moves, the display shows feature points and their corresponding optical flow vectors.

The system should demonstrate meaningful differences between translation, rotation, and stationary camera behavior, without incorrectly claiming that optical flow alone fully distinguishes these motions.

## PHASE 4 — Camera Calibration

Objective:

Estimate the camera's intrinsic parameters and lens distortion.

Use a printed checkerboard or another suitable calibration target.

Implement:

- Calibration image capture.
- Corner detection.
- Intrinsic camera matrix estimation.
- Lens distortion estimation.
- Reprojection error measurement.
- Calibration parameter storage.
- Image undistortion.

Explain:

- Focal length in pixel coordinates.
- Principal point.
- Radial distortion.
- Tangential distortion.
- Camera coordinate systems.
- Why calibration is important for visual odometry.

Important:

Camera Module 3 autofocus can change the camera's optical characteristics. Establish a consistent focus configuration for calibration and subsequent experiments.

Acceptance criteria:

The system produces a saved camera calibration file and reports reprojection error.

## PHASE 5 — Monocular Visual Odometry

Objective:

Estimate relative camera motion from successive camera images.

Implement a basic calibrated monocular visual-odometry pipeline.

Suggested steps:

1. Detect or track corresponding image features.
2. Reject unreliable correspondences.
3. Estimate the essential matrix using a robust method such as RANSAC.
4. Recover relative camera rotation and translation direction.
5. Maintain a consistent coordinate convention.
6. Accumulate relative camera poses.
7. Visualize the resulting trajectory.
8. Detect and report estimation failures.

Relevant mathematical concepts:

- Pinhole camera model.
- Homogeneous coordinates.
- Rotation matrices.
- Translation vectors.
- Epipolar geometry.
- Fundamental matrix.
- Essential matrix.
- RANSAC.
- Coordinate transformations.
- Rigid-body transformations.
- SE(3).

Critical technical limitation:

A single monocular camera cannot generally recover absolute translation scale from arbitrary image sequences alone.

Do not report estimated translation in meters unless a valid scale source has been introduced.

For initial trajectory visualization, use explicitly labeled arbitrary-scale units.

Investigate scale recovery through:

- Known-size calibration targets.
- Known-distance experimental motion.
- Known planar geometry under appropriate assumptions.
- Additional sensors in future hardware upgrades.

Do not treat normalized translation vectors as measured physical displacement.

Acceptance criteria:

The system estimates relative orientation and translation direction for suitable camera movements.

It visualizes a trajectory while clearly documenting scale ambiguity, drift, and failure conditions.

## PHASE 6 — Navigation Dashboard

Objective:

Build a graphical monitoring interface.

Required displays:

- Live camera feed.
- Tracked feature overlay.
- Optical flow visualization.
- Estimated camera trajectory.
- Current orientation estimate.
- Tracking status.
- Feature count.
- Processing FPS.
- Network latency.
- Dropped frames.
- System warnings.

Recommended design:

A mission-control-inspired engineering dashboard with a clean, professional dark interface.

Possible technologies:

- PyQt6
- Plotly Dash
- Streamlit for an initial prototype

Choose the simplest option that supports the required performance.

The dashboard must clearly distinguish measured values, estimates, and simulated or illustrative data.

Acceptance criteria:

The system can be operated and monitored from the laptop without requiring direct interaction with the Pi.

## PHASE 7 — AI Integration

Objective:

Add meaningful AI capabilities to the navigation system.

Do not use an LLM as the primary real-time visual-odometry algorithm.

Instead, implement an AI assistant that can analyze navigation data and explain system behavior.

### Capability A — AI Scene Analysis

Use an OpenAI or Anthropic vision-capable model to analyze selected camera images.

Possible tasks:

- Describe the environment.
- Identify useful visual landmarks.
- Explain low-texture conditions.
- Identify possible tracking obstacles.
- Recommend experimental improvements.

### Capability B — Navigation Diagnostics

Allow the AI assistant to inspect structured telemetry such as:

- Feature counts.
- Tracking failure rates.
- Estimated pose changes.
- Network latency.
- Frame rate.
- System logs.

Example user query:

"Why did tracking fail during the last 10 seconds?"

The assistant should inspect the relevant data and provide an evidence-based explanation.

### Capability C — AI Engineering Assistant

Implement controlled tool-calling capabilities that allow the assistant to:

- Read navigation logs.
- Retrieve recent telemetry.
- Retrieve selected camera frames.
- Summarize experiments.
- Compare test runs.
- Generate diagnostic reports.
- Suggest configuration adjustments.

Tools must be explicitly allowlisted.

Any action that changes configuration or executes system commands must require appropriate authorization.

Never allow unrestricted shell execution from untrusted model output.

### Capability D — Automated Experiment Reports

Generate reports containing:

- Experiment configuration.
- Test conditions.
- Performance metrics.
- Tracking failures.
- Accuracy estimates when ground truth exists.
- Plots.
- AI-generated observations.
- Recommended next experiments.

All generated interpretations must be clearly distinguished from measured results.

### AI API requirements

- Support OpenAI and/or Anthropic.
- Store API keys in environment variables.
- Never commit secrets to Git.
- Include configurable API usage limits.
- Avoid sending unnecessary images.
- Document privacy and data handling.
- Provide a local-only mode that does not require API access.
- Record model identifiers and relevant configuration for reproducibility.

Acceptance criteria:

The AI assistant can explain at least one documented navigation failure using real telemetry and, where appropriate, selected images.

## PHASE 8 — Engineering Validation

Objective:

Evaluate the system quantitatively.

Create controlled experiments for:

1. Stationary camera.
2. Horizontal translation.
3. Vertical translation.
4. Rotation.
5. Low-light conditions.
6. Low-texture environments.
7. Rapid camera motion.
8. Temporary feature loss.
9. Network interruption.
10. Repeated motion along a known path.

When practical, measure ground truth using known distances, angles, and fixed reference markers.

Evaluate:

- Processing FPS.
- End-to-end latency.
- Feature tracking success rate.
- Pose-estimation success rate.
- Relative rotation error.
- Trajectory drift.
- Translation-direction error.
- Scale error only when scale is recoverable.
- Recovery time following tracking failure.
- CPU and memory utilization.

If using standard visual-odometry metrics such as Absolute Trajectory Error or Relative Pose Error, explain the required trajectory alignment, scale assumptions, and ground-truth requirements.

Avoid reporting accuracy percentages without a meaningful definition.

Deliverables:

- Repeatable testing scripts.
- Experimental datasets.
- Evaluation plots.
- Results tables.
- Known limitations.
- Technical report.

## PHASE 9 — Advanced Extensions

Only begin after the core navigation system has been demonstrated and validated.

Potential extensions:

### A. Visual SLAM

Explore map creation, keyframes, loop closure, and pose optimization.

Consider ORB-SLAM3 or another suitable implementation.

### B. Deep Learning-Based Depth Estimation

Evaluate monocular depth-estimation models.

Explain the distinction between relative depth and metric depth.

### C. Visual-Inertial Navigation

If an IMU is purchased later, investigate sensor fusion using an extended Kalman filter or another appropriate estimator.

### D. Drone Navigation Simulation

Integrate the visual navigation system into a simulated drone or robotics environment.

Evaluate navigation in GPS-denied conditions.

### E. Aerospace Landing Navigation

Investigate visual navigation concepts relevant to planetary landing, terrain-relative navigation, and spacecraft guidance.

Clearly distinguish a research prototype from a flight-qualified navigation system.

---

# 6. Suggested Repository Structure

Use the following as an initial reference architecture, adjusting it when justified:

```text
AEGIS/
|
|-- README.md
|-- LICENSE
|-- .gitignore
|-- docs/
|   |-- architecture.md
|   |-- setup.md
|   |-- calibration.md
|   |-- experiments.md
|   |-- ai_integration.md
|
|-- pi/
|   |-- camera_server.py
|   |-- camera_config.py
|   |-- system_monitor.py
|   |-- requirements.txt
|
|-- laptop/
|   |-- camera_client.py
|   |-- feature_detector.py
|   |-- optical_flow.py
|   |-- camera_calibration.py
|   |-- visual_odometry.py
|   |-- trajectory.py
|   |-- dashboard.py
|   |-- requirements.txt
|
|-- ai/
|   |-- assistant.py
|   |-- diagnostics.py
|   |-- tools.py
|   |-- report_generator.py
|
|-- configs/
|   |-- default.yaml
|   |-- camera.yaml
|
|-- tests/
|   |-- test_camera.py
|   |-- test_tracking.py
|   |-- test_odometry.py
|   |-- test_network.py
|
|-- scripts/
|   |-- setup_pi.sh
|   |-- setup_windows.ps1
|
|-- data/
|   |-- calibration/
|   |-- recordings/
|   |-- telemetry/
|
|-- results/
|   |-- plots/
|   |-- reports/
|
|-- .env.example
```

The repository should be designed so that code can be tested independently using prerecorded videos or synthetic data without requiring the physical Pi to be connected.

Keep large recordings, secrets, and generated files out of Git unless intentionally included.

---

# 7. Software Engineering Standards

All code must follow reasonable professional software development practices.

Requirements:

- Clear module boundaries.
- Descriptive names.
- Python type hints where useful.
- Docstrings for important functions.
- Configurable parameters.
- Structured logging.
- Graceful shutdown.
- Input validation.
- Exception handling.
- Unit tests.
- Integration tests.
- Reproducible dependency installation.
- Cross-platform compatibility where applicable.

Use Git commits at meaningful milestones.

When modifying existing files, inspect their current contents before replacing them.

Avoid introducing dependencies that are not needed.

For algorithms, explain major mathematical assumptions and coordinate conventions.

Use standard libraries and established implementations where practical instead of unnecessarily reinventing mature algorithms.

---

# 8. Documentation and Portfolio Requirements

The completed project should include a professional GitHub repository.

Required documentation:

- Project overview.
- Engineering motivation.
- System architecture diagram.
- Hardware specifications.
- Installation guide.
- Operating instructions.
- Algorithm explanations.
- Camera calibration procedure.
- Mathematical background.
- Performance measurements.
- Experimental methodology.
- Known limitations.
- Future development roadmap.

Include screenshots, demonstration videos, and plots when available.

Maintain a development log describing:

- What was implemented.
- Why technical decisions were made.
- Problems encountered.
- How problems were solved.
- What was learned.
- What remains incomplete.

### AI Development Transparency

Because one of my goals is demonstrating proficiency with AI-assisted engineering, document how OpenAI, Claude, or other AI systems were used.

Distinguish between:

- AI-generated code.
- Human-reviewed code.
- AI-assisted debugging.
- AI-assisted research.
- Independently verified results.
- AI-powered features integrated into the final system.

The portfolio should demonstrate that I understand the engineering and can explain the system, not merely that an AI generated it.

---

# 9. Project Success Criteria

The minimum viable project is successful when:

1. The Raspberry Pi Camera Module 3 captures live video.
2. Video streams successfully to the Windows laptop.
3. OpenCV detects and tracks visual features.
4. Optical flow vectors are displayed in real time.
5. Camera calibration has been completed.
6. Relative camera motion can be estimated under suitable conditions.
7. An estimated trajectory can be visualized.
8. Tracking failures are detected and reported.
9. The system produces meaningful performance measurements.
10. The project is documented and reproducible.

The advanced project is successful when:

1. An AI assistant can inspect real navigation telemetry.
2. The assistant can explain documented failure conditions.
3. The dashboard provides live navigation diagnostics.
4. Experiments demonstrate repeatable performance.
5. The project includes a professional technical report.
6. The GitHub repository clearly demonstrates software engineering, AI integration, and aerospace-relevant technical skills.

Do not sacrifice correctness to meet these criteria.

---

# 10. How I Want You to Work With Me

Use an incremental development workflow.

For each phase:

**Step 1 — Explain**

Describe what we are building, why it matters, and how it works.

**Step 2 — Prepare**

Identify dependencies, commands, configuration, and file locations.

**Step 3 — Implement**

Provide complete code and instructions for creating or modifying the required files.

**Step 4 — Test**

Give me specific commands to verify the implementation.

**Step 5 — Troubleshoot**

If something fails, investigate the error and provide targeted corrections.

**Step 6 — Document**

Update the project documentation and development log.

**Step 7 — Review**

Summarize what was accomplished and what comes next.

Do not overwhelm me by attempting to implement every phase simultaneously.

Do not skip tests simply because the code appears correct.

When possible, provide both a simple explanation and a more technical engineering explanation.

Treat this as an actual research and development project.

---

# 11. Instructions for Starting the Project

Begin with Phase 0.

First, ask me only the essential questions needed to verify my development environment, including:

- Raspberry Pi OS version.
- Raspberry Pi Python version.
- Camera connectivity.
- Laptop development tools.
- Preferred AI API provider, if needed later.

Do not assume these details are already known.

Then:

1. Explain the initial system architecture.
2. Provide the exact commands for verifying my Raspberry Pi environment.
3. Help me configure VS Code Remote SSH if needed.
4. Help me verify Camera Module 3 functionality.
5. Create the initial project repository structure.
6. Implement a minimal camera capture test.
7. Verify that the first test works before moving to Phase 1.

**Begin by guiding me through the first practical setup steps. Do not generate the entire project at once.**