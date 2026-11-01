"""Execute fixed target/sizing/partial manager. No BE or trailing; unchanged zone SL."""
from pathlib import Path
import ast,re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'Sniper_Manager_v3_6_5_BASE_HALF_1000_TP_2000_FIX.mq5').read_text()
def extract(n):
 m=re.search(r'^(?:bool|string|void|double|int) '+n+r'\([^{};]*\)\s*\{',s,re.M);assert m,n
 return s[m.start():s.index('\n}',m.end())+2]
def literal(file,n):
 tree=ast.parse((r/'tests'/file).read_text())
 return next(ast.literal_eval(v.value) for v in tree.body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in v.targets))
def run(h,names,cases):
 fs='\n'.join(extract(n) for n in names).replace('double atr[];','std::vector<double> atr;')
 with tempfile.TemporaryDirectory(prefix='boundary-half-') as t:
  p=Path(t)/'c.cpp';exe=Path(t)/'c';p.write_text(h+'\n'+fs+'\n'+cases)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
h=literal('check_stage1_management.py','h')
h=h.replace('BaseHalfExitPips=1000','BasePartialPips=1000').replace('BasePipSize=.01','BaseBoundaryPipSize=.01')
h=h.replace('string comment="SMC_B65:123"','string comment="SMC_Base_Edge_B:123"').replace('comment="SMC_B65:123"','comment="SMC_Base_Edge_B:123"')
h=h.replace('double BaseTrailBufferPips=0;', 'double BaseTrailBufferPips=0;')
h+='\ndouble BaseFinalPips=2000;int fullCloses=0;\nbool SafeClose(ulong){fullCloses++;own=false;return true;}\n'
h=h.replace('assert(claims.count("test.half.123"))','assert(claims.count("test.boundaryhalf.123"))')
h=h.replace('assert(tp==0);modifyCalls++;sl=stop;::tp=tp;return true;','assert(stop==sl);modifyCalls++;::tp=tp;return true;')
# All fixtures have a stable initial SL; PositionModify must NEVER change it.
run(h,['BoundaryFixedTarget','BoundaryHalfVolume','IsBoundaryBaseModule','BoundaryTryHalfExit','ManageBoundaryFixedPosition'],r'''
int main(){
 fixture();BasePartialPips=1000;BaseFinalPips=2000;BaseBoundaryPipSize=.01;
 current=.02;deals={{DEAL_ENTRY_IN,.02}};ManageBoundaryFixedPosition(1);
 assert(closeCalls==0&&tp==120&&sl==90); // below +10.00, no BE even though far above old trigger
 bid=110;ask=110.02;ManageBoundaryFixedPosition(1);assert(closeCalls==1&&lastClose==.01&&current==.01&&sl==90&&tp==120);
 ManageBoundaryFixedPosition(1);assert(closeCalls==1&&sl==90);
 claims.clear();ManageBoundaryFixedPosition(1);assert(closeCalls==1); // restart, recovered exit history
 bid=119.99;ask=120.01;ManageBoundaryFixedPosition(1);assert(fullCloses==0&&sl==90);
 bid=120;ask=120.02;ManageBoundaryFixedPosition(1);assert(fullCloses==1); // fallback full target on actual-fill price
 fixture();side=1;comment="SMC_Base_Edge_S:123";entry=120;sl=130;bid=110;ask=110.01;current=.02;deals={{DEAL_ENTRY_IN,.02}};
 ManageBoundaryFixedPosition(1);assert(closeCalls==0&&tp==100&&sl==130); // SELL uses ASK, not BID
 ask=110;bid=109.98;ManageBoundaryFixedPosition(1);assert(closeCalls==1&&current==.01&&tp==100&&sl==130);
 fixture();entry=100.07;bid=110.07;ask=110.09;ManageBoundaryFixedPosition(1);assert(std::abs(tp-120.07)<1e-8&&sl==90); // actual slippage, not trigger
 fixture();entry=4100.07;bid=4110.07;ask=4110.09;sl=4090;ManageBoundaryFixedPosition(1);
 assert(closeCalls==1&&std::abs(tp-4120.07)<1e-8&&sl==4090); // GOLD-scale floating point at the exact threshold
 fixture();bid=110;sendOK=false;retcode=10018;orderResult=0;ManageBoundaryFixedPosition(1);
 assert(closeCalls==1&&claims.empty());ManageBoundaryFixedPosition(1);assert(closeCalls==1);
 now+=61;sendOK=true;retcode=10009;orderResult=1;ManageBoundaryFixedPosition(1);assert(closeCalls==2&&sl==90);
 fixture();bid=110;sendOK=false;retcode=10012;orderResult=0;ManageBoundaryFixedPosition(1);ManageBoundaryFixedPosition(1);assert(closeCalls==1); // timeout never doubles the half
 fixture();bid=110;history=false;ManageBoundaryFixedPosition(1);assert(closeCalls==0&&sl==90);
 fixture();bid=110;writeOK=false;ManageBoundaryFixedPosition(1);assert(closeCalls==0&&claims.empty());
 fixture();mutations=false;bid=110;ManageBoundaryFixedPosition(1);assert(closeCalls==0&&modifyCalls==0&&claims.empty());
 fixture();own=false;bid=110;ManageBoundaryFixedPosition(1);assert(closeCalls==0&&modifyCalls==0);
 fixture();comment="";bid=110;ManageBoundaryFixedPosition(1);assert(closeCalls==1&&sl==90); // own remainder can lose its comment
 fixture();G_InstanceLock=-1;bid=110;ManageBoundaryFixedPosition(1);assert(closeCalls==0&&modifyCalls==0);
 std::cout<<"PASS: BUY/Sell +10 half once, +20 actual-fill TP, unchanged SL, restart/timeout, history/storage/ownership guards\n";
}
''')
h=literal('check_base_stop_orders.py','h')+'\ndouble BaseMinimumLots=.02;\n'
run(h,['BoundaryFixedTarget','BoundarySplitEntryVolume','IsBoundaryBaseModule','IsBaseStopModule','BaseATRTarget','SubmitEntry'],r'''
bool near(double a,double b){return std::abs(a-b)<1e-8;}
int main(){
 assert(near(BoundarySplitEntryVolume(.03,.05,.01,.01,.02),.02));
 assert(near(BoundarySplitEntryVolume(.05,.05,.01,.01,.02),.04));
 assert(BoundarySplitEntryVolume(.01,.05,.01,.01,.02)==0);
 assert(BoundarySplitEntryVolume(.1,.01,.01,.01,.02)==0);
 assert(BoundarySplitEntryVolume(.1,.1,.1,.1,.02)==0); // cannot leave a legal half
 assert(near(BoundaryFixedTarget(true,4100,20,.01,2),4120));
 assert(near(BoundaryFixedTarget(false,4100,20,.01,2),4080));
 assert(near(BoundaryFixedTarget(true,4100.07,20,.01,2),4120.07));
 assert(near(BoundaryFixedTarget(false,4100.07,20,.01,2),4080.07));
 fixture();balanceValue=500;assert(SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130));
 assert(near(sent.volume,.04)&&sent.type==ORDER_TYPE_BUY_STOP&&sent.sl==99.5&&sent.tp==130);
 fixture();quoteBid=4099.8;quoteAsk=4099.9;assert(SubmitEntry(0,true,4100.07,4090,"SMC_Base_Edge_B:100",0,1,4120.07));
 assert(near(sent.tp,4120.07)); // no floating-point truncation by one tick
 fixture();balanceValue=100;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0); // .01 cap cannot force .02
 fixture();balanceValue=500;buyBefore=.04;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 fixture();balanceValue=500;riskBefore=25;assert(!SubmitEntry(0,true,110,99.5,"SMC_Base_Edge_B:100",0,1,130)&&network==0);
 std::cout<<"PASS: entry minimum .02, exact-half even-step volume, rounding DOWN, original cap and risk\n";
}
''')
body=extract('ManageBoundaryFixedPosition');assert 'SafeModify' not in body and 'Physical_BE' not in body and 'CopyBuffer' not in body
assert 'ManageBoundaryFixedPosition(ticket)' in extract('ManagePositions')
assert 'Physical_BE' not in s and 'Fixed_TakeProfit' not in s
assert 'ManageBaseATRPositions' not in s
assert 'BoundaryFixedTarget' in extract('CheckBaseStopSetup') and 'BaseATRTarget' not in extract('CheckBaseStopSetup')
old=(r/'Sniper_Manager_v3_6_5_BASE_BOUNDARY_STOP.mq5').read_text()
for n in ('SafeVolume','OwnExposure','LossAtSL','GetDynamicRisk','GetDynamicGlobalRisk','SafeClose','CheckEquityProtection','OnTradeTransaction','ReviewOwnPending','DirectionAllowed'):
 assert extract(n) in old,n
print('PASS: no BASE BE/trailing/ATR TP; entry geometry, countertrend, OCO and core risk unchanged')
# Actual setup submits the fixed +20 target even when ATR is 20 (old 2 ATR would be 40).
h=literal('check_fix2_setup.py','h')
for a,b in [('G_BaseStage','G_Boundary'),('BaseInitialSLPips','BaseBoundarySLPips'),('BasePipSize','BaseBoundaryPipSize')]:h=h.replace(a,b)
h=h.replace('out={10}','out={20}').replace('assert(pending&&kind==1&&tp==0);','assert(pending&&kind==1&&std::abs(tp-(entry+(side==0?20:-20)))<1e-8);')
h+='''\ndouble BaseFinalPips=2000;const int SYMBOL_TRADE_TICK_SIZE=99;
double SymbolInfoDouble(int,int){return .01;}
double MathFloor(double x){return std::floor(x);}double MathCeil(double x){return std::ceil(x);}
double NormalizeDouble(double x,int d){double f=std::pow(10,d);return std::round(x*f)/f;}
'''
source=s;s=s.replace('OrderGetTicket(i)','SelectOrder(i)').replace('OrderGetString(ORDER_COMMENT)','SelectedComment(ORDER_COMMENT)')
run(h,['BoundaryGeometry','BoundaryHasPending','BoundarySameConsumedZone','BoundaryFixedTarget','CheckBaseStopSetup'],r'''
int main(){
 fixture();CheckBaseStopSetup();assert(orders.size()==2&&submitted==2);
 assert(triggers[0]==110&&triggers[1]==100);
 now+=6;CheckBaseStopSetup();assert(submitted==2);
 fixture();bid=99;ask=99.2;CheckBaseStopSetup();assert(orders.size()==1);
 now+=6;bid=105;ask=105.2;CheckBaseStopSetup();assert(orders.size()==2&&submitted==3);
 std::cout<<"PASS: actual setup uses boundary SL and fixed 2000-pip target, independent of ATR magnitude, missing-side retry without duplicate\n";
}
''')
s=source
