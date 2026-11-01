"""Execute fixed BASE state machine: eight CLOSED candles without a ninth-bar delay, old-zone latch and missing-side retry regressions."""
from pathlib import Path
import re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5').read_text()
def extract(n):
 m=re.search(r'^(?:bool|string|void|double|int) '+n+r'\([^{};]*\)\s*\{',s,re.M);assert m,n
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('Stage1Geometry','Stage1HasPending','Stage1SameConsumedZone','CheckBaseStopSetup'))
funcs=funcs.replace('double atr[];','std::vector<double> atr;')
h=r'''
#include <string>
#include <vector>
#include <cassert>
#include <cmath>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;
const int _Symbol=0,_Period=5,_Digits=2,SERIES_SYNCHRONIZED=0,MODE_HIGH=0,MODE_LOW=1,AUDIT_BASE=4,clrDarkGray=0,POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1,ORDER_COMMENT=1;
int h_atr=1,Vol_SMA_Period=20,BaseMaxWaitBars=10,BaseEntryRetrySeconds=5,draws=0,submitted=0,cancels=0;
bool positionOpen=false,G_BaseConsumed=false,G_BaseStopOCOTripped=false,G_BaseStageReady=false;
bool DiagnosticMode=false,EnableAutoTrade=true,EnableSMC_Base=true,BaseRequireVolumeSpike=false,historyReady=true;
datetime G_BaseCheckedBar=0,G_BaseStarted=0,G_BaseStageDeadline=0,G_BaseStageAttempt=0,now=10000,closed=9900;
double G_BaseLow=0,G_BaseHigh=0,BaseInitialSLPips=50,BasePipSize=.01,VolSpikeCoef=1.5,closePrice=105,high=110,low=100,ask=105,bid=104.8;
struct Order{string module;};std::vector<Order> orders;std::vector<double> triggers;
bool Positive(double x){return std::isfinite(x)&&x>0;}
int OrdersTotal(){return orders.size();}ulong OrderGetTicket(int i){return i+1;}bool IsOwnOrder(ulong){return true;}
string OrderGetString(int){static int unused=0;(void)unused;return "";}
// Capture MT5's selected order context for the actual Stage1HasPending loop.
ulong selected=0;ulong SelectOrder(int i){selected=i+1;return selected;}
string SelectedComment(int){return orders[selected-1].module;}
bool SeriesInfoInteger(int,int,int){return true;}
int CopyBuffer(int,int,int shift,int n,std::vector<double>& out){assert(shift==1&&n==1);out={10};return 1;}
datetime iTime(int,int,int shift){return closed-(shift-1)*300;}datetime TimeCurrent(){return now;}
int Bars(int,int){return 100;}
int iHighest(int,int,int,int count,int shift){assert(count==8&&shift==1);return 2;}
int iLowest(int,int,int,int count,int shift){assert(count==8&&shift==1);return 3;}
double iHigh(int,int,int){return high;}double iLow(int,int,int){return low;}
double iClose(int,int,int){return closePrice;}long iVolume(int,int,int){return 100;}double GetVolumeSMA(int){return 10;}
string IntegerToString(long x){return std::to_string(x);}string TimeToString(datetime t){return std::to_string(t);}string DoubleToString(double x,int){return std::to_string(x);}
int PeriodSeconds(){return 300;}int PeriodSeconds(int){return 300;}
void DrawR(string,datetime,double h,datetime,double l,int,string){assert(h>l);draws++;}
void SafetyLog(string){}
void AuditModuleCall(int){}void AuditModuleRead(int){}template<typename... T>void Print(T...){}
bool BaseStopHasPosition(){return positionOpen;}bool BaseStopHasPending(){return !orders.empty();}
void CancelBaseStopOrders(){cancels++;orders.clear();}
bool BaseStopFilledSince(datetime,string,bool& ready){ready=historyReady;return false;}
bool SubmitEntry(int side,bool pending,double entry,double sl,string module,double,int kind,double tp){
 assert(pending&&kind==1&&tp==0);submitted++;
 if(side==0?entry<=ask:entry>=bid)return false;
 assert(side==0?sl<entry:sl>entry);orders.push_back({module});triggers.push_back(entry);return true;
}
void fixture(){
 orders.clear();triggers.clear();G_BaseCheckedBar=G_BaseStarted=G_BaseStageDeadline=G_BaseStageAttempt=0;
 G_BaseConsumed=G_BaseStopOCOTripped=G_BaseStageReady=positionOpen=DiagnosticMode=false;
 historyReady=EnableAutoTrade=EnableSMC_Base=true;now=10000;closed=9900;high=110;low=100;closePrice=105;ask=105;bid=104.8;draws=submitted=cancels=0;
}
'''
funcs=funcs.replace('OrderGetTicket(i)','SelectOrder(i)').replace('OrderGetString(ORDER_COMMENT)','SelectedComment(ORDER_COMMENT)')
cases=r'''
int main(){
 fixture();CheckBaseStopSetup();assert(orders.size()==2&&submitted==2&&draws==1&&G_BaseStarted==7800);
 CheckBaseStopSetup();assert(submitted==2);now+=6;CheckBaseStopSetup();assert(submitted==2); // never duplicate either side
 fixture();bid=103;ask=103.2;CheckBaseStopSetup();assert(orders.size()==1&&submitted==2);
 now+=6;bid=105;ask=105.2;CheckBaseStopSetup();assert(orders.size()==2&&submitted==3&&triggers[1]==103.5); // missing SELL retried SAME closed bar
 fixture();bid=106.8;ask=107;CheckBaseStopSetup();assert(orders.size()==1);now+=6;bid=105;ask=105.2;CheckBaseStopSetup();assert(orders.size()==2&&triggers[1]==106.5); // missing BUY retried
 fixture();G_BaseConsumed=true;G_BaseStarted=1000;G_BaseLow=10;G_BaseHigh=20;
 CheckBaseStopSetup();assert(orders.size()==2); // price outside OLD zone must not block NEW zone
 fixture();G_BaseConsumed=true;G_BaseStarted=7800;CheckBaseStopSetup();assert(orders.empty()); // same consumed identity blocked
 fixture();CheckBaseStopSetup();double frozen=G_BaseLow;closed+=300;now+=300;low=101;high=111;closePrice=106;
 CheckBaseStopSetup();assert(G_BaseLow==frozen&&orders.size()==2); // pending setup bounds do not drift
 now=G_BaseStageDeadline;CheckBaseStopSetup();assert(orders.empty()&&!G_BaseStageReady&&G_BaseConsumed); // exact TTL
 closed+=300;now+=300;CheckBaseStopSetup();assert(G_BaseStageReady&&orders.size()==2); // expiry does not latch all later zones
 fixture();historyReady=false;CheckBaseStopSetup();assert(submitted==0);now+=6;historyReady=true;CheckBaseStopSetup();assert(orders.size()==2);
 fixture();DiagnosticMode=true;CheckBaseStopSetup();assert(submitted==0&&draws==1);
 fixture();EnableAutoTrade=false;CheckBaseStopSetup();assert(submitted==0&&draws==1);
 fixture();positionOpen=true;CheckBaseStopSetup();assert(submitted==0&&G_BaseConsumed&&cancels==1);
 fixture();closePrice=111;CheckBaseStopSetup();assert(submitted==0&&draws==1);
 // Reported Oct 1 zone bounds; the pre-breakout quote here is synthetic, not a tick replay.
 fixture();now=12*3600+50*60;closed=now-300;
 low=4158.41;high=4163.62;closePrice=4161.0;bid=4161.0;ask=4161.19;
 CheckBaseStopSetup();assert(orders.size()==2&&G_BaseStarted==12*3600+10*60);
 assert(std::abs(triggers[0]-4161.7965)<1e-8&&std::abs(triggers[1]-4160.2335)<1e-8);
 // The ninth close (4157.94, from the journal) must not be required before arming this pair.
 closed+=300;now+=300;closePrice=4157.94;CheckBaseStopSetup();assert(orders.size()==2);
 std::cout<<"PASS FIX3 BASE: last eight CLOSED bars, no ninth-bar confirmation, old-zone latch regression, intrabar missing BUY/SELL retry, fixed geometry, no duplicates, expiry/rearm, history and diagnostics\n";
}
'''
with tempfile.TemporaryDirectory(prefix='fix2-setup-') as tmp:
 cpp=Path(tmp)/'c.cpp';exe=Path(tmp)/'c';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
