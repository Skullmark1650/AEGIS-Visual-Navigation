# Recovered landmark tracking v8

## Change

Default estimator is landmark-recovery-v8. When frozen map images pass the existing bidirectional LK and PnP checks but fewer than50 old map points coincide with newly seeded tracker corners, recovery can now retain the actual verified current-image map points. It does not enlarge the .75px old-ID association radius or guess landmark identities. At least50 distinct in-bounds verified map observations and the existing two-distinct-frame pose confirmation are required before tracker mutation.

The tracker assigns monotonically fresh IDs to these points, removes nearby unrelated seeds, preserves distant seeds within the300point budget, and begins tracking them on the next image. It never inserts a fabricated previous-frame vector into last_ids/last_current. Mutation happens only after confirmed geometry. Existing associations remain the preferred path when sufficient. Camera/profile, pose gates, expiry/session/resolution checks and final acceptance limits remain unchanged. Stationary keyframe refresh and rotation estimator changes are outside this fix.

## Measured development replay

Full-state paired replay verifies every source JPEG hash, profile and CSV provenance, and advances independent real tracker instances for v7 and v8. Frozen point caches are unsuitable because new points alter subsequent tracking. The baseline uses the new tracker class but never calls its additive adoption method; all existing tracker update behavior is unchanged.

Fresh horizontal recording1879frames: baseline has2map initializations and1051map-tracking frames, fails map1 recovery. V8 has1initialization,1504map-tracking frames,2tentative recovery observations and1confirmed map1 recovery. First trial candidate at1165/76.203s, confirmed1175/76.875s with100PnP inliers and .468px median reprojection residual. Board first fully detected selected clear sample1145/74.860s: recovery2.015s later, with approximately .21s stride timing uncertainty. This is selected clear-board timing, not exact physical uncover time. Original heading/reference and map1 restored; last frame remains map1. No origin bridge fills the lost interval.

One initial board-derived scale10.0454mm/unit, frozen for the remaining comparisons:853shared reference samples,2.370mm RMS,3.472mm max, endpoint discrepancy1.722mm, local endpoint/peak ratio .1345. These are correlated camera/calibration comparisons after fitted scale, NOT independent metric accuracy or live acceptance. Long holds are included, so these all-sample errors do not alone qualify moving accuracy. Physical setup had unintended turning. Development footage is no longer held out.

Fresh rotation1043frames is unchanged against v7:22rotation observations, one original-heading recovery, same epoch gaps. No translation/map is introduced. This fix does not repair rotation geometry.

## Verification and limitations

79automated tests pass. New tests exercise fresh-ID recovery when tracker seeds deliberately do not coincide, blank/wrong scene rejection before mutation, repeated-frame nonconfirmation, continued next-image map tracking, unique IDs/bounded pool, invalid/duplicate coordinates, unchanged historical flow observations, stale references and wrong resolution/session rejection. Existing pose/heading/synthetic controls remain.

Long control replays are recorded separately in v8-stateful-controls.json. Final counts are appended below after completion. No camera, Pi stream, network fault, external API or new user motion was used. The prior final-series result stays failed/inconclusive; this software version requires fresh validation eventually. Physical recovery beyond the tested overlap/age/geometry remains unproven. Phase8 OPEN; noPhase9 or Pi-only migration.

## Artifacts and reproduction

- laptop/replay_stateful.py: paired real-state replay, example: .venv/Scripts/python.exe -m laptop.replay_stateful --recording data/validation/final-horizontal-redo-20261029-141146 --output results/reports/NEW-NAME.json
- results/reports/v8-stateful-horizontal.json and v8-stateful-horizontal-review.json
- results/reports/v8-stateful-rotation.json
- results/reports/v8-stateful-controls.json
- results/backups/improvements-v7/visual_odometry.py: original v7 baseline
- tests/test_recovered_seeds.py and test_odometry.py: adoption and recovery tests

## Completed controls

[
  {
    "recording": "stationary-20261029-000109",
    "frames": 439,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 438
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 438
      }
    },
    "baseline_recoveries": [],
    "candidate_recoveries": []
  },
  {
    "recording": "low-light-20261029-032158",
    "frames": 1793,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 1784,
        "reset_tracking_quality": 8
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 1784,
        "reset_tracking_quality": 8
      }
    },
    "baseline_recoveries": [],
    "candidate_recoveries": []
  },
  {
    "recording": "low-texture-20261029-033007",
    "frames": 1791,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 1185,
        "insufficient_tracks": 2,
        "reset_tracking_quality": 603
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 1185,
        "insufficient_tracks": 2,
        "reset_tracking_quality": 603
      }
    },
    "baseline_recoveries": [],
    "candidate_recoveries": []
  },
  {
    "recording": "feature-loss-20261029-034548",
    "frames": 1791,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 1024,
        "reset_tracking_quality": 766
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 1024,
        "reset_tracking_quality": 766
      }
    },
    "baseline_recoveries": [],
    "candidate_recoveries": []
  },
  {
    "recording": "network-interruption-20261029-035012",
    "frames": 829,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 827,
        "reset_frame_gap": 1
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 827,
        "reset_frame_gap": 1
      }
    },
    "baseline_recoveries": [],
    "candidate_recoveries": []
  },
  {
    "recording": "repeat-path-20261029-035424",
    "frames": 2690,
    "statuses": {
      "baseline": {
        "reset_startup": 1,
        "waiting_baseline": 491,
        "planar_or_rotation": 1,
        "waiting_geometry": 4,
        "low_parallax": 3,
        "accepted": 1,
        "map_tracking": 2182,
        "reset_map_lost": 1,
        "relocalizing": 4,
        "pose_support_failed": 1,
        "relocalized": 1
      },
      "candidate": {
        "reset_startup": 1,
        "waiting_baseline": 490,
        "planar_or_rotation": 1,
        "waiting_geometry": 4,
        "low_parallax": 3,
        "accepted": 1,
        "map_tracking": 2182,
        "reset_map_lost": 1,
        "relocalizing": 5,
        "pose_support_failed": 1,
        "relocalized": 1
      }
    },
    "baseline_recoveries": [
      {
        "frame": 1310,
        "elapsed_s": 85.85900000017136,
        "map_id": 1
      }
    ],
    "candidate_recoveries": [
      {
        "frame": 1310,
        "elapsed_s": 85.85900000017136,
        "map_id": 1
      }
    ]
  }
]

Total paired real-state replay evidence: 12255 unique frames. Stationary/lighting/texture/feature-loss/interruption negative controls retain zero observed positions. Repeated path retains2182map-tracking frames and one map recovery; tentative recovery count changes4to5 and is reported rather than treated as a new observed position. No position observations occur in fresh horizontal frames1070-1144; recovery restores original heading1/root32 and starts segment79 at its observed nonzero map center, leaving a gap from segment4.
