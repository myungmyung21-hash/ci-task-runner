import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
from research24 import agg4h
DAYS=300
res={}
for name in BV:
    if name=="BTC": continue
    r1,_=fetch_bv(name,"1h",DAYS+20)
    for tf,rows,step in (("1시간",r1,1),("4시간",agg4h(r1),4)):
        d=M.indicators(rows); c=d["c"]; n=len(c); hz={"1시간":(4,24),"4시간":(1,6)}[tf]
        for i in range(40,n-hz[1]-1):
            if d["up"][i]==d["up"][i-1]: continue
            run=0
            for q in range(i-1,max(0,i-80),-1):
                if d["up"][q]==d["up"][i-1]: run+=1
                else: break
            dirn=1 if d["up"][i] else -1
            # 직전 추세 동안 움직인 폭
            seg=c[i-run:i]; move=(max(seg)/min(seg)-1)*100 if seg else 0
            e=c[i]; a=(c[i+hz[0]]/e-1)*100*dirn; b=(c[i+hz[1]]/e-1)*100*dirn
            fav=((max(d["h"][i+1:i+1+hz[1]])/e-1) if dirn==1 else (1-min(d["l"][i+1:i+1+hz[1]])/e))*100
            adv=((1-min(d["l"][i+1:i+1+hz[1]])/e) if dirn==1 else (max(d["h"][i+1:i+1+hz[1]])/e-1))*100
            for th in (0,10,20,30):
                if run>=th:
                    res.setdefault((tf,"하락 전환(short)" if dirn==-1 else "상승 전환(롱)",f"직전 {th}봉+ 유지"),[]).append((rows[i][0],a,b,fav,adv))
            if run>=20 and move>=5:
                res.setdefault((tf,"하락 전환(short)" if dirn==-1 else "상승 전환(롱)","직전 20봉+ 유지·추세폭 5%+"),[]).append((rows[i][0],a,b,fav,adv))
def blk(v):
    t0=min(x[0] for x in v); w=(max(x[0] for x in v)-t0)/5 or 1
    return [[x[2] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
print(f"바이낸스 {DAYS}일 12종목 SAR 전환 (수익은 전환 방향 기준 %, 1시간봉: 4h/24h 후, 4시간봉: 4h/24h 후)")
print(" 봉 | 방향 | 조건 | 건수 | 하루 | 4h후 | 24h후 | 24h 유리최대 | 24h 역행최대 | 24h후 5구간 | 플러스")
for k in sorted(res):
    v=res[k]; bl=blk(v)
    print(f" {k[0]} | {k[1]} | {k[2]} | {len(v)} | {len(v)/DAYS:.2f} | {st.mean(x[1] for x in v):+.2f} | {st.mean(x[2] for x in v):+.2f} | {st.mean(x[3] for x in v):.2f} | {st.mean(x[4] for x in v):.2f} | "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
