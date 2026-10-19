import time
from datetime import datetime
import monitor as M
from research6 import fetch, rsi
def outcome(d,i,stop,H=16):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    return max(-1.0,min(2.0,(d["c"][i+H]-e)/R))
m,_=M.resolve(); data={}
for name,(k,s) in m.items():
    if name in ("KAIA","MBABYDOGE","BRETT"): continue
    r15=fetch(k,s,"15m",60); r1h=fetch(k,s,"1h",65)
    d=M.indicators(r15); d["t"]=[r[0] for r in r15]; d["rsi"]=rsi(d["c"])
    h=M.indicators(r1h); h["t"]=[r[0] for r in r1h]
    data[name]=(d,h)
def j1h(h,t):
    js=[q for q in range(len(h["t"])) if h["t"][q]+3600<=t+900]; return js[-1] if js else -1
def feats(d,h,i,sup):
    c=d["c"][i]; ub,lb,mb=d["ub"][i],d["lb"][i],d["mb"][i]; a=M.atr(d,i); j=j1h(h,d["t"][i])
    return dict(pctb=(c-lb)/(ub-lb) if ub>lb else 0.5, hist_up=d["hist"][i]>d["hist"][i-3], rsi=d["rsi"][i],
                ret4h=(c/d["c"][i-16]-1)*100, mbdist=(c-mb)/a if a else 0, true_low=sup<=min(d["l"][i-24:i+1])*1.001,
                h1_down=(j>0 and (not h["up"][j]) and h["c"][j]<h["mb"][j]), h1_up=(j>0 and h["up"][j] and h["c"][j]>h["mb"][j]),
                sar_up=d["up"][i])
# B. 양봉2회방어 학습
ev=[]
for name,(d,h) in data.items():
    if name=="BTC": continue
    last=0
    for i in range(80,len(d["c"])-16):
        hd=M.hold2(d,i)
        if not hd or M.vratio(d,i)<1.5 or d["t"][i]-last<8*900: continue
        last=d["t"][i]; o=outcome(d,i,hd["sup"]*0.999)
        if o is None: continue
        ev.append((d["t"][i],o,feats(d,h,i,hd["sup"]),name))
ev.sort(key=lambda x:x[0]); cut=ev[int(len(ev)*0.7)][0]
def show(nm,sel):
    a=[o for t,o,f,n in ev if sel(f) and t<cut]; b=[o for t,o,f,n in ev if sel(f) and t>=cut]
    fa=lambda z:f"n={len(z)} R={sum(z)/len(z):+.3f}" if z else "n=0"
    print(f" {nm} | 앞70% {fa(a)} | 뒤30% {fa(b)}")
print(f"\n양봉2회방어(거래150%+) 60일 {len(ev)}건, 분할 {datetime.fromtimestamp(cut,M.KST):%m/%d}")
show("전체",lambda f:True)
show("%B 0.5 이하(밴드 아래쪽)",lambda f:f["pctb"]<=0.5)
show("%B 0.8 초과(밴드 상단)",lambda f:f["pctb"]>0.8)
show("MACD 히스토 상승 중",lambda f:f["hist_up"])
show("MACD 히스토 하락 중",lambda f:not f["hist_up"])
show("직전4h +2% 미만",lambda f:f["ret4h"]<2)
show("직전4h +2% 이상",lambda f:f["ret4h"]>=2)
show("진짜 저점(6시간 최저)",lambda f:f["true_low"])
show("국지 저점(6시간 최저 아님)",lambda f:not f["true_low"])
show("1시간 하락추세 아님",lambda f:not f["h1_down"])
show("1시간 하락추세",lambda f:f["h1_down"])
show("RSI 60 미만",lambda f:f["rsi"]<60)
show("RSI 60 이상",lambda f:f["rsi"]>=60)
show("진짜저점 + 히스토상승",lambda f:f["true_low"] and f["hist_up"])
show("%B 0.5이하 + 히스토상승",lambda f:f["pctb"]<=0.5 and f["hist_up"])
show("진짜저점 + 1h하락아님",lambda f:f["true_low"] and not f["h1_down"])
print("\nTRUMP 오늘 알람과 같은 조건(국지저점·%B 0.8초과·히스토하락):")
show("국지저점+밴드상단+히스토하락",lambda f:(not f["true_low"]) and f["pctb"]>0.8 and not f["hist_up"])
