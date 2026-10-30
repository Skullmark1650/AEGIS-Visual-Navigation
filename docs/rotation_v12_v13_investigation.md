# Rotation v12/v13: recent anchors and bounded brightness compensation

Production remains landmark-recovery-v8. No production files, calibration, limits, live camera or Pi/API state changed. Both candidates are separate experiment modules. Paired integrity-checked replay covers the same1043unique saved fresh rotation frames; 79production automated tests pass. This is development evidence, not held-out/live validation. Full negative/older rotation regressions were not run because original-reference continuity did not improve; neither candidate is promoted.

## Retention diagnosis

554->560:263source points,201strict passes(76.43%).554->570:225pass both LK status flags,18pass photoerror<5,163passFB<.5,16passall(6.08%); median patch error7.063,95th9.171.554->574:223status,20photo,158FB,17all(6.46%); photo median7.218,p959.513. Thus low photometric consistency is a concrete rejection contributor; the data do not uniquely establish whether exposure, blur, scene motion or mismatches cause it.

861->880:255/287passall(88.85%).861->890:179/287(62.37%);861->892:160/287(55.75%). Lower retention includes status failures and forward/backward inconsistency; it is not literally zero matches. Tests retain original70%source-fraction gate. Full photo/FB percentiles and counts are in rotation-v12/match-diagnostics.json. Source JPEG hashes were rechecked for every diagnostic image; paired full replay provenance is in each fresh-rotation.json.

## V12: recent observed anchors

Keeps up to3recent measured orientation views with5frame spacing. Fallback uses only the same session/epoch, within30producer frames, and unchanged strict image, rotation or nonplanar orientation gates. An older observed source's rotation is composed through its measured camera-to-world matrix, never guessed from an unobserved intermediate image. Result18rotation updates vs22baseline; fallback876. Original epoch resets574and909, original restored940; baseline second reset892. Original-reference availability64.9089%, RMS .573690deg,max4.556115deg unchanged. Delaying a reset in an already different epoch does not repair the original gap. No promotion.

## V13: bounded global brightness offset

Independent candidate, built directly on v8, preserves ordinary fallback first. Uses one global image-median additive correction only when absolute offset is .5-10gray levels, no per-patch fitting, spatial warp or geometry threshold relaxation. Rematching uses the same strict image checks; geometry unchanged. This preprocessing changes the photometric observation model, so unchanged numerical gates alone do not establish unchanged false-positive behavior.

Adds fallback observations877(offset-1)and902(offset-3),21rotation updates overall vs22baseline. Keeps epoch2/root574 through the return instead of resetting a second time at892; original epoch1/root32 still recovered940. One available same-camera sample at902 compares within .1333deg of epoch2's board-derived heading; frame877was not a selected reference, so no error score. This isolated local score does not establish overall accuracy or justify interpolating errors. Overall original-reference availability64.9089%, RMS .573690deg,max4.556115deg remain unchanged.

Local continuity improvement is archived as promising but NOT production-qualified. Main first gap remains; no claim of complete repair, continuous original-reference heading or independent angular accuracy. No map/translation observations added. Future promotion requires negative/old/new rotation controls, explicit brightness/planar-slide adversarial tests and broader error assessment.

## Artifacts / next step

laptop/diagnose_rotation_retention.py; rotation_observed_candidate.py and probe_rotation_observed.py; rotation_brightness_candidate.py and probe_rotation_brightness.py. Results under results/experiments/rotation-v12 and rotation-v13 include fresh-rotation.json, comparison.json, retention diagnostics and local-diagnostics.json. Probe paths refuse overwrites. New experimental results must use fresh output names. Existing v8mapfix remains intact.

Next focus first gap, not another unmeasured threshold sweep: inspect raw554/570/574images and quantify blur/exposure changes; test a separately gated descriptor-based correspondence route if justified, keeping nonplanar identifiability/subset checks and no translation. If testing/promoting v13local benefit, first complete the listed regressions; do not count the second reset reduction as original-heading recovery. No user camera movement required now. Phase8OPEN, initialized-map network recovery and fresh final validation still pending, noPhase9/Pi-only migration.
