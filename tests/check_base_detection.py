"""Actual closed-bar BASE classifier, data adapter and independent visual model."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];s=(root/'Sniper_Manager_v3_6_5_M5_BASE_OTE_FIX_1.mq5').read_text()
def extract(name):
 m=re.search(r'^(?:bool|void) '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m,name
 return s[m.start():s.index('\n}',m.end())+2]
state=s[s.index('struct BaseZone {'):s.index('};',s.index('struct BaseZone {'))+2]
funcs='\n'.join(extract(n) for n in ('EvaluateBaseWindow','SelectBaseZone','ReadBaseZone','UpdateBaseZoneModel'))
funcs=funcs.replace('const MqlRates &rates[]','const std::vector<MqlRates> &rates').replace('const double &atr[]','const std::vector<double> &atr')
funcs=funcs.replace('MqlRates rates[]; double atr[];', 'std::vector<MqlRates> rates; std::vector<double> atr;')
h=r'''
#include <cmath>
#include <string>
#include <vector>
#include <cassert>
#include <iostream>
using string=std::string;using datetime=long long;
struct MqlRates{datetime time;double open,high,low,close;};
int _Symbol=0,_Period=5,h_atr=1,_Digits=2,BaseMinBars=6,BaseMaxBars=24;
const int SERIES_SYNCHRONIZED=0,clrDarkGray=0;
double BaseMaxRangeATR=4,BaseMaxEfficiency=.35,BaseMinOverlap=.55;
bool BaseDetectionDiagnostics=true,historyReady=true;
bool G_StopLatched=true,G_ExecutionUncertain=true,G_StateOK=false,EnableAutoTrade=false;
datetime G_BaseModelCheckedBar=0,G_BaseModelDataLogBar=0;
int painted=0,printed=0,lastShift=0;double paintedHigh=0,paintedLow=0;
std::vector<MqlRates> market;std::vector<double> volatility;
bool Positive(double x){return std::isfinite(x)&&x>0;}bool MathIsValidNumber(double x){return std::isfinite(x);}
double MathMin(double x,double y){return std::min(x,y);}double MathMax(double x,double y){return std::max(x,y);}double MathAbs(double x){return std::abs(x);}
template<typename T>int ArraySize(const std::vector<T>& v){return (int)v.size();}
template<typename T>void ArraySetAsSeries(T&,bool){}
bool SeriesInfoInteger(int,int,int){return historyReady;}
int PeriodSeconds(int tf){return tf*60;}int PeriodSeconds(){return 300;}
int CopyRates(int,int,int shift,int count,std::vector<MqlRates>& v){
 assert(shift>=1);lastShift=shift;v.clear();if(!historyReady)return 0;
 for(int i=shift;i<shift+count&&i<(int)market.size();i++){v.push_back(market[i]);}return (int)v.size();
}
int CopyBuffer(int,int,int shift,int count,std::vector<double>& v){
 assert(shift>=1);v.clear();for(int i=shift;i<shift+count&&i<(int)volatility.size();i++)v.push_back(volatility[i]);return (int)v.size();
}
datetime iTime(int,int,int shift){return market[shift].time;}datetime TimeCurrent(){return market[0].time;}
string TimeToString(datetime t){return std::to_string(t);}string DoubleToString(double x,int){return std::to_string(x);}
void DrawR(string,datetime,double high,datetime,double low,int,string){painted++;paintedHigh=high;paintedLow=low;}
template<typename... T>void Print(T...){printed++;}
std::vector<MqlRates> sideways(int count){
 double wave[]={100,100.3,100.6,100.3,100,99.7,99.4,99.7};std::vector<MqlRates> result;
 for(int i=0;i<count;i++){double c=wave[i%8];result.push_back({100000-i*300,c,c+.6,c-.6,c});}return result;
}
void fixture(){market=sideways(40);market[0].high=100000;market[0].low=.01;volatility.assign(40,.8);volatility[0]=1000;historyReady=true;painted=printed=0;G_BaseModelCheckedBar=G_BaseModelDataLogBar=0;}
'''
cases=r'''
int main(){
 auto bars=sideways(24);std::vector<double> atr(25,.8);BaseZone zone{};string why;
 assert(EvaluateBaseWindow(bars,atr,24,300,4,.35,.55,zone,why));
 assert(zone.valid && zone.bars==24 && zone.rangeATR>1.5 && zone.overlap>=.55); // broad sideways missed by old 1.5 ATR rule
 assert(SelectBaseZone(bars,atr,6,24,300,4,.35,.55,zone,why) && zone.bars==24); // longest eligible window
 atr[0]=.01;assert(EvaluateBaseWindow(bars,atr,24,300,4,.35,.55,zone,why)); // use pre-window ATR, not shrunken recent ATR
 // Narrow directional drift is not accumulation, even with width and overlap passing.
 auto trend=bars;for(int i=0;i<24;i++){double c=100+i*.1;trend[i]={100000-i*300,c,c+.6,c-.6,c};}
 std::vector<double> wideATR(25,2);
 assert(!EvaluateBaseWindow(trend,wideATR,24,300,4,.35,.55,zone,why) && why=="DIRECTIONAL_DRIFT");
 // Close-to-close back-and-forth without overlapping ranges is not a coherent balance zone.
 auto jumps=bars;for(int i=0;i<24;i++){double c=100+(i%2);jumps[i]={100000-i*300,c,c+.1,c-.1,c};}
 assert(!EvaluateBaseWindow(jumps,wideATR,24,300,4,.35,.55,zone,why) && why=="LOW_OVERLAP");
 auto wick=bars;wick[10].high=150;
 assert(!EvaluateBaseWindow(wick,atr,24,300,4,.35,.55,zone,why) && why=="RANGE_ATR");
 auto gap=bars;gap[10].time-=1;
 assert(!EvaluateBaseWindow(gap,atr,24,300,4,.35,.55,zone,why) && why=="SESSION_GAP");
 auto bad=bars;bad[5].close=200;
 assert(!EvaluateBaseWindow(bad,atr,24,300,4,.35,.55,zone,why) && why=="INVALID_OHLC");
 std::vector<double> emptyATR(25,0);
 assert(!EvaluateBaseWindow(bars,emptyATR,24,300,4,.35,.55,zone,why));
 // The last six closed bars form a zone; longer windows include a distinct earlier impulse.
 auto shortBase=bars;for(int i=6;i<24;i++){double c=120+i;shortBase[i]={100000-i*300,c,c+.6,c-.6,c};}
 assert(SelectBaseZone(shortBase,atr,6,24,300,4,.35,.55,zone,why) && zone.bars==6);
 // Forming candle is excluded. Both shifts are causal: 1 for live pending, 2 before a closed breakout.
 fixture();bool ready=false;
 assert(ReadBaseZone(1,zone,why,ready) && ready && lastShift==1 && zone.last==market[1].time && zone.high<102);
 assert(ReadBaseZone(2,zone,why,ready) && ready && lastShift==2 && zone.last==market[2].time);
 fixture();historyReady=false;UpdateBaseZoneModel();assert(painted==0 && G_BaseModelCheckedBar==0);
 historyReady=true;UpdateBaseZoneModel();assert(painted==1 && printed==2); // retry same bar on history arrival
 UpdateBaseZoneModel();assert(painted==1 && printed==2); // one model update / closed candle
 assert(G_StopLatched && G_ExecutionUncertain && !G_StateOK && !EnableAutoTrade); // model did not alter any trade permission
 fixture();volatility[24]=0;assert(!ReadBaseZone(1,zone,why,ready) && !ready && why=="ATR_NOT_READY");
 fixture();market.resize(10);assert(!ReadBaseZone(1,zone,why,ready) && !ready);
 std::cout<<"PASS: actual adaptive BASE classification, longest/short windows, drift/overlap rejection, pre-window ATR, closed-data shifts and independent detection under trade locks\n";
}
'''
with tempfile.TemporaryDirectory(prefix='base-detect-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+state+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
# Verify the actual update is called from the shared data path before OnTick's permission return.
refresh=extract('UpdateBaseZoneModel')
assert 'SubmitEntry' not in refresh and 'SaveSafetyState' not in refresh
start=s.index('void RefreshMarketContext() {');end=s.index('\n}',start)
assert 'UpdateBaseZoneModel()' in s[start:end]
print('PASS: adaptive model connected to shared market refresh, with no order/state-file mutations')
