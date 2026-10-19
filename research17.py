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
            ev.append(dict(nm=nm,name=name,t=t,fav=fav,kf=kf,adv=adv,ka=ka,fin=fin,f=f))
print(f"바이낸스 선물 15분봉 {DAYS}일, 12종목, 알람 후 4시간(16봉) / 유리=알람 방향, 반대=역방향 (%)")
for nm in ("[단독]","[속보]","short","전체"):
    g=[e for e in ev if nm=="전체" or e["nm"]==nm]
    bothfirst=sum(1 for e in g if e["kf"]<e["ka"])/len(g)*100
    print(f"\n== {nm} {len(g)}건")
    print(f" 유리 최대폭 평균 {st.mean(e['fav'] for e in g):.2f} 중앙 {st.median(e['fav'] for e in g):.2f} | 도달까지 평균 {st.mean(e['kf'] for e in g)*15:.0f}분 중앙 {st.median(e['kf'] for e in g)*15:.0f}분")
    print(f" 반대 최대폭 평균 {st.mean(e['adv'] for e in g):.2f} 중앙 {st.median(e['adv'] for e in g):.2f} | 도달까지 평균 {st.mean(e['ka'] for e in g)*15:.0f}분 중앙 {st.median(e['ka'] for e in g)*15:.0f}분 | 유리 고점이 먼저 온 비율 {bothfirst:.0f}%")
    print(f" 4시간 후 평균 {st.mean(e['fin'] for e in g):+.2f} 중앙 {st.median(e['fin'] for e in g):+.2f} | 4시간 후 +1% 이상 {sum(e['fin']>=1 for e in g)/len(g)*100:.0f}% / -1% 이하 {sum(e['fin']<=-1 for e in g)/len(g)*100:.0f}%")
    print(" 유리 최대폭 분포: " + " | ".join(f"{x}% 이상 {sum(e['fav']>=x for e in g)}건({sum(e['fav']>=x for e in g)/len(g)*100:.1f}%)" for x in (1,3,5,10)))
big=[e for e in ev if e["fav"]>=10]; mid=[e for e in ev if e["fav"]>=5]; rest=[e for e in ev if e["fav"]<5]
print(f"\n== 4시간 안에 알람 방향으로 10% 이상 간 사례 {len(big)}건")
for e in sorted(big,key=lambda x:-x["fav"]):
    f=e["f"]
    print(f" {e['name']} {e['nm']} {datetime.fromtimestamp(e['t']+900,M.KST):%y-%m-%d %H:%M} | 최대 {e['fav']:.1f}% ({e['kf']*15}분) 4시간후 {e['fin']:+.1f}% 반대최대 {e['adv']:.1f}% | ATR {f['atrp']:.2f}% 거래 {f['vr']*100:.0f}% 밴드폭 {f['bw']:.1f}% 24h {f['ret24']:+.1f}% BTC4h {f['btc4']:+.1f}% RSI {f['rsi']:.0f}")
def cmp(lbl,A,B):
    print(f"\n== {lbl}: {len(A)}건 vs 나머지 {len(B)}건 (중앙값)")
    for k in ("atrp","vr","bw","rs","btc4","ret24","rsi"):
        print(f" {k} | {st.median(e['f'][k] for e in A):.2f} | {st.median(e['f'][k] for e in B):.2f}")
    print(f" 1시간 상승추세 비율 | {sum(e['f']['h1_up'] for e in A)/len(A)*100:.0f}% | {sum(e['f']['h1_up'] for e in B)/len(B)*100:.0f}%")
if mid: cmp("5% 이상 간 알람",mid,rest)
# 변동성 상위 알람만 골랐을 때
ev.sort(key=lambda e:e["t"]); cut=ev[int(len(ev)*0.7)]["t"]
q=sorted(e["f"]["atrp"] for e in ev if e["t"]<cut); th=q[int(len(q)*0.8)]
for lbl,sel in (("ATR 상위 20%",lambda e:e["f"]["atrp"]>=th),("나머지",lambda e:e["f"]["atrp"]<th)):
    A=[e for e in ev if e["t"]>=cut and sel(e)]
    print(f"\n검증구간(뒤30%) {lbl} n={len(A)} | 유리최대 평균 {st.mean(e['fav'] for e in A):.2f} | 5%이상 {sum(e['fav']>=5 for e in A)/len(A)*100:.1f}% | 반대최대 평균 {st.mean(e['adv'] for e in A):.2f} | 4시간후 평균 {st.mean(e['fin'] for e in A):+.2f}")
print(f"(ATR 기준값 {th:.2f}%, 앞70% 구간으로 정함)")
