# Fresh v10 limited-prototype validation

## Frozen scope and evidence

Frozen retained-map-recovery-v10tested under phase8-v10-fresh-v4, same numerical gates asv9. User accepted temporary rotation gaps. Explicit unknown intervals and independent map origins remain visible; no reliable continuous/global/independent metric navigation qualification. Original v1/v2/v9failedtrials retained. Source hashes verified unchanged during capture. Raw recording: data/validation/v10-fresh-20261029-193256. Pointer results/reports/phase8-v10-fresh-current.json provides manifest, frozen sources, controls and events. All results below are fresh live measurements except where marked reference analysis.

## Operational results

3892receivedframes over264.891s,14.6891FPSoverall.2connections,one intentionally induced connection error and one47producer-frame gap; other gaps are checked separately against events. Initial20s301frames,zero observedposes, mean-LK-flow95th .02661px (<.25).

Operator confirms full nominal50mmA->B, fixedsheet. Map1initializes705/46.344s, is lost duringoutbound movement; NEWmap2initializes767/50.484s, headingepoch2/root726. This restart was explicitly reported BEFORE faults; map2is the recovery test map. Original path origins/scales are not silently joined.

Actual ownedSSHforward closesandrestores after2.250s. Same map2/root726returns at1000/66.000s; pose-ready latency1.657s measured using same-host monotonic timestamps (<5s).105verifiedpoints/landmarks retained. Supported stationary hold78.375s;inliercount~101atcovercue, preserving refresh eligibility.

Operator confirms fullviewcovered~5s, camera fixedatB. Tracking resets2992/198.781s; no position observations from that reset untilmap2returns3115/206.984s. Recovery has100mapinliers/landmarks andsameheadingroot726. Clear-scene-relative latency and final reference/accuracy gates pending offline image analysis; do not substitute reset-relative8.203sfor clear-view latency.

After recovery, operator confirms5cmB->Areturn withfixedtarget. Map2last observed3813/253.500s, lost3814/253.578s; finalstatewaiting_baseline. This returntrackinggap is retained explicitly. No same-map endpoint pose/globalloopclosure/drift claim is available after loss. It is not disguised as a zero endpoint or a recovered oldmap. Overall limited-scope verdict awaits every preregistered numericalgate; do not add or waive requirements after seeing outcome.

## Cleanup

Receivercompletednormally, ownedforward/Pistreamstoppedcleanly and cleanup_finishedlogged. No further camera movement requested. Analysis workers operate only on saved rawfiles. NoPhase9automatically starts. Final reference metrics, gate matrix and scoped verdict appended once analysis completes.

## Final scoped-series assessment
See docs/phase8_v10_final_series.md and phase8-v10-final-series-verdict.json. Maincoverpose-readyrecovery1.797s passes5s;mainobservedmapRMS1.880/1.800mm,max2.847/2.622pass. Original66.813mmnominalmove remainsINCONCLUSIVE;separatepreregistered followup57.138mm/7.769mmreturnpasses,retainsone map through return. Requiredcomponentgatespass acrossseries,Phase8completeONLYforlimitedlocal-map prototype. Mainoutboundrestart/returnlossretained;no globalmetricqualification.
