"""Execute the actual ATR position manager with a fake broker position book."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:void|double|bool) '+name+r'\([^{};]*\)\s*\{',s,re.M)
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('IsBaseStopModule','IsIndividualBaseModule','BaseATRTarget','ManageBaseATRPositions')).replace('double atr[];','std::vector<double> atr;')
h=r'''
#include <cmath>
#include <string>
#include <vector>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;
const int INVALID_HANDLE=-1,POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1;
const int POSITION_COMMENT=1,POSITION_TYPE=2,POSITION_PRICE_OPEN=3,POSITION_SL=4,POSITION_TP=5;
const int SYMBOL_TRADE_TICK_SIZE=6,SYMBOL_TRADE_STOPS_LEVEL=7,SYMBOL_TRADE_FREEZE_LEVEL=8;
int _Symbol=0,_Period=5,_Digits=2,h_atr=1,G_InstanceLock=1,Physical_BE_Trigger=1000,Physical_BE_Level=1;
double _Point=1,atrValue=2,bid=102,ask=103,freeze=0;
bool G_StopLatched=false,G_StateOK=true,G_ExecutionUncertain=false,mutate=true;
datetime closedBar=10;
bool TradingMutationAllowed(){return mutate;}
int StringFind(string text,string sub){auto p=text.find(sub);return p==string::npos?-1:(int)p;}
bool Positive(double x){return std::isfinite(x)&&x>0;}
double MathCeil(double x){return std::ceil(x);}double MathFloor(double x){return std::floor(x);}
double MathMax(double x,double y){return std::max(x,y);}double MathAbs(double x){return std::abs(x);}
double NormalizeDouble(double x,int d){double f=std::pow(10,d);return std::round(x*f)/f;}
datetime iTime(int,int,int){return closedBar;}
int CopyBuffer(int,int,int shift,int,std::vector<double>& v){assert(shift==1);v={atrValue};return 1;}
struct MqlTick{double bid,ask;};bool SymbolInfoTick(int,MqlTick& q){q.bid=bid;q.ask=ask;return true;}
double SymbolInfoDouble(int,int){return 0.01;}long SymbolInfoInteger(int,int){return (long)freeze;}
struct Position{bool own;string comment;int side;double entry,sl,tp;bool closed=false;};
std::vector<Position> positions;int selected=-1,modifications=0,closures=0,breakEvens=0;
int PositionsTotal(){return (int)positions.size();}
ulong PositionGetTicket(int i){selected=i;return i+1;}
bool IsOwnPosition(ulong ticket){selected=(int)ticket-1;return selected>=0 && selected<(int)positions.size() && positions[selected].own && !positions[selected].closed;}
string PositionGetString(int){return positions[selected].comment;}
long PositionGetInteger(int){return positions[selected].side;}
double PositionGetDouble(int p){auto& x=positions[selected];return p==POSITION_PRICE_OPEN?x.entry:(p==POSITION_SL?x.sl:x.tp);}
void SafetyLog(string){}
bool SafeClose(ulong t){assert(IsOwnPosition(t));positions[selected].closed=true;closures++;return true;}
bool SafeModify(ulong t,double sl,double tp){assert(IsOwnPosition(t));auto& x=positions[selected];assert(x.side==0?sl>x.sl:sl<x.sl);x.sl=sl;x.tp=tp;breakEvens++;return true;}
struct Trade{bool PositionModify(ulong t,double sl,double tp){assert(IsOwnPosition(t));assert(positions[selected].sl==sl);positions[selected].tp=tp;modifications++;return true;}}trade;
bool TradeResult(bool ok,bool,string){return ok;}
'''
cases=r'''
int main(){
 positions={{true,"SMC_Base_ATR",0,100,90,106},{true,"SMC_Base",0,100,90,0},{false,"SMC_Base_ATR",0,100,90,106}};
 ManageBaseATRPositions();assert(modifications==1 && positions[0].tp==104 && positions[0].sl==90);
 assert(positions[1].tp==0 && positions[2].tp==106); // own module and ownership isolation
 atrValue=3;ManageBaseATRPositions();assert(modifications==1 && positions[0].tp==104); // only closed-bar change
 closedBar++;ManageBaseATRPositions();assert(modifications==2 && positions[0].tp==106);
 G_StopLatched=true;closedBar++;atrValue=2;ManageBaseATRPositions();assert(modifications==2);
 G_StopLatched=false;ManageBaseATRPositions();assert(modifications==3 && positions[0].tp==104);
 freeze=5;closedBar++;atrValue=3;ManageBaseATRPositions();assert(modifications==3);freeze=0;
 closedBar++;atrValue=0;ManageBaseATRPositions();assert(modifications==3); // invalid ATR cannot remove TP/SL
 atrValue=3;ManageBaseATRPositions();assert(modifications==4 && positions[0].tp==106);
 Physical_BE_Trigger=1;ManageBaseATRPositions();assert(breakEvens==1 && positions[0].sl==101 && positions[0].tp==106);
 Physical_BE_Trigger=1000;atrValue=1;bid=103;ask=104;closedBar++;ManageBaseATRPositions();assert(closures==1); // shrunken ATR target already crossed
 positions={{true,"SMC_Base_ATR",1,100,110,94}};bid=97;ask=98;atrValue=2;closedBar++;
 ManageBaseATRPositions();assert(positions[0].tp==96 && positions[0].sl==110);
 atrValue=1;bid=96;ask=97;closedBar++;ManageBaseATRPositions();assert(closures==2); // mirrored SELL reached revised target
 positions={{true,"SMC_Base_Stop_B",0,100,90,109}};bid=102;ask=103;atrValue=2;closedBar++;
 ManageBaseATRPositions();assert(positions[0].tp==109); // nearest-extremum target must not be replaced by ATR
 Physical_BE_Trigger=1;ManageBaseATRPositions();assert(positions[0].sl==101 && positions[0].tp==109);
 std::cout<<"PASS: actual ATR manager updates on closed bars, preserves SL/ownership/BE and respects freeze/global stop\n";
}
'''
with tempfile.TemporaryDirectory(prefix='atr-manager-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
