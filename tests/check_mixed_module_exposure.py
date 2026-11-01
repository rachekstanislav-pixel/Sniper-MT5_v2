"""Execute the real common exposure ledger across modules, pending types and foreign rows."""
from pathlib import Path
import re,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5').read_text()
def extract(name):
 m=re.search(r'^bool '+name+r'\([^{};]*\)\s*\{',s,re.M);assert m
 return s[m.start():s.index('\n}',m.end())+2]
h=r'''
#include <vector>
#include <string>
#include <cmath>
#include <cassert>
#include <iostream>
using ulong=unsigned long;
const int _Symbol=0,POSITION_TYPE_BUY=0,POSITION_TYPE_SELL=1,POSITION_TYPE=1,POSITION_VOLUME=2,POSITION_PRICE_OPEN=3,POSITION_SL=4;
const int ORDER_TYPE=5,ORDER_VOLUME_CURRENT=6,ORDER_PRICE_OPEN=7,ORDER_SL=8;
const int ORDER_TYPE_BUY=0,ORDER_TYPE_SELL=1,ORDER_TYPE_BUY_LIMIT=2,ORDER_TYPE_SELL_LIMIT=3,ORDER_TYPE_BUY_STOP=4,ORDER_TYPE_SELL_STOP=5,ORDER_TYPE_BUY_STOP_LIMIT=6,ORDER_TYPE_SELL_STOP_LIMIT=7;
using ENUM_ORDER_TYPE=int;
struct Row{bool own;int side;double volume,entry,sl;std::string module;};
std::vector<Row> positions,orders;int pos=0,ord=0;
bool Positive(double x){return std::isfinite(x)&&x>0;}bool MathIsValidNumber(double x){return std::isfinite(x);}double MathMax(double a,double b){return std::max(a,b);}
int PositionsTotal(){return (int)positions.size();}ulong PositionGetTicket(int i){pos=i;return i+1;}
bool IsOwnPosition(ulong t){pos=(int)t-1;return positions[pos].own;}
int PositionGetInteger(int){return positions[pos].side;}
double PositionGetDouble(int p){auto r=positions[pos];return p==POSITION_VOLUME?r.volume:(p==POSITION_PRICE_OPEN?r.entry:r.sl);}
int OrdersTotal(){return (int)orders.size();}ulong OrderGetTicket(int i){ord=i;return i+1;}
bool IsOwnOrder(ulong t){ord=(int)t-1;return orders[ord].own;}
int OrderGetInteger(int){return orders[ord].side;}
double OrderGetDouble(int p){auto r=orders[ord];return p==ORDER_VOLUME_CURRENT?r.volume:(p==ORDER_PRICE_OPEN?r.entry:r.sl);}
bool OrderCalcProfit(int side,int,double v,double entry,double sl,double& profit){profit=(side==0?sl-entry:entry-sl)*100*v;return true;}
bool OrderCalcMargin(int,int,double v,double price,double& margin){margin=price*v;return true;}
'''
cases=r'''
int main(){
 positions={{true,0,.01,105,100,"SMC_Comp"},{true,1,.01,104,110,"SMC_EMA"},{false,0,1,105,100,"foreign"}};
 orders={{true,2,.01,102,99,"SMC_Comp_Limit"},{true,4,.01,106,100,"SMC_Base_Stop_B:1"},{true,5,.01,98,104,"SMC_Base_Stop_S:1"},{false,4,1,106,100,"foreign"}};
 double risk=0,buy=0,sell=0,margin=0;
 assert(OwnExposure(risk,buy,sell,margin));
 assert(std::abs(risk-26)<1e-9 && std::abs(buy-.03)<1e-9 && std::abs(sell-.02)<1e-9 && std::abs(margin-3.06)<1e-9);
 positions[0].sl=106;assert(OwnExposure(risk,buy,sell,margin) && std::abs(risk-21)<1e-9); // protected profitable SL is zero cash loss, volume still reserved
 positions[0].sl=0;assert(!OwnExposure(risk,buy,sell,margin)); // incomplete protection cannot be hidden by another module
 std::cout<<"PASS: actual mixed-module exposure ledger reserves all own positions/orders and excludes foreign rows\n";
}
'''
with tempfile.TemporaryDirectory(prefix='mixed-exposure-') as tmp:
 cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(h+'\n'+extract('LossAtSL')+'\n'+extract('OwnExposure')+'\n'+cases)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
