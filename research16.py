from datetime import datetime
import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=16
def run(d,i,side,mode,W,rng):
    """mode: now=알람봉 종가 즉시, touch=범위 돌파 터치, close=범위 밖 종가 확정 / 반환: (진입방향, 수익%) 또는 None"""
    c,hh,ll=d["c"],d["h"],d["l"]; end=i+H
    Hi=max(hh[i-rng+1:i+1]); Lo=min(ll[i-rng+1:i+1])
    if mode=="now":
        e=c[i]; stop=Lo if side==1 else Hi; k0=i; dirn=side
    else:
        k0=None
        for k in range(i+1,i+1+W):
            up = (hh[k]>Hi*1.001) if mode=="touch" else (c[k]>Hi)
            dn = (ll[k]<Lo*0.999) if mode=="touch" else (c[k]<Lo)
            if up and dn: return None
            if up: dirn=1; e=Hi*1.001 if mode=="touch" else c[k]; k0=k; break
            if dn: dirn=-1; e=Lo*0.999 if mode=="touch" else c[k]; k0=k; break
        if k0 is None: return None
        stop=Lo if dirn==1 else Hi
    for k in range(k0+1,end+1):
        if dirn==1 and ll[k]<=stop: return dirn,(stop/e-1)*100
        if dirn==-1 and hh[k]>=stop: return dirn,(e/stop-1)*100
    return dirn,((c[end]/e-1) if dirn==1 else (e/c[end]-1))*100

if __name__=="__main__":
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
        for i in range(80,n-H-1):
            t=d["t"][i]; bi=bidx.get(t)
            if bi is None or bi<16: continue
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
                last[nm]=t; ev.append((nm,side,name,i,t))
    t0=min(e[4] for e in ev); t1=max(e[4] for e in ev); w=(t1-t0)/5
    setups=[("바로 진입(알람 방향, 손절=알람봉 반대끝)","now",0,1,False),
            ("1시간 안 알람봉 고저 돌파 터치→그 방향","touch",4,1,True),
            ("1시간 안 알람봉 고저 밖 종가 확정→그 방향","close",4,1,True),
            ("1시간 안 최근3봉 고저 밖 종가 확정→그 방향","close",4,3,True),
            ("30분 안 최근3봉 고저 밖 종가 확정→그 방향","close",2,3,True),
            ("1시간 안 최근3봉 종가 확정, 알람 방향일 때만","close",4,3,False)]
    print(f"바이낸스 선물 15분봉 {DAYS}일, 12종목, 알람 후 4시간 보유(손절 시 조기 종료), 수수료 미반영, 단위 %")
    for nm0 in ("[단독]","[속보]","short","전체"):
        g=[e for e in ev if nm0=="전체" or e[0]==nm0]
        print(f"\n== {nm0} 알람 {len(g)}건")
        for label,mode,W,rng,both in setups:
            rs=[]; same=0; blocks=[[] for _ in range(5)]
            for nm,side,name,i,t in g:
                r=run(data[name][0],i,side,mode,W,rng)
                if r is None: continue
                dirn,ret=r
                if not both and dirn!=side: continue
                same+=dirn==side; rs.append(ret); blocks[min(4,int((t-t0)/w))].append(ret)
            if not rs: print(f" {label} | 진입 0"); continue
            wins=[x for x in rs if x>0]; loss=[x for x in rs if x<=0]
            bl=" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in blocks)
            print(f" {label} | 진입 {len(rs)}({len(rs)/len(g)*100:.0f}%) 알람방향 {same/len(rs)*100:.0f}% | 평균 {st.mean(rs):+.3f} 중앙 {st.median(rs):+.3f} | 승률 {len(wins)/len(rs)*100:.0f}% 평균익 {st.mean(wins) if wins else 0:+.2f} 평균손 {st.mean(loss) if loss else 0:+.2f} | 5구간 {bl}")
    