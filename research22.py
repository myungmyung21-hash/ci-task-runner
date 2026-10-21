import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=16
res={}
for name in BV:
    if name=="BTC": continue
    r,_=fetch_bv(name,"15m",DAYS); r1,_=fetch_bv(name,"1h",DAYS+5); d=M.indicators(r); n=len(r); s1=[False]*n; last=0; hj=0
    for i in range(120,n-H):
        t=r[i][0]
        while hj+1<len(r1) and r1[hj+1][0]+3600<=t+900: hj+=1
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        if not(sig and sig[0]==2 and any(s1[i-12:i])) or t-last<8*900 or hj<100: continue
        last=t; g=M.s2_grade(d,i,r1[hj-99:hj+1]); fin=(d["c"][i+H]/d["c"][i]-1)*100
        fav=(max(d["h"][i+1:i+1+H])/d["c"][i]-1)*100; adv=(1-min(d["l"][i+1:i+1+H])/d["c"][i])*100
        for k in ("전체(기존 [단독])", {"strong":"새 [1면 단독]","normal":"새 [단독]",None:"제외(1시간 중심선 아래)"}[g]):
            res.setdefault(k,[]).append((t,fin,fav,adv))
allt=[x[0] for v in res.values() for x in v]; t0,t1=min(allt),max(allt); w=(t1-t0)/5
print("바이낸스 300일 12종목, 새 등급 기준 4시간 후 % (5구간)")
for k,v in res.items():
    bl=[[x[1] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
    print(f" {k} | n={len(v)} 하루 {len(v)/DAYS:.2f} | 4h후 {st.mean(x[1] for x in v):+.2f}% | +1%이상 {sum(x[1]>=1 for x in v)/len(v)*100:.0f}% | 유리최대 {st.mean(x[2] for x in v):.2f} 역행최대 {st.mean(x[3] for x in v):.2f} | 5구간 "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
