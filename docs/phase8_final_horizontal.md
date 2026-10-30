# Final Phase 8 horizontal trial



Recording: data/validation/final-horizontal-redo-20261029-141146. Estimator, calibration and acceptance limits unchanged. Operator confirmed full 50 mm outbound and return moves with fixed target, and full-view occlusion for approximately five seconds at B. Raw JPEG integrity is checked by the offline analyzer.



Transport passed: 1,879 frames at 15.003 FPS, zero producer sequence gaps and zero connection errors. Map 1 initialized at 18.594 s and was lost at 69.860 s during the occlusion interval. The original heading reference returned at 87.875 s (18.015 s after loss; this is NOT restored-view-relative latency). Map 1 never returned. Return motion initialized map 2 at 107.110 s. Heading recovery is not position recovery; independent map origins and scales cannot be joined, so no completed VO loop closure or endpoint drift score is available.



Same-map position recovery FAILS. The planned network pause was deferred because the original map was unavailable; network recovery is INCONCLUSIVE. No source changes or acceptance-limit relaxation were made in response. Phase 8 remains OPEN. The stationary repeat passed; fresh small-angle rotation and initialized-map network testing remain, alongside diagnosis of physical occlusion recovery. Accuracy remains a correlated same-camera comparison, not independent metric navigation qualification.



Detailed board-reference analysis and partial map-1 comparison are recorded in horizontal-redo-analysis.json and horizontal-redo-verdict.json when analysis completes. Intentionally blocked frames must not be treated as ordinary reference-detection failures; separate their windows before any reference availability score. No interpolation fills unseen motion.



Completed reference analysis: 954 usable samples, 25 rejected (includes occlusion). Maximum reference excursion 54.245 mm; final displacement 3.621 mm, within execution limits, but reference endpoint orientation differs by 2.342 degrees, so unintended turning is present. These reference values are not VO accuracy/drift. Partial map1 comparison: {"initial_scale_mm_per_unit": 10.045426519527629, "samples": 513, "rms_mm": 2.5640929679744064, "max_mm": 3.4722077500461266, "note": "Partial pre-occlusion map only; not independent accuracy or completed path validation."}


Reference analysis: 954 usable samples, 25 rejected including occlusion. Excursion54.245mm, final displacement3.621mm; endpoint orientation differs2.342deg, indicating some turning. Not VO accuracy/drift. Partial pre-occlusion map1 correlated comparison:513samples, one initial scale10.0454mm/unit, RMS2.564mm, max3.472mm. Does not validate return or complete trajectory.
