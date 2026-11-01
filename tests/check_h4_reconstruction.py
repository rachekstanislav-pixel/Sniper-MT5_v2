"""Replay the actual old/new H4 model with identical causal synthetic H4 candles."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
old=(r/'Sniper_Manager_v3_6_5_BASE_DETECT_2.mq5').read_text()
# The legacy function is a regression reference, not a trading bypass.
def extract(text,name):
 m=re.search(r'^(?:bool|void|int) '+name+r'\([^{};]*\)\s*\{',text,re.M);assert m,name
 return text[m.start():text.index('\n}',m.end())+2]
funcs='\n'.join(extract(s,n) for n in ('SF_RequiredLookback','SF_High','SF_Low','SF_Update'))+'\n'+extract(old,'SF_Update').replace('void SF_Update()', 'void SF_Update_Legacy()',1)
funcs=funcs.replace('SF_Pivot pivots[];', 'std::vector<SF_Pivot> pivots;').replace('int eventBreak[], eventPivot[], eventOrigin[], eventTrend[], eventType[];', 'std::vector<int> eventBreak,eventPivot,eventOrigin,eventTrend,eventType;')
h=r'''
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>
#include <random>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;using ulong=unsigned long;
int _Symbol=0,_Digits=2,SF_StructureTF=240,SF_LeftBars=2,SF_RightBars=2,SF_LookbackBars=40,SF_HistoryCount=8;
double _Point=.01,SF_MinSwingPoints=0,SF_BreakBufferPoints=0;
bool SF_DataReady=false,SF_ShowHistory=true,SF_ShowAnchor=true,DiagnosticMode=false,EnableAutoTrade=true,G_StateOK=true;
int SF_ConfirmedDirection=0;
datetime SF_LastClosed=0,SF_ConfirmedBreakTime=0,SF_OriginTime=0,SF_EndpointTime=0,SF_RebuildStartTime=0;
double SF_ConfirmedOrigin=0,SF_ConfirmedBreak=0;
string SF_PivotStructure,G_SF_EventLabel="BOS/INITIAL",SF_ActivePrefix,SF_Prefix="SF_",status;
const int SERIES_SYNCHRONIZED=0,clrAqua=1,clrSlateGray=2,clrSilver=3,clrGold=4;
struct MqlRates{datetime time;double open,high,low,close;};
struct SF_Pivot{datetime time;double price;int type,shift;};
std::vector<MqlRates> all,SF_Rates;int cursor=80,outside=0,changed=0;
double MathMin(double a,double b){return std::min(a,b);}double MathMax(double a,double b){return std::max(a,b);}double MathAbs(double a){return std::abs(a);}
template<typename T>int ArraySize(const std::vector<T>& v){return (int)v.size();}
template<typename T>void ArrayResize(std::vector<T>& v,int n){v.resize(n);}
template<typename T>void ArraySetAsSeries(T&,bool){}
int Bars(int,int){return cursor+1;}
datetime iTime(int,int,int shift){return cursor-shift>=0?all[cursor-shift].time:0;}
int iBarShift(int,int,datetime t,bool){for(int i=cursor;i>=0;i--)if(all[i].time==t)return cursor-i;return -1;}
bool SeriesInfoInteger(int,int,int){return true;}
int CopyRates(int,int,int start,int count,std::vector<MqlRates>& out){out.clear();for(int i=start;i<start+count&&cursor-i>=0;i++)out.push_back(all[cursor-i]);return (int)out.size();}
ulong GetTickCount64(){static ulong at=0;return at+=2000;}
void SF_Clear(){}void SF_Status(string text){status=text;}
void SafetyLog(string reason){if(reason.find("outside reconstruction")!=string::npos)outside++;if(reason.find("same event changed")!=string::npos)changed++;}
template<typename... T>void Print(T...){ }
string IntegerToString(long x){return std::to_string(x);}string TimeToString(datetime t){return std::to_string(t);}string DoubleToString(double x,int){return std::to_string(x);}
template<typename... T>void DrawConfirmedPivotLabels(T...){ }template<typename... T>void DrawStructureEvent(T...){ }
template<typename... T>void SF_Trend(T...){ }template<typename... T>void SF_Line(T...){ }template<typename... T>void SF_OTE(T...){ }
bool H4Retracement(int dir,double origin,double end,double ratio,double& out){if(dir==0||origin==end)return false;out=end+(origin-end)*ratio;return true;}
bool SaveSafetyState(){return true;}
'''
cases=r'''
int main(int argc,char** argv){
 assert(SF_RequiredLookback(300,1000,3,301,0)==301);
 assert(SF_RequiredLookback(300,1000,3,0,50)==350);
 assert(SF_RequiredLookback(300,302,3,0,0)==0);
 assert(SF_RequiredLookback(300,10000,3,5001,0)==0);
 bool legacy=argc>1&&string(argv[1])!="pinned";
 std::mt19937 gen(argc>2?std::stoul(argv[2]):1729);std::normal_distribution<double> noise(0,1.2);double close=150;
 for(int i=0;i<450;i++){double open=close;close+=noise(gen);double wick=std::abs(noise(gen))*.3+.05;all.push_back({100000+(datetime)i*14400,open,std::max(open,close)+wick,std::min(open,close)-wick,close});}
 int ready=0;datetime lastEvent=0;
 for(cursor=80;cursor<440;cursor++){
  if(legacy)SF_Update_Legacy();else SF_Update();
  if(SF_DataReady){ready++;assert(SF_LastClosed==iTime(0,0,1));assert(SF_ConfirmedBreakTime<=SF_LastClosed);assert(SF_ConfirmedBreakTime>=lastEvent);lastEvent=SF_ConfirmedBreakTime;}
 }
 std::cout<<(legacy?"LEGACY":"PINNED")<<" ready="<<ready<<" outside="<<outside<<" changed="<<changed<<std::endl;
 if(legacy)assert(outside>0);else assert(outside==0&&changed==0&&ready>300);
}
'''
with tempfile.TemporaryDirectory(prefix='h4-rebuild-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe),'legacy','2'],check=True)
 subprocess.run([str(exe),'pinned','2'],check=True)
print('PASS: moving-window regression reproduced in actual old SF_Update; pinned reconstruction preserves monotonic closed events without bypassing guards')
