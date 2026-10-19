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


def recl(d,i,vx=3.0,mode="open",win=16):
    o,h,l,c,v=d["o"],d["h"],d["l"],d["c"],d["v"]
    if i<win+25 or not c[i]>o[i]: return None
    for k in range(i-2,i-win-1,-1):
        if not (c[k]<o[k] and ratio(v,k)>=vx and l[k]<=d["lb"][k]): continue
        ks=[j for j in (k-1,k,k+1) if c[j]<o[j] and ratio(v,j)>=vx*0.66]
        top=max(o[j] for j in ks); bot=min(c[j] for j in ks)
        lvl=top if mode=="open" else (top+bot)/2
        a=M.atr(d,i); base=min(l[k-1:min(k+2,i)+1])
        if min(l[k:i+1])<base-0.5*a: return None
        if c[i]>lvl and c[i-1]<=lvl:
            return dict(lvl=lvl,low=min(l[k-1:i+1]),cvx=ratio(v,k),ivx=ratio(v,i))
        return None
    return None
B=[(0,0.8),(0.8,1.5),(1.5,3),(3,99)]
def bucket(x):
    for b in B:
        if b[0]<=x<b[1]: return f"{b[0]*100:.0f}~{(str(int(b[1]*100))+'%') if b[1]<99 else '이상'}"
res={}; recent=[]
for name,(rows,d) in data.items():
    if name=="BTC": continue
    n=len(rows); last={}
    for i in range(60,n):
        t=rows[i][0]
        for vx in (2.0,3.0,4.0):
            for mode in ("open","half"):
                key=(vx,mode); rc=recl(d,i,vx,mode)
                if not rc or t-last.get(key,0)<8*M.BAR: continue
                last[key]=t
                nm=f"투매{vx:.0f}배·{'시가' if mode=='open' else '몸통50%'}회복"
                if t>=time.time()-30*3600: recent.append((nm,name,kst(t).strftime("%m/%d %H:%M시작"),d["c"][i],rc["lvl"],round(rc["cvx"],1),round(rc["ivx"],1)))
                if i<n-16:
                    o=outcome(d,i,rc["low"]*0.999)
                    if o is not None:
                        res.setdefault((nm,"전체"),[]).append(o)
                        res.setdefault((nm,"회복봉 "+bucket(rc["ivx"])),[]).append(o)
print("성과 (손절=투매 저점 아래, 목표 2R, 4시간)")
for k,vals in sorted(res.items()):
    w=sum(1 for x in vals if x==2.0); lo=sum(1 for x in vals if x==-1.0)
    print(f" {k[0]} | {k[1]} | n={len(vals)} | 하루={len(vals)/30:.1f} | 2R승={w} | 손절={lo} | 기대값R={sum(vals)/len(vals):+.3f}")
print("최근30h")
for r in sorted(recent,key=lambda x:(x[1],x[2])): print(" ",r)
