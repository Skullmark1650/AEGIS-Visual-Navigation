import json
from pathlib import Path
import laptop.replay_cached as r
from laptop.rotation_brightness_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
p=Path('results/experiments/rotation-v19');cases=[('older','data/validation/rotation-20261029-031748'),('newer','data/validation/rotation-20261029-043945')]
for name,record in cases:
 out=p/(name+'.json');assert not out.exists();out.write_text(json.dumps(r.compare(Path(record),Path('results/cache/v19-'+name+'.npz'),Path('results/experiments/rotation-v9/v8-baseline.py')),indent=2))
