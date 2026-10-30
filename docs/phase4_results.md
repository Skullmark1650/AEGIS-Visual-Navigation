# Phase 4 camera calibration results

Measured on 2026-10-28 local time (fit timestamp 2026-10-29T03:42:35.810216+00:00). Phase 4 is complete for research use with the recorded camera profile. Phase 5 has not started.

## Dataset and focus

All 25 real camera images in `data/calibration/session-20261028-211233` were retained. SHA-256 integrity, matching camera geometry/focus settings, 640 x 480 resolution, fresh checkerboard detection, image quality, and distinct-view checks passed for every image. No views were removed and no thresholds were relaxed. The target has 9 x 6 internal corners (54 points); the user measured five squares at 100 mm, giving 20 mm per square. User estimates of distance and tilt are recorded separately in `operator_notes.json`; they are not measured ground truth.

The IMX708 uses manual lens position 2.0, BGR888, raw 1536 x 864 BGGR_PISP_COMP1, identity transform, and crop [1152,432,2304,1728]. Profile ID: `382c33be218c54383b037e40b1f7942bcb11c65bed62c40d06279533606460f4`. Sixty metadata frames before restart and sixty after restart each reported lens position exactly 2.0 with the same geometry profile (see `results/reports/phase4-focus-before-restart.json` and `phase4-focus-after-restart.json`). This establishes reported focus control stability, not independent physical lens metrology.

Saved images cover 8 of 9 center regions, have a linear size ratio of 2.787, and maximum fitted board tilt 52.19 degrees. Fitted tilt is model-derived, not an operator measurement.

## Method and measured accuracy

OpenCV 4.12.0 pinhole calibration with five distortion coefficients. Intrinsics were fitted on 20 images; views 1, 6, 11, 16, and 21 were held out. Those five images were used only to fit their individual board poses with fixed intrinsics and distortion. The released reviewed artifact retains this 20-view fit so the reported holdout evaluation corresponds to the actual parameters; it is not an all-25-view refit.

- Training RMS: **0.404009 pixels**, threshold 1.0.
- Mean held-out per-view RMS: **0.387437 pixels**, threshold 1.0.
- Worst individual view: **0.625433 pixels**, view 24, threshold 1.5.
- Numerical checks: passed; no warnings.
- All 30 automated tests passed, including synthetic known-parameter recovery, held-out evaluation, source preservation, focus/profile mismatch rejection, duplicate rejection, safe resume/integrity checks, and undistortion provenance checks. Synthetic tests are software verification, separate from these real-camera measurements.

Camera matrix in pixels:

```text
[973.5994788955328, 0.0, 291.4574285348106]
[0.0, 971.286546745171, 236.59395050017164]
[0.0, 0.0, 1.0]
```

Distortion [k1, k2, p1, p2, k3]:

```text
[0.03711729087340731, 0.32390669777977427, -0.0005628576811965002, -0.013187569697081302, -2.0066047912977805]
```

## Visual review and artifacts

Raw/undistorted previews were inspected for view 12 (upper-left tilted board) and view 23 (close board). There was no obvious gross warping or foldover; the correction was modest, with black borders expected when retaining the original camera matrix. Qualitative inspection does not independently validate lens distortion or spatial accuracy.

- Original fit with review gate: `results/calibration/phase4-real-camera.json`.
- Reviewed artifact: `results/calibration/phase4-reviewed-camera.json`, with review evidence and matching-profile restriction.
- Previews: `results/calibration/phase4-preview-upper-left.png` and `phase4-preview-close.png`.
- Original image hashes and source filenames are embedded in both calibration artifacts.

Generated images, calibration parameters, and machine reports remain local under ignored data/results paths. This document preserves the measured summary in the repository.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m laptop.camera_calibration fit --dataset data/calibration/session-20261028-211233 --output results/calibration/new-fit.json --square-mm 20
.\.venv\Scripts\python.exe -m laptop.camera_calibration preview --dataset data/calibration/session-20261028-211233 --calibration results/calibration/new-fit.json --view view-0012.png --output results/calibration/new-preview.png
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Output paths must be unused. To resume capture, run `scripts/start_calibration.ps1 -Dataset data/calibration/session-20261028-211233 -Resume`. Resume verifies existing images and settings before appending.

## Limits and phase boundary

Residuals measure how consistently the model explains detected checkerboard points. They do not establish navigation accuracy, absolute distance accuracy, or flight readiness. Held-out poses still use the held-out corners. Printed-target flatness, printer geometry, corner localization, JPEG artifacts, and hand movement can introduce systematic error. Intrinsic standard deviations in the JSON are linearized estimates, not a complete uncertainty budget. Higher radial coefficients may be weakly constrained outside the observed board regions; avoid treating them as independently measured lens properties.

Use this calibration only at the recorded resolution, focus, crop, and camera configuration. Changes require profile verification and potentially recalibration. Future tracking/odometry must explicitly apply the reviewed calibration; existing live feature/flow modes have not been silently switched to corrected coordinates. No odometry, trajectory scale claim, or Phase 5 work was performed.

## Per-view residuals

| View | Split | RMS (pixels) |
|---|---|---:|
| 1 | holdout | 0.2702 |
| 2 | train | 0.1511 |
| 3 | train | 0.1519 |
| 4 | train | 0.1440 |
| 5 | train | 0.3768 |
| 6 | holdout | 0.3666 |
| 7 | train | 0.5147 |
| 8 | train | 0.5565 |
| 9 | train | 0.3075 |
| 10 | train | 0.4257 |
| 11 | holdout | 0.4847 |
| 12 | train | 0.3656 |
| 13 | train | 0.3469 |
| 14 | train | 0.4785 |
| 15 | train | 0.2547 |
| 16 | holdout | 0.2322 |
| 17 | train | 0.3523 |
| 18 | train | 0.4565 |
| 19 | train | 0.3053 |
| 20 | train | 0.3383 |
| 21 | holdout | 0.5834 |
| 22 | train | 0.5795 |
| 23 | train | 0.5749 |
| 24 | train | 0.6254 |
| 25 | train | 0.2448 |
