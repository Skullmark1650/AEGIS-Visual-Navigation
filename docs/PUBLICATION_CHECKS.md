# Publication verification

This snapshot was assembled separately from the working installation. Original recordings, calibration evidence, environment reports, local session notes, virtual environments and Git history are excluded. Source, tests, configuration defaults and research descriptions are included.

Local Windows verification with the existing Python 3.12 environment: **84 tests ran; 82 passed and 2 skipped**. The skips require private development image/telemetry evidence. No live Pi trial or cloud API call was performed for this packaging pass. Historical v10 measurements and their limits appear in PHASE8_RESULTS.md.

The actual dashboard was launched with synthetic input and the resulting screenshot visually inspected. Architecture and calibration figures are explanatory diagrams. None depicts an autonomous drone trial or measured room map.

Publication launchers add output-directory creation and a calibration-file preflight, preserving the v10 estimator. A fresh-machine installation has not been performed during packaging. An optional Windows GitHub Actions configuration is supplied as `docs/ci/windows-tests.yml.example`; it is inactive. To enable it later, copy it to `.github/workflows/tests.yml` and push using credentials permitted to update workflows. No hosted CI result is claimed.
