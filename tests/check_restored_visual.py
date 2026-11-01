"""Prove rollback is BASE_ATR plus a strict display-only allowlist."""
from pathlib import Path
import re
r=Path(__file__).resolve().parents[1]
a=(r/'Sniper_Manager_v3_6_5_BASE_ATR.mq5').read_text();b=(r/'Sniper_Manager_v3_6_5_BASE_ATR_RESTORED_VISUAL.mq5').read_text()
def funcs(s):
 out={}
 for m in re.finditer(r'^(?:bool|string|void|double|int) (\w+)\([^{};]*\)\s*\{',s,re.M):
  depth=1
  for t in re.finditer(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|[{}]',s[m.end():]):
   if t[0]=='{':depth+=1
   elif t[0]=='}':depth-=1
   if depth==0:
    out[m[1]]=s[m.start():m.end()+t.end()];break
 return out
fa,fb=funcs(a),funcs(b)
visual={'UpdateHudLayout','UpdateCenterInfo','UpdateDashboardMTF','PaintHeaderBackground','CoveredByHud','PaintPriceCaptions','PaintSignalViews','UpdateFiboDiagnostics','SF_Status','UpdateD1FibonacciTool'}
assert fa.keys()==fb.keys(), 'No new entry/exit helpers permitted'
for name in fa:
 if name not in visual:assert fa[name]==fb[name],name
# Entire remaining source must also match, except the explicit visual globals/input/description.
x,y=a,b
for name in fa:x=x.replace(fa[name],'FUNCTION '+name);y=y.replace(fb[name],'FUNCTION '+name)
y=y.replace('int G_HudLeft=12;\n','').replace('input int HudWidthPercent = 72; // Visual only: entire information panel, right aligned\n','')
x=re.sub(r'^#property description.*$', '',x,flags=re.M);y=re.sub(r'^#property description.*$', '',y,flags=re.M)
assert x==y,'Unexpected change outside visual functions'
assert 'BaseTrailBars' not in b and 'Stage1' not in b and 'G_BaseStage' not in b
for name in ('EnableSMC_Comp','EnableSMC_Sweep'):assert f'input bool {name} = true;' in b
assert 'input bool BaseUseStopOrders = false;' in b
print(f'PASS: {len(fa)-len(visual)} non-visual functions and all original inputs/globals match BASE_ATR; only {len(visual)} rendering functions differ')
# Exercise actual restored HUD calculations and summary at several chart widths.
import ast,subprocess,tempfile
existing=ast.parse((r/'tests/check_fix2_hud.py').read_text())
def literal(n):
 return next(ast.literal_eval(v.value) for v in existing.body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in v.targets))
h=literal('h');cases=literal('cases');cases=cases[:cases.index(' G_BaseViews=')]+''' std::cout<<"PASS restored visual: right HUD and one-row summary at 800..2560px\\n";
}
'''
functions='\n'.join(fb[n] for n in ('UpdateHudLayout','CoveredByHud','UpdateCenterInfo'))
functions=functions.replace('"P/L: all magic on symbol; management: own magic only | "+','string("P/L: all magic on symbol; management: own magic only | ")+')
with tempfile.TemporaryDirectory(prefix='restored-hud-') as tmp:
 cpp=Path(tmp)/'c.cpp';exe=Path(tmp)/'c';cpp.write_text(h+'\n'+functions+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
