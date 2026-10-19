import time
import monitor as M
from research6 import fetch
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
now=time.time(); info={}
for name,(rows,d) in data.items():
    last24=sum(r[5] for r in rows if r[0]>=now-86400)
    d30=sum(r[5] for r in rows if r[0]>=now-30*86400)/30
    rng=[r[2]-r[3] for r in rows[-2880:]]; wick=[(r[2]-r[3]-abs(r[4]-r[1]))/(r[2]-r[3]) for r in rows[-2880:] if r[2]>r[3]]
    flat=sum(1 for x in rng if x==0)/len(rng)
    info[name]=dict(t24=last24,d30=d30,wick=sum(wick)/len(wick),flat=flat)
print("종목별 Gate 거래대금(USDT) | 최근24h | 30일 일평균 | 꼬리비율 | 무변동봉")
for n,v in sorted(info.items(),key=lambda x:-x[1]["d30"]):
    print(f" {n} | {v['t24']:,.0f} | {v['d30']:,.0f} | {v['wick']*100:.0f}% | {v['flat']*100:.1f}%")
alts=sorted([n for n in info if n!="BTC"],key=lambda n:-info[n]["d30"])
tiers={"상위6":alts[:6],"중위6":alts[6:12],"하위6":alts[12:]}
print({k:v for k,v in tiers.items()})
res={}
for tier,names in tiers.items():
    for name in names:
        rows,d=data[name]; n=len(rows); last={}; c=d["c"]; s1=[False]*n
        for i in range(60,n-16):
            t=rows[i][0]; bi=bidx.get(t)
            rs=(c[i]/c[i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1) if bi and bi>=16 else None
            sig=M.detect(d,i)
            if sig and sig[0]==1: s1[i]=True
            cands=[]
            if sig and sig[0]==1 and rs is not None and rs>=0.01: cands.append(("1단계",d["sar"][i]))
            if sig and sig[0]==2 and any(s1[i-12:i]): cands.append(("2단계",d["sar"][i]))
            hd=M.hold2(d,i)
            if hd and M.vratio(d,i)>=1.5: cands.append(("양봉2회",hd["sup"]))
            rc=M.recl(d,i)
            if rc: cands.append(("투매회복",rc["low"]))
            for nm,stop in cands:
                if t-last.get(nm,0)<8*M.BAR: continue
                last[nm]=t; o=outcome(d,i,stop*0.999)
                if o is not None: res.setdefault((tier,nm),[]).append(o)
            if i%4==0 and d["mb"][i] and c[i]>d["mb"][i]:
                o=outcome(d,i,min(d["l"][i-16:i])*0.999)
                if o is not None: res.setdefault((tier,"비교기준"),[]).append(o)
import statistics as st
print("\n거래대금 구간별 60일 성과 (R 평균 ± 표준오차)")
for tier in tiers:
    for nm in ("비교기준","1단계","2단계","양봉2회","투매회복"):
        v=res.get((tier,nm),[])
        if len(v)>2: print(f" {tier} | {nm} | n={len(v)} | R={sum(v)/len(v):+.3f} ± {st.pstdev(v)/len(v)**0.5:.3f} | 표준편차 {st.pstdev(v):.2f}")
