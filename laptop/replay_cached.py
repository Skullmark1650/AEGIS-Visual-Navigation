"""Integrity-checked LK cache and repeatable offline estimator comparisons."""
import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
from PIL import Image
from .optical_flow import OpticalFlowTracker, FlowConfig
from .visual_odometry import VisualOdometry

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_cache(path):
    # NpzFile lazily decompresses on every key access; load once per replay.
    with np.load(path,allow_pickle=False) as archive:
        return {name:archive[name] for name in archive.files}


def load_tracks(directory, cache):
    manifest=json.loads((directory/'manifest.json').read_text())
    csv_path=Path(manifest['report']).with_suffix('.csv')
    with csv_path.open(newline='') as source:rows=list(csv.DictReader(source))
    identity=dict(recording=str(directory.resolve()),csv_sha256=digest(csv_path),flow_sha256=digest(ROOT/'laptop/optical_flow.py'),config=FlowConfig().__dict__)
    metadata=cache.with_suffix('.json')
    if cache.exists():
        saved=json.loads(metadata.read_text())
        if saved['identity']!=identity or saved['cache_sha256']!=digest(cache):raise ValueError('Cache provenance mismatch')
        return rows,read_cache(cache),saved
    tracker=OpticalFlowTracker(FlowConfig());n=len(rows);maximum=300
    arrays=dict(ids=np.zeros((n,maximum),np.int64),points=np.zeros((n,maximum,2),np.float32),
                last_ids=np.zeros((n,maximum),np.int64),last_current=np.zeros((n,maximum,2),np.float32),
                count=np.zeros(n,np.int32),last_count=np.zeros(n,np.int32))
    flows=[]
    for i,row in enumerate(rows):
        path=(directory/row['recorded_image']).resolve()
        if path.parent!=directory.resolve() or digest(path)!=row['recorded_sha256']:raise ValueError('Raw recording integrity failure')
        with Image.open(path) as source:image=source.convert('RGB')
        _,flow=tracker.update(image,row['session'],int(row['frame_id']),int(row['sensor_ns']),render=False)
        count,last=len(tracker.ids),len(tracker.last_ids)
        arrays['count'][i]=count;arrays['last_count'][i]=last
        arrays['ids'][i,:count]=tracker.ids;arrays['points'][i,:count]=tracker.points
        arrays['last_ids'][i,:last]=tracker.last_ids;arrays['last_current'][i,:last]=tracker.last_current
        flows.append(flow['reset_reason'])
    cache.parent.mkdir(parents=True,exist_ok=True)
    with cache.open('xb') as output:np.savez_compressed(output,**arrays)
    saved=dict(identity=identity,cache_sha256=digest(cache),verified_frames=n,resets=flows)
    with metadata.open('x') as output:json.dump(saved,output,indent=2)
    print('Cached',directory.name,n,'verified frames',flush=True)
    return rows,read_cache(cache),saved


def compare(directory,cache,baseline=None,inject_reset=None):
    rows,arrays,metadata=load_tracks(directory,cache)
    calibration=json.loads(Path(json.loads((directory/'manifest.json').read_text())['calibration']).read_text())
    classes={'candidate':VisualOdometry}
    if baseline:
        spec=importlib.util.spec_from_file_location('laptop._cached_baseline',baseline)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        classes['baseline']=module.VisualOdometry
    result=dict(recording=str(directory),frames=len(rows),cache_sha256=metadata['cache_sha256'],source_sha256=digest(ROOT/'laptop/visual_odometry.py'),
                baseline_sha256=digest(baseline) if baseline else None,calibration_sha256=digest(Path(json.loads((directory/'manifest.json').read_text())['calibration'])),
                fault_injection={'tracker_id_reset_at_frame':inject_reset,'limits':'Simulated tracker state loss on real unmodified video, not a physical camera/occlusion test'} if inject_reset is not None else None,estimators={})
    result['dependency_sha256']={name:digest(ROOT/name) for name in ['laptop/partial_orientation.py'] if (ROOT/name).exists()}
    for label,cls in classes.items():
        vo=cls(calibration);outputs=[]
        for i,row in enumerate(rows):
            count,last=int(arrays['count'][i]),int(arrays['last_count'][i])
            tracker=SimpleNamespace(ids=arrays['ids'][i,:count],points=arrays['points'][i,:count],last_ids=arrays['last_ids'][i,:last],last_current=arrays['last_current'][i,:last],last_info=(row['session'],int(row['frame_id']),int(row['sensor_ns'])))
            reason=metadata['resets'][i]
            if inject_reset is not None and int(row['frame_id'])>=inject_reset:
                tracker.ids=tracker.ids+1_000_000;tracker.last_ids=tracker.last_ids+1_000_000
                if int(row['frame_id'])==inject_reset:reason='tracking_quality'
            if hasattr(vo,'recover_map'):
                with Image.open(directory/row['recorded_image']) as source:
                    tracker.previous=cv2.cvtColor(np.asarray(source.convert('RGB')),cv2.COLOR_RGB2GRAY)
            displacement=None
            if hasattr(vo,'anchor'):
                pairs=[(vo.anchor[int(k)],p) for k,p in zip(tracker.last_ids,tracker.last_current) if int(k) in vo.anchor]
                if pairs:displacement=float(np.median([np.linalg.norm(b-a) for a,b in pairs]))
            cv2.setRNGSeed(i)
            pose=vo.update_tracks(tracker,{'reset_reason':reason})
            outputs.append(dict(frame_id=int(row['frame_id']),elapsed_s=float(row['elapsed_s']),anchor_displacement_px=displacement,**pose))
        counts=dict(Counter(r['status'] for r in outputs))
        print(directory.name,label,counts,flush=True)
        result['estimators'][label]=dict(version=cls.VERSION,statuses=counts,rows=outputs)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--baseline',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--inject-reset-frame',type=int)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=compare(args.recording,args.cache,args.baseline,args.inject_reset_frame)
    with args.output.open('x') as output:json.dump(result,output,indent=2)
