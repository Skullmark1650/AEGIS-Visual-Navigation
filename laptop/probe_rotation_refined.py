import json
from pathlib import Path
import laptop.replay_cached as r
from laptop.rotation_refined_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
p=Path('results/experiments/rotation-v15/fresh-rotation.json');assert not p.exists();p.write_text(json.dumps(r.compare(Path('data/validation/final-rotation-20261029-141705'),Path('results/cache/v9-final-rotation.npz'),Path('results/experiments/rotation-v9/v8-baseline.py')),indent=2))
