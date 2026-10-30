# Calibrated monocular visual odometry

## Start

From Windows PowerShell in the repository:

```powershell
./scripts/start_stream.ps1 -OdometryCalibration results/calibration/phase4-reviewed-camera.json
```

This enables LK tracking and calibrated geometry. The window shows features, pose status, and an X/Z direction sketch. Q or closing the window stops the stream, tunnel, and camera. Use `-DurationSeconds 60` for a short run. Calibration artifacts are local; see phase4_results.md if rebuilding them.

Translate the camera slowly sideways while looking at stationary textured objects at multiple depths. Keep its pointing direction approximately fixed. A single wall, rotation, moving foreground objects, and tiny displacement are poor inputs. Waiting for baseline is expected until sufficient movement accumulates.

## Pipeline

The existing forward/backward LK tracker supplies persistent point IDs. Correspondences are matched to an anchor until median raw-image displacement reaches 12 pixels. New seeds join the next anchor and cannot fabricate earlier correspondences. Geometry corrects coordinates with the reviewed camera matrix and distortion; the displayed image remains raw.

Require at least 30 correspondences. A homography supported by over 85% of points triggers a rotation-model check before translation is rejected. The homography RANSAC threshold is 1.5 pixels. Rotation-only acceptance requires at least 60 points, 90% homography support, convex-hull coverage of at least 10% of the image, median bearing-fit reprojection residual at most .4 pixels, 90% of residuals below 1 pixel, and an angle between .05 and 20 degrees. The bearing rotation is fitted with a proper orthogonal SVD transform. All homography decomposition rotation branches must differ by at most .3 degrees, and the proposed turn must exceed twice their separation. This branch separation is a model-ambiguity check, not a statistical confidence interval. A separate rotation-only probe can run from four pixels of median movement, while two-view translation initialization still waits for twelve pixels. This model is rotation-compatible, not proof of zero translation. Estimate an essential matrix using RANSAC probability .999, a .5-pixel-equivalent normalized threshold, and at most 1000 iterations. Missing or stacked multiple solutions are rejected. RANSAC inliers are then refitted with normalized eight-point geometry and the equal-singular-value essential constraint; at least 90% must retain Sampson support, otherwise the original RANSAC fit is kept. The same refit is applied to the direction-check subsets.

Recover pose using cheirality and a normalized triangulation-distance bound of 1000 (not physical units). Require at least 30 supported points, 60% support, median rotation-compensated ray parallax of .75 degrees, and no more than 20 degrees recovered rotation per estimate. A lower baseline exposed false directions in rendered tests; these conservative gates reduce acceptance and still cannot guarantee correctness.

Accepted translation also passes the v2 disjoint-subset direction gate (see improvements_20261029.md). Accepted transforms accumulate within a segment. With at least 90 retained anchor matches, weak geometry can retry up to sixteen attempts without changing the anchor or integrating a pose. Another attempt requires at least one pixel of median change from the last attempted pair; otherwise `waiting_geometry` preserves state without spending the allowance. The seventeenth failed attempt, insufficient matches, or a tracking/session/gap reset breaks the segment. Baseline waiting preserves the anchor. A rotation-only result updates orientation, declares translation unknown and breaks position continuity; returning to translation starts another local position segment. It does not recover global position after feature loss.

## Coordinates and scale

Camera axes: X right, Y down, Z forward. Relative recovery obeys X_current = R X_anchor + t. Tracking/geometry resets start with camera-to-world orientation Rwc = identity and camera center C = zero. Rotation-only transitions preserve the accepted relative orientation while starting a new local position origin. Update Rwc_new = Rwc_old R.T and C_new = C_old - Rwc_new t. Unit tests check the inverse-transform convention.

After a supported two-view step, at least 50 well-conditioned nonplanar triangulated landmarks can initialize a temporary map. A map starts a new local position segment instead of attaching a new arbitrary scale to older steps. Retained point IDs provide 3D-to-2D PnP, with at least 40 inliers, 70% support, image coverage, positive depth and reprojection checks. LM refinement updates absolute local position/orientation. On well-supported low-residual map poses, newly seeded IDs can be triangulated after at least five frames, .1 local units of camera separation and .75 degrees of ray parallax; reprojection and positive-depth checks protect the existing scale. Seeds expire after 150 producer frames. Insufficient mapped IDs or a failed pose breaks the observed path.

The CSV saves relative R and t direction, accumulated orientation, center, segment, support, parallax, timing, `map_landmarks`, `map_reprojection_px`, `map_reference_frame_id`, `translation_map` and `scale_mode`. `map_tracking` is a fitted pose, not a unit movement event. Within one map, position updates share its initial arbitrary scale. JSON summaries and the dashboard distinguish this from the fallback, whose accepted translations remain independent unit steps. Across resets, segments still have unknown origins and scales; the sketch is not a globally scale-consistent trajectory. It shows no meters, speed, distance traveled, ATE, or RPE. Its viewport rescales automatically.

Up to three frozen image/map keyframes support bounded local recovery after ID loss. Bidirectional keyframe LK, PnP, subpixel-near one-to-one tracker association and two distinct consistent frames are required. Recovery checks run every five producer frames, limit pose change to two local map units / 20 degrees from a keyframe, and use keyframes no older than 900 producer frames. Session/resolution/nonmonotonic-frame resets invalidate them. A recovered map keeps its map_id, origin and scale, but starts a new observed segment at the recovered position so no line crosses the unseen interval. There is still no bundle adjustment, loop-closure optimization, IMU fusion or global place-recognition system. Rotation-only output is explicitly labeled and leaves translation unobserved. Dominant moving objects, distant scenes and planar-scene ambiguity can still mislead the estimator.

## Calibration and verification

Only a numerically passed, visually reviewed real-camera calibration is allowed. Every frame must match profile ID, resolution, manual focus, and lens position within .05. Changes require revalidation. Synthetic calibrations are prohibited for live use.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m laptop.verify_odometry --calibration results/calibration/phase4-reviewed-camera.json --output results/reports/new-odometry-validation.json
```

Choose an unused output path. Projected-point tests use .15-pixel Gaussian noise and 15% mismatches. Rendered textured 3D points separately exercise detection, LK, IDs, anchors, geometry, and accumulation. Synthetic evidence is not real-world ground truth. See phase5_results.md for measured results.

Reference: [OpenCV calibration and 3D reconstruction](https://docs.opencv.org/4.11.0/d9/d0c/group__calib3d.html). Essential-matrix pose recovery returns unit translation direction known only up to scale.

Current measured results and limits: [local-map v4](improvements_v4.md).

Latest rotation/recovery verification: [v5 results](improvements_v5.md).


## Recent-anchor image confirmation (v6)

When already tracking rotation, a failed tracked-point model can be checked against a frozen image anchor no more than 30 producer frames old. Direct 31-pixel/four-level LK must retain at least 60 matches and 70% of source points, patch error below five, bidirectional error below .5 pixels and valid image coordinates. The same bearing residual, support, coverage and homography branch-ambiguity gates then apply. No heading extrapolation or unknown translation is accepted. `rotation_method=photometric_retrack` and corresponding quality fields identify these updates. See [v6 verification and unresolved older interval](improvements_v6.md).


## Heading reference recovery (v7)

After a heading reset, up to three trusted heading images (including the initial reference) can verify reappearance of that local reference. They must share the producer session/image shape and be no more than 1,800 producer frames old. Existing map recovery takes priority. Strict bidirectional image matches feed either the unchanged pure-rotation model or an identifiable nonplanar epipolar model; orientation is retained and translation discarded. Three distinct agreeing frames within 30 producer frames confirm `heading_relocalized`; candidates are `heading_relocalizing`. `heading_epoch` and `heading_reference_frame_id` distinguish local references. Position stays unknown and the unseen interval is never filled. See [v7 evidence and limits](improvements_v7.md).
