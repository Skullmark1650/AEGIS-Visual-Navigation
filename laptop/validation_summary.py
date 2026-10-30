"""Aggregate explicit Phase 8 case artifacts without inventing unavailable accuracy metrics."""
import argparse
import hashlib
import json
from pathlib import Path


def summarize(study, output):
    study=Path(study);output=Path(output)
    if output.exists():raise FileExistsError('Choose an unused summary directory')
    spec=json.loads(study.read_text());cases=[];hashes={str(study):hashlib.sha256(study.read_bytes()).hexdigest()}
    for case in spec['cases']:
        source=Path(case['validation']);v=json.loads(source.read_text())
        transport=Path(v['source_report']);s=json.loads(transport.read_text())
        notes=Path(case['recording'])/'operator_notes.json'
        if not notes.exists():raise ValueError('Missing operator confirmation: '+case['case'])
        n=json.loads(notes.read_text())
        for p in [source,transport,transport.with_suffix('.csv'),notes]:hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        statuses=s['odometry']['statuses']
        evaluated={k:count for k,count in statuses.items() if not k.startswith('reset_') and k not in {'waiting_baseline','low_motion'}}
        cases.append({'case':case['case'],'validation':str(source),'frames':v['frames'],
            'receive_fps':v['receive_fps'],'processing_mean_ms':v['processing_ms']['mean'],
            'processing_p95_ms':v['processing_ms']['p95'],'tracking_consistency':v['weighted_track_acceptance'],
            'accepted_poses':v['accepted_pose_count'],'statuses':statuses,
            'geometry_evaluation_outcomes':evaluated,'accepted_fraction_of_evaluations':v['accepted_pose_count']/sum(evaluated.values()) if sum(evaluated.values()) else None,
            'connection_errors':s['connection_errors'],'producer_gaps':s['sequence_gaps'],
            'cpu_percent_one_core':v['resources']['cpu_percent_one_core'],
            'peak_rss_bytes':v['resources']['process_peak_rss_bytes'],
            'operator_protocol_status':n['protocol_status'],
            'pose_comparisons':v['pose_comparisons'],'recovery_events':v['recovery_events'],
            'metric_vo_drift':v['metric_vo_drift']})
    result={'cases':cases,'total_frames':sum(c['frames'] for c in cases),'study_limits':spec['limits'],
        'conclusion':'Ten-condition research validation series, not navigation qualification. Continuous pose reliability failed in motion cases; independent metric drift and angular/direction accuracy remain unavailable.',
        'metric_definitions':'LK consistency is accepted/attempted image correspondences. Geometry-evaluation acceptance excludes waits/resets and is not ground-truth correctness. Reference comparisons share calibration and cannot establish independent accuracy.'}
    output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(result,indent=2))
    (output/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
    lines=['# Phase 8 controlled validation summary','',result['conclusion'],'',
        '| Case | Frames | Receive FPS | Mean / p95 processing ms | LK consistency | Accepted poses |',
        '|---|---:|---:|---:|---:|---:|']
    for c in cases:
        lines.append(f"| {c['case']} | {c['frames']} | {c['receive_fps']:.3f} | {c['processing_mean_ms']:.2f} / {c['processing_p95_ms']:.2f} | {100*c['tracking_consistency']:.3f}% | {c['accepted_poses']} |")
    lines+=['',f"Total verified frames in selected cases: {result['total_frames']}.",'',result['metric_definitions'],'',spec['limits']]
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,default=Path('configs/phase8_study.json'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=summarize(a.study,a.output);print(json.dumps({'cases':len(r['cases']),'frames':r['total_frames']}))
