"""Execute actual HUD layout/summary/masking and numerical BASE guide-line painting."""
from pathlib import Path
import re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5').read_text()
def extract(n):
 m=re.search(r'^(?:bool|string|void|double|int) '+n+r'\([^{};]*\)\s*\{',s,re.M);assert m,n
 return s[m.start():s.index('\n}',m.end())+2]
funcs='\n'.join(extract(n) for n in ('UpdateHudLayout','CoveredByHud','UpdateCenterInfo','PaintStage1Midlines'))
funcs=funcs.replace('"P/L: symbol | management: own Magic | "+','string("P/L: symbol | management: own Magic | ")+')
h=r'''
#include <string>
#include <vector>
#include <cmath>
#include <cassert>
#include <iostream>
using string=std::string;using ulong=unsigned long;using datetime=long long;
const string _Symbol="GOLD";
const int CHART_WIDTH_IN_PIXELS=1,CHART_HEIGHT_IN_PIXELS=2,POSITION_SYMBOL=1,POSITION_VOLUME=2,POSITION_PROFIT=3,POSITION_SWAP=4,ACCOUNT_BALANCE=1,SYMBOL_BID=1,clrLime=1,clrRed=2,clrSilver=3,clrOrange=4;
int chartWidth=1920,chartHeight=1080,G_HudLeft=0,G_HudWidth=0,G_HudFont=0,G_HudRow=0,G_HudColumns=0,G_HudTop=0,G_SummaryY=0,G_ScopeY=0,G_DiagTop=0,G_DiagBottom=0;
int InfoRightMarginPx=24,HudWidthPercent=72,HudFontSize=11,HudTopOffsetPx=90,InfoFontSize=13,DiagnosticTopOffsetPx=20;
bool DiagnosticCleanView=false,ShowMTFDashboard=true,ShowFiboDiagnostics=false,G_HudCompact=false,DiagnosticMode=false,G_StopLatched=false,EnableAutoTrade=true,BaseUseStopOrders=true;
double BaseHalfExitPips=1000;int BaseTrailBars=5;
int MathMin(int x,int y){return std::min(x,y);}int MathMax(int x,int y){return std::max(x,y);}
int ChartGetInteger(int,int p){return p==1?chartWidth:chartHeight;}
int ViewTextWidth(string s,int font){return std::ceil(s.size()*font*.6);}int ViewTextHeight(int font){return std::ceil(font*1.4);}
int PositionsTotal(){return 0;}ulong PositionGetTicket(int){return 0;}string PositionGetString(int){return _Symbol;}double PositionGetDouble(int){return 0;}
string GetTimerToNextBar(){return "02:11";}double AccountInfoDouble(int){return 387.87;}double GetDailyPNL(){return -43.1;}double GetDynamicRisk(){return 3.7;}
double SymbolInfoDouble(string,int){return 4160;}string GetActiveMacroOTE(double){return "D1 BUY";}string GetNearestOBDistance(){return "4093 pts";}
string DoubleToString(double d,int){return std::to_string(d);}string IntegerToString(long d){return std::to_string(d);}
void ClearSegmentedLabel(string){}
struct Label{string name,text;int x,y,width;};std::vector<Label> labels;
void SetFittedViewLabel(string name,string text,int x,int y,int,int,int width){labels.push_back({name,text,x,y,width});}
struct View{string name,text;datetime first,last;double high,low;};std::vector<View> G_BaseViews;
template<typename T>int ArraySize(const std::vector<T>& x){return x.size();}
struct Line{string name;double price;datetime first,last;};std::vector<Line> lines;
void CreateStructLine(string name,datetime first,double p,datetime last,double p2,int,string){assert(p==p2);lines.push_back({name,p,first,last});}
'''
cases=r'''
int main(){
 for(int width:{800,1366,1536,1920,2560}) {
  chartWidth=width;UpdateHudLayout();assert(G_HudLeft>=12&&G_HudLeft>width/5);
  assert(G_HudLeft+G_HudWidth==width-InfoRightMarginPx);
  assert(G_HudColumns==1||G_HudColumns==2||G_HudColumns==3||G_HudColumns==6);
  assert(!CoveredByHud(0,G_HudTop));assert(CoveredByHud(G_HudLeft,G_HudTop));
  assert(!CoveredByHud(width-1,G_HudTop));
  labels.clear();UpdateCenterInfo();assert(labels.size()==2&&labels[0].name=="InfoOneRow");
  assert(labels[0].text.find('\n')==string::npos&&labels[0].text.find("LOTS")!=string::npos&&labels[0].text.find("RISK")!=string::npos);
  for(auto l:labels)assert(l.x==G_HudLeft&&l.x+l.width<=width-InfoRightMarginPx);
  assert(labels[1].y>labels[0].y);
 }
 G_BaseViews={{"BASE1","BASE",100,200,4110,4100},{"OTHER","Compression",100,200,4110,4100}};
 PaintStage1Midlines();assert(lines.size()==3);
 assert(lines[0].price==4105&&lines[1].price==4106.5&&lines[2].price==4103.5);
 for(auto l:lines)assert(l.first==100&&l.last==200);
 std::cout<<"PASS FIX2 HUD: right anchoring at 800..2560px, one summary row, correct annotation mask, BASE 35/50/65 guide prices\n";
}
'''
with tempfile.TemporaryDirectory(prefix='fix2-hud-') as tmp:
 cpp=Path(tmp)/'c.cpp';exe=Path(tmp)/'c';cpp.write_text(h+'\n'+funcs+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
