from datetime import datetime
import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
from research6 import rsi
DAYS=300; H=16
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    d=M.indicators(r15); d["t"]=[r[0] for r in r15]; d["rsi"]=rsi(d["c"]); h=M.indicators(r1h); h["t"]=[r[0] for r in r1h]
    data[name]=(d,h)
btc=data["BTC"][0]; bidx={t:i for i,t in enumerate(btc["t"])}
ev=[]
for name,(d,h) in data.items():
    if name=="BTC": continue
    c=d["c"]; n=len(c); last={}; s1=[False]*n; hj=0
    for i in range(100,n-H-1):
        t=d["t"][i]; bi=bidx.get(t)
        if bi is None or bi<96: continue
        rs=(c[i]/c[i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1)
        while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        cs=[]
        if M.recl(d,i): cs.append(("[속보]",1))
        if sig and sig[0]==2 and any(s1[i-12:i]): cs.append(("[단독]",1))
        sh=M.short_sig(d,i,rs)
        if sh and hj>30 and (not h["up"][hj]) and h["mb"][hj] and h["c"][hj]<h["mb"][hj]: cs.append(("short",-1))
        for nm,side in cs:
            if t-last.get(nm,0)<8*900: continue
            last[nm]=t; e=c[i]
            hs=d["h"][i+1:i+1+H]; ls=d["l"][i+1:i+1+H]
            if side==1:
                fav=(max(hs)/e-1)*100; kf=hs.index(max(hs))+1; adv=(1-min(ls)/e)*100; ka=ls.index(min(ls))+1; fin=(c[i+H]/e-1)*100
            else:
                fav=(1-min(ls)/e)*100; kf=ls.index(min(ls))+1; adv=(max(hs)/e-1)*100; ka=hs.index(max(hs))+1; fin=(1-c[i+H]/e)*100
            a=M.atr(d,i); j=hj
            f=dict(atrp=a/e*100, vr=M.vratio(d,i), bw=(d["ub"][i]-d["lb"][i])/d["mb"][i]*100, rs=rs*100,
                   btc4=(btc["c"][bi]/btc["c"][bi-16]-1)*100, ret24=(c[i]/c[i-96]-1)*100, rsi=d["rsi"][i],
                   h1_up=bool(h["up"][j]), hour=datetime.fromtimestamp(t+900,M.KST).hour)
            ev.append(dict(nm=nm,name=name,t=t,i=i,side=side,fav=fav,kf=kf,adv=adv,ka=ka,fin=fin,f=f))

from research16 import run
t0=min(e["t"] for e in ev); w=(max(e["t"] for e in ev)-t0)/5
def rep(lbl,g):
    if len(g)<10: print(f" {lbl} | n={len(g)} (표본 부족)"); return
    bl=[[e["fin"] for e in g if min(4,int((e["t"]-t0)/w))==b] for b in range(5)]
    cf=[run(data[e["name"]][0],e["i"],e["side"],"close",2,3) for e in g]; cf=[r[1] for r in cf if r]
    print(f" {lbl} | n={len(g)} 하루{len(g)/DAYS:.2f} | 5%+ {sum(e['fav']>=5 for e in g)/len(g)*100:.1f}% 10%+ {sum(e['fav']>=10 for e in g)/len(g)*100:.1f}% | 유리 {st.mean(e['fav'] for e in g):.2f} 반대 {st.mean(e['adv'] for e in g):.2f} | 4h후 평균 {st.mean(e['fin'] for e in g):+.2f} 5구간 "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | 30분확인 진입 {len(cf)}건 평균 {st.mean(cf) if cf else 0:+.2f}")
for nm in ("[단독]","[속보]","short"):
    g=[e for e in ev if e["nm"]==nm]; up=nm!="short"
    print(f"\n== {nm}")
    rep("전체",g)
    rep("RSI 70+" if up else "RSI 30-",[e for e in g if (e["f"]["rsi"]>=70 if up else e["f"]["rsi"]<=30)])
    rep("24h +5%+" if up else "24h -5%-",[e for e in g if (e["f"]["ret24"]>=5 if up else e["f"]["ret24"]<=-5)])
    rep("거래 300%+",[e for e in g if e["f"]["vr"]>=3])
    rep("밴드폭 4%+",[e for e in g if e["f"]["bw"]>=4])
    rep("1h 추세 같은 방향",[e for e in g if e["f"]["h1_up"]==up])
    rep("RSI극단+24h추세+거래300%",[e for e in g if (e["f"]["rsi"]>=70 if up else e["f"]["rsi"]<=30) and (e["f"]["ret24"]>=5 if up else e["f"]["ret24"]<=-5) and e["f"]["vr"]>=3])
    rep("거래300%+밴드폭4%+",[e for e in g if e["f"]["vr"]>=3 and e["f"]["bw"]>=4])
