import sys, time
from datetime import datetime
import monitor as M
sym = sys.argv[1] if len(sys.argv) > 1 else "PEPE"; hours = int(sys.argv[2]) if len(sys.argv) > 2 else 16
m, _ = M.resolve()
def load(n):
    k, s = m[n]; r = M.candles(k, s, limit=300); return r, M.indicators(r)
br, bd = load("BTC"); bidx = {r[0]: i for i, r in enumerate(br)}
rows, d = load(sym); o,h,l,c,v = d["o"],d["h"],d["l"],d["c"],d["v"]
print("contract", m[sym])
print("KST마감 | O H L C | MB UB | SAR(상승?) | DIF>DEA hist | 거래량/MA10 | RS4h | 판정 | 1단계 탈락사유")
for i in range(len(rows)):
    if rows[i][0] < time.time() - hours * 3600 or i < 40: continue
    t = datetime.fromtimestamp(rows[i][0] + M.BAR, M.KST).strftime("%m/%d %H:%M")
    bi = bidx.get(rows[i][0]); rs = None
    if bi and bi >= 16 and i >= 16: rs = (c[i]/c[i-16]-1) - (bd["c"][bi]/bd["c"][bi-16]-1)
    sig = M.detect(d, i)
    why = []
    mb, ub, up = d["mb"][i], d["ub"][i], d["up"]
    if not all(up[i-2:i+1]): why.append("SAR상승3봉X")
    if not c[i] >= mb*0.997: why.append("종가<MB")
    if not min(l[i-3:i+1]) <= mb*1.005: why.append("MB터치X")
    if not c[i] < ub: why.append("UB이미위")
    if not (d["dif"][i] > d["dea"][i] or d["hist"][i] > d["hist"][i-1] > d["hist"][i-2]): why.append("MACD X")
    big = False
    for j in range(i-8, i):
        body = o[j]-c[j]; avg = sum(abs(o[k]-c[k]) for k in range(j-10, j))/10
        if body > 0 and avg > 0 and body >= 2*avg and all(up[j:i+1]): big = True
    if not big: why.append("장대음봉+SAR유지X")
    print(f"{t} | {o[i]:.8g} {h[i]:.8g} {l[i]:.8g} {c[i]:.8g} | {mb:.8g} {ub:.8g} | {d['sar'][i]:.8g}({'U' if up[i] else 'D'}) | {'Y' if d['dif'][i]>d['dea'][i] else 'N'} {d['hist'][i]:+.3g} | {v[i]/d['vma'][i]:.1f} | {'' if rs is None else f'{rs*100:+.2f}'} | {sig[0] if sig else '-'} | {','.join(why)}")
