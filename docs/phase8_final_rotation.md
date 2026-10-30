# Final Phase 8 rotation trial

Saved data/validation/final-rotation-20261029-141705: 1,043 frames at14.996FPS, no sequence gaps or connection errors. All367 sampled checkerboard references usable. Operator confirmed full target visibility and return.

Execution INCONCLUSIVE for acceptance: the correlated reference measured8.937 degrees of turn (requested3-8) and22.792mm maximum camera translation (limit15mm); final direction was .532degrees from initial. The trial exceeded pure-turn protocol limits despite the intended pivot, so do not attribute all failures to prescribed pure rotation or silently relax limits.

Diagnostic tracking gaps remain: heading epoch1/root32 switched at36.813s to epoch2/root574, then58.016s to epoch3/root892; original epoch1/root32 restored61.204s. Upper bound on original-reference availability64.9%, below90% even counting stale held states.22 rotation updates, one heading relocalization, zero translations. No original-reference continuity through the gap.

Correlated comparison in original-reference states only:233samples, .574degrees RMS,4.556degrees max; endpoint .054degrees.17 diagnostic moving samples RMS1.853degrees (adjacent-reference change>.1deg, explicitly exploratory; holds must not hide motion errors). Not independent angular accuracy. Excluded epochs were not realigned; recovered endpoint does not reconstruct missing motion.

Results and traces: results/reports/phase8-final-validation/rotation-analysis.json and rotation-verdict.json. Camera/receiver stopped cleanly. Phase8 remains OPEN: stationary PASS, horizontal same-map recovery FAIL, rotation execution INCONCLUSIVE with observed tracking gaps, network recovery untested. Diagnose saved physical-occlusion and rotation data before requesting another movement test. Any estimator change needs new-version acceptance validation. No Phase9 or Pi-only migration started.
