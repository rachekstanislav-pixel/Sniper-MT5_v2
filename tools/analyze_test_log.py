"""Summarize own EA deal ledgers separately for each tester run (UTF-16 or UTF-8).
Usage: python3 tools/analyze_test_log.py INPUT.log [OUTPUT.json]
No prices/cashflows are inferred from chart screenshots or broker trade-print duplicates.
"""
from pathlib import Path
import re,json,sys
raw=Path(sys.argv[1]).read_bytes()
s=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
starts=[m.start() for m in re.finditer('expert file added:',s)]
out=[]
for idx,start in enumerate(starts):
 text=s[start:starts[idx+1] if idx+1<len(starts) else len(s)]
 name=text.splitlines()[0].split('Experts\\')[-1].split('.ex5')[0]
 deposit=re.search(r'initial deposit ([\d.]+)',text)
 positions={};ledger=[]
 for line in text.splitlines():
  if 'SN363 DEAL |' not in line and 'SN365 DEAL |' not in line:continue
  fields=dict(re.findall(r'(\w+)=([^|\n]+)',line));fields={k:v.strip() for k,v in fields.items()}
  pos=fields.get('position');kind=int(fields['entry']);module=fields.get('comment','')
  if kind==0:positions[pos]=module
  fields['net']=sum(float(fields.get(k,0)) for k in ('profit','commission','swap','fee'));ledger.append(fields)
 modules={}
 for d in ledger:
  module=positions.get(d['position'],'UNKNOWN')
  module=re.sub(r':\d+$','',module)
  a=modules.setdefault(module,dict(entries=0,exit_deals=0,wins=0,losses=0,net=0))
  a['entries']+=int(d['entry']=='0');a['exit_deals']+=int(d['entry']!='0');a['wins']+=int(d['entry']!='0' and float(d['profit'])>0);a['losses']+=int(d['entry']!='0' and float(d['profit'])<0);a['net']+=d['net']
 for a in modules.values():a['net']=round(a['net'],2)
 out.append(dict(run=idx+1,build=name,deposit=float(deposit[1]) if deposit else None,modules=modules))
print(json.dumps(out,ensure_ascii=False,indent=2))
if len(sys.argv)>2: Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
