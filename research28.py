import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=96
res={}
BTC15,_=fetch_bv("BTC","15m",DAYS)
for name in BV:
    if name=="BTC": continue
    r15,_=fetch_bv(name,"15m",DAYS); r1,_=fetch_bv(name,"1h",DAYS+60); r1d=None
    now=r15[-1][0]+900; d=M.indicators(r15); c=d["c"]; hh=d["h"]; ll=d["l"]; n=len(c)
    bidx={x[0]:j for j,x in enumerate(BTC15)}
    idx1={x[0]:j for j,x in enumerate(r1)}; r4=M.agg_closed(r1,14400,now); rd=M.agg_closed(r1,86400,now)
    fl=M.mtf_flips(r15,r1,rd,now); s1=[False]*n; last={}; prevk={1:0,-1:0}; j1=0
    def add(nm,i,dirn):
        e=c[i]; fin=(c[i+H]/e-1)*100*dirn
        fav=((max(hh[i+1:i+1+H])/e-1) if dirn==1 else (1-min(ll[i+1:i+1+H])/e))*100
        res.setdefault(nm,[]).append((r15[i][0],fin,fav))
    q4=0
    for i in range(200,n-H):
        t=r15[i][0]; ct=t+900
        while j1+1<len(r1) and r1[j1+1][0]+3600<=ct: j1+=1
        h1=r1[max(0,j1-99):j1+1]
        bi=bidx.get(t)
        rs=(c[i]/c[i-16]-1)-(BTC15[bi][4]/BTC15[bi-16][4]-1) if bi and bi>=16 else None
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        if sig and sig[0]==2 and any(s1[i-12:i]) and t-last.get("s2",0)>=8*900:
            g=M.s2_grade(d,i,h1)
            if g: last["s2"]=t; add("1위 [1면 단독]" if g=="strong" else "3위 [단독]",i,1)
        sh=M.short_sig(d,i,rs) if rs is not None else None
        if sh and t-last.get("s",0)>=8*900 and M.down_1h(r1[max(0,j1-59):j1+1]): last["s"]=t; add("4위 short [해설]",i,-1)
        if ct%14400==0:
            r4c=[x for x in r4 if x[0]+14400<=ct][-100:]
            s4=M.short4h_sig(r4c)
            if s4 and last.get("s4")!=s4["t"]: last["s4"]=s4["t"]; add("2위 short [사설]",i,-1)
        cnt=M.mtf_count(fl,ct)
        for dirn in (1,-1):
            k=len(cnt[dirn])
            if k==4 and k>prevk[dirn]: add("0-1위 [특집]"+(" short" if dirn==-1 else ""),i,dirn)
            prevk[dirn]=k
print(f"바이낸스 {DAYS}일 12종목, 알람 후 24시간 (수익은 알람 방향 기준 %)")
print(" 알람 | 건수 | 24h후 평균 | 24h후 중앙값 | 24h 유리최대 평균 | 24h 안 +2% 도달 비율 | 24h후 +2% 이상 비율")
for k,v in sorted(res.items()):
    print(f" {k} | {len(v)} | {st.mean(x[1] for x in v):+.2f} | {st.median(x[1] for x in v):+.2f} | {st.mean(x[2] for x in v):.2f} | {sum(x[2]>=2 for x in v)/len(v)*100:.0f}% | {sum(x[1]>=2 for x in v)/len(v)*100:.0f}%")
