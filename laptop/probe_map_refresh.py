import json
from pathlib import Path
import laptop.replay_stateful as r
from laptop.map_refresh_candidate import VisualOdometry
r.VisualOdometry=VisualOdometry
j=json.loads(Path('results/reports/phase8-v2-current.json').read_text());out=Path('results/experiments/map-refresh-v20/fresh-v2.json');assert not out.exists();out.write_text(json.dumps(r.replay(Path(j['recording']),Path('results/experiments/map-refresh-v20/v8-baseline.py')),indent=2))
