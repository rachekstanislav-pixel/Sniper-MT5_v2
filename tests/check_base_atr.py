"""Exercise the actual BASE decision functions with deterministic market history."""
from pathlib import Path
import runpy, subprocess, tempfile
ctx=runpy.run_path(str(Path(__file__).with_name('check_working_revision.py')))
s,extract=ctx['s'],ctx['function']

state=s[s.index('struct BaseZone {'):s.index('};',s.index('struct BaseZone {'))+2]
_adaptive_h='\n'+state+r'''
bool BaseAdaptiveDetection=false,adaptiveFound=true,adaptiveReady=true;
BaseZone adaptiveZone{true,6,900,1000,110,100,2,0.1,0.8};
int adaptiveShift=0;
bool ReadBaseZone(int shift,BaseZone& zone,string&,bool& ready){adaptiveShift=shift;zone=adaptiveZone;ready=adaptiveReady;return adaptiveFound;}
'''
functions='\n'.join(extract(s,n) for n in ('BaseBreakoutSide','BaseSwingStop','BaseATRTarget','CheckBaseBreakout'))
functions=functions.replace('const MqlRates &bars[]','const std::vector<MqlRates> &bars').replace('double atr[];','std::vector<double> atr;').replace('MqlRates rates[];','std::vector<MqlRates> rates;')
h=ctx['harness']
h=h.replace('datetime iTime(int,int,int shift){return shift==1?99:100;}', 'datetime closedBar=100; datetime iTime(int,int,int shift){return closedBar+1-shift;}')
h=h.replace('double iHigh(int,int,int){return 120;} double iLow(int,int,int){return 100;}', 'double rangeHigh=110,rangeLow=100,closePrice=105; double iHigh(int,int,int){return rangeHigh;} double iLow(int,int,int){return rangeLow;}')
h=h.replace('struct MqlTick{double ask=111,bid=110;};', 'double ask=98,bid=97; struct MqlTick{double ask=::ask,bid=::bid;};')
a=h.index('bool SubmitEntry(');b=h.index('\nvoid SafetyLog',a)
h=h[:a]+'''int lastSide=-1;double lastSL=0,lastATR=0;
bool SubmitEntry(int side,bool,double,double sl,string,double atr){attempts++;if(!gate)return false;successful++;lastSide=side;lastSL=sl;lastATR=atr;return true;}
'''+h[b:]
h+=r'''
bool BaseUseStopOrders=false;void CheckBaseStopSetup(){assert(false);}
#include <sstream>
constexpr int AUDIT_BASE=4,clrDarkGray=0;
bool G_BaseArmed=false,G_BaseConsumed=false,EnableSMC_Base=true,BaseRequireVolumeSpike=false;
double G_BaseHigh=0,G_BaseLow=0;
datetime G_BaseStarted=0,G_BaseArmedBar=0,G_BaseCheckedBar=0;
int BaseMaxWaitBars=10,BaseSwingStrength=2,BaseSwingLookback=64,BaseSLBufferPoints=15;
int Vol_SMA_Period=20;double VolSpikeCoef=1.5;
struct MqlRates{datetime time=0;double high=0,low=0;};
std::vector<MqlRates> market;
template<typename T> int ArraySize(const std::vector<T>& x){return (int)x.size();}
template<typename T> void ArraySetAsSeries(T&,bool){}
int CopyRates(int,int,int,int,std::vector<MqlRates>& dest){dest=market;return (int)dest.size();}
double iClose(int,int,int){return closePrice;}
int iBarShift(int,int,datetime when,bool){return (int)(closedBar-when)+1;}
long iVolume(int,int,int){return 10;}double GetVolumeSMA(int){return 20;}
string TimeToString(datetime t){return std::to_string(t);}
string DoubleToString(double x,int){return std::to_string(x);}
int PeriodSeconds(){return 300;}
void DrawR(string,datetime,double,datetime,double,int,string){}
template<typename... T> void Print(T...){ }
double MathCeil(double x){return std::ceil(x);}
void fixture(){
 G_BaseArmed=false;G_BaseConsumed=false;G_BaseCheckedBar=0;G_BaseArmedBar=0;
 closedBar=100;rangeHigh=110;rangeLow=100;closePrice=105;atr=10;
 BaseRequireVolumeSpike=false;gate=true;DiagnosticMode=false;EnableAutoTrade=true;
 attempts=successful=0;lastSide=-1;market.clear();
 const double highs[]={100,105,111,106,104,110,107,105};
 for(int i=0;i<8;i++) market.push_back({101-i,highs[i],highs[i]-5});
}
void breakout(){closedBar=101;rangeHigh=140;rangeLow=90;closePrice=98;ask=98;bid=97;}
'''
h+=_adaptive_h
cases=r'''
int main(){
 assert(BaseBreakoutSide(99,100,110)==POSITION_TYPE_SELL);
 assert(BaseBreakoutSide(111,100,110)==POSITION_TYPE_BUY);
 assert(BaseBreakoutSide(100,100,110)==-1);
 assert(BaseBreakoutSide(110,100,110)==-1);
 assert(BaseBreakoutSide(105,110,100)==-1);
 assert(BaseBreakoutSide(NAN,100,110)==-1);
 fixture();CheckBaseBreakout();assert(G_BaseArmed && attempts==0 && G_BaseLow==100 && G_BaseHigh==110);
 breakout();CheckBaseBreakout();assert(successful==1 && lastSide==POSITION_TYPE_SELL);
 assert(std::abs(lastSL-111.15)<1e-9 && lastATR==10); // latest confirmed pivot, not box high
 CheckBaseBreakout();assert(successful==1); // same bar cannot duplicate
 closedBar=102;CheckBaseBreakout();assert(successful==1); // no chasing same breakout
 fixture();CheckBaseBreakout();breakout();closePrice=100;CheckBaseBreakout();assert(attempts==0); // wick only
 fixture();CheckBaseBreakout();breakout();BaseRequireVolumeSpike=true;CheckBaseBreakout();assert(attempts==0);
 fixture();CheckBaseBreakout();breakout();DiagnosticMode=true;CheckBaseBreakout();assert(attempts==0);
 fixture();CheckBaseBreakout();breakout();gate=false;CheckBaseBreakout();assert(attempts==1 && successful==0);
 gate=true;closedBar=102;CheckBaseBreakout();assert(attempts==1); // rejected signal is not replayed
 fixture();CheckBaseBreakout();breakout();market.resize(3);CheckBaseBreakout();assert(attempts==0); // no confirmed swing
 fixture();CheckBaseBreakout();breakout();ask=101;bid=100;CheckBaseBreakout();assert(attempts==0); // quote back inside
 // Mirror the same history: BUY stop at latest local minimum, no future/unclosed candles.
 fixture();CheckBaseBreakout();closedBar=101;closePrice=112;rangeHigh=140;rangeLow=90;ask=113;bid=112;
 for(auto& bar:market){double high=210-bar.low;bar.low=210-bar.high;bar.high=high;}
 CheckBaseBreakout();assert(successful==1 && lastSide==POSITION_TYPE_BUY && std::abs(lastSL-98.85)<1e-9);
 // Adaptive market entries use a window excluding the just-closed breakout candle.
 fixture();BaseAdaptiveDetection=true;closedBar=101;adaptiveZone.first=90;adaptiveZone.last=100;closePrice=112;ask=113;bid=112;
 CheckBaseBreakout();assert(adaptiveShift==2 && successful==1 && lastSide==POSITION_TYPE_BUY);
 fixture();G_BaseArmed=true;G_BaseHigh=108;G_BaseLow=100;G_BaseArmedBar=100;closedBar=101;
 closePrice=109;ask=109.2;bid=109;CheckBaseBreakout();assert(successful==0 && G_BaseHigh==110); // use latest pre-break bounds, not an older narrower box
 fixture();G_BaseArmed=true;G_BaseHigh=110;G_BaseLow=100;G_BaseArmedBar=100;closedBar=101;adaptiveFound=false;
 closePrice=112;ask=113;bid=112;CheckBaseBreakout();assert(successful==1); // existing valid base survives a failed fresh candidate
 adaptiveFound=true;BaseAdaptiveDetection=false;
 // A more recent unconfirmed pivot cannot replace the most recent confirmed pivot.
 fixture();double sl=0;market[0].high=109;market[1].high=110;
 assert(BaseSwingStop(market,POSITION_TYPE_SELL,2,0.15,sl));assert(std::abs(sl-111.15)<1e-9);
 assert(BaseATRTarget(true,100,3,0.01,2)==106);
 assert(BaseATRTarget(false,100,3,0.01,2)==94);
 assert(BaseATRTarget(true,100,1,0.01,2)==102); // closed ATR changes target, entry stays fixed
 assert(BaseATRTarget(false,100,1,0.01,2)==98);
 assert(BaseATRTarget(false,1,3,0.01,2)==0);
 assert(BaseATRTarget(true,100,0,0.01,2)==0);
 std::cout<<"PASS: frozen BASE breakout, BUY/SELL swing stops, rejection/replay and ATR targets\n";
}
'''
with tempfile.TemporaryDirectory(prefix='base-check-') as tmp:
 cpp=Path(tmp)/'checks.cpp';exe=Path(tmp)/'checks';cpp.write_text(h+'\n'+functions+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
# Verify the real submission uses checked TP in both market order directions.
submit=extract(s,'SubmitEntry')
assert 'request.tp=tp' in submit
assert 'trade.Buy(volume,_Symbol,entry,sl,tp,comment)' in submit
assert 'trade.Sell(volume,_Symbol,entry,sl,tp,comment)' in submit
# Existing basket close and BE loops must exclude new ATR positions.
manager=extract(s,'ManagePositions')
assert manager.count('!IsIndividualBaseModule(PositionGetString(POSITION_COMMENT))')==4
assert 'if(IsIndividualBaseModule(PositionGetString(POSITION_COMMENT))) continue;' in manager
print('PASS: ATR TP submission and legacy basket isolation checks')
