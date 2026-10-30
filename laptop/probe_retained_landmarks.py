import json
from pathlib import Path
from laptop.replay_stateful import replay
p=Path('results/experiments/retained-landmarks-v22');cur=json.loads(Path('results/reports/phase8-v9-fresh-current.json').read_text());(p/'fresh-v9.json').write_text(json.dumps(replay(Path(cur['recording']),p/'v9-baseline.py'),indent=2))
