import json
from pathlib import Path
from laptop.replay_stateful import replay
p=Path('results/experiments/retained-landmarks-v22');cases=json.loads(Path('configs/phase8_study.json').read_text())['cases'];records=[Path(c['recording']) for c in cases]+[Path('data/validation')/n for n in ['horizontal-20261029-043504','rotation-20261029-043945','stationary-20261029-043226','final-horizontal-redo-20261029-141146','final-rotation-20261029-141705']];cur=json.loads(Path('results/reports/phase8-v2-current.json').read_text());records.append(Path(cur['recording']));results=[]
for i,d in enumerate(records):
 out=p/('regression-'+str(i)+'.json');assert not out.exists();j=replay(d,p/'v9-baseline.py');out.write_text(json.dumps(j,indent=2));results.append({'recording':str(d),'report':str(out),'frames':j['frames'],'statuses':{n:e['statuses'] for n,e in j['estimators'].items()}});(p/'regression-index.json').write_text(json.dumps(results,indent=2))
