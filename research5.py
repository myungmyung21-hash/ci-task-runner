import time
from datetime import datetime
import monitor as M
from research import fetch_all, outcome
data = fetch_all(30)
def avg(v,i,n=20): return sum(v[i-n:i])/n
def ratio(v,i,n=20):
    a=avg(v,i,n); return v[i]/a if a>0 else 0
def kst(t): return datetime.fromtimestamp(t,M.KST)
def show(name, day, h0, h1):
    rows,d=data[name]; v=d["v"]
    print(f"\n{name} {day} {h0}~{h1}시 (봉시작 KST | O C | 양음 | 거래대금 | 20봉평균대비 | MB LB | SAR | DIF-DEA | hold2 | stage)")
    for i,r in enumerate(rows):
        t=kst(r[0])
        if t.strftime("%m/%d")==day and h0<=t.hour<=h1:
            hd=M.hold2(d,i); s=M.detect(d,i)
            print(f" {t:%H:%M} | {d['o'][i]:.7g} {d['c'][i]:.7g} | {'양' if d['c'][i]>d['o'][i] else '음'} | {v[i]:,.0f} | {ratio(v,i)*100:.0f}% | {d['mb'][i]:.7g} {d['lb'][i]:.7g} | {d['sar'][i]:.7g}{'U' if d['up'][i] else 'D'} | {d['dif'][i]-d['dea'][i]:+.2e} | {'Y' if hd else '-'} | {s[0] if s else '-'}")
show("PEPE","10/19",1,9)
show("HBAR","10/18",15,18)

def recl(d,i,win=16,vx=3.0):
    """투매(거래량 vx배 이상 장대음봉이 하단밴드 이탈) → 바닥 → 투매봉 시가 회복 양봉"""
    o,h,l,c,v=d["o"],d["h"],d["l"],d["c"],d["v"]
    if i<win+25 or not c[i]>o[i]: return None
    for k in range(i-3,i-win-1,-1):
        if not (c[k]<o[k] and ratio(v,k)>=vx and l[k]<=d["lb"][k]): continue
        ks=[k]+[j for j in (k-1,k+1) if c[j]<o[j] and ratio(v,j)>=vx*0.66]
        lvl=max(o[j] for j in ks)              # 투매 구간 첫 음봉 시가
        low=min(l[k-1:i+1])
        a=M.atr(d,i)
        if min(l[k:i+1])<min(l[k-1:k+2])-0.5*a: return None   # 바닥 재붕괴 없음
        if not (c[i]>lvl and c[i-1]<=lvl): return None
        return dict(k=k,lvl=lvl,low=low,cvx=ratio(v,k),ivx=ratio(v,i))
    return None

B=[(0,0.8),(0.8,1.2),(1.2,1.5),(1.5,2),(2,3),(3,99)]
def bucket(x):
    for b in B:
        if b[0]<=x<b[1]: return f"{b[0]*100:.0f}~{(str(int(b[1]*100))+'%') if b[1]<99 else '이상'}"
res={}; recent=[]
for name,(rows,d) in data.items():
    if name=="BTC": continue
    n=len(rows); lh=lr=0; v=d["v"]
    for i in range(60,n):
        t=rows[i][0]
        hd=M.hold2(d,i)
        if hd and t-lh>=8*M.BAR and i<n-16:
            lh=t; o=outcome(d,i,hd["sup"]*0.999)
            if o is not None:
                res.setdefault(("양봉2회방어","신호봉 "+bucket(ratio(v,i))),[]).append(o)
                res.setdefault(("양봉2회방어","전체"),[]).append(o)
        for vx in (2.0,3.0):
            rc=recl(d,i,vx=vx)
            if rc and t-lr>=8*M.BAR:
                if vx==2.0: lr=t
                if t>=time.time()-30*3600 and vx==3.0:
                    recent.append((name,kst(t).strftime("%m/%d %H:%M 시작"),d["c"][i],round(rc["lvl"],10),round(rc["cvx"],1),round(rc["ivx"],1)))
                if i<n-16:
                    o=outcome(d,i,rc["low"]*0.999)
                    if o is not None:
                        res.setdefault((f"투매후 시가회복(투매 {vx:.0f}배)","전체"),[]).append(o)
                        res.setdefault((f"투매후 시가회복(투매 {vx:.0f}배)","회복봉 "+bucket(rc["ivx"])),[]).append(o)
print("\n성과 (손절=저점 아래, 목표 2R, 4시간)")
for k,vals in sorted(res.items()):
    w=sum(1 for x in vals if x==2.0); lo=sum(1 for x in vals if x==-1.0)
    print(f" {k[0]} | {k[1]} | n={len(vals)} | 하루={len(vals)/30:.1f} | 2R승={w} | 손절={lo} | 기대값R={sum(vals)/len(vals):+.3f}")
print("\n최근30h 투매후 시가회복(3배) (종목,봉,종가,회복기준,투매배수,회복봉배수)")
for r in recent: print(" ",r)
