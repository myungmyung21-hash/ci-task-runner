import time
from datetime import datetime
import monitor as M
from research import fetch_all, outcome
data = fetch_all(30)
for n,(rows,d) in data.items(): d["t"]=[r[0] for r in rows]
btc = data["BTC"][1]; bidx = {t:i for i,t in enumerate(btc["t"])}
res = {}; recent = []; perbar = {}
for name,(rows,d) in data.items():
    n = len(rows); last = 0
    for i in range(60, n):
        hd = M.hold2(d, i)
        if not hd or rows[i][0] - last < 8*M.BAR: continue
        last = rows[i][0]; t = rows[i][0]; perbar[t] = perbar.get(t,0)+1
        bi = bidx.get(t); rs = (d["c"][i]/d["c"][i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1) if bi and bi>=16 else None
        if t >= time.time()-16*3600:
            recent.append((name, datetime.fromtimestamp(t+M.BAR,M.KST).strftime("%m/%d %H:%M"), d["c"][i], hd["sup"], None if rs is None else round(rs*100,2)))
        if i < n-16:
            o = outcome(d, i, hd["sup"]*0.999)
            if o is not None:
                res.setdefault("양봉 2회 방어", []).append(o)
                if rs is not None and rs >= 0.005: res.setdefault("양봉 2회 방어 +RS0.5%", []).append(o)
for k,v in res.items():
    w=sum(1 for x in v if x==2.0); lo=sum(1 for x in v if x==-1.0)
    print(f"{k} | n={len(v)} | 하루={len(v)/30:.1f} | 2R승={w} | 손절={lo} | 기대값R={sum(v)/len(v):+.3f}")
print("같은 봉 동시발생 4종목 이상 비율", round(sum(1 for x in perbar.values() if x>=4)/max(1,len(perbar))*100,1), "%")
print("RECENT16H (종목,KST마감,종가,지지선,RS%)")
for r in sorted(recent,key=lambda x:x[1]): print(" ",r)
