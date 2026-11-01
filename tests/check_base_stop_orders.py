"""Compile actual stop request and pivot target code with a deterministic fake broker."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'Sniper_Manager_v3_6_5_M5_BASE_OTE_FIX_1.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|string|void|double|int) '+name+r'\([^{};]*\)\s*\{',s,re.M)
 assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('IsBaseStopModule','IsIndividualBaseModule','BaseExtremumTarget','BaseATRTarget','LogPortfolioBlock','LogEntrySizeFailure','SubmitEntry'))
funcs=funcs.replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars')
h=r'''
#include <cmath>
#include <string>
#include <vector>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;
using ENUM_ORDER_TYPE=int;using ENUM_ORDER_TYPE_TIME=int;
const int POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1,ORDER_TYPE_BUY=0,ORDER_TYPE_SELL=1,ORDER_TYPE_BUY_LIMIT=2,ORDER_TYPE_SELL_LIMIT=3,ORDER_TYPE_BUY_STOP=4,ORDER_TYPE_SELL_STOP=5,ORDER_TYPE_SELL_STOP_LIMIT=7;
const int SYMBOL_TRADE_TICK_SIZE=1,SYMBOL_TRADE_STOPS_LEVEL=2,SYMBOL_ORDER_MODE=3,SYMBOL_VOLUME_STEP=4,SYMBOL_VOLUME_MIN=5,SYMBOL_FILLING_MODE=6,SYMBOL_TRADE_EXEMODE=7,SYMBOL_EXPIRATION_MODE=8;
const int SYMBOL_ORDER_STOP=4,SYMBOL_ORDER_STOP_LIMIT=8,SYMBOL_EXPIRATION_SPECIFIED=4;
const int ACCOUNT_BALANCE=1,ACCOUNT_MARGIN_FREE=2,TRADE_ACTION_PENDING=1,TRADE_ACTION_DEAL=2,ORDER_TIME_GTC=0,ORDER_TIME_SPECIFIED=2;
const int ORDER_FILLING_RETURN=2,ORDER_FILLING_FOK=0,ORDER_FILLING_IOC=1,SYMBOL_FILLING_FOK=1,SYMBOL_FILLING_IOC=2,SYMBOL_TRADE_EXECUTION_MARKET=2,TRADE_RETCODE_DONE=10009;
int _Symbol=0,_Digits=2,_Period=5,BaseStopLimitOffsetPoints=15,BaseMaxWaitBars=10;
ulong MagicNumber=123;double _Point=.01;bool G_ExecutionUncertain=false,G_StateOK=true,BaseStopBothDirections=true,AllowD1OTEAgainstH4=false,AllowOTEReclaimAgainstH4=true;
int SF_ConfirmedDirection=1;double CounterTrendRiskMult=.5;datetime G_EntryRetryAfter=0,G_LastBuyTime=0,G_LastSellTime=0;
int StringFind(string text,string sub){auto p=text.find(sub);return p==string::npos?-1:(int)p;}
bool MathIsValidNumber(double x){return std::isfinite(x);}
bool Positive(double x){return std::isfinite(x)&&x>0;}double MathCeil(double x){return std::ceil(x);}double MathFloor(double x){return std::floor(x);}double MathRound(double x){return std::round(x);}
double MathMin(double a,double b){return std::min(a,b);}
double MathAbs(double x){return std::abs(x);}double MathMax(double a,double b){return std::max(a,b);}
double NormalizeDouble(double x,int d){double p=std::pow(10,d);return std::round(x*p)/p;}
template<typename T>int ArraySize(const std::vector<T>& a){return (int)a.size();}
struct MqlRates{double high,low;};
struct MqlTick{double bid,ask;};
struct MqlTradeRequest{int action=0,type=0,symbol=0,type_time=0,type_filling=0,deviation=0;ulong magic=0;double volume=0,price=0,sl=0,tp=0,stoplimit=0;string comment;datetime expiration=0;};
struct MqlTradeCheckResult{int retcode=0;string comment;};
double balanceValue=1000;
string G_BaseEntryStatus="",G_OTEEntryStatus="";
MqlTradeRequest checked,sent;double quoteBid=104,quoteAsk=105,riskBefore=0,buyBefore=0,sellBefore=0,marginBefore=0;
long allowedModes=SYMBOL_ORDER_STOP|SYMBOL_ORDER_STOP_LIMIT;bool policy=true,checkOK=true,sendOK=true,visible=true,canSave=true,exposureOK=true;
int saves=0,network=0;string reason;
void RefreshMarketContext(){}void CheckEquityProtection(){}
bool EntryPolicy(int,string,bool,bool){return policy && !G_ExecutionUncertain && G_StateOK;}
datetime TimeCurrent(){return 1000;}
int PeriodSeconds(int tf){return tf*60;}
bool SymbolInfoTick(int,MqlTick& q){q.bid=quoteBid;q.ask=quoteAsk;return true;}
double SymbolInfoDouble(int,int prop){if(prop==SYMBOL_VOLUME_STEP || prop==SYMBOL_VOLUME_MIN)return .01;return .01;}
long SymbolInfoInteger(int,int prop){switch(prop){case SYMBOL_TRADE_STOPS_LEVEL:return 10;case SYMBOL_ORDER_MODE:return allowedModes;case SYMBOL_FILLING_MODE:return SYMBOL_FILLING_FOK;case SYMBOL_EXPIRATION_MODE:return SYMBOL_EXPIRATION_SPECIFIED;default:return 0;}}
void SafetyLog(string s){reason=s;}
bool SafeVolume(int,double,double,double& v,double mult){v=.1*mult;return true;}
bool OwnExposure(double& risk,double& bv,double& sv,double& margin){risk=riskBefore;bv=buyBefore;sv=sellBefore;margin=marginBefore;return exposureOK;}
bool LossAtSL(int,double vol,double entry,double sl,double& loss){loss=vol*std::abs(entry-sl)*10;return true;}
double AccountInfoDouble(int prop){return prop==ACCOUNT_BALANCE?balanceValue:500;}
double GetDynamicGlobalRisk(){return 5;}double GetDynamicRisk(){return 2;}
bool OrderCalcMargin(int,int,double v,double,double& m){m=v*100;return true;}
bool OrderCheck(const MqlTradeRequest& r,MqlTradeCheckResult& check){checked=r;check.retcode=0;return checkOK;}
string IntegerToString(long x){return std::to_string(x);}string DoubleToString(double x,int){return std::to_string(x);}
template<typename... T>void Print(T...){ }
bool SaveSafetyState(){saves++;return canSave;}
void AuditSubmission(string,bool,bool){}
bool IsOwnOrder(ulong x){return visible && x==123;}bool IsOwnPosition(ulong){return false;}
bool TradeResult(bool ok,bool,string){return ok;}
void ResolveEntryRejection(string){}
struct Trade{
 void SetAsyncMode(bool){}void SetDeviationInPoints(int){}void SetTypeFilling(int){}
 bool send(){assert(G_ExecutionUncertain && saves>=1);network++;return sendOK;}
 bool OrderOpen(int symbol,int type,double volume,double limit,double price,double sl,double tp,int time,datetime expires,string module){
 sent={};sent.symbol=symbol;sent.type=type;sent.volume=volume;sent.stoplimit=limit;sent.price=price;sent.sl=sl;sent.tp=tp;sent.type_time=time;sent.expiration=expires;sent.comment=module;return send();}
 bool BuyLimit(double,double,int,double,double,int,int,string){sent.type=ORDER_TYPE_BUY_LIMIT;return send();}
 bool SellLimit(double,double,int,double,double,int,int,string){sent.type=ORDER_TYPE_SELL_LIMIT;return send();}
 bool Buy(double volume,int,double price,double sl,double tp,string){sent.type=ORDER_TYPE_BUY;sent.volume=volume;sent.price=price;sent.sl=sl;sent.tp=tp;return send();}
 bool Sell(double volume,int,double price,double sl,double tp,string){sent.type=ORDER_TYPE_SELL;sent.volume=volume;sent.price=price;sent.sl=sl;sent.tp=tp;return send();}
 ulong ResultOrder(){return 123;}ulong ResultDeal(){return 123;}double ResultVolume(){return sent.volume;}
}trade;
void fixture(){
 G_ExecutionUncertain=false;G_StateOK=true;G_EntryRetryAfter=0;saves=network=0;checked={};sent={};reason="";
 balanceValue=1000;quoteBid=104;quoteAsk=105;riskBefore=buyBefore=sellBefore=marginBefore=0;
 policy=checkOK=sendOK=visible=canSave=exposureOK=true;allowedModes=SYMBOL_ORDER_STOP|SYMBOL_ORDER_STOP_LIMIT;
}
'''
cases=r'''
int main(){
 assert(IsBaseStopModule("SMC_Base_Stop_B:100"));assert(!IsBaseStopModule("OTHER:100"));
 fixture();assert(SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120));
 assert(sent.type==ORDER_TYPE_BUY_STOP && sent.price==110 && sent.sl==100 && sent.tp==120 && sent.stoplimit==0);
 assert(checked.type==sent.type && checked.tp==sent.tp && checked.price==sent.price);
 assert(sent.type_time==ORDER_TIME_SPECIFIED && sent.expiration==4000 && !G_ExecutionUncertain);
 fixture();assert(SubmitEntry(1,true,100,110,"SMC_Base_Stop_S:100",0,1,90));assert(sent.type==ORDER_TYPE_SELL_STOP && sent.tp==90);
 fixture();quoteAsk=110;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0); // crossed trigger
 fixture();quoteBid=100;assert(!SubmitEntry(1,true,100,110,"SMC_Base_Stop_S:100",0,1,90) && network==0);
 fixture();assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,110) && network==0); // no target
 fixture();allowedModes=0;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0);
 fixture();riskBefore=49;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0); // aggregate cash risk
 fixture();buyBefore=.1;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0); // direction volume cap
 fixture();marginBefore=499;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0);
 fixture();checkOK=false;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0);
 fixture();canSave=false;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==0 && !G_StateOK);
 fixture();visible=false;assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120) && network==1 && G_ExecutionUncertain);
 fixture();assert(!SubmitEntry(0,true,110,100,"SMC_Comp_Limit",0,1,120) && network==0); // no module escape
 fixture();assert(!SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,2,120) && network==0); // unsupported stop-limit mode
 fixture();balanceValue=118.83;assert(SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120));assert(sent.volume==.01); // reduce to valid cap, preserve cash risk
 fixture();buyBefore=.06;assert(SubmitEntry(0,true,110,100,"SMC_Base_Stop_B:100",0,1,120));assert(sent.volume<=.04); // only remaining volume
 fixture();balanceValue=100;LogEntrySizeFailure("SMC_OTE_Reclaim",0,110,90,.5);
 assert(reason.find("MIN_LOT_RISK")!=string::npos && network==0 && saves==0); // diagnostics cannot force an unaffordable trade
 // Most recent pivot is 120; nearest by price is older 115. Unconfirmed first/last samples are excluded.
 std::vector<MqlRates> bars={{130,90},{110,95},{120,96},{110,97},{108,94},{115,95},{109,96},{108,97}};
 assert(BaseExtremumTarget(bars,0,1,111,false)==115);
 assert(BaseExtremumTarget(bars,0,1,111,true)==120);
 assert(BaseExtremumTarget(bars,0,1,125,false)==0);
 assert(BaseExtremumTarget(bars,0,1,115,false)==120); // target exactly at entry isn't profitable
 std::vector<MqlRates> mirror;for(auto b:bars)mirror.push_back({220-b.low,220-b.high});
 assert(BaseExtremumTarget(mirror,1,1,109,false)==105);
 assert(BaseExtremumTarget(mirror,1,1,109,true)==100);
 std::cout<<"PASS: actual pending submission, Buy Stop/Sell Stop types, native SL/TP, expiration, risk/margin/uncertain-state gates and confirmed targets\n";
}
'''
with tempfile.TemporaryDirectory(prefix='base-stop-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
