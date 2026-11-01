"""Actual D1/M15/OB state machine and orchestration, compiled with MT5 API doubles."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|void|int) '+name+r'\([^{};]*\)\s*\{',s,re.M)
 assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
state=s[s.index('struct OTEReclaimState {'):s.index('};',s.index('struct OTEReclaimState {'))+2]
functions='\n'.join(extract(n) for n in ('FindOTEOrderBlock','AdvanceOTEReclaim','OTEReclaimQuoteAllowed','CheckOTEReclaim'))
functions=functions.replace('const MqlRates &rates[]','const std::vector<MqlRates> &rates')
for name in ('bars','h4','history'):
 functions=functions.replace('MqlRates '+name+'[];', 'std::vector<MqlRates> '+name+';')
functions=functions.replace('double atr[];', 'std::vector<double> atr;')
h=r'''
#include <cmath>
#include <vector>
#include <string>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;
constexpr int PERIOD_M15=15,PERIOD_H4=240,SERIES_SYNCHRONIZED=0,POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1;
int _Symbol=0,_Digits=2,h_ote_atr=3;
struct MqlRates { datetime time;double open,high,low,close; };
bool Positive(double x){return std::isfinite(x)&&x>0;}
double MathMin(double a,double b){return std::min(a,b);}double MathMax(double a,double b){return std::max(a,b);}
double NormalizeDouble(double x,int d){double p=std::pow(10,d);return std::round(x*p)/p;}
int PeriodSeconds(int tf){return tf*60;}
template<typename T> int ArraySize(const std::vector<T>& v){return (int)v.size();}
template<typename T> void ArraySetAsSeries(T&,bool){}
bool RequireOTEReclaim=true,EnableSMC_OTE=true,G_D1_DataReady=true,G_D1_Valid=true;
int G_D1_Direction=1,MinSweepPoints=100,InvalidationPoints=500,OTEReclaimMaxBars=4;
double _Point=.01,G_Struct_Low=100,G_Struct_High=120,G_Fibo_790=104.2,OTEReclaimMaxDistanceATR=.5;
datetime G_D1_SourceDay=1000,G_OTEContextDay=0,G_OTEReclaimCheckedBar=0,G_OTEReclaimSignalBar=0,G_OTEReclaimDay=0;
double G_OTEContextLow=0,G_OTEContextHigh=0;int G_OTEContextDirection=0,G_OTEReclaimSide=-1;
std::vector<MqlRates> m15,h4rates,prior;
double atrValue=2,quoteBid=105,quoteAsk=105.1;
bool historyOK=true,atrOK=true,submissionAllowed=true;
int submissions=0,accepted=0,lastSide=-1;
string G_OTEEntryStatus="";
string lastReason;
bool SeriesInfoInteger(int,int,int){return historyOK;}
int CopyBuffer(int,int,int shift,int,std::vector<double>& a){assert(shift==1);a={atrValue};return atrOK?1:0;}
int CopyRates(int,int tf,int start,int count,std::vector<MqlRates>& v){
 if(tf==PERIOD_H4){v=h4rates;return (int)v.size();}
 if(start==1){v=m15;return (int)v.size();}
 v.clear();for(int i=0;i<count;i++)v.push_back({m15[0].time-900*(i+1),106,108,103,106});
 for(auto b:prior)for(auto& dest:v)if(dest.time==b.time)dest=b;
 return (int)v.size();
}
int iBarShift(int,int,datetime t,bool){return (int)((m15[0].time+900-t)/900);}
bool TradeOTE(double origin,double endpoint,double& lo,double& hi){double edge=endpoint+(origin-endpoint)*.790;lo=std::min(origin,edge);hi=std::max(origin,edge);return true;}
void SafetyLog(string s){lastReason=s;}
string TimeToString(datetime t){return std::to_string(t);}string DoubleToString(double x,int){return std::to_string(x);}
template<typename... T>void Print(T...){ }
void DrawDiagnosticSignal(string,int,datetime,double,string){}
struct MqlTick{double bid,ask;};bool SymbolInfoTick(int,MqlTick& q){q.bid=quoteBid;q.ask=quoteAsk;return true;}
bool SubmitEntry(int side,bool,double,double,string module){assert(module=="SMC_OTE_Reclaim");lastSide=side;submissions++;if(submissionAllowed)accepted++;return submissionAllowed;}
'''
fixtures=r'''
OTEReclaimState G_OTEReclaim{};
void fixture(){
 G_OTEReclaim={};G_OTEContextDay=0;G_OTEReclaimCheckedBar=0;G_OTEReclaimSignalBar=0;G_OTEContextDirection=0;
 G_D1_DataReady=G_D1_Valid=RequireOTEReclaim=EnableSMC_OTE=historyOK=atrOK=submissionAllowed=true;
 G_D1_SourceDay=1000;G_D1_Direction=1;G_Struct_Low=100;G_Struct_High=120;G_Fibo_790=104.2;
 submissions=accepted=0;lastSide=-1;lastReason="";prior.clear();quoteBid=105;quoteAsk=105.1;atrValue=2;
 m15={{57600,106,107,103,105.5},{56700,106,108,105,106}}; // sweep, red return: needs a later bullish close
 h4rates={{57600,112,114,111,113},{43200,106,114,104,112},{28800,108,110,100,105}};
}
void confirm(){m15={{58500,104.5,106,104,105.5},{57600,106,107,103,105.5}};}
'''
cases=r'''
int main(){
 fixture();CheckOTEReclaim();assert(G_OTEReclaim.active && submissions==0 && G_OTEReclaim.obLow==100);
 confirm();CheckOTEReclaim();assert(accepted==1 && lastSide==0 && G_OTEReclaimSignalBar==58500);
 CheckOTEReclaim();assert(submissions==1); // same closed M15 cannot replay
 fixture();m15[0].open=104.5;CheckOTEReclaim();assert(accepted==1); // same-candle bullish return above .790 is legal
 fixture();CheckOTEReclaim();confirm();m15[0].low=98;m15[0].close=99;CheckOTEReclaim();assert(!G_OTEReclaim.active && submissions==0); // close invalidates OB
 fixture();m15[0].low=99;CheckOTEReclaim();assert(G_OTEReclaim.active); // wick outside OB is allowed
 confirm();CheckOTEReclaim();assert(accepted==1);
 fixture();h4rates[1].time=57600;CheckOTEReclaim();assert(submissions==0 && !G_OTEReclaim.active); // unclosed displacement cannot form an OB
 fixture();h4rates[2].low=109;CheckOTEReclaim();assert(submissions==0 && !G_OTEReclaim.active); // OB does not overlap deep OTE
 fixture();CheckOTEReclaim();confirm();quoteBid=108;quoteAsk=108.1;CheckOTEReclaim();assert(submissions==0 && !G_OTEReclaim.active); // chase rejected
 fixture();CheckOTEReclaim();confirm();quoteBid=104;quoteAsk=104.1;CheckOTEReclaim();assert(submissions==0); // return lost
 fixture();CheckOTEReclaim();confirm();G_D1_SourceDay=60000;CheckOTEReclaim();assert(!G_OTEReclaim.active && submissions==0); // day changed
 fixture();CheckOTEReclaim();confirm();submissionAllowed=false;CheckOTEReclaim();assert(submissions==1 && accepted==0);
 submissionAllowed=true;CheckOTEReclaim();assert(submissions==1); // policy rejection cannot replay the confirmation
 fixture();CheckOTEReclaim();confirm();m15[0].time=61200;CheckOTEReclaim();assert(!G_OTEReclaim.active && submissions==0); // expiry across missed candles
 fixture();RequireOTEReclaim=false;CheckOTEReclaim();assert(submissions==0); // legacy mode unchanged
 fixture();historyOK=false;CheckOTEReclaim();assert(submissions==0);
 fixture();atrOK=false;CheckOTEReclaim();assert(submissions==0);
 // Already invalidated blocks may not be resurrected at the sweep.
 fixture();m15[0].time=59400;m15[1].time=58500;prior={{57600,102,103,98,99}};
 CheckOTEReclaim();assert(submissions==0 && !G_OTEReclaim.active);
 // SELL mirror: bullish origin, bearish displacement, sweep above .790 and bearish close below.
 fixture();G_D1_Direction=-1;G_Fibo_790=115.8;quoteBid=114.9;quoteAsk=115;
 m15={{57600,115.5,117,114,115},{56700,114,116,113,114}};
 h4rates={{57600,109,111,108,110},{43200,114,116,106,108},{28800,112,120,110,115}};
 CheckOTEReclaim();assert(accepted==1 && lastSide==1);
 // Direct state tests: doji isn't confirmation; strict OB-close invalidation; bounded waiting.
 fixture();OTEReclaimState st{};st.active=true;st.obLow=100;st.obHigh=110;st.extreme=103;st.sweepTime=57600;
 MqlRates bar{57600,105,107,103,105};assert(AdvanceOTEReclaim(st,true,bar,104.2,4)==0);
 bar={58500,105,107,104,106};assert(AdvanceOTEReclaim(st,true,bar,104.2,4)==1 && !st.active);
 assert(OTEReclaimQuoteAllowed(true,105,105.1,104.2,2,.5)); // outside the old zone is intended
 assert(!OTEReclaimQuoteAllowed(true,105,104,104.2,2,.5)); // invalid spread
 assert(!OTEReclaimQuoteAllowed(false,114.9,115,115.8,0,.5));
 std::cout<<"PASS: actual OTE orchestration/state machine, historical OB proof, M15 confirmation, expiry, quote limits, BUY/SELL and no replay\n";
}
'''
with tempfile.TemporaryDirectory(prefix='ote-check-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+state+'\n'+fixtures+'\n'+functions+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
