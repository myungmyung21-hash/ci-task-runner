import time
from datetime import datetime
import monitor as M
from research6 import fetch
def outcome(d,i,stop,H=16):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.06: return None
    for k in range(i+1,i+1+H):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    return max(-1.0,min(2.0,(d["c"][i+H]-e)/R))
m,_=M.resolve()
for tf,days in (("1h",90),("15m",30)):
    res={}; recent=[]
    for name,(k,s) in m.items():
        if name=="BTC": continue
        rows=fetch(k,s,tf,days); d=M.indicators(rows); n=len(rows); last={}
        for i in range(60,n):
            for vx in (3.0,4.0,5.0):
                rc=M.recl(d,i,vx)
                if not rc or rows[i][0]-last.get(vx,0) < 8*(rows[1][0]-rows[0][0]): continue
                last[vx]=rows[i][0]
                if name=="KAIA" and rows[i][0]>=1792278000: recent.append((vx,datetime.fromtimestamp(rows[i][0],M.KST).strftime("%m/%d %H:%M시작"),d["c"][i],rc["lvl"],rc["low"],round(rc["cvx"],1)))
                if i<n-16:
                    o=outcome(d,i,rc["low"]*0.999)
                    if o is not None: res.setdefault(vx,[]).append((rows[i][0],o))
    print(f"\n== {tf} {days}일 투매후 시가회복 (손절=투매저점, 2R, 16봉)")
    for vx,v in sorted(res.items()):
        v.sort(); cut=int(len(v)*0.7); a=[x for _,x in v[:cut]]; b=[x for _,x in v[cut:]]
        f=lambda z: f"n={len(z)} 2R승={sum(1 for x in z if x==2.0)} 손절={sum(1 for x in z if x==-1.0)} R={sum(z)/len(z):+.3f}" if z else "n=0"
        print(f" 투매{vx:.0f}배 | 하루 {len(v)/days:.1f} | 앞70% {f(a)} | 뒤30% {f(b)}")
    print(" KAIA 10/18 08시~:", recent)
