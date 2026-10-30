import json
from pathlib import Path
import laptop.replay_cached as r
from laptop.rotation_image_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
out=Path('results/experiments/rotation-v10/fresh-rotation.json');assert not out.exists()
j=r.compare(Path('data/validation/final-rotation-20261029-141705'),Path('results/cache/v9-final-rotation.npz'),Path('results/experiments/rotation-v9/v8-baseline.py'));out.write_text(json.dumps(j,indent=2))
