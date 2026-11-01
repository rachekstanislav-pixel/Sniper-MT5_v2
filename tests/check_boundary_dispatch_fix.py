"""Reproduce real remainder-to-basket regression in FULL old ManagePositions, then verify fix."""
from pathlib import Path
import ast,re,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
new=(r/'Sniper_Manager_v3_6_5_BASE_HALF_1000_TP_2000_FIX.mq5').read_text();old=(r/'Sniper_Manager_v3_6_5_BASE_HALF_1000_TP_2000.mq5').read_text()
def extract(s,n):
 m=re.search(r'^(?:bool|string|void|double|int) '+n+r'\([^{};]*\)\s*\{',s,re.M);assert m,n
 return s[m.start():s.index('\n}',m.end())+2]
t=ast.parse((r/'tests/check_stage1_management.py').read_text())
h=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='h' for x in n.targets))
h=h.replace('BaseHalfExitPips=1000','BasePartialPips=1000').replace('BasePipSize=.01','BaseBoundaryPipSize=.01')
h=h.replace('SMC_B65:123','SMC_Base_Edge_B:123').replace('"test.half.123"','"test.boundaryhalf.123"')
h=h.replace('assert(tp==0);modifyCalls++;sl=stop;::tp=tp;return true;','modifyCalls++;sl=stop;::tp=tp;return true;')
h=h.replace('deals.push_back({DEAL_ENTRY_OUT,v});','deals.push_back({DEAL_ENTRY_OUT,v});comment="";')
h=h.replace('string PositionGetString(int){return comment;}','string PositionGetString(int p){return p==901?_Symbol:comment;}')
h=h.replace('return p==POSITION_TYPE?side:123;','return p==902?(long)MagicNumber:(p==POSITION_TYPE?side:123);')
h=h.replace('double SymbolInfoDouble(string,int p){return p==SYMBOL_VOLUME_STEP||p==SYMBOL_VOLUME_MIN?.01:.01;}', 'double SymbolInfoDouble(string,int p){if(p==904)return bid;if(p==905)return ask;if(p==906)return 1;return .01;}')
h+='''
const int POSITION_SYMBOL=901,POSITION_MAGIC=902,SYMBOL_POINT=903,SYMBOL_BID=904,SYMBOL_ASK=905,SYMBOL_TRADE_TICK_VALUE=906,ACCOUNT_BALANCE=907;
const int clrLime=1,clrRed=2,clrFireBrick=3,STYLE_SOLID=1,STYLE_DOT=2;
int Physical_BE_Trigger=250,Physical_BE_Level=50,Fixed_TakeProfit=1000,_Period=5,h_atr=1,fullCloses=0;
double BaseFinalPips=2000;
bool G_StopLatched=false,G_StateOK=true,G_ExecutionUncertain=false;
bool PositionSelectByTicket(ulong t){return IsOwnPosition(t);}
double AccountInfoDouble(int){return 500;}double GetDynamicGlobalRisk(){return 15;}
void CreateFiboLine(string,double,int,int,string){}
bool SafeClose(ulong){fullCloses++;own=false;return true;}
datetime iTime(string,int,int){return 500;}
int CopyBuffer(int,int,int,int,std::vector<double>& out){out={2};return 1;}
'''
funcs='\n'.join(extract(new,n) for n in ('IsBoundaryBaseModule','IsBaseStopModule','IsIndividualBaseModule','BaseATRTarget','BoundaryFixedTarget','BoundaryHalfVolume','SafeModify','BoundaryTryHalfExit','ManageBoundaryFixedPosition','BaseStopHasPosition'))
# The old manager must execute its actual old per-BASE loop and then its actual basket logic.
# The partial helper and fixed-target helper are identical other than robust ownership dispatch.
funcs+='\n'+extract(old,'ManageBaseATRPositions')+'\n'+extract(old,'ManagePositions').replace('void ManagePositions()', 'void ManagePositions_Legacy()')
funcs+='\n'+extract(new,'ManagePositions')
funcs=funcs.replace('double atr[];','std::vector<double> atr;')
cases=r'''
int main(){
 fixture();current=.02;deals={{DEAL_ENTRY_IN,.02}};tp=120;bid=110.1;ask=110.12;fullCloses=0;
 ManagePositions_Legacy();
 assert(closeCalls==1&&current==.01&&comment.empty());
 assert(fullCloses==1&&modifyCalls==1&&sl==100.5); // REPRO: basket BE then full close at +1000
 fixture();current=.02;deals={{DEAL_ENTRY_IN,.02}};tp=120;bid=110.1;ask=110.12;fullCloses=0;
 ManagePositions();
 assert(closeCalls==1&&current==.01&&comment.empty());
 assert(fullCloses==0&&modifyCalls==0&&sl==90&&tp==120); // FIX: original SL, remainder still alive
 assert(BaseStopHasPosition()); // no new zone opens against an unrecognized remainder
 bid=115;ask=115.02;ManagePositions();assert(closeCalls==1&&fullCloses==0&&sl==90&&tp==120);
 claims.clear();ManagePositions();assert(closeCalls==1&&fullCloses==0); // restart: history alone prevents another half
 bid=120;ask=120.02;ManagePositions();assert(fullCloses==1&&sl==90); // only the final +2000 closes the remainder
 fixture();own=false;bid=110.1;ManagePositions();assert(closeCalls==0&&modifyCalls==0);
 fixture();mutations=false;bid=110.1;ManagePositions();assert(closeCalls==0&&modifyCalls==0);
 std::cout<<"PASS: reproduced old half+BE+full-close on one tick; fixed full dispatcher preserves remainder/SL/TP across comment loss, repeated ticks and restart\n";
}
'''
with tempfile.TemporaryDirectory(prefix='boundary-dispatch-') as t:
 p=Path(t)/'c.cpp';exe=Path(t)/'c';p.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
