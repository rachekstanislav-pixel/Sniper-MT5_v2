"""Execute actual pending review, deal callback and restart OCO recovery."""
from pathlib import Path
import re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|string|void) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('IsBaseStopModule','BaseStopGroup','BaseStopHasPosition','BaseStopHasPending','CancelBaseStopOrders','BaseStopFilledSince','ReviewOwnPending','OnTradeTransaction'))
h=r'''
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cmath>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;
const string _Symbol="GOLD";ulong MagicNumber=123;
const int POSITION_COMMENT=1,ORDER_COMMENT=2,ORDER_TYPE=3,ORDER_TIME_SETUP=4,ORDER_TP=5;
const int ORDER_TYPE_BUY_LIMIT=2,ORDER_TYPE_BUY_STOP=4,ORDER_TYPE_BUY_STOP_LIMIT=6,POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1;
const int SYMBOL_VOLUME_STEP=1,SYMBOL_VOLUME_MIN=2,ACCOUNT_BALANCE=1,ACCOUNT_MARGIN_FREE=2;
const int DEAL_SYMBOL=1,DEAL_MAGIC=2,DEAL_ENTRY=3,DEAL_COMMENT=4,DEAL_ORDER=5,DEAL_TIME=6,DEAL_TYPE=7,DEAL_POSITION_ID=8,DEAL_VOLUME=9,DEAL_PRICE=10,DEAL_PROFIT=11,DEAL_COMMISSION=12,DEAL_SWAP=13,DEAL_FEE=14,DEAL_REASON=15;
const int DEAL_ENTRY_IN=0,DEAL_ENTRY_OUT=1,DEAL_ENTRY_INOUT=2,DEAL_TYPE_BUY=0,DEAL_TYPE_SELL=1;
const int TRADE_TRANSACTION_DEAL_ADD=1,TIME_DATE=1,TIME_SECONDS=2;
const int INVALID_HANDLE=-1;int G_InstanceLock=1;
int _Period=5,_Digits=2,BaseMaxWaitBars=10;
bool DiagnosticMode=false,BaseUseStopOrders=true,G_BaseStopOCOTripped=false,G_BaseConsumed=false,G_StateOK=true,G_D1_DataReady=true,G_D1_Valid=true,G_Fibo_isUp=true;
datetime G_LastBuyTime=0,G_LastSellTime=0,now=1000;
struct Order{ulong id;string symbol,comment;ulong magic;int type;datetime setup;double tp;bool deleted=false;};
struct Position{ulong id;string symbol,comment;ulong magic;};
struct Deal{ulong id;string symbol,comment;ulong magic,order;int entry,side;datetime time;};
std::vector<Order> orders;std::vector<Position> positions;std::vector<Deal> deals;
std::map<ulong,string> historicalOrders;std::vector<ulong> history;
int selectedOrder=-1,selectedPosition=-1,deletions=0,saves=0;
bool historyOK=true,deleteOK=true,saveOK=true,policy=true;double risk=0,quoteBid=104,quoteAsk=105;
int StringFind(string t,string part){auto p=t.find(part);return p==string::npos?-1:(int)p;}
string StringSubstr(string t,int from){return t.substr(from);}long StringToInteger(string t){try{return std::stoll(t);}catch(...){return 0;}}
bool Positive(double x){return std::isfinite(x)&&x>0;}double MathMax(double a,double b){return std::max(a,b);}double MathFloor(double x){return std::floor(x);}
int OrdersTotal(){return (int)orders.size();}ulong OrderGetTicket(int i){selectedOrder=i;return orders[i].id;}
bool IsOwnOrder(ulong id){for(int i=0;i<(int)orders.size();i++)if(orders[i].id==id){selectedOrder=i;return !orders[i].deleted&&orders[i].symbol==_Symbol&&orders[i].magic==MagicNumber;}return false;}
string OrderGetString(int){return orders[selectedOrder].comment;}
long OrderGetInteger(int p){return p==ORDER_TYPE?orders[selectedOrder].type:orders[selectedOrder].setup;}
double OrderGetDouble(int){return orders[selectedOrder].tp;}
int PositionsTotal(){return (int)positions.size();}ulong PositionGetTicket(int i){selectedPosition=i;return positions[i].id;}
bool IsOwnPosition(ulong id){for(int i=0;i<(int)positions.size();i++)if(positions[i].id==id){selectedPosition=i;return positions[i].symbol==_Symbol&&positions[i].magic==MagicNumber;}return false;}
string PositionGetString(int){return positions[selectedPosition].comment;}
bool SafeDelete(ulong id){assert(IsOwnOrder(id));if(!deleteOK)return false;orders[selectedOrder].deleted=true;deletions++;return true;}
datetime TimeCurrent(){return now;}int PeriodSeconds(int tf){return tf*60;}
Deal& deal(ulong id){for(auto& d:deals)if(d.id==id)return d;assert(false);return deals[0];}
bool HistorySelect(datetime since,datetime until){history.clear();if(!historyOK)return false;for(auto d:deals)if(d.time>=since&&d.time<=until)history.push_back(d.id);return true;}
int HistoryDealsTotal(){return (int)history.size();}ulong HistoryDealGetTicket(int i){return history[i];}
string HistoryDealGetString(ulong id,int p){return p==DEAL_SYMBOL?deal(id).symbol:deal(id).comment;}
long HistoryDealGetInteger(ulong id,int p){auto& d=deal(id);switch(p){case DEAL_MAGIC:return d.magic;case DEAL_ENTRY:return d.entry;case DEAL_ORDER:return d.order;case DEAL_TIME:return d.time;case DEAL_TYPE:return d.side;default:return 0;}}
double HistoryDealGetDouble(ulong,int){return 0;}
string HistoryOrderGetString(ulong id,int){auto it=historicalOrders.find(id);return it==historicalOrders.end()?"":it->second;}
bool HistoryOrderSelect(ulong id){return historicalOrders.count(id);}
bool HistoryDealSelect(ulong id){for(auto d:deals)if(d.id==id)return true;return false;}
bool OwnExposure(double& r,double& bv,double& sv,double& margin){r=risk;bv=sv=margin=0;return true;}
double AccountInfoDouble(int p){return p==ACCOUNT_BALANCE?1000:500;}
double SymbolInfoDouble(string,int){return .01;}double GetDynamicGlobalRisk(){return 5;}
bool EntryPolicy(int,string,bool,bool){return policy;}
struct MqlTick{double bid,ask;};bool SymbolInfoTick(string,MqlTick& q){q.bid=quoteBid;q.ask=quoteAsk;return true;}
struct MqlTradeTransaction{int type;ulong deal,order;};struct MqlTradeRequest{};struct MqlTradeResult{};
string TimeToString(datetime t,int){return std::to_string(t);}string DoubleToString(double x,int){return std::to_string(x);}
template<typename... T>void Print(T...){ }void SafetyLog(string){}
bool SaveSafetyState(){saves++;return saveOK;}
void fixture(){
 orders={{1,"GOLD","SMC_Base_Stop_B:500",123,4,900,120}, {2,"GOLD","SMC_Base_Stop_S:500",123,5,901,90},
 {3,"GOLD","SMC_Comp_Limit",123,2,900,0},{4,"GOLD","SMC_Base_Stop_S:500",999,5,900,90}, {5,"EURUSD","SMC_Base_Stop_S:500",123,5,900,90}};
 positions.clear();deals.clear();historicalOrders.clear();history.clear();deletions=saves=0;
 G_InstanceLock=1;historyOK=deleteOK=saveOK=policy=G_StateOK=BaseUseStopOrders=true;
 DiagnosticMode=G_BaseStopOCOTripped=G_BaseConsumed=false;risk=0;quoteBid=104;quoteAsk=105;now=1000;G_LastBuyTime=G_LastSellTime=0;
}
'''
cases=r'''
int main(){
 fixture();ReviewOwnPending();assert(deletions==0);
 G_BaseStopOCOTripped=true;ReviewOwnPending();assert(deletions==2 && !orders[2].deleted && !orders[3].deleted && !orders[4].deleted);
 fixture();positions={{10,"GOLD","SMC_Base_Stop_B:500",123}};ReviewOwnPending();assert(deletions==2);
 // Restart recovery: no position remains; the first side filled even before sibling setup.
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:500",123,10,0,0,900}};ReviewOwnPending();assert(deletions==2);
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:400",123,10,0,0,950}};ReviewOwnPending();assert(deletions==0); // unrelated zone must not cancel
 fixture();deals={{101,"GOLD","broker-fill",123,10,0,0,950}};historicalOrders[10]="SMC_Base_Stop_B:500";ReviewOwnPending();assert(deletions==2);
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:500",999,10,0,0,950}};ReviewOwnPending();assert(deletions==0);
 fixture();historyOK=false;ReviewOwnPending();assert(deletions==2); // fail closed with unavailable history
 fixture();now=4001;ReviewOwnPending();assert(deletions==2); // client expiry even if broker has no specified expiration
 fixture();BaseUseStopOrders=false;ReviewOwnPending();assert(deletions==2);
 fixture();quoteBid=121;quoteAsk=122;ReviewOwnPending();assert(orders[0].deleted && !orders[1].deleted); // target exhausted without fill
 fixture();DiagnosticMode=true;G_BaseStopOCOTripped=true;ReviewOwnPending();assert(deletions==0);
 fixture();DiagnosticMode=true;deals={{101,"GOLD","SMC_Base_Stop_B:500",123,10,0,0,950}};
 OnTradeTransaction({1,101,10},{},{});assert(deletions==0 && saves==0); // diagnostics must never write safety state
 fixture();G_InstanceLock=INVALID_HANDLE;deals={{101,"GOLD","SMC_Base_Stop_B:500",123,10,0,0,950}};
 OnTradeTransaction({1,101,10},{},{});assert(deletions==0 && saves==0);
 // Real deal callback: cooldown and OCO are driven by own entry fills, never foreign/exit deals.
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:500",123,10,0,0,950}};
 OnTradeTransaction({TRADE_TRANSACTION_DEAL_ADD,101,10},{},{});assert(deletions==2 && G_BaseStopOCOTripped && G_LastBuyTime==950 && saves==1);
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:500",999,10,0,0,950}};
 OnTradeTransaction({1,101,10},{},{});assert(deletions==0 && saves==0);
 fixture();deals={{101,"GOLD","SMC_Base_Stop_B:500",123,10,1,0,950}};
 OnTradeTransaction({1,101,10},{},{});assert(deletions==0 && saves==0);
 fixture();deals={{101,"GOLD","SMC_Base_Stop_S:500",123,10,0,1,960}};deleteOK=false;
 OnTradeTransaction({1,101,10},{},{});assert(deletions==0 && G_BaseStopOCOTripped && G_LastSellTime==960);
 deleteOK=true;ReviewOwnPending();assert(deletions==2); // retry cancellation on a later event
 std::cout<<"PASS: actual OCO callbacks/review, group recovery after restart, partial-fill cancellation retry, expiry and Symbol/Magic isolation\n";
}
'''
with tempfile.TemporaryDirectory(prefix='base-oco-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
