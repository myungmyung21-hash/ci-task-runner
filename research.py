import time, json
from datetime import datetime
import monitor as M

def fetch_all(days=30):
    m, _ = M.resolve()
    end = int(time.time()) // M.BAR * M.BAR; start = end - days*86400 - 80*M.BAR
    data = {}
    for name,(k,s) in m.items():
        rows=[]
        for a in range(start,end,900*M.BAR):
            rows += M.candles(k,s,a,min(a+900*M.BAR,end)); time.sleep(0.12)
        rows = sorted({r[0]:r for r in rows}.values())
        data[name]=(rows, M.indicators(rows))
    return data

def flags(name,d,i,btc_idx,btc):
    sig = M.detect(d,i)
    if not sig: return None
    st,info = sig
    c=d["c"]
    gc = any(d["dif"][j-1]<=d["dea"][j-1] and d["dif"][j]>d["dea"][j] for j in range(i-6,i+1))
    rs = None
    t = d["t"][i]
    if t in btc_idx and i>=16:
        bi=btc_idx[t]
        if bi>=16:
            rs = (c[i]/c[i-16]-1) - (btc["c"][bi]/btc["c"][bi-16]-1)
    return st, gc, rs

def outcome(d,i,stop,hor=16):
    e=d["c"][i]; R=e-stop
    if R<=0 or R/e>0.05: return None
    for k in range(i+1,min(i+1+hor,len(d["c"]))):
        if d["l"][k]<=stop: return -1.0
        if d["h"][k]>=e+2*R: return 2.0
    k=min(i+hor,len(d["c"])-1)
    return max(-1.0,min(2.0,(d["c"][k]-e)/R))

def main():
    data=fetch_all(30)
    for n,(rows,d) in data.items(): d["t"]=[r[0] for r in rows]
    btc=data["BTC"][1]; btc_idx={t:i for i,t in enumerate(btc["t"])}
    res={}; daycount={}; recent=[]
    def add(key,v,t):
        if v is None: return
        res.setdefault(key,[]).append(v); daycount.setdefault(key,set()).add(t//86400)
    for name,(rows,d) in data.items():
        last={}
        n=len(rows)
        for i in range(60,n):
            # baseline: SAR 상승 + MB 위 아무 봉
            if d["up"][i] and d["mb"][i] and d["c"][i]>d["mb"][i] and i<n-16 and i%4==0:
                add("BASE(SAR상승+MB위 임의봉)", outcome(d,i,d["sar"][i]*0.999), rows[i][0])
            f=flags(name,d,i,btc_idx,btc)
            if not f: continue
            st,gc,rs=f
            if rows[i][0]-last.get(st,0)<8*M.BAR: continue
            last[st]=rows[i][0]
            prior1 = st==2 and last.get(1,0)>=rows[i][0]-12*M.BAR
            if rows[i][0]>=time.time()-14*3600:
                recent.append((name,st,datetime.fromtimestamp(rows[i][0]+M.BAR,M.KST).strftime("%m/%d %H:%M"),d["c"][i],gc,None if rs is None else round(rs*100,2),prior1))
            if i>=n-16: continue
            stop=d["sar"][i]*0.999
            o=outcome(d,i,stop); t=rows[i][0]
            add(f"S{st} 기본",o,t)
            if gc: add(f"S{st} +골든크로스6봉",o,t)
            if rs is not None and rs>=0.01: add(f"S{st} +BTC대비 4h +1%",o,t)
            if rs is not None and rs>=0.02: add(f"S{st} +BTC대비 4h +2%",o,t)
            if gc and rs is not None and rs>=0.01: add(f"S{st} +골든+RS1%",o,t)
            if st==2 and prior1: add("S2 +직전3h내 1단계",o,t)
            if st==2 and prior1 and rs is not None and rs>=0.01: add("S2 +1단계선행+RS1%",o,t)
    out=[]
    for k,v in res.items():
        w=sum(1 for x in v if x==2.0); l=sum(1 for x in v if x==-1.0)
        out.append(f"{k} | n={len(v)} | 하루평균={len(v)/30:.1f} | 2R승={w} | 손절={l} | 기대값R={sum(v)/len(v):+.3f}")
    print("\n".join(sorted(out)))
    print("RECENT14H (name,stage,KST마감,종가,골든6봉,RS%,1단계선행)")
    for r in sorted(recent,key=lambda x:x[2]): print(" ",r)

if __name__=="__main__": main()
