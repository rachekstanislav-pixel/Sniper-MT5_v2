"""Actual Stage1 exit manager + SafeModify, with durable claim/history/broker mocks."""
from pathlib import Path
import re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|string|void|double|int) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('Stage1WickStop','Stage1HalfVolume','IsStage1BaseModule','SafeModify','Stage1TryHalfExit','ManageStage1Position'))
funcs=funcs.replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars').replace('MqlRates bars[];','std::vector<MqlRates> bars;')
h=r'''
#include <cmath>
#include <string>
#include <vector>
#include <set>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;using uint=unsigned int;
const string _Symbol="GOLD";const ulong MagicNumber=777;int _Digits=2;double _Point=.01;
const int POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1,POSITION_TYPE=1,POSITION_SL=2,POSITION_PRICE_OPEN=3,POSITION_VOLUME=4,POSITION_IDENTIFIER=5,POSITION_COMMENT=6;
const int SYMBOL_TRADE_TICK_SIZE=1,SYMBOL_TRADE_STOPS_LEVEL=2,SYMBOL_TRADE_FREEZE_LEVEL=3,SYMBOL_VOLUME_STEP=4,SYMBOL_VOLUME_MIN=5;
const int DEAL_TYPE=1,DEAL_SYMBOL=2,DEAL_POSITION_ID=3,DEAL_ENTRY=4,DEAL_VOLUME=5,DEAL_MAGIC=6;
const int DEAL_TYPE_BUY=0,DEAL_TYPE_SELL=1,DEAL_ENTRY_IN=0,DEAL_ENTRY_OUT=1,DEAL_ENTRY_OUT_BY=3;
const int PERIOD_M5=5,SERIES_SYNCHRONIZED=0,FILE_COMMON=1,FILE_WRITE=2,FILE_BIN=4,INVALID_HANDLE=-1;
int G_InstanceLock=1,BaseTrailBars=5;double BasePipSize=.01,BaseHalfExitPips=1000,BaseTrailBufferPips=0;
string G_StateFile="test";bool mutations=true,own=true,history=true,writeOK=true,openOK=true,hedging=true,sendOK=true;
string comment="SMC_B65:123";int side=0,closeCalls=0,modifyCalls=0;double initial=.1,current=.1,entry=100,sl=90,bid=109.99,ask=110.01,lastClose=0;
uint retcode=10009;ulong orderResult=1;datetime now=10000;std::set<string> claims;string opened;
struct MqlRates{datetime time;double high,low;};struct MqlTick{double bid,ask;};
std::vector<MqlRates> candles;
struct Deal{int kind;double volume;};std::vector<Deal> deals;
int StringFind(string text,string sub){auto p=text.find(sub);return p==string::npos?-1:(int)p;}
bool Positive(double x){return std::isfinite(x)&&x>0;}bool MathIsValidNumber(double x){return std::isfinite(x);}
double MathMin(double x,double y){return std::min(x,y);}double MathMax(double x,double y){return std::max(x,y);}double MathFloor(double x){return std::floor(x);}double MathCeil(double x){return std::ceil(x);}double MathAbs(double x){return std::abs(x);}
double NormalizeDouble(double x,int d){double p=std::pow(10,d);return std::round(x*p)/p;}
template<typename T>int ArraySize(const std::vector<T>& x){return x.size();}template<typename T>void ArraySetAsSeries(T&,bool){}
bool TradingMutationAllowed(){return mutations;}bool IsOwnPosition(ulong t){return own&&t==1;}bool HedgingAccount(){return hedging;}
string PositionGetString(int){return comment;}
long PositionGetInteger(int p){return p==POSITION_TYPE?side:123;}
double PositionGetDouble(int p){if(p==POSITION_SL)return sl;if(p==POSITION_PRICE_OPEN)return entry;if(p==POSITION_VOLUME)return current;return 0;}
bool SymbolInfoTick(string,MqlTick& q){q={bid,ask};return true;}
double SymbolInfoDouble(string,int p){return p==SYMBOL_VOLUME_STEP||p==SYMBOL_VOLUME_MIN?.01:.01;}
long SymbolInfoInteger(string,int){return 10;}
string IntegerToString(long x){return std::to_string(x);}string DoubleToString(double x,int){return std::to_string(x);}
datetime TimeCurrent(){return now;}
bool FileIsExist(string p,int){return claims.count(p);}
int FileOpen(string p,int){opened=p;if(!openOK)return -1;claims.insert(p);return 1;}
void ResetLastError(){}int GetLastError(){return 0;}
uint FileWriteLong(int,long){return writeOK?8:0;}void FileFlush(int){}void FileClose(int){}
bool FileDelete(string p,int){claims.erase(p);return true;}
bool HistorySelectByPosition(ulong){return history;}int HistoryDealsTotal(){return deals.size();}
ulong HistoryDealGetTicket(int i){return i+1;}
long HistoryDealGetInteger(ulong d,int p){if(p==DEAL_TYPE)return side;if(p==DEAL_POSITION_ID)return 123;if(p==DEAL_ENTRY)return deals[d-1].kind;if(p==DEAL_MAGIC)return MagicNumber;return 0;}
string HistoryDealGetString(ulong,int){return _Symbol;}double HistoryDealGetDouble(ulong d,int){return deals[d-1].volume;}
bool SeriesInfoInteger(string,int tf,int){assert(tf==PERIOD_M5);return true;}
int CopyRates(string,int tf,int shift,int n,std::vector<MqlRates>& out){assert(tf==PERIOD_M5&&shift==1);out=candles;return out.size()==(unsigned)n?n:0;}
void SafetyLog(string){}template<typename... T>void Print(T...){}
bool TradeResult(bool ok,bool,string){return ok;}
bool DefiniteEntryRejection(uint code,ulong order,ulong,double){return code==10018&&order==0;}
struct Trade{
 void SetTypeFillingBySymbol(string){}
 bool PositionClosePartial(ulong,double v){assert(claims.count("test.half.123"));closeCalls++;lastClose=v;if(sendOK){current-=v;deals.push_back({DEAL_ENTRY_OUT,v});}return sendOK;}
 bool PositionModify(ulong,double stop,double tp){assert(tp==0);modifyCalls++;sl=stop;return true;}
 uint ResultRetcode(){return retcode;}ulong ResultOrder(){return orderResult;}ulong ResultDeal(){return orderResult;}double ResultVolume(){return sendOK?lastClose:0;}
}trade;
void fixture(){
 mutations=own=history=writeOK=openOK=hedging=sendOK=true;G_InstanceLock=1;comment="SMC_B65:123";
 side=0;closeCalls=modifyCalls=0;initial=current=.1;entry=100;sl=90;bid=109.99;ask=110.01;lastClose=0;
 claims.clear();deals={{DEAL_ENTRY_IN,.1}};retcode=10009;orderResult=1;now+=100;
 candles={{500,108,104},{400,107,103},{300,106,102},{200,105,101},{100,104,100.5}};
}
'''
cases=r'''
int main(){
 fixture();ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==1&&sl==100.5); // wick, NOT entry+BE
 fixture();bid=110;ask=110.02;ManageStage1Position(1);assert(closeCalls==1&&lastClose==.05&&current==.05);
 ManageStage1Position(1);assert(closeCalls==1); // repeating tick + persistent claim
 claims.clear();ManageStage1Position(1);assert(closeCalls==1); // restart recovered solely from deal history
 fixture();bid=110;ask=110.02;current=.01;deals={{DEAL_ENTRY_IN,.01}};
 ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==1&&current==.01); // minimum lot keeps trailing
 fixture();bid=110;history=false;ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==1);
 fixture();bid=110;openOK=false;ManageStage1Position(1);assert(closeCalls==0);
 fixture();bid=110;writeOK=false;ManageStage1Position(1);assert(closeCalls==0);
 fixture();bid=110;sendOK=false;retcode=10012;orderResult=0;ManageStage1Position(1);ManageStage1Position(1);
 assert(closeCalls==1&&claims.count("test.half.123")); // ambiguous timeout never blind-retried
 fixture();bid=110;sendOK=false;retcode=10018;orderResult=0;ManageStage1Position(1);
 assert(closeCalls==1&&!claims.count("test.half.123"));ManageStage1Position(1);assert(closeCalls==1);
 now+=61;sendOK=true;retcode=10009;orderResult=1;ManageStage1Position(1);assert(closeCalls==2);
 fixture();sl=105;ManageStage1Position(1);assert(modifyCalls==0&&sl==105); // never widen to wick
 fixture();bid=100.55;ask=100.57;ManageStage1Position(1);assert(modifyCalls==0); // broker stop/freeze distance
 fixture();side=1;comment="SMC_S35:123";entry=120;bid=109.98;ask=110;sl=125;candles[0].high=112;
 ManageStage1Position(1);assert(closeCalls==1&&sl==112); // sell max HIGH, ask-based trigger
 fixture();mutations=false;bid=110;ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==0&&claims.empty());
 fixture();own=false;bid=110;ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==0);
 fixture();comment="SMC_EMA";bid=110;ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==0);
 fixture();G_InstanceLock=-1;bid=110;ManageStage1Position(1);assert(closeCalls==0&&modifyCalls==0);
 std::cout<<"PASS Stage1 manager: bid/ask trigger, partial once, durable restart/timeout, min lot, closed wicks, no BE/TP, no widening, ownership/diagnostic gates\n";
}
'''
with tempfile.TemporaryDirectory(prefix='stage1-exit-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
