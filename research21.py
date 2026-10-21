import time, statistics as st
from datetime import datetime
import numpy as np
import monitor as M
from bvdata import fetch_bv, BV
from research6 import rsi, fetch
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
DAYS=300; H=16
# A. 최근 48시간 Gate [단독] 실제 결과
m,_=M.resolve(); print("== Gate 최근 48시간 [단독]/[1면 단독] 재현 (알람 후 4시간, %)")
for name,(k,s) in m.items():
    if name=="BTC": continue
    r=fetch(k,s,"15m",4); d=M.indicators(r); n=len(r); s1=[False]*n; last=0
    for i in range(60,n):
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        if r[i][0]<time.time()-48*3600 or not(sig and sig[0]==2 and any(s1[i-12:i])) or r[i][0]-last<8*900: continue
        last=r[i][0]; e=d["c"][i]; fut=r[i+1:i+1+H]
        if not fut: continue
        print(f" {name} {datetime.fromtimestamp(r[i][0]+900,M.KST):%m/%d %H:%M} {'1면' if M.strong_s2(d,i) else '일반'} | 최고 {(max(x[2] for x in fut)/e-1)*100:+.2f} 최저 {(min(x[3] for x in fut)/e-1)*100:+.2f} 마지막 {(fut[-1][4]/e-1)*100:+.2f} ({len(fut)}봉)")
# B. 300일 [단독] 특징 학습
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    d=M.indicators(r15); d["t"]=[x[0] for x in r15]; d["rsi"]=rsi(d["c"])
    h=M.indicators(r1h); h["t"]=[x[0] for x in r1h]; h["rsi"]=rsi(h["c"]); data[name]=(d,h)
btc=data["BTC"][0]; bidx={t:i for i,t in enumerate(btc["t"])}
ev=[]
for name,(d,h) in data.items():
    if name=="BTC": continue
    c,o,hh,ll=d["c"],d["o"],d["h"],d["l"]; n=len(c); s1=[False]*n; last=0; hj=0; s2hist=[]
    for i in range(120,n-H):
        t=d["t"][i]; bi=bidx.get(t)
        while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        if not(sig and sig[0]==2 and any(s1[i-12:i])) or bi is None or bi<96 or hj<30: continue
        s2hist.append(i)
        if t-last<8*900: continue
        last=t; e=c[i]; a=M.atr(d,i); rng=hh[i]-ll[i]
        green=0
        for q in range(i,i-12,-1):
            if c[q]>o[q]: green+=1
            else: break
        f=dict(rsi=d["rsi"][i], bw=(d["ub"][i]-d["lb"][i])/d["mb"][i]*100, vr=M.vratio(d,i), vrmax4=max(M.vratio(d,q) for q in range(i-3,i+1)),
               ret4h=(e/c[i-16]-1)*100, ret24=(e/c[i-96]-1)*100, btc4=(btc["c"][bi]/btc["c"][bi-16]-1)*100, btc24=(btc["c"][bi]/btc["c"][bi-96]-1)*100,
               rs4=((e/c[i-16])-(btc["c"][bi]/btc["c"][bi-16]))*100, atrp=a/e*100, uwick=(hh[i]-c[i])/rng if rng>0 else 0,
               body_atr=(c[i]-o[i])/a if a else 0, green=green, from_high96=(e/max(hh[i-96:i+1])-1)*100,
               h1_rsi=h["rsi"][hj], h1_up=1 if h["up"][hj] else 0, h1_above_mb=1 if h["c"][hj]>h["mb"][hj] else 0,
               h1_bw=(h["ub"][hj]-h["lb"][hj])/h["mb"][hj]*100, prior_s2_24h=sum(1 for q in s2hist if i-96<=q<i),
               hour=datetime.fromtimestamp(t+900,M.KST).hour)
        fut_h=max(hh[i+1:i+1+H]); fut_l=min(ll[i+1:i+1+H])
        ev.append(dict(t=t,name=name,f=f,fin=(c[i+H]/e-1)*100,fav=(fut_h/e-1)*100,adv=(1-fut_l/e)*100))
ev.sort(key=lambda x:x["t"]); K=list(ev[0]["f"].keys())
X=np.array([[e["f"][k] for k in K] for e in ev]); y=np.array([1 if e["fin"]>=1 else 0 for e in ev]); fin=np.array([e["fin"] for e in ev])
cut=int(len(ev)*0.7); t0=ev[0]["t"]; w=(ev[-1]["t"]-t0)/5
print(f"\n== [단독] {len(ev)}건 학습 (목표: 4시간 후 +1% 이상, 기준비율 {y.mean()*100:.1f}%)")
gb=GradientBoostingClassifier(max_depth=2,n_estimators=200,learning_rate=0.05,subsample=0.8,random_state=0).fit(X[:cut],y[:cut])
p=gb.predict_proba(X[cut:])[:,1]; print(f" 검증 AUC {roc_auc_score(y[cut:],p):.3f}")
for q in (0.5,0.8,0.9):
    th=np.quantile(p,q); s=p>=th
    print(f" 검증 상위 {int((1-q)*100)}% | n={s.sum()} | +1%이상 {y[cut:][s].mean()*100:.1f}% | 4h후 평균 {fin[cut:][s].mean():+.2f}% (검증 전체 {fin[cut:].mean():+.2f}%)")
print(" 중요 변수:",", ".join(f"{k} {v:.2f}" for k,v in sorted(zip(K,gb.feature_importances_),key=lambda x:-x[1])[:8]))
def blocks(g): return [[e["fin"] for e in g if min(4,int((e["t"]-t0)/w))==b] for b in range(5)]
def line(lbl,g):
    if len(g)<15: print(f" {lbl} | n={len(g)} 표본부족"); return
    bl=blocks(g); pos=sum(1 for b in bl if b and st.mean(b)>0)
    print(f" {lbl} | n={len(g)} 하루 {len(g)/DAYS:.2f} | 4h후 {st.mean(e['fin'] for e in g):+.2f}% | +1%이상 {sum(e['fin']>=1 for e in g)/len(g)*100:.0f}% | 유리최대 {st.mean(e['fav'] for e in g):.2f} 역행최대 {st.mean(e['adv'] for e in g):.2f} | 5구간 "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {pos}/5")
print("\n== 변수별 5분위 (4시간 후 평균 %)")
for k in K:
    vals=sorted(e["f"][k] for e in ev); qs=[vals[int(len(vals)*z)] for z in (0.2,0.4,0.6,0.8)]
    buck=[[e for e in ev if (b==0 or e["f"][k]>=qs[b-1]) and (b==4 or e["f"][k]<qs[b])] for b in range(5)]
    print(f" {k} | "+" | ".join(f"{('<'+format(qs[0],'.1f')) if b==0 else ('>='+format(qs[b-1],'.1f'))}: {st.mean(x['fin'] for x in g):+.2f}({len(g)})" for b,g in enumerate(buck) if g))
print("\n== 후보 규칙")
line("전체",ev)
line("RSI 70+ (현 1면)",[e for e in ev if e["f"]["rsi"]>=70])
line("밴드폭 4%+ (현 1면)",[e for e in ev if e["f"]["bw"]>=4])
line("1시간 RSI 65+",[e for e in ev if e["f"]["h1_rsi"]>=65])
line("1시간 밴드폭 상위(8%+)",[e for e in ev if e["f"]["h1_bw"]>=8])
line("24h +5%+",[e for e in ev if e["f"]["ret24"]>=5])
line("24h 고점 근처(-1% 이내)",[e for e in ev if e["f"]["from_high96"]>=-1])
line("BTC 4h 플러스",[e for e in ev if e["f"]["btc4"]>0])
line("BTC 대비 강세 4h +2%p",[e for e in ev if e["f"]["rs4"]>=2])
line("알람봉 윗꼬리 30% 미만",[e for e in ev if e["f"]["uwick"]<0.3])
line("24h 안 첫 [단독]",[e for e in ev if e["f"]["prior_s2_24h"]==0])
line("RSI70+ & 1h RSI65+",[e for e in ev if e["f"]["rsi"]>=70 and e["f"]["h1_rsi"]>=65])
line("RSI70+ & BTC 4h 플러스",[e for e in ev if e["f"]["rsi"]>=70 and e["f"]["btc4"]>0])
line("RSI70+ & 윗꼬리 30% 미만",[e for e in ev if e["f"]["rsi"]>=70 and e["f"]["uwick"]<0.3])
line("밴드폭4%+ 또는 RSI70+ (현 1면 전체)",[e for e in ev if e["f"]["bw"]>=4 or e["f"]["rsi"]>=70])
line("현 1면 & BTC 대비 +2%p",[e for e in ev if (e["f"]["bw"]>=4 or e["f"]["rsi"]>=70) and e["f"]["rs4"]>=2])
