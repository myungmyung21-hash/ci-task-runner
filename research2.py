import time
from datetime import datetime
import monitor as M
from research import fetch_all, outcome

def sweep(d, i, win=16, lb=6):
    """최근 win봉 안에 '직전 lb봉 저점 이탈' 2회 이상 → 이번 봉이 회복 돌파"""
    o,h,l,c = d["o"],d["h"],d["l"],d["c"]; mb = d["mb"][i]
    if mb is None or i < win + lb + 5: return None
    ks = [k for k in range(i-win, i) if l[k] < min(l[k-lb:k])]
    ev = []
    for k in ks:
        if not ev or k - ev[-1] >= 2: ev.append(k)
    if len(ev) < 2: return None
    k2 = ev[-1]
    if i - k2 > 8: return None
    lvl = max(h[k2:i])               # 2번째 이탈 이후 고점
    low = min(l[ev[0]:i+1])
    if not (c[i] > o[i] and c[i] > lvl and c[i-1] <= lvl and c[i] > mb): return None
    macd = d["dif"][i] > d["dea"][i] or d["hist"][i] > d["hist"][i-1]
    return dict(low=low, macd=macd, n=len(ev))

def main():
    data = fetch_all(30)
    for n,(rows,d) in data.items(): d["t"]=[r[0] for r in rows]
    btc = data["BTC"][1]; bidx = {t:i for i,t in enumerate(btc["t"])}
    res = {}; recent = []
    def add(k,v):
        if v is not None: res.setdefault(k,[]).append(v)
    for name,(rows,d) in data.items():
        if name == "BTC": continue
        n = len(rows); last = {}
        for i in range(60, n):
            t = rows[i][0]; bi = bidx.get(t); rs = None
            if bi and bi >= 16: rs = (d["c"][i]/d["c"][i-16]-1) - (btc["c"][bi]/btc["c"][bi-16]-1)
            s = sweep(d, i)
            if s and t - last.get("sw",0) >= 8*M.BAR:
                last["sw"] = t
                if t >= time.time()-16*3600:
                    recent.append((name,"스윕",datetime.fromtimestamp(t+M.BAR,M.KST).strftime("%m/%d %H:%M"),d["c"][i],s["n"],s["macd"],None if rs is None else round(rs*100,2)))
                if i < n-16:
                    o1 = outcome(d,i,s["low"]*0.999); o2 = outcome(d,i,d["sar"][i]*0.999) if d["up"][i] else None
                    add("스윕2회 기본 (손절=스윕저점)", o1)
                    if s["macd"]: add("스윕2회 +MACD (손절=스윕저점)", o1)
                    if s["macd"] and rs is not None and rs >= 0.005: add("스윕2회 +MACD+RS0.5%", o1)
                    if s["macd"] and rs is not None and rs >= 0.01: add("스윕2회 +MACD+RS1%", o1)
                    if d["up"][i]: add("스윕2회 +SAR상승 (손절=SAR)", o2)
            g = M.detect(d, i)
            if g and g[0] == 2 and t - last.get("s2",0) >= 8*M.BAR and i < n-16:
                last["s2"] = t; o = outcome(d,i,d["sar"][i]*0.999)
                add("2단계 단독", o)
                if rs is not None and rs >= 0.01: add("2단계 단독 +RS1%", o)
            if i % 4 == 0 and i < n-16 and d["mb"][i] and d["c"][i] > d["mb"][i]:
                add("비교기준: MB위 임의봉 (손절=직전16봉저점)", outcome(d,i,min(d["l"][i-16:i])*0.999))
    for k,v in sorted(res.items()):
        w=sum(1 for x in v if x==2.0); lo=sum(1 for x in v if x==-1.0)
        print(f"{k} | n={len(v)} | 하루={len(v)/30:.1f} | 2R승={w} | 손절={lo} | 기대값R={sum(v)/len(v):+.3f}")
    print("RECENT16H (종목,유형,KST마감,종가,이탈횟수,MACD,RS%)")
    for r in sorted(recent,key=lambda x:x[2]): print(" ",r)

if __name__ == "__main__": main()
