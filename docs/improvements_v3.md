# Rotation, anchor recovery and reference checks — 29 October 2026

## Outcome

Version `rotation-anchor-v3` adds rotation-compatible orientation estimates, bounded retries against the same tracked reference, and explicit checks for unreliable checkerboard references. No new camera movement, Pi configuration change or API request was needed. The current dashboard launcher uses this estimator automatically.

Path continuity improved on the saved repeated-path recording: the paired v2 baseline accepted four translations in four separate segments; v3 accepted ten translations across three segments, with at most five accepted translations in one segment. These are independently scaled unit steps, not a continuous metric trajectory. More accepted estimates do not establish better accuracy. Two translations accepted in the vertical recording cannot be scored reliably with its frontal checkerboard reference.

The saved rotation recording produces one rotation-only estimate, about 1.13 degrees, with no translation step. This is partial turn observation: it does not measure the entire approximate out-and-back turn, or demonstrate heading closure. Full recovery of global camera position remains unresolved.

## What changed

A dominant homography now triggers a conservative calibrated rotation check. A proper orthogonal transform fits unit camera bearings, after homography shape, feature coverage and support checks. Rotation-only output updates orientation but marks translation unknown; it starts a disconnected local position segment. Rotation-compatible image motion cannot rule out hidden translation in a distant or planar scene. The dashboard and local diagnostic rules explain this limitation.

With at least 90 surviving anchor correspondences, failed geometry can retry eight times against that same anchor, allowing more parallax to accumulate. These attempts do not integrate any pose. The ninth failed attempt breaks the segment. Tracker resets, insufficient matches and connection gaps never bridge missing motion. Regression tests verify the retained anchor, one-time integration and bounded failure behavior. This improves short weak-pair recovery; it is not map-based relocalization after complete feature loss.

The checkerboard evaluator now uses both IPPE planar pose hypotheses. Two distinct physical poses with reprojection errors less than .15 pixels apart are ambiguous if their centers differ by more than 5 mm or orientations by more than .5 degrees. Otherwise, sixteen deterministic .15-pixel Gaussian corner perturbations test numerical sensitivity; a maximum center change above 5 mm or rotation change above .5 degrees makes the reference unusable. These engineering thresholds and assumed perturbations are not measured noise, a confidence interval, or independent ground truth. Raw candidate diagnostics remain available rather than being reported as zero error.

The rendered verifier now uses the estimator's recorded anchor frame when calculating synthetic error; deferred anchors must not be confused with the previous attempted frame. CSV schemas remain stable across all estimator statuses and record observation flags plus rotation residual/model diagnostics.

## Paired replay

Every one of the 14,693 JPEGs passed its recorded SHA-256 check. Both estimators received the same LK correspondences and per-frame OpenCV random seed. The previous v2 source was saved under `results/backups/improvements-v2/visual_odometry.py` before editing. Source hashes identify both implementations. Original live measurements and prior improvement reports remain intact.

| Recording | Frames | v2 translations | v3 translations | v3 rotation-only |
|---|---:|---:|---:|---:|
| stationary | 439 | 0 | 0 | 0 |
| horizontal | 886 | 1 | 1 | 0 |
| vertical | 891 | 0 | 2 | 1 |
| rotation | 1792 | 0 | 0 | 1 |
| low-light | 1793 | 0 | 0 | 0 |
| low-texture | 1791 | 0 | 0 | 0 |
| rapid-motion | 1791 | 1 | 1 | 0 |
| feature-loss | 1791 | 0 | 0 | 0 |
| interruption | 829 | 0 | 0 | 0 |
| repeat-path | 2690 | 4 | 10 | 0 |

Stationary, lighting change, low texture, feature loss and interruption still produce no accepted translation or rotation. Horizontal and rapid-motion each retain one accepted translation. Offline mean geometry cost ranges from 0 to .243 ms per recorded frame, including baseline-waiting frames; this is not a new live transport/display benchmark.

## Synthetic regression

Twenty known pure-turn trials cover positive/negative yaw, pitch and roll with .15-pixel coordinate noise. Eighteen accept rotation only; two conservatively reject it. Maximum accepted angular error is .00731 degrees, with zero translation updates. These exact synthetic inputs do not represent hand motion, rolling shutter, exposure changes, or hardware accuracy.

Nine of ten known nonplanar translation trials remain accepted, with maximum rotation error 1.3625 degrees and direction error 13.3446 degrees. Stationary, planar translation and 80%-outlier controls reject translation. The rendered textured-point LK sequence accepts eight poses; maximum rotation error is .5570 degrees and direction error 5.0059 degrees. All 61 automated tests pass.

## Why no real-world accuracy number yet

All 31 detected stationary reference samples and all 63 detected vertical reference samples have near-tied planar hypotheses. Event-specific review initially found five paired references in the repeated path, including a 75.8-degree direction disagreement. The added sensitivity probe finds every one of those reference pairs unusable, so no verified real-world error score can be assigned. This does not prove the VO estimates correct; both the estimator and reference remain possible sources of disagreement. The initial diagnostic report is preserved alongside the stricter review.

Metric scale, global drift, full turn tracking, loop closure and recovery of the original world origin after complete feature loss remain unavailable. The data used here informed development and are not held-out accuracy validation. Phase 9 and standalone Pi migration have not started.

## Next live check

Use the existing printed target, fixed flat and tilted about 20–30 degrees, rather than facing the camera straight on. First check that the reference reports a unique, stable pose. Then record one stationary interval, one slow turn-and-return, and one measured sideways out-and-back while keeping the target fixed. If the reference remains unstable, adjust its angle or distance before recording further motion. Fresh recordings are necessary before claiming improved real-world accuracy.

Start as usual: `./scripts/start_stream.ps1 -Dashboard`. Camera calibration, manual focus and image size are unchanged.

## Artifacts and reproduction

- `results/reports/improvements-v3-replay.json`: paired full-recording replay, source hashes, status counts and pose events.
- `results/reports/improvements-v3-regression-final.json`: synthetic and rendered controls.
- `results/reports/improvements-v3-stationary-reference.json` and `improvements-v3-vertical-reference.json`: ambiguity diagnostics for sampled frontal boards (generated before the later sensitivity addition, which does not change their ambiguity rejection).
- `results/reports/improvements-v3-event-reference.json`: initial two-hypothesis event review.
- `results/reports/improvements-v3-event-reference-reviewed.json`: stricter sensitivity review.

Choose new output paths when repeating these commands; reports refuse overwrite:

```powershell
.\.venv\Scripts\python.exe -m laptop.replay_improvements --baseline results/backups/improvements-v2/visual_odometry.py --output results/reports/NEW-replay.json
.\.venv\Scripts\python.exe -m laptop.review_replay_reference --replay results/reports/NEW-replay.json --output results/reports/NEW-reference.json
```

The dashboard's state logic is tested; no new live-camera UI inspection has been performed in this pass.


## Fresh tilted-target stationary check — 04:32 local

Recording `stationary-20261029-043226` contains 214 verified frames over a 15-second requested run, receive FPS 15.0796, no connection errors or sequence gaps. The live dashboard opened and closed normally; server and tunnel stopped cleanly. Raw frame 165 was visually reviewed: full pattern and surrounding margin visible, no gross blur. User prepared the left-edge-closer target after the 20–30 degree instruction; no independent target angle measurement.

All 16 sampled checkerboard poses passed the hypothesis and sensitivity checks, with zero rejected reference samples. Minimum competing-hypothesis reprojection gap was 4.477 px. Maximum .15-pixel perturbation sensitivity was 2.043 mm / .1433 degrees. Stationary board-derived center spread was .459 / .553 / .629 mm in X/Y/Z; endpoint reference change .268 mm / .02664 degrees. These are image-derived stationary reference checks, not independent navigation accuracy or VO drift.

VO produced zero translation or rotation updates (one startup reset, 213 baseline waits). All 63,900 attempted LK correspondences passed tracker gates. Camera and target were requested stationary; post-record physical confirmation is not yet recorded. Reference now supports proceeding to a fresh short controlled motion test, keeping the tilted sheet fixed.

Artifacts: `results/reports/stationary-20261029-043226-validation.json`, corresponding SVG, source `viewer-20261029-043229.json` report, and raw recording/notes under `data/validation/stationary-20261029-043226`.


## Fresh tilted-target horizontal test — 04:35 local

Operator confirmed both nominal 50 mm moves, ending at A with the target fixed. A 90-second requested run saved 1,336 verified frames at 15.0133 receive FPS, no connection errors, no producer gaps, no tracking resets beyond startup, and weighted LK consistency 99.9759%. All 91 selected board poses passed reference gates; maximum perturbation sensitivity 2.304 mm / .1626 degrees.

The estimator accepted one translation, after one deferred pose-support failure, at elapsed 30.375 seconds (frame 481, anchor 40). Compared with the shared-calibration board reference, rotation difference was .2275 degrees and signed direction difference .8360 degrees over a reference baseline of 32.192 mm. These describe one partial movement estimate, not the full nominal 50 mm leg or independent accuracy.

The return was not reconstructed as an accepted pose: 1,333 frames waited for baseline. No continuous out-and-back path or VO loop-closure score exists. The board-derived final-versus-start difference was 8.087 mm / 1.1297 degrees; it must not be called VO drift, nor used to override the operator's position confirmation. Direction reference is now usable, but pose availability remains the immediate limitation.

Recording/camera/tunnel shut down cleanly. No estimator thresholds changed during this trial. Artifacts: `results/reports/horizontal-20261029-043504-validation.json`, SVG and `improvements-v3-horizontal-review.json`; raw images and operator notes under the matching recording directory. Next fresh test is a slow turn-and-return with the tilted target fixed.


## Fresh tilted-target rotation test — 04:39 local

Operator confirmed the approximate right turn and return, original direction restored and target fixed. A 90-second requested run saved 1,341 verified frames at 15.0061 receive FPS, zero connection errors/producer gaps and 99.9059% weighted LK consistency. No tracking reset beyond startup and no accepted translation step occurred. The camera/server/tunnel stopped cleanly.

Two rotation-only increments were accepted: 1.2022 degrees at elapsed 26.250 s (frame 419, anchor 413, segment 7), and 1.2273 degrees at 35.312 s (frame 555, anchor 551, segment 10). They belong to different segments and cannot be summed into a total turn or return/heading closure score. Other statuses: 1,248 baseline waits, 86 planar-or-rotation rejections, two support failures and two low-parallax rejections. This remains partial orientation tracking, not the complete turn-and-return trajectory.

Reference detection succeeded for 77 sampled frames and failed for 14; every detected pose passed the reference ambiguity/sensitivity gates. However, all four exact anchor/current images for the accepted orientation events lack a detected checkerboard, so neither increment has a reference error score. Raw frame 419 was visually reviewed: most of the target has moved outside the left image boundary. This explains missing reference coverage at that event, and prevents an angular accuracy claim. Reference endpoint change where the board is visible again was 1.416 mm / 2.0969 degrees, a correlated board-derived check, not VO drift or a contradiction of the operator's approximate direction confirmation.

Artifacts: `rotation-20261029-043945-validation.json` and SVG, `improvements-v3-rotation-review.json`, and raw frames/operator notes in the matching recording directory. No estimator thresholds changed during the three fresh tests. Planned physical testing is complete; use these saved images for baseline/rotation rejection investigation before requesting another physical test.
