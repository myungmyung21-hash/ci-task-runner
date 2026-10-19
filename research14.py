import time
from datetime import datetime
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=16
def lo(d,i,stop):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    return max(-1.0,min(2.0,(d["c"][i+H]-e)/R))
def so(d,i,stop):
    e=d["c"][i]; R=stop-e
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["h"][k]>=stop: return -1.0
        if d["l"][k]<=e-2*R: return 2.0
    return max(-1.0,min(2.0,(e-d["c"][i+H])/R))
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    d=M.indicators(r15); d["t"]=[r[0] for r in r15]
    h=M.indicators(r1h); h["t"]=[r[0] for r in r1h]
    data[name]=(d,h)
btc=data["BTC"][0]; bidx={t:i for i,t in enumerate(btc["t"])}
res={}
for name,(d,h) in data.items():
    if name=="BTC": continue
    c=d["c"]; n=len(c); last={}; s1=[False]*n; hj=0
    for i in range(80,n-H):
        t=d["t"][i]; bi=bidx.get(t)
        if bi is None or bi<16: continue
        rs=(c[i]/c[i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1)
        while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        c_=[]
        rc=M.recl(d,i)
        if rc: c_.append(("[속보] 투매후회복","L",rc["low"]))
        if sig and sig[0]==2 and any(s1[i-12:i]): c_.append(("[단독] 2단계돌파","L",d["sar"][i]))
        hd=M.hold2(d,i)
        if hd and M.vratio(d,i)>=1.5:
            c_.append(("[종합] 양봉2회(필터없음)","L",hd["sup"]))
            if M.hold_ok(d,i): c_.append(("[종합] 양봉2회(현재필터)","L",hd["sup"]))
        sh=M.short_sig(d,i,rs)
        if sh and hj>30 and (not h["up"][hj]) and h["mb"][hj] and h["c"][hj]<h["mb"][hj]: c_.append(("short SAR전환+1h하락","S",sh["stop"]))
        for nm,side,stop in c_:
            if t-last.get(nm,0)<8*900: continue
            last[nm]=t; o=(lo if side=="L" else so)(d,i,stop*(0.999 if side=="L" else 1.001))
            if o is not None: res.setdefault(nm,[]).append((t,o))
        if i%8==0 and d["mb"][i]:
            o=lo(d,i,min(d["l"][i-16:i])*0.999)
            if o is not None: res.setdefault("비교: 아무봉 롱",[]).append((t,o))
            o=so(d,i,max(d["h"][i-16:i])*1.001)
            if o is not None: res.setdefault("비교: 아무봉 short",[]).append((t,o))
allt=[t for v in res.values() for t,_ in v]; t0,t1=min(allt),max(allt); nb=5; w=(t1-t0)/nb
blk=lambda t:min(nb-1,int((t-t0)/w))
print(f"바이낸스 선물 15분봉 {DAYS}일, 12종목 | {datetime.fromtimestamp(t0,M.KST):%Y-%m-%d}~{datetime.fromtimestamp(t1,M.KST):%Y-%m-%d} | 5구간 R(건수)")
print(" 알람 | "+" | ".join(f"{datetime.fromtimestamp(t0+w*b,M.KST):%m/%d}~" for b in range(nb))+" | 전체 | 하루 | 플러스구간")
for nm in sorted(res):
    v=res[nm]; cells=[]; pos=0
    for b in range(nb):
        z=[o for t,o in v if blk(t)==b]
        if z: r=sum(z)/len(z); pos+=r>0; cells.append(f"{r:+.3f}({len(z)})")
        else: cells.append("-")
    a=[o for _,o in v]
    print(f" {nm} | "+" | ".join(cells)+f" | {sum(a)/len(a):+.3f}({len(a)}) | {len(a)/DAYS:.1f} | {pos}/{nb}")
