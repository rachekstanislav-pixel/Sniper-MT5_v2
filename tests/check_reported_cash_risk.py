"""Real risk curve/sizing against numerical examples derived from the reported log.
Uses an optimistic entry at .790 and SL at the sweep extreme to show when even
that distance is unaffordable. This is not a historical tick replay.
"""
from pathlib import Path
import ast,re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|double) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m
 return s[m.start():s.index('\n}',m.end())+2]
tree=ast.parse(Path(__file__).with_name('check_working_revision.py').read_text())
h=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='harness' for t in n.targets))
h=h.replace('double GetDynamicRisk(){return 2;}',extract('GetDynamicRisk'))
cases=r'''
int main(){
 balance=125.14;double v=0;double budget=balance*GetDynamicRisk()/100*.5;
 assert(std::abs(budget-3.059673)<1e-6);
 unitLoss=(4150.49-4133.74)*100;
 assert(!SafeVolume(0,4150.49,4133.74,v,.5) && v==0);
 unitLoss=(4150.49-4147.30)*100;
 assert(!SafeVolume(0,4150.49,4147.30,v,.5) && v==0);
 balance=500;unitLoss=(4150.49-4133.74)*100;
 assert(!SafeVolume(0,4150.49,4133.74,v,.5)); // $500 is not sufficient for every OTE stop
 unitLoss=(4150.49-4147.30)*100;
 assert(SafeVolume(0,4150.49,4147.30,v,.5)); // some tighter OTE stops ARE feasible at $500
 unitLoss=(4164.74-4151.18)*100;
 assert(SafeVolume(0,4164.74,4151.18,v,1) && v>=.01); // a BASE example can fit $500: must not blame every failure on deposit
 balance=5000;unitLoss=(4150.49-4133.74)*100;
 assert(SafeVolume(0,4150.49,4133.74,v,.5));
 std::cout<<"PASS: actual risk curve/sizing distinguishes affordable and blocked $125/$500 OTE/BASE examples without forcing minimum volume\n";
}
'''
with tempfile.TemporaryDirectory(prefix='reported-risk-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+extract('SafeVolume')+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
