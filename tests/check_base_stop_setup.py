"""Execute the actual BASE setup, H1/H4 target choice and stop submission together."""
from pathlib import Path
import ast,re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];s=(root/'Sniper_Manager_v3_6_5_BASE_ATR.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|string|void|double|int) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
tree=ast.parse(Path(__file__).with_name('check_base_stop_orders.py').read_text())
h=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='h' for t in n.targets))
h=h.replace('struct MqlTradeCheckResult{int retcode=0;};','struct MqlTradeCheckResult{int retcode=0;};\nstd::vector<MqlTradeRequest> book;')
h=h.replace('bool EntryPolicy(int,string,bool,bool){return policy && !G_ExecutionUncertain && G_StateOK;}', 'int onlySide=-1;bool EntryPolicy(int side,string,bool,bool){return policy && (onlySide<0||side==onlySide) && !G_ExecutionUncertain && G_StateOK;}')
h=h.replace('datetime TimeCurrent(){return 1000;}', 'datetime now=100000;datetime TimeCurrent(){return now;}')
h=h.replace('bool IsOwnOrder(ulong x){return visible && x==123;}', 'bool IsOwnOrder(ulong x){return visible && x>=123 && x<123+book.size();}')
h=h.replace('sent.comment=module;return send();', 'sent.comment=module;bool ok=send();if(ok)book.push_back(sent);return ok;')
h=h.replace('ulong ResultOrder(){return 123;}', 'ulong ResultOrder(){return 122+book.size();}')
h=h.replace('risk=riskBefore;bv=buyBefore;sv=sellBefore;margin=marginBefore;return exposureOK;', 'risk=riskBefore;bv=buyBefore;sv=sellBefore;margin=marginBefore;for(auto p:book){risk+=p.volume*std::abs(p.price-p.sl)*10;margin+=p.volume*100;if(p.type==ORDER_TYPE_BUY_STOP)bv+=p.volume;else sv+=p.volume;}return exposureOK;')
h+=r'''
using ENUM_TIMEFRAMES=int;
const int PERIOD_H1=60,PERIOD_H4=240,PERIOD_CURRENT=0,SERIES_SYNCHRONIZED=0,MODE_HIGH=0,MODE_LOW=1,AUDIT_BASE=4,clrDarkGray=0;
const int BASE_TARGET_H1=1,BASE_TARGET_H4=2,BASE_TARGET_H1_H4=3;
int BaseTargetScope=BASE_TARGET_H1_H4,BaseSwingStrength=2,BaseSwingLookback=64,BaseSLBufferPoints=15,Vol_SMA_Period=20,h_atr=1;
bool BaseUseStopOrders=true,BaseRequireVolumeSpike=false,EnableSMC_Base=true,EnableAutoTrade=true,DiagnosticMode=false,G_BaseConsumed=false,G_BaseStopOCOTripped=false;
double G_BaseHigh=0,G_BaseLow=0,VolSpikeCoef=1.5;
datetime G_BaseCheckedBar=0,G_BaseStarted=0;
std::vector<MqlRates> stopBars,h1,h4;
bool h1Ready=true,h4Ready=true,positionOpen=false;int canceled=0;
double atr=10,closePrice=105;
template<typename T>void ArraySetAsSeries(T&,bool){}
bool SeriesInfoInteger(int,int tf,int){return tf==PERIOD_H1?h1Ready:(tf==PERIOD_H4?h4Ready:true);}
int CopyRates(int,int tf,int shift,int,std::vector<MqlRates>& v){assert(shift==1);v=tf==PERIOD_H1?h1:(tf==PERIOD_H4?h4:stopBars);return (int)v.size();}
int CopyBuffer(int,int,int shift,int,std::vector<double>& v){assert(shift==1);v={atr};return 1;}
datetime iTime(int,int,int shift){return now-shift*300;}
int Bars(int,int){return 100;}int iHighest(int,int,int,int,int){return 0;}int iLowest(int,int,int,int,int){return 0;}
double iHigh(int,int,int){return 110;}double iLow(int,int,int){return 100;}double iClose(int,int,int){return closePrice;}
int iVolume(int,int,int){return 100;}double GetVolumeSMA(int){return 10;}
int PeriodSeconds(){return 300;}string TimeToString(datetime t){return std::to_string(t);}
void AuditModuleCall(int){}void AuditModuleRead(int){}void DrawR(string,datetime,double,datetime,double,int,string){}
bool BaseStopHasPosition(){return positionOpen;}bool BaseStopHasPending(){return !book.empty();}
void CancelBaseStopOrders(){canceled++;book.clear();}
void setupFixture(){
 fixture();book.clear();onlySide=-1;G_BaseCheckedBar=0;G_BaseHigh=G_BaseLow=0;G_BaseConsumed=G_BaseStopOCOTripped=false;
 positionOpen=false;canceled=0;closePrice=105;h1Ready=h4Ready=true;DiagnosticMode=false;EnableAutoTrade=EnableSMC_Base=true;
 BaseTargetScope=BASE_TARGET_H1_H4;stopBars.clear();h1.clear();h4.clear();
 double sh[]={107,108,109,107,106,110,108};double sl[]={104,103,101,102,104,100,103};
 double hh1[]={110,112,120,115,113,112,111},ll1[]={105,103,90,94,95,96,97};
 double hh4[]={110,112,115,114,113,112,111},ll4[]={105,103,95,99,100,101,102};
 for(int i=0;i<7;i++){stopBars.push_back({sh[i],sl[i]});h1.push_back({hh1[i],ll1[i]});h4.push_back({hh4[i],ll4[i]});}
 for(int i=7;i<64;i++){stopBars.push_back({108-i*.01,103+i*.01});h1.push_back({110-i*.01,98+i*.01});h4.push_back({110-i*.01,103+i*.01});}
}
'''

state=s[s.index('struct BaseZone {'):s.index('};',s.index('struct BaseZone {'))+2]
h+='\n'+state+r'''
bool BaseAdaptiveDetection=false,adaptiveFound=true,adaptiveReady=true;
BaseZone adaptiveZone{true,6,900,1000,110,100,2,0.1,0.8};
int adaptiveShift=0;
bool ReadBaseZone(int shift,BaseZone& zone,string&,bool& ready){adaptiveShift=shift;zone=adaptiveZone;ready=adaptiveReady;return adaptiveFound;}
'''
funcs='\n'.join(extract(n) for n in ('IsBaseStopModule','BaseBreakoutSide','BaseSwingStop','BaseExtremumTarget','BaseATRTarget','GetBaseStopTarget','SubmitEntry','CheckBaseStopSetup'))
funcs=funcs.replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars')
for name in ('rates','stops'):
 funcs=funcs.replace('MqlRates '+name+'[];', 'std::vector<MqlRates> '+name+';')
funcs=funcs.replace('double atr[];', 'std::vector<double> atr;')
cases=r'''
int main(){
 setupFixture();CheckBaseStopSetup();assert(book.size()==2 && network==2);
 assert(book[0].type==ORDER_TYPE_BUY_STOP && book[0].price==110 && book[0].tp==115);
 assert(book[1].type==ORDER_TYPE_SELL_STOP && book[1].price==100 && book[1].tp==95);
 assert(book[0].sl<110 && book[1].sl>100);
 CheckBaseStopSetup();assert(network==2);now+=300;CheckBaseStopSetup();assert(network==2); // no duplicate/replacement while live
 setupFixture();onlySide=0;CheckBaseStopSetup();assert(book.size()==1 && book[0].type==ORDER_TYPE_BUY_STOP); // keep directional gates
 setupFixture();BaseTargetScope=BASE_TARGET_H1;CheckBaseStopSetup();assert(book[0].tp==120 && book[1].tp==90);
 setupFixture();h4Ready=false;CheckBaseStopSetup();assert(book.empty());h4Ready=true;CheckBaseStopSetup();assert(book.size()==2); // cannot ignore unloaded closer H4 targets
 setupFixture();h4.resize(5);CheckBaseStopSetup();assert(book.empty()); // full requested target window required
 setupFixture();closePrice=112;CheckBaseStopSetup();assert(book.empty()); // wait for a new inside base, never chase a break
 setupFixture();DiagnosticMode=true;CheckBaseStopSetup();assert(book.empty());
 setupFixture();EnableAutoTrade=false;CheckBaseStopSetup();assert(book.empty());
 setupFixture();positionOpen=true;CheckBaseStopSetup();assert(book.empty() && canceled==1);
 setupFixture();riskBefore=49;CheckBaseStopSetup();assert(book.empty()); // shared exposure budget blocks both
 setupFixture();BaseAdaptiveDetection=true;adaptiveZone.high=108;adaptiveZone.low=102;
 CheckBaseStopSetup();assert(adaptiveShift==1 && book.size()==2 && book[0].price==108 && book[1].price==102);
 setupFixture();adaptiveFound=false;CheckBaseStopSetup();assert(book.empty());
 std::cout<<"PASS: actual BASE setup + H1/H4 nearest target + broker requests; two sides, directional gates, no chase/duplicates, incomplete history and diagnostic mode\n";
}
'''
with tempfile.TemporaryDirectory(prefix='base-setup-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
