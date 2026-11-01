"""Execute actual Stage 1 geometry, closed-wick stops and native pending submission.
C++ mocks verify logic; this does not replace a MetaEditor build / MT5 replay.
"""
from pathlib import Path
import ast,re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|string|void|double|int) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
def harness(file):
 tree=ast.parse((root/'tests'/file).read_text())
 return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='h' for t in n.targets))
def run(h,funcs,cases):
 funcs=funcs.replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars')
 with tempfile.TemporaryDirectory(prefix='stage1-') as tmp:
  cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(cpp),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
h=harness('check_base_stop_orders.py').replace('struct MqlRates{double high,low;};','struct MqlRates{double high,low;datetime time;};')
funcs='\n'.join(extract(n) for n in ('Stage1Geometry','Stage1WickStop','Stage1HalfVolume','IsStage1BaseModule','IsBaseStopModule','IsIndividualBaseModule','BaseATRTarget','LogEntrySizeFailure','SubmitEntry'))
cases=r'''
bool near(double x,double y){return std::abs(x-y)<1e-8;}
int main(){
 double e=0,sl=0;
 assert(Stage1Geometry(0,4100,4110,.5,e,sl)&&near(e,4106.5)&&near(sl,4099.5));
 assert(Stage1Geometry(1,4100,4110,.5,e,sl)&&near(e,4103.5)&&near(sl,4110.5));
 assert(!Stage1Geometry(0,4110,4100,.5,e,sl));assert(!Stage1Geometry(2,4100,4110,.5,e,sl));
 assert(!Stage1Geometry(0,4100,4110,0,e,sl));
 std::vector<MqlRates> bars={{108,104,500},{109,103,400},{107,102,300},{110,101,200},{111,100,100}};
 assert(Stage1WickStop(bars,0,5,.5,sl)&&near(sl,99.5));
 assert(Stage1WickStop(bars,1,5,.5,sl)&&near(sl,111.5));
 bars.resize(3);assert(Stage1WickStop(bars,0,3,0,sl)&&near(sl,102));
 assert(!Stage1WickStop(bars,0,5,0,sl));bars[1].time=600;assert(!Stage1WickStop(bars,0,3,0,sl));
 assert(near(Stage1HalfVolume(.1,.1,.01,.01),.05));
 assert(Stage1HalfVolume(.1,.05,.01,.01)==0); // restart/history: half already exited
 assert(near(Stage1HalfVolume(.1,.08,.01,.01),.03)); // manual exit counts
 assert(Stage1HalfVolume(.01,.01,.01,.01)==0); // cannot split minimum lot
 assert(near(Stage1HalfVolume(.03,.03,.01,.01),.01)); // round DOWN only
 assert(Stage1HalfVolume(.02,.01,.01,.01)==0);
 assert(IsIndividualBaseModule("SMC_B65:123")&&IsIndividualBaseModule("SMC_S35:123"));
 fixture();assert(SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0));
 assert(sent.type==ORDER_TYPE_BUY_STOP&&near(sent.price,106.5)&&sent.tp==0&&near(sent.sl,99.5));
 assert(checked.tp==0&&sent.stoplimit==0&&!G_ExecutionUncertain);
 fixture();assert(SubmitEntry(1,true,103.5,110.5,"SMC_S35:100",0,1,0));
 assert(sent.type==ORDER_TYPE_SELL_STOP&&sent.tp==0&&near(sent.price,103.5));
 fixture();assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,120)&&network==0);
 fixture();assert(!SubmitEntry(0,true,106.5,99.5,"SMC_Base_Stop_B:100",0,1,0)&&network==0); // legacy TP rule retained
 fixture();quoteAsk=107;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&network==0); // no market chase
 fixture();allowedModes=0;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&network==0);
 fixture();policy=false;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&network==0);
 fixture();riskBefore=50;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&network==0);
 fixture();canSave=false;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&network==0);
 fixture();visible=false;assert(!SubmitEntry(0,true,106.5,99.5,"SMC_B65:100",0,1,0)&&G_ExecutionUncertain);
 std::cout<<"PASS Stage1: 65/35, zone SL, 3-5 closed wicks, lot split, no-TP native Stop, retained risk gates\n";
}
'''
run(h,funcs,cases)
# Existing risk, order ownership and tightening implementations must remain byte-for-byte.
old=(root/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
for name in ('SafeVolume','SafeModify','SafeClose','OwnExposure','LossAtSL','GetDynamicRisk','GetDynamicGlobalRisk','CheckCompressionPhase'):
 assert extract(name) in old, name
assert 'input bool EnableSMC_Comp = false;' in s
assert 'input bool EnableSMC_Sweep = false;' in s
assert 'input int BaseTrailBars = 5;' in s
assert 'input double BasePipSize = 0.01;' in s
assert 'input double BaseInitialSLPips = 50.0;' in s
assert 'input double BaseHalfExitPips = 1000.0;' in s
assert 'MODE_HIGH,8,2' in extract('CheckBaseStopSetup')
assert 'GetBaseStopTarget' not in extract('CheckBaseStopSetup')
assert 'BaseSwingStop' not in extract('CheckBaseStopSetup')
assert 'ReadBaseZone' not in extract('CheckBaseStopSetup')
for name in ('EnableSMC_EMA','EnableSMC_OTE','EnableSMC_Base','EnableAICommands'):
 assert f'input bool {name} = true;' in s
assert 'ManageStage1Position(ticket)' in extract('ManagePositions')
assert 'Physical_BE' not in extract('ManagePositions')
assert 'Fixed_TakeProfit' not in extract('ManagePositions')
assert 'CopyRates(_Symbol,PERIOD_M5,1,BaseTrailBars,bars)' in extract('ManageStage1Position')
print('PASS FIX2: embedded settings, Compression disabled, one common exit manager')
# Execute current no-TP review + OCO callbacks with the established deterministic book.
tree=ast.parse((root/'tests/check_base_stop_oco.py').read_text())
oco_cases=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cases' for t in n.targets))
oco_cases=oco_cases.replace('int main(){',r'''int main(){
 fixture();orders[0].comment="SMC_B65:500";orders[1].comment="SMC_S35:500";
 orders[0].tp=orders[1].tp=0;ReviewOwnPending();assert(deletions==0);
 deals={{101,"GOLD","SMC_B65:500",123,10,0,0,950}};
 OnTradeTransaction({1,101,10},{},{});assert(deletions==2&&G_BaseStopOCOTripped);
 fixture();orders[0].comment="SMC_B65:500";orders[1].comment="SMC_S35:500";
 orders[0].tp=orders[1].tp=0;deals={{101,"GOLD","SMC_S35:500",123,10,0,1,950}};
 ReviewOwnPending();assert(deletions==2); // restart, same BASE group
''')
oco_funcs='\n'.join(extract(n) for n in ('IsStage1BaseModule','IsBaseStopModule','BaseStopGroup','BaseStopHasPosition','BaseStopHasPending','CancelBaseStopOrders','BaseStopFilledSince','ReviewOwnPending','OnTradeTransaction'))
run(harness('check_base_stop_oco.py'),oco_funcs,oco_cases)
# Real module switch used at the central entry gate; existing disabled pending orders are cleaned up.
disabled_h=harness('check_base_stop_oco.py')
disabled_h=disabled_h.replace('bool EntryPolicy(int,string,bool,bool){return policy;}',
 'bool SignalModuleEnabled(string);\nbool EntryPolicy(int,string module,bool,bool){return policy&&SignalModuleEnabled(module);}')
disabled_h+='\nbool EnableSMC_EMA=true,EnableSMC_OTE=true,RequireOTEReclaim=true,EnableSMC_Base=true,EnableAICommands=true,EnableSMC_Comp=false,EnableSMC_Sweep=false;\n'
disabled_funcs='\n'.join(extract(n) for n in ('IsStage1BaseModule','IsBaseStopModule','BaseStopGroup','BaseStopHasPosition','BaseStopHasPending','CancelBaseStopOrders','BaseStopFilledSince','SignalModuleEnabled','ReviewOwnPending'))
run(disabled_h,disabled_funcs,r'''
int main(){
 fixture();assert(!SignalModuleEnabled("SMC_Comp")&&!SignalModuleEnabled("SMC_Comp_Limit")&&!SignalModuleEnabled("SMC_Sweep"));
 assert(SignalModuleEnabled("SMC_B65:500")&&SignalModuleEnabled("SMC_S35:500")&&SignalModuleEnabled("SMC_OTE_Reclaim"));
 ReviewOwnPending();assert(deletions==1&&orders[2].deleted&&!orders[0].deleted&&!orders[1].deleted&&!orders[3].deleted&&!orders[4].deleted);
 std::cout<<"PASS FIX2: Compression + paired limit and standalone Sweep disabled; OTE reclaim intact; disabled own pending cleaned, foreign orders preserved\n";
}
''')

assert (root/"Sniper_Manager_v3_6_5_BASE_FIX2.mq5").read_bytes()==(root/"Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5").read_bytes(), "Current file and fresh-name release must match"
