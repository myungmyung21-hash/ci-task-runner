import time
from datetime import datetime
import monitor as M
from research6 import fetch, rsi
DAYS = 300
def outcome(d,i,stop,H=16):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    return max(-1.0,min(2.0,(d["c"][i+H]-e)/R))
m,_=M.resolve(); data={}; now=time.time()
print(f"요청 기간 {DAYS}일")
for name,(k,s) in m.items():
    if name in ("KAIA","MBABYDOGE","BRETT","BTC"): continue
    r15=fetch(k,s,"15m",DAYS)
    if len(r15)<500: print(" ",name,"데이터 부족",len(r15)); continue
    d=M.indicators(r15); d["t"]=[r[0] for r in r15]; d["rsi"]=rsi(d["c"])
    data[name]=d
    print(f"  {name}: {len(r15)}봉, 시작 {datetime.fromtimestamp(r15[0][0],M.KST):%Y-%m-%d}")
ev=[]; base=[]
for name,d in data.items():
    last=0; c=d["c"]
    for i in range(80,len(c)-16):
        if i%8==0 and d["mb"][i]:
            o=outcome(d,i,min(d["l"][i-16:i])*0.999)
            if o is not None: base.append((d["t"][i],o))
        hd=M.hold2(d,i)
        if not hd or M.vratio(d,i)<1.5 or d["t"][i]-last<8*900: continue
        last=d["t"][i]; o=outcome(d,i,hd["sup"]*0.999)
        if o is None: continue
        ub,lb=d["ub"][i],d["lb"][i]
        f=dict(pctb=(c[i]-lb)/(ub-lb) if ub>lb else 0.5, hist_up=d["hist"][i]>d["hist"][i-3], rsi=d["rsi"][i],
               true_low=hd["sup"]<=min(d["l"][i-24:i+1])*1.001)
        ev.append((d["t"][i],o,f,name))
if not ev: print("이벤트 없음"); raise SystemExit
t0=min(t for t,_,_,_ in ev); t1=max(t for t,_,_,_ in ev); nb=5; w=(t1-t0)/nb
def blk(t): return min(nb-1,int((t-t0)/w))
rules=[("비교기준(임의봉)",None),("전체",lambda f:True),("%B 0.5 이하",lambda f:f["pctb"]<=0.5),("%B 0.8 초과",lambda f:f["pctb"]>0.8),
       ("히스토 상승",lambda f:f["hist_up"]),("히스토 하락",lambda f:not f["hist_up"]),("6시간 최저",lambda f:f["true_low"]),
       ("RSI 60 이상",lambda f:f["rsi"]>=60),("필터(%B≤0.5+히스토상승)",lambda f:f["pctb"]<=0.5 and f["hist_up"]),
       ("필터 반대(그 외)",lambda f:not (f["pctb"]<=0.5 and f["hist_up"]))]
heads=[f"{datetime.fromtimestamp(t0+w*b,M.KST):%m/%d}~" for b in range(nb)]
print(f"\n양봉2회방어(거래150%+) {len(ev)}건 | 구간 {datetime.fromtimestamp(t0,M.KST):%Y-%m-%d} ~ {datetime.fromtimestamp(t1,M.KST):%Y-%m-%d} | 5구간 R (건수)")
print(" 조건 | " + " | ".join(heads) + " | 전체 | 플러스 구간 수")
for nm,fn in rules:
    src=base if fn is None else [(t,o) for t,o,f,_ in ev if fn(f)]
    cells=[]; pos=0
    for b in range(nb):
        z=[o for t,o in src if blk(t)==b]
        if z:
            r=sum(z)/len(z); pos+=r>0; cells.append(f"{r:+.3f}({len(z)})")
        else: cells.append("-")
    allz=[o for _,o in src]
    print(f" {nm} | " + " | ".join(cells) + f" | {sum(allz)/len(allz):+.3f}({len(allz)}) | {pos}/{nb}")
