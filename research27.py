import statistics as st, bisect
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H4=16; H24=96
import sys
VAR={"C(4시간 10봉+ 전환 필수)":[16,12,6,3]}
res={}
for name in BV:
    if name=="BTC": continue
    r15,_=fetch_bv(name,"15m",DAYS); r1,_=fetch_bv(name,"1h",DAYS+60)
    now=r15[-1][0]+900
    tfs=[r15, r1, M.agg_closed(r1,14400,now), M.agg_closed(r1,86400,now)]
    flips=[M.sar_flips(rows,sec,need) for rows,(nm,sec,need,fr) in zip(tfs,M.MTF)]
    c=[x[4] for x in r15]; hh=[x[2] for x in r15]; ll=[x[3] for x in r15]
    for vn,fr in VAR.items():
     M.MTF=[(a,b,c_,f) for (a,b,c_,_),f in zip(M.MTF,fr)]
     prev={1:0,-1:0}
     for i in range(200,len(r15)-H24):
        T=r15[i][0]+900; cnt=M.mtf_count(flips,T)
        for dirn in (1,-1):
            k=len(cnt[dirn])
            if k==0: prev[dirn]=0; continue
            if k>prev[dirn]:
                key=(vn,k,dirn)
                e=c[i]; a=(c[i+H4]/e-1)*100*dirn; b=(c[i+H24]/e-1)*100*dirn
                fav=((max(hh[i+1:i+1+H24])/e-1) if dirn==1 else (1-min(ll[i+1:i+1+H24])/e))*100
                adv=((1-min(ll[i+1:i+1+H24])/e) if dirn==1 else (max(hh[i+1:i+1+H24])/e-1))*100
                res.setdefault(key,[]).append((r15[i][0],a,b,fav,adv,"+".join(cnt[dirn])))
            prev[dirn]=k
def blk(v,j):
    t0=min(x[0] for x in v); w=(max(x[0] for x in v)-t0)/5 or 1
    return [[x[j] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
print(f"바이낸스 {DAYS}일 12종목 | 15분·1시간(20봉+)·4시간(10봉+, 필수)·일봉(10봉+) SAR 전환 동시 발생 수 | 수익은 전환 방향 기준 %")
print(" 등급 | 방향 | 건수 | 하루 | 4h후 | 24h후 | 24h 유리최대 | 24h 역행최대 | 24h후 5구간 | 플러스 | 흔한 조합")
for vn,fr in VAR.items():
  print(f"\n[신선도 {vn}] 전환 후 유효 봉수 15분 {fr[0]}봉, 1시간 {fr[1]}봉, 4시간 {fr[2]}봉, 일봉 {fr[3]}봉")
  for k in (4,3,2,1):
    for dirn in (1,-1):
        v=res.get((vn,k,dirn),[])
        if not v: print(f" 0-{5-k}위({k}개) | {'롱' if dirn==1 else 'short'} | 0건"); continue
        bl=blk(v,2); combos={}
        for x in v: combos[x[5]]=combos.get(x[5],0)+1
        top=", ".join(f"{a}({b})" for a,b in sorted(combos.items(),key=lambda z:-z[1])[:2])
        print(f" 0-{5-k}위({k}개) | {'롱' if dirn==1 else 'short'} | {len(v)} | {len(v)/DAYS:.2f} | {st.mean(x[1] for x in v):+.2f} | {st.mean(x[2] for x in v):+.2f} | {st.mean(x[3] for x in v):.2f} | {st.mean(x[4] for x in v):.2f} | "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {sum(1 for b in bl if b and st.mean(b)>0)}/5 | {top}")
