from datetime import datetime
import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=16
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    d=M.indicators(r15); d["t"]=[r[0] for r in r15]; h=M.indicators(r1h); h["t"]=[r[0] for r in r1h]
    data[name]=(d,h)
btc=data["BTC"][0]; bidx={t:i for i,t in enumerate(btc["t"])}
ev=[]
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
        cs=[]
        if M.recl(d,i): cs.append("[속보] 투매후회복")
        if sig and sig[0]==2 and any(s1[i-12:i]): cs.append("[단독] 2단계돌파")
        sh=M.short_sig(d,i,rs)
        if sh and hj>30 and (not h["up"][hj]) and h["mb"][hj] and h["c"][hj]<h["mb"][hj]: cs.append("short SAR전환")
        for nm in cs:
            if t-last.get(nm,0)<8*900: continue
            last[nm]=t; e=c[i]
            up=(max(d["h"][i+1:i+1+H])/e-1)*100; dn=(min(d["l"][i+1:i+1+H])/e-1)*100; cl=(c[i+H]/e-1)*100
            ev.append(dict(nm=nm,name=name,t=t,up=up,dn=dn,cl=cl))
kst=lambda t: datetime.fromtimestamp(t+900,M.KST).strftime("%y-%m-%d %H:%M")
print(f"바이낸스 선물 15분봉 {DAYS}일, 12종목, 알람 후 4시간 기준 (%)")
for nm in ("[단독] 2단계돌파","[속보] 투매후회복","short SAR전환"):
    g=[e for e in ev if e["nm"]==nm]; sh=nm.startswith("short")
    fav=[(-e["dn"] if sh else e["up"]) for e in g]; adv=[(e["up"] if sh else -e["dn"]) for e in g]; cl=[(-e["cl"] if sh else e["cl"]) for e in g]
    best=max(g,key=lambda e:(-e["dn"] if sh else e["up"])); worst=min(g,key=lambda e:(-e["cl"] if sh else e["cl"]))
    print(f"\n{nm} | {len(g)}건 | 유리한 방향 최대폭 평균 {st.mean(fav):.2f} 중앙값 {st.median(fav):.2f} | 4시간 후 수익 평균 {st.mean(cl):+.2f} 중앙값 {st.median(cl):+.2f} | 4시간 후 플러스 비율 {sum(x>0 for x in cl)/len(cl)*100:.0f}% | 반대방향 최대폭 평균 {st.mean(adv):.2f}")
    print(f"  최고: {best['name']} {kst(best['t'])} 유리한 최대폭 {(-best['dn'] if sh else best['up']):.2f} (4시간 후 {(-best['cl'] if sh else best['cl']):+.2f})")
    print(f"  최저: {worst['name']} {kst(worst['t'])} 4시간 후 {(-worst['cl'] if sh else worst['cl']):+.2f} (반대방향 최대 {(worst['up'] if sh else -worst['dn']):.2f})")
    print("  종목별 | 건수 | 유리 최대폭 평균 | 4시간 후 평균 | 플러스 비율")
    for nmc in sorted(set(e["name"] for e in g), key=lambda x: -st.mean([(-e['cl'] if sh else e['cl']) for e in g if e['name']==x])):
        z=[e for e in g if e["name"]==nmc]
        f=[(-e["dn"] if sh else e["up"]) for e in z]; c2=[(-e["cl"] if sh else e["cl"]) for e in z]
        print(f"   {nmc} | {len(z)} | {st.mean(f):.2f} | {st.mean(c2):+.2f} | {sum(x>0 for x in c2)/len(c2)*100:.0f}%")
