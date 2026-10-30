import json
from pathlib import Path
import laptop.replay_stateful as r
from laptop.guided_map_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
p=Path('results/experiments/map-diagnosis-v21');cases=json.loads(Path('configs/phase8_study.json').read_text())['cases'];out=[]
for c in cases:
 if c['case'] in ['stationary','low-light','low-texture','feature-loss','interruption','repeat-path']:out.append(r.replay(Path(c['recording']),p/'v8-baseline.py'))
for record in ['data/validation/final-horizontal-redo-20261029-141146','data/validation/final-rotation-20261029-141705']:out.append(r.replay(Path(record),p/'v8-baseline.py'))
(p/'regressions.json').write_text(json.dumps(out,indent=2))
