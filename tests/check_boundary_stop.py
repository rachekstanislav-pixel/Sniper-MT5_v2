"""Execute actual boundary requests, scoped countertrend gate, setup lifecycle, OCO and exits.
C++ MT5 mocks: not a MetaEditor build or historical replay.
"""
from pathlib import Path
import ast,re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'Sniper_Manager_v3_6_5_BASE_BOUNDARY_STOP.mq5').read_text()
def extract(n):
 m=re.search(r'^(?:bool|string|void|double|int) '+n+r'\([^{};]*\)\s*\{',s,re.M);assert m,n
 return s[m.start():s.index('\n}',m.end())+2]
def literal(file,n):
 tree=ast.parse((r/'tests'/file).read_text())
 return next(ast.literal_eval(v.value) for v in tree.body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in v.targets))
def run(h,names,cases):
 fs='\n'.join(extract(n) for n in names).replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars').replace('double atr[];','std::vector<double> atr;').replace('double atrTarget[];','std::vector<double> atrTarget;')
 with tempfile.TemporaryDirectory(prefix='boundary-') as t:
  p=Path(t)/'c.cpp';exe=Path(t)/'c';p.write_text(h+'\n'+fs+'\n'+cases)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
h=literal('check_base_stop_orders.py','h')
run(h,['BoundaryGeometry','IsBoundaryBaseModule','IsBaseStopModule','IsIndividualBaseModule','BaseATRTarget','SubmitEntry'],r'''
int main(){
 double e=0,sl=0;
 assert(BoundaryGeometry(0,100,110,.5,e,sl)&&e==110&&sl==99.5);
 assert(BoundaryGeometry(1,100,110,.5,e,sl)&&e==100&&sl==110.5);
 assert(!BoundaryGeometry(2,100,110,.5,e,sl));assert(!BoundaryGeometry(0,110,100,.5,e,sl));
 fixture();assert(SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130));
 assert(sent.type==ORDER_TYPE_BUY_STOP&&sent.price==110&&sent.sl==99.5&&sent.tp==130&&sent.stoplimit==0);
 assert(sent.type_time==ORDER_TIME_SPECIFIED&&sent.expiration==4000&&!G_ExecutionUncertain);
 fixture();assert(SubmitEntry(1,true,100,110.5,"SMC_Base_Edge_S:100",0,1,80));
 assert(sent.type==ORDER_TYPE_SELL_STOP&&sent.price==100&&sent.sl==110.5&&sent.tp==80&&sent.stoplimit==0);
 fixture();balanceValue=500;assert(SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130));assert(sent.volume==.05);
 fixture();quoteAsk=110;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();quoteBid=100;assert(!SubmitEntry(1,true,100,110.5,"SMC_Base_Edge_S:100",0,1,80)&&network==0);
 fixture();riskBefore=49;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();buyBefore=.1;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();marginBefore=499;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();checkOK=false;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();canSave=false;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();visible=false;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&G_ExecutionUncertain);
 std::cout<<"PASS boundary: real Stop requests at 100/110, opposite SL 99.5/110.5, ATR TP, expiry, no chase, cap/risk/margin and durable uncertainty\n";
}
''')
# Scope of the direction exception: both BASE sides allowed; data and other modules unchanged.
h=literal('check_working_revision.py','harness')
run(h,['IsBoundaryBaseModule','IsBaseStopModule','DirectionAllowed'],r'''
int main(){
 string why;BaseUseStopOrders=true;D1_RequireDirectionForEntries=true;
 G_D1_Direction=1;SF_ConfirmedDirection=-1;
 assert(DirectionAllowed(0,why,"SMC_Base_Edge_B:100"));assert(DirectionAllowed(1,why,"SMC_Base_Edge_S:100"));
 assert(!DirectionAllowed(0,why,"SMC_EMA"));assert(!DirectionAllowed(1,why,"SMC_EMA"));
 structureOK=false;assert(!DirectionAllowed(0,why,"SMC_Base_Edge_B:100"));structureOK=true;
 G_D1_DataReady=false;assert(!DirectionAllowed(0,why,"SMC_Base_Edge_B:100"));G_D1_DataReady=true;
 G_D1_Valid=false;assert(!DirectionAllowed(1,why,"SMC_Base_Edge_S:100"));
 std::cout<<"PASS boundary: both countertrend directions, original D1/H4 data guards and other-module filters retained\n";
}
''')
# OCO test book, now using the new entry comments. All existing ownership/restart cases retained.
h=literal('check_base_stop_oco.py','h');cases=literal('check_base_stop_oco.py','cases')
for a,b in [('SMC_Base_Stop_B:','SMC_Base_Edge_B:'),('SMC_Base_Stop_S:','SMC_Base_Edge_S:')]:h=h.replace(a,b);cases=cases.replace(a,b)
run(h,['IsBoundaryBaseModule','IsBaseStopModule','BaseStopGroup','BaseStopHasPosition','BaseStopHasPending','CancelBaseStopOrders','BaseStopFilledSince','ReviewOwnPending','OnTradeTransaction'],cases)
# Actual ATR/BE manager handles the new BASE comments; legacy cases remain unchanged.
h=literal('check_atr_management.py','h');cases=literal('check_atr_management.py','cases').replace('SMC_Base_ATR','SMC_Base_Edge_B:100')
run(h,['IsBoundaryBaseModule','IsBaseStopModule','IsIndividualBaseModule','BaseATRTarget','ManageBaseATRPositions'],cases)
# Use established setup regressions with boundary prices, positive ATR targets and real new helpers.
h=literal('check_fix2_setup.py','h');cases=literal('check_fix2_setup.py','cases')
for a,b in [('G_BaseStage','G_Boundary'),('BaseInitialSLPips','BaseBoundarySLPips'),('BasePipSize','BaseBoundaryPipSize')]:h=h.replace(a,b);cases=cases.replace(a,b)
h=h.replace('tp==0','tp>0')
h+='''\nconst int SYMBOL_TRADE_TICK_SIZE=99;double SymbolInfoDouble(int,int){return .01;}
double MathFloor(double x){return std::floor(x);}double MathCeil(double x){return std::ceil(x);}
double NormalizeDouble(double x,int d){double f=std::pow(10,d);return std::round(x*f)/f;}
'''
cases=cases.replace('bid=103;ask=103.2','bid=99;ask=99.2').replace('triggers[1]==103.5','triggers[1]==100').replace('bid=106.8;ask=107','bid=110.8;ask=111').replace('triggers[1]==106.5','triggers[1]==110')
cases=cases.replace('triggers[0]-4161.7965','triggers[0]-4163.62').replace('triggers[1]-4160.2335','triggers[1]-4158.41')
# Replace selected-order wrappers just as the established setup harness does.
source=s;s=s.replace('OrderGetTicket(i)','SelectOrder(i)').replace('OrderGetString(ORDER_COMMENT)','SelectedComment(ORDER_COMMENT)')
run(h,['BoundaryGeometry','BoundaryHasPending','BoundarySameConsumedZone','BaseATRTarget','CheckBaseStopSetup'],cases)
s=source
# Core sizing, global risk, exits and OCO have not been rewritten.
control=(r/'Sniper_Manager_v3_6_5_BASE_ONLY_CONTROL.mq5').read_text()
for n in ('SafeVolume','OwnExposure','LossAtSL','GetDynamicRisk','GetDynamicGlobalRisk','EntryPolicy','SafeModify','SafeClose','CheckEquityProtection','OnTradeTransaction','ReviewOwnPending','ManagePositions'):
 assert extract(n) in control,n
for n in ('EnableSMC_EMA','EnableSMC_Comp','EnableSMC_OTE','EnableSMC_Sweep','EnableAICommands'):assert f'input bool {n} = false;' in s
assert 'input bool BaseUseStopOrders = true;' in s
assert 'MODE_HIGH,8,1' in extract('CheckBaseStopSetup') and 'MODE_LOW,8,1' in extract('CheckBaseStopSetup')
assert 'BaseSwingStop' not in extract('CheckBaseStopSetup') and 'GetBaseStopTarget' not in extract('CheckBaseStopSetup')
print('PASS boundary: core risk/exposure/OCO unchanged; BASE only; latest eight closed candles; no pivot/HTF-target dependency')
