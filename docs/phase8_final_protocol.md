# Final Phase 8 acceptance protocol

Limits are preregistered in configs/phase8_final_limits.json; hashes and lock time are in results/reports/phase8-final-validation/preregistration.json, before fresh acquisition. Estimator, calibration and limits stay frozen throughout the series. Observer-only status/stop controls are tested before use; their disk overhead is included in receiver processing time. Source JPEGs and final CSVs are the evidence, not live status files.

Scope: controlled research-prototype acceptance, not reliable GPS-denied navigation qualification. Every required operational gate needs sufficient valid evidence. A measured miss is FAIL; missing evidence, an unsuitable reference, or invalid execution is INCONCLUSIVE. Neither counts as PASS. Independent metric accuracy, true north, global metric drift and arbitrary-place recovery remain NOT DEMONSTRATED even if the prototype gates pass. Do not move to Phase 9 on a failed/inconclusive operational series.

Three fresh recordings: 20 seconds stationary; one horizontal 50 mm out-and-back with map-established occlusion and controlled two-second stream pause; one small approximately five-degree turn-and-return. The tilted target remains fixed and fully visible. Trials have their own starting reference; origins are not compared across trials. During rotation keep its excursion approximately 3–8 degrees so the complete pattern stays visible. No protractor is assumed; angles are image-reference checks, not independent truth.

| Gate | Predeclared limit |
|---|---|
| Transport, outside intentional pause | at least 12 received FPS, no unintended connection errors, producer gaps at most 1% |
| Reference suitability | at least 80% of selected samples usable; same ambiguity/sensitivity guards (5 mm / .5 degrees) |
| Stationary false motion | zero translation initializations and rotation updates; p95 LK motion at most .25 pixels; reference center radius at most 5 mm and orientation change at most .5 degrees |
| Horizontal execution | ruler marks 50 mm; reference excursion 40–60 mm, final reference position within 10 mm of start; at least three valid moving samples on each leg |
| Horizontal pose | map established before faults; at least 90% same-map pose availability after initialization outside intentional faults and five-second recovery grace periods |
| Correlated position comparison | one INITIAL map-baseline scale alignment only; RMS at most 5 mm, maximum at most 10 mm, endpoint difference at most 10 mm; map endpoint/peak-excursion ratio at most .25 |
| Rotation execution | reference excursion 3–8 degrees, return within 2 degrees, reference translation at most 15 mm; at least three moving reference samples on each leg |
| Correlated heading comparison | original reference retained/recovered; at least 90% valid original-reference availability outside intentional faults; RMS at most 1 degree, maximum at most 2 degrees, endpoint difference at most 1 degree |
| Recovery | same initialized map and heading reference regained within 5 seconds after clear scene / server resume; no position observations on fully blocked frames; no invented path bridge; heading-only recovery does not pass position recovery |

Recovery is tested only after an initialized map is visibly confirmed in live telemetry. If it never initializes, recovery is INCONCLUSIVE and initialization/continuity fails; do not manufacture a pass from empty tracking or a new arbitrary origin. Occlusion timing uses recorded restored-scene evidence and sampling bounds. Stream-pause timing records command bounds and actual resume acknowledgement. User confirmations/cues are recorded as approximate physical timing, never exact motion timestamps.

At least a short settled hold precedes and follows each movement. Evaluate movement-window reference errors separately from long holds so stationary frames cannot hide bad moving estimates. Deliberate blocked/stale frames and a maximum five-second recovery allowance are excluded only where explicitly logged; unexpected losses remain in availability. If return/angle/visibility is unsuitable, retain the trial and mark execution inconclusive rather than attributing the error automatically to VO.

No limits are tuned after seeing the final results. Any later estimator change starts a new version and requires a new final validation. Existing saved/synthetic tests are regression evidence, not replacements for the fresh series. Conclude with PASS, FAIL or INCONCLUSIVE for each gate plus explicit capability limits; Phase 8 is not declared reliable metric navigation.

## Final validation started — setup adjustment needed
Limits frozen in configs/phase8_final_limits.json; protocol docs/phase8_final_protocol.md; preregistration results/reports/phase8-final-validation/preregistration.json. 76 tests pass. Stationary recording data/validation/final-stationary-20261029-140035: 286 frames, 15.036 FPS, zero connection errors/gaps, zero accepted or rotation-only updates, mean-flow p95 .02771 px. Strict board detector failed all 96 selected samples (zero usable), so reference suitability FAIL and accuracy/stability checks INCONCLUSIVE. Do not declare stationary overall PASS. Raw image inspected: full checkerboard visible, protective surface and bright window nearby; cause of detection failure not established. Need adjust target angle/lighting and verify detector before repeating stationary or starting movements. First server startup failed because rpicam-hello owned camera; closed PID4579 preview, retry succeeded, server stopped cleanly after recording. No horizontal/rotation/fault capture yet, estimator and limits unchanged. User asked to continue final validation; awaiting target adjustment. Preserve failed trial.

## Target check — adjusted view
Saved final-target-check-20261029-140404 (67 frames, 15.193 FPS, no connection errors/gaps). Standard SB detection still fails. Offline diagnostic using SB NORMALIZE_IMAGE|EXHAUSTIVE|ACCURACY detects correct 9x6 pattern on first frame; unchanged planar-reference guards accept it: center sensitivity radius 1.355 mm, orientation sensitivity .1022 degrees, reprojection branch gap 6.358 px. Pattern dimensions correct. This is one-frame suitability evidence only, not final validation. No frozen source/limits modified. Next: explicitly version/preregister offline reference detector flags before new acquisition, then run stationary20s with enough received-span margin (requested20 yielded18.954s of frames previously). Keep estimator/calibration/limits fixed; archive original detector outcomes. User need not reposition further. Stream stopped cleanly. A manually reopened rpicam-hello preview PID4698 was closed to release camera.


## Final stationary repeat completed
{
  "trial": "stationary-repeat",
  "verdict": "PASS",
  "measured": {
    "received_span_s": 22.280999999959022,
    "frames": 336,
    "receive_fps": 15.03523181188529,
    "connection_errors": 0,
    "sequence_gaps": 0,
    "usable_reference_fraction": 1.0,
    "usable_reference_samples": 113,
    "translation_initializations": 0,
    "rotation_updates": 0,
    "flow_p95_px": 0.02462993748486042,
    "reference_radius_from_start_mm": 1.4517933038215765,
    "reference_rotation_from_start_deg_max": 0.0928012046077489
  },
  "limits_file": "configs/phase8_final_limits.json",
  "reference_search_preregistration": "reference-search-v2-preregistration.json",
  "limitations": "Correlated checkerboard reference, not independent metric accuracy. No map/recovery tested.",
  "saved_utc": "2026-10-29T19:08:30.374269+00:00"
}
Next: operator readiness for horizontal 5 cm out/back and initialized-map recovery. No horizontal motion capture started. Stream stopped cleanly. Keep target/camera calibration unchanged.


## Horizontal final trial aborted by operator
Saved data/validation/final-horizontal-20261029-140957 (1001 frames). Measurement setup failed; excluded from acceptance, INCONCLUSIVE execution. Map1 had initialized but no planned fault/recovery or valid out/back demonstrated. Graceful stop saved data and Pi server stopped cleanly. Stationary PASS remains valid if setup/calibration unchanged. Next: secure A/B marks 50mm apart, camera at A, fixed tilted sheet; wait for user readiness before fresh uniquely named horizontal retry and fresh control directory (old horizontal/stop exists).
