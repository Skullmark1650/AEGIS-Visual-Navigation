import json
from pathlib import Path
import laptop.replay_cached as r
from laptop.rotation_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
p=Path('results/experiments/rotation-v9');out=r.compare(Path('data/validation/final-rotation-20261029-141705'),Path('results/cache/v9-final-rotation.npz'),p/'v8-baseline.py');(p/'fresh-rotation.json').write_text(json.dumps(out,indent=2))

