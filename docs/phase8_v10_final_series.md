# Phase 8: completed limited-prototype validation

## Verdict and scope

PASS for the agreed limited local-map research-prototype checks, using frozen retained-map-recovery-v10. This closes Phase8for that scoped prototype, not the original stronger goal of continuous/global/independently measured metric navigation. Temporary rotation gaps, position unavailability and independent map restarts remain documented limitations. NoPhase9orPi-onlydeployment was started. This is a two-recording validation series, not one uninterrupted flawless end-to-end run.

Source hashes were locked before each recording and remained unchanged. Maintrial3892frames plus short followup1096frames =4988freshsourceframes, allJPEGhashes checked. Softwarequalification before these fresh runs:84tests and27059savedframes; freshrecordings were not used to tune v10. Numeric gates were not changed after capture.

## Fresh recovery/long-hold trial

Main record: data/validation/v10-fresh-20261029-193256

| Check | Fresh measured result | Limit/result |
|---|---|---|
| Initial stationary |20s,301frames,0observedposes;flowp95 .02661px |PASS,<=.25px |
| Stationary image reference |101samples,.3918mmradius,.03617degrotation |PASS,<=5mm/.5deg |
| Receive rate |14.6891FPS |PASS,>=12 |
| Transport faults |Oneintentionalconnectionerror/47producer-framegap;noothergaps |PASS within loggedfault |
| Actual forward outage |2.250s |Requested2s,creationoverheadrecorded |
| Network recovery |Same map2/epoch2/root726,pose-ready1.657safterlisten |PASS,<=5s |
| Supported hold before cover |78.375s,~101inliersatcue |PASS,>=65s |
| Fullcover/restoration |Operatorconfirms~5s,camerastillB;raw3030flat,poseunobserved |PASS,honestunknowninterval |
| Covered-view recovery |Same map2/epoch2/root726;100verifiedlandmarks |PASS |
| Clear-view to pose ready |1.797sfromfirstsampledclearframe3090 |PASS,<=5sevenwith~.21ssamplingmargin |
| Observed map1referencecomparison |14samples,1.880mmRMS/2.847max |PASS,<=5RMS/10max |
| Observed map2referencecomparison |1913samples,1.800mmRMS/2.622max |PASS,<=5RMS/10max |

Map1was lost during outbound movement; NEWtestmap2was established and explicitly logged BEFORE bothfaults. Recovery success is of map2, not a claim of recovering originalmap1. After successful coverrecovery and duringreturn, map2waslost at3814/253.578s and endedunknown. Thatgapremains. No globalendpoint/loop/driftvalue is available from this run.

The nominal50mmoutbound movement measured66.813mmin the camera-derivedreference, outside the preset40-60mmexecutionrange. Thatexecution remainsINCONCLUSIVE. No numericlimit was relaxed and it was not retroactively markedpass. Recoveryevents occurred while stationarywithasupportedtestmap, so theircomponent measurements remain usable. A short preregistered same-version movementfollowup resolved the movement-execution gate separately.

## Short measured movement followup

Followup record: data/validation/v10-movement-20261029-194638

Operator realigned one consistentcamera-basepoint at A/Bmarked50mmapart; fixedsheet, camera slidoutandback.1096framesat15.0033FPS,noerrors/orgaps;556usableboardreferences,0rejections. Camera-derived excursion57.138mmandreturnoffset7.769mm satisfy40-60mmand<=10mm. Endpoint referenceorientation changed2.428deg, so this is not a pure-translation accuracy certification.

One localmap1retainedthroughthereturn,endstatusmap_tracking.379pairedpositions,oneINITIALscale22.84466mm/unit,2.77826mmRMS/4.03523mmmaximum,endpointcomparison1.14850mm;localendpoint/peakratio .13149. Observedpositiongates pass. These are same-camera/calibration correlatedcomparisons after one fittedinitialscale, not independent millimeteraccuracy. LongholdsaffectRMS; maximumerrorsalsoreported. This successfulrun doesnoterasethelonger-runreturnloss or guaranteecontinuousnavigation.

## Limitations carried forward

- Rotation/positiontrackingcanbeunavailable;laterrecoverycannotreconstructunseenmotion.
- Eachnewmaphasitsownorigin/arbitraryscale;originsare neverjoined as a globalpath.
- Maintrialreturnlossandoriginal66.813mmexecution retained asobservedmisses; earlier v1/v2/v9failures retained.
- NoindependentphysicalATE/RPE,globalloopclosure/drift,true-northheading,globalplace recognition or metricnavigation qualification.
- Prototype checks pass under this controlledscene/profile/calibration, not arbitraryenvironments or indefinitelylongholds.
- Pi-onlymigration andPhase9arefuturework requiring aseparaterequest.

## Evidence, cleanup and resume

Preregistrations/events/rawmanifests/sourcehashes under results/reports/phase8-v10-fresh-current.json and phase8-v10-movement-current.json. Compositegateverdict: results/reports/phase8-v10-final-series-verdict.json; seriesindex: phase8-v10-series.json. Detailedanalysis/positionreviews remain in eachcontroldirectory. No testdata or failedattempt deleted. Bothreceivers/ownedSSHforwards/Pistreamsstoppedcleanly;Pi remains powered. No morerequiredcameraactionforthisscopedPhase8validation. Software remains frozenv10; updateandtestbeforeanyfurtherdeploymentwork.
