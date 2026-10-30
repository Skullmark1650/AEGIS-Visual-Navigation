import json
from pathlib import Path
import laptop.replay_stateful as r
from laptop.guided_map_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
cur=json.loads(Path('results/reports/phase8-v2-current.json').read_text());p=Path('results/experiments/map-diagnosis-v21');out=p/'fresh-v2.json';assert not out.exists();out.write_text(json.dumps(r.replay(Path(cur['recording']),Path('results/experiments/map-refresh-v20/v8-baseline.py')),indent=2))
