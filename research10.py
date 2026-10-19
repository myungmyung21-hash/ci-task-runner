import time
import monitor as M
from research6 import fetch
M.WATCH=[w for w in M.WATCH if w not in ("KAIA","MBABYDOGE","BRETT")]
def outcome(d,i,stop,H=16):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.06: return None
    for k in range(i+1,i+1+H):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    return max(-1.0,min(2.0,(d["c"][i+H]-e)/R))
m,_=M.resolve(); data={}
for name,(k,s) in m.items(): rows=fetch(k,s,"15m",60); data[name]=(rows,M.indicators(rows))
btc=data["BTC"][1]; bidx={r[0]:i for i,r in enumerate(data["BTC"][0])}
res={}
for name,(rows,d) in data.items():
    if name=="BTC": continue
    n=len(rows); last={}; c=d["c"]
    s1=[False]*n
    for i in range(60,n-16):
        t=rows[i][0]; bi=bidx.get(t)
        rs=(c[i]/c[i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1) if bi and bi>=16 else None
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        cands=[]
        if sig and sig[0]==1 and rs is not None and rs>=0.01: cands.append(("1단계 눌림(RS1%)",d["sar"][i]))
        if sig and sig[0]==1 and rs is not None and 0.01<=rs<0.02: cands.append(("1단계 일반(RS1~2%)",d["sar"][i]))
        if sig and sig[0]==1 and rs is not None and rs>=0.02: cands.append(("1단계 강(RS2%+)",d["sar"][i]))
        if sig and sig[0]==2 and any(s1[i-12:i]): cands.append(("2단계 돌파(1단계 선행)",d["sar"][i]))
        hd=M.hold2(d,i)
        if hd and M.vratio(d,i)>=1.5: cands.append(("양봉2회방어(부하150%+)",hd["sup"]))
        rc=M.recl(d,i)
        if rc: cands.append(("투매후 시가회복",rc["low"]))
        for nm,stop in cands:
            if t-last.get(nm,0)<8*M.BAR: continue
            last[nm]=t; o=outcome(d,i,stop*0.999)
            if o is not None: res.setdefault(nm,[]).append((t,o))
        if i%4==0 and d["mb"][i] and c[i]>d["mb"][i]:
            o=outcome(d,i,min(d["l"][i-16:i])*0.999)
            if o is not None: res.setdefault("비교기준(임의봉)",[]).append((t,o))
allt=sorted(t for v in res.values() for t,_ in v); cut_t=allt[int(len(allt)*0.7)]
f=lambda z: f"n={len(z)} R={sum(z)/len(z):+.3f}" if z else "n=0"
print("60일 15분봉, 손절=패턴별 기준, 목표 2R, 4시간 / 기간분할 기준시각", time.strftime('%m/%d %H:%M', time.gmtime(cut_t+9*3600)))
for nm,v in res.items():
    a=[o for t,o in v if t<cut_t]; b=[o for t,o in v if t>=cut_t]
    print(f" {nm} | 하루 {len(v)/60:.1f} | 앞70% {f(a)} | 뒤30% {f(b)}")
