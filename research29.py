import time, statistics as st, pickle, base64
from datetime import datetime
import numpy as np
import monitor as M
from bvdata import fetch_bv, BV
from research6 import rsi
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import roc_auc_score
DAYS=300; H=96; UP=5.0; DN=2.5
def last_idx(ts, T):
    lo,hi,j=0,len(ts)-1,-1
    while lo<=hi:
        m=(lo+hi)//2
        if ts[m]<=T: j=m; lo=m+1
        else: hi=m-1
    return j
def tf_pack(rows, sec):
    d=M.indicators(rows); d["rsi"]=rsi(d["c"]); d["close_t"]=[r[0]+sec for r in rows]; return d
def feats(d15,i,d1,j1,d4,j4,dd,jd,btc1,jb):
    c=d15["c"]; e=c[i]
    f=dict(ret1h=(e/c[i-4]-1)*100, ret4h=(e/c[i-16]-1)*100, ret24=(e/c[i-96]-1)*100,
           ret7d=(d1["c"][j1]/d1["c"][j1-168]-1)*100 if j1>=168 else 0,
           rsi15=d15["rsi"][i], rsi1h=d1["rsi"][j1], rsi4h=d4["rsi"][j4], rsid=dd["rsi"][jd],
           bw15=(d15["ub"][i]-d15["lb"][i])/d15["mb"][i]*100, bw1h=(d1["ub"][j1]-d1["lb"][j1])/d1["mb"][j1]*100,
           bw4h=(d4["ub"][j4]-d4["lb"][j4])/d4["mb"][j4]*100,
           atr15=M.atr(d15,i)/e*100, vr15=M.vratio(d15,i), vr1h=M.vratio(d1,j1),
           fromhi7=(d1["c"][j1]/max(d1["h"][max(0,j1-168):j1+1])-1)*100, fromlo7=(d1["c"][j1]/min(d1["l"][max(0,j1-168):j1+1])-1)*100,
           sar1h=1 if d1["up"][j1] else 0, sar4h=1 if d4["up"][j4] else 0, sard=1 if dd["up"][jd] else 0,
           above_d_mb=1 if dd["c"][jd]>dd["mb"][jd] else 0,
           btc4h=(btc1["c"][jb]/btc1["c"][jb-4]-1)*100, btc24=(btc1["c"][jb]/btc1["c"][jb-24]-1)*100, btcrsi1h=btc1["rsi"][jb],
           hour=datetime.fromtimestamp(d15["close_t"][i],M.KST).hour)
    return f
b1,_=fetch_bv("BTC","1h",DAYS+40); btc1=tf_pack(b1,3600)
X=[]; Y=[]; INFO=[]
for name in BV:
    if name=="BTC": continue
    r15,_=fetch_bv(name,"15m",DAYS); r1,_=fetch_bv(name,"1h",DAYS+40); now=r15[-1][0]+900
    d15=tf_pack(r15,900); d1=tf_pack(r1,3600); d4=tf_pack(M.agg_closed(r1,14400,now),14400); dd=tf_pack(M.agg_closed(r1,86400,now),86400)
    for i in range(400,len(r15)-H,4):
        T=d15["close_t"][i]
        j1=last_idx(d1["close_t"],T); j4=last_idx(d4["close_t"],T); jd=last_idx(dd["close_t"],T); jb=last_idx(btc1["close_t"],T)
        if min(j1,j4,jd,jb)<30 or d15["mb"][i] is None or dd["mb"][jd] is None or d4["mb"][j4] is None: continue
        e=d15["c"][i]; y=0; res=None
        for k in range(i+1,i+1+H):
            if d15["l"][k]<=e*(1-DN/100): break
            if d15["h"][k]>=e*(1+UP/100): y=1; break
        fav=(max(d15["h"][i+1:i+1+H])/e-1)*100; fin=(d15["c"][i+H]/e-1)*100
        f=feats(d15,i,d1,j1,d4,j4,dd,jd,btc1,jb)
        X.append(list(f.values())); Y.append(y); INFO.append((T,name,fav,fin))
K=list(f.keys()); X=np.array(X); Y=np.array(Y)
order=np.argsort([x[0] for x in INFO]); X=X[order]; Y=Y[order]; INFO=[INFO[o] for o in order]
cut=int(len(Y)*0.7); tcut=INFO[cut][0]
print(f"표본 {len(Y)}개(1시간 간격) | 24시간 안 +{UP}%를 -{DN}%보다 먼저 찍은 비율: 전체 {Y.mean()*100:.1f}% | 학습 ~{datetime.fromtimestamp(tcut,M.KST):%m/%d}, 이후 검증")
gb=GradientBoostingClassifier(max_depth=3,n_estimators=250,learning_rate=0.05,subsample=0.8,min_samples_leaf=100,random_state=0).fit(X[:cut],Y[:cut])
p=gb.predict_proba(X[cut:])[:,1]; yt=Y[cut:]; it=INFO[cut:]
print(f"검증 AUC {roc_auc_score(yt,p):.3f} | 검증 기준비율 {yt.mean()*100:.1f}%")
tdays=(it[-1][0]-it[0][0])/86400
for q in (0.95,0.98,0.99,0.995):
    th=np.quantile(p,q); s=p>=th; idx=np.where(s)[0]
    favs=[it[j][2] for j in idx]; fins=[it[j][3] for j in idx]
    t0=it[0][0]; w=(it[-1][0]-t0)/3
    bl=[[it[j][3] for j in idx if min(2,int((it[j][0]-t0)/w))==b] for b in range(3)]
    print(f" 상위 {100-q*100:.1f}% (확률≥{th:.3f}) | n={s.sum()} 하루 {s.sum()/tdays:.2f} | +5% 먼저 {yt[s].mean()*100:.1f}% | 24h 유리최대 {st.mean(favs):.2f}% | 24h후 평균 {st.mean(fins):+.2f}% 중앙 {st.median(fins):+.2f}% | 검증 3구간 "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl))
print("중요 변수:",", ".join(f"{k} {v:.2f}" for k,v in sorted(zip(K,gb.feature_importances_),key=lambda x:-x[1])[:10]))
tr=DecisionTreeClassifier(max_depth=3,min_samples_leaf=300,random_state=0).fit(X[:cut],Y[:cut])
print(export_text(tr,feature_names=K,decimals=2))
lt=tr.apply(X[:cut]); lv=tr.apply(X[cut:])
for lf in sorted(set(lt)):
    a=lt==lf; b=lv==lf
    if b.sum(): print(f" leaf{lf} | 학습 n={a.sum()} 적중 {Y[:cut][a].mean()*100:.1f}% | 검증 n={b.sum()} 적중 {yt[b].mean()*100:.1f}% 24h후 {np.mean([it[j][3] for j in np.where(b)[0]]):+.2f}%")
# 전체 데이터로 재학습해 모델 저장(배포용)
gbf=GradientBoostingClassifier(max_depth=3,n_estimators=250,learning_rate=0.05,subsample=0.8,min_samples_leaf=100,random_state=0).fit(X,Y)
th99=float(np.quantile(gb.predict_proba(X[cut:])[:,1],0.99))
open("surge_model.b64","w").write(base64.b64encode(pickle.dumps({"model":gbf,"keys":K,"th99_valid":th99,"th99_full":float(np.quantile(gbf.predict_proba(X)[:,1],0.99))})).decode())
print("model saved")
