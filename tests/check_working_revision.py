"""Compile selected *actual* MQL functions as C++ with deterministic MT5 API doubles.
This exercises decision logic, not MQL compilation, broker execution or chart rendering.
"""
from pathlib import Path
import subprocess, tempfile, re, hashlib, json
root=Path(__file__).resolve().parents[1]
s=(root/'Sniper_Manager_v3_6_5_M5_BASE_OTE_FIX_1.mq5').read_text()
base=(root/'baseline/Sniper_Manager_v3_6_5_VISUAL_AUDIT.mq5').read_text(encoding='utf-8-sig')
def function(text,name):
 m=re.search(r'^(?:bool|void|double|int|string) '+re.escape(name)+r'\([^{};]*\)\s*\{',text,re.M)
 if not m: raise RuntimeError(name)
 # Functions in this source end on their own unindented closing brace.
 end=text.index('\n}',m.end())+2
 return text[m.start():end]
# These risk, management and visual geometry functions must remain literally unchanged.
unchanged=['GetDynamicRisk','GetDynamicGlobalRisk','SafeVolume','OwnExposure',
'LossAtSL','SafeModify','SafeClose','SafeDelete','CheckEquityProtection',
'PaintSignalViews','UpdatePreviousDayFibo','UpdateH4Zones','UpdateLegacyStructureVisuals']
for name in unchanged:
 assert function(s,name)==function(base,name), f'Unexpected change: {name}'
# BASE stop placements now obey cooldown, unlike the paired compression limit.
policy=function(s,'EntryPolicy').replace('(!pending || IsBaseStopModule(comment))','!pending')
assert policy==function(base,'EntryPolicy'), 'Unexpected change outside the new BASE pending cooldown guard'
functions='\n'.join(function(s,n) for n in ['IsBaseStopModule','DirectionAllowed','SafeVolume','CheckCompressionPhase'])
functions=functions.replace('double atr_val[], atr_ma_val[];', 'std::vector<double> atr_val, atr_ma_val;')
harness=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>
#include <limits>
using string=std::string;
using datetime=long long;
int StringFind(string text,string sub){auto p=text.find(sub);return p==string::npos?-1:(int)p;}
bool BaseUseStopOrders=false,BaseStopBothDirections=true;
constexpr int POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1,PERIOD_M15=15;
constexpr int SYMBOL_ASK=1,SYMBOL_BID=2,SERIES_SYNCHRONIZED=3,MODE_HIGH=4,MODE_LOW=5;
constexpr int SYMBOL_VOLUME_STEP=6,SYMBOL_VOLUME_MIN=7,SYMBOL_VOLUME_MAX=8,SYMBOL_TRADE_TICK_SIZE=9,SYMBOL_TRADE_TICK_VALUE_LOSS=10,ACCOUNT_BALANCE=11;
int _Symbol=0,_Period=5,_Digits=2,AUDIT_COMP=1,h_atr=1,h_atr_ma=2;
double _Point=0.01;
bool MathIsValidNumber(double x){return std::isfinite(x);}
bool Positive(double x){return std::isfinite(x)&&x>0;}
double MathMax(double x,double y){return std::max(x,y);}
double MathMin(double x,double y){return std::min(x,y);}
double MathFloor(double x){return std::floor(x);}
double NormalizeDouble(double x,int digits){double d=std::pow(10,digits);return std::round(x*d)/d;}
bool G_D1_DataReady=true,G_D1_Valid=true,G_Fibo_isUp=true;
bool G_Compression_Active=false,G_CompEntryDone=false;
bool EnableAutoTrade=true,DiagnosticMode=false,EnableSMC_Comp=true;
double G_CompHigh=0,G_CompLow=0;
datetime G_CompDay=0,G_CompRetryAt=0,G_D1_SourceDay=10;
int G_CompDirection=0,InvalidationPoints=500;
bool D1_RequireDirectionForEntries=false,AllowOTEReclaimAgainstH4=false,AllowD1OTEAgainstH4=false;
bool EnforceH4Direction=true,BlockD1H4ConflictForEntries=true;
int G_D1_Direction=1,SF_ConfirmedDirection=1,G_OTEReclaimSide=0;
datetime G_OTEReclaimSignalBar=99,G_OTEReclaimDay=10;
bool structureOK=true;
bool StructureCurrent(){return structureOK;}
datetime now=100;
datetime TimeCurrent(){return now;}
datetime iTime(int,int,int shift){return shift==1?99:100;}
double atr=1,atrma=2;
bool bufferOK=true,historyOK=true,gate=true,uncertain=false;
int successful=0,pending=0,attempts=0,deletes=0;
int CopyBuffer(int handle,int,int,int,std::vector<double>& out){out={handle==h_atr?atr:atrma};return bufferOK?1:0;}
void AuditModuleCall(int){} void AuditModuleRead(int){}
void DeleteOrdersByComment(string){deletes++;}
bool SeriesInfoInteger(int,int,int){return historyOK;}
int Bars(int,int){return 100;}
int iHighest(int,int,int,int,int){return 0;} int iLowest(int,int,int,int,int){return 0;}
double iHigh(int,int,int){return 120;} double iLow(int,int,int){return 100;}
void DrawDiagnosticSignal(string,int,datetime,double,string){}
struct MqlTick{double ask=111,bid=110;};
bool SymbolInfoTick(int,MqlTick&){return true;}
bool SubmitEntry(int,bool isPending,double,double,string){
 if(isPending){pending++;return true;}
 attempts++;
 if(!gate||uncertain)return false;
 successful++;return true;
}
void SafetyLog(string){}
double step=0.01,minV=0.01,maxV=100,balance=1000,unitLoss=1000;
double SymbolInfoDouble(int,int prop){
 switch(prop){case SYMBOL_VOLUME_STEP:return step;case SYMBOL_VOLUME_MIN:return minV;case SYMBOL_VOLUME_MAX:return maxV;case SYMBOL_TRADE_TICK_SIZE:return 0.01;case SYMBOL_TRADE_TICK_VALUE_LOSS:return 1;default:return 0;}
}
double AccountInfoDouble(int){return balance;}
double GetDynamicRisk(){return 2;}
bool LossAtSL(int,double volume,double,double,double& loss){loss=volume*unitLoss;return true;}
'''
cases=r'''
int main(){
 // Execute original working compression function: temporary rejection does not consume phase.
 gate=false;CheckCompressionPhase();assert(G_Compression_Active && !G_CompEntryDone && successful==0);
 gate=true;now=102;CheckCompressionPhase();assert(successful==0); // throttle
 now=106;CheckCompressionPhase();assert(successful==1 && pending==1 && G_CompEntryDone);
 now=112;CheckCompressionPhase();assert(successful==1); // one success per phase
 atr=3;CheckCompressionPhase();assert(!G_Compression_Active);
 atr=1;now=118;CheckCompressionPhase();assert(successful==2);
 // A new daily context cannot inherit a consumed old phase.
 G_D1_SourceDay=20;now=124;CheckCompressionPhase();assert(successful==3 && G_CompDay==20);
 G_D1_DataReady=false;CheckCompressionPhase();assert(!G_Compression_Active);
 G_D1_DataReady=true;uncertain=true;now=130;CheckCompressionPhase();now=136;CheckCompressionPhase();assert(successful==3);
 uncertain=false;bufferOK=false;now=142;CheckCompressionPhase();assert(successful==3);
 bufferOK=true;DiagnosticMode=true;CheckCompressionPhase();assert(successful==3);
 DiagnosticMode=false;EnableSMC_Comp=false;CheckCompressionPhase();assert(successful==3);
 EnableSMC_Comp=true;EnableAutoTrade=false;CheckCompressionPhase();assert(successful==3);
 EnableAutoTrade=true;now=148;CheckCompressionPhase();assert(successful==4);
 // H4 exception is scoped; missing data and stale confirmation cannot be waived.
 G_D1_SourceDay=G_OTEReclaimDay=10;SF_ConfirmedDirection=-1;string why;
 assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));
 AllowOTEReclaimAgainstH4=true;assert(DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));
 assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Comp"));
 assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE"));
 structureOK=false;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));structureOK=true;
 G_OTEReclaimSignalBar=98;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));G_OTEReclaimSignalBar=99;
 G_D1_DataReady=false;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));G_D1_DataReady=true;
 G_D1_Direction=-1;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_OTE_Reclaim"));G_D1_Direction=1;
 // Two-sided BASE exception is scoped and retains all market-data prerequisites.
 BaseUseStopOrders=true;BaseStopBothDirections=true;G_D1_Direction=1;SF_ConfirmedDirection=-1;
 assert(DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Base_Stop_B:1"));
 assert(DirectionAllowed(POSITION_TYPE_SELL,why,"SMC_Base_Stop_S:1"));
 D1_RequireDirectionForEntries=true;assert(DirectionAllowed(POSITION_TYPE_SELL,why,"SMC_Base_Stop_S:1"));D1_RequireDirectionForEntries=false;
 assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Comp"));
 G_D1_Valid=false;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Base_Stop_B:1"));G_D1_Valid=true;
 structureOK=false;assert(!DirectionAllowed(POSITION_TYPE_SELL,why,"SMC_Base_Stop_S:1"));structureOK=true;
 G_D1_DataReady=false;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Base_Stop_B:1"));G_D1_DataReady=true;
 BaseStopBothDirections=false;assert(!DirectionAllowed(POSITION_TYPE_BUY,why,"SMC_Base_Stop_B:1"));
 BaseUseStopOrders=false;BaseStopBothDirections=true;
 // Actual unchanged lot sizing: half cash budget, no forced minimum above budget.
 double volume=0;assert(SafeVolume(0,110,100,volume,1.0));assert(std::abs(volume-0.02)<1e-9);
 assert(SafeVolume(0,110,100,volume,0.5));assert(std::abs(volume-0.01)<1e-9);
 unitLoss=2000;assert(!SafeVolume(0,110,100,volume,0.5));assert(volume==0);
 assert(!SafeVolume(0,110,100,volume,1.5));
 std::cout<<"PASS: compression lifecycle, H4 policy and dynamic volume cases\n";
}
'''
with tempfile.TemporaryDirectory(prefix='sniper-check-') as tmp:
 cpp=Path(tmp)/'checks.cpp'; exe=Path(tmp)/'checks'
 cpp.write_text(harness+'\n'+functions+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print(f'PASS: {len(unchanged)} existing risk/management/geometry functions unchanged')
