import time, statistics as st
from datetime import datetime
import monitor as M
from research6 import fetch, rsi
H = 16
def short_outcome(d, i, stop):
    e = d["c"][i]; R = stop - e
    if R <= 0 or R / e > 0.06 or i + H >= len(d["c"]): return None
    for k in range(i + 1, i + 1 + H):
        if d["h"][k] >= stop: return -1.0
        if d["l"][k] <= e - 2 * R: return 2.0
    return max(-1.0, min(2.0, (e - d["c"][i + H]) / R))

m, _ = M.resolve(); data = {}
for name, (k, s) in m.items():
    if name in ("KAIA", "MBABYDOGE", "BRETT"): continue
    r15 = fetch(k, s, "15m", 30); r1h = fetch(k, s, "1h", 40)
    d = M.indicators(r15); d["t"] = [r[0] for r in r15]; d["rsi"] = rsi(d["c"])
    h1 = M.indicators(r1h); h1["t"] = [r[0] for r in r1h]; h1["rsi"] = rsi(h1["c"])
    data[name] = (d, h1)
btc = data["BTC"][0]; bidx = {t: i for i, t in enumerate(btc["t"])}

def ctx1h(h1, t):
    # t(15분봉 시작)의 마감 시점에 이미 마감된 마지막 1시간봉
    lo, hi = 0, len(h1["t"]) - 1; j = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if h1["t"][mid] + 3600 <= t + 900: j = mid; lo = mid + 1
        else: hi = mid - 1
    return j

rules = {}; drops = []; allfeat = []
def add(rule, filt, t, o):
    if o is not None: rules.setdefault((rule, filt), []).append((t, o))

for name, (d, h1) in data.items():
    if name == "BTC": continue
    o_, h_, l_, c_ = d["o"], d["h"], d["l"], d["c"]; n = len(c_); last = {}
    for i in range(80, n - H):
        t = d["t"][i]; j = ctx1h(h1, t)
        if j < 30 or h1["mb"][j] is None or d["mb"][i] is None: continue
        bi = bidx.get(t)
        if bi is None or bi < 16: continue
        a = M.atr(d, i); vr = M.vratio(d, i)
        rs = (c_[i] / c_[i - 16] - 1) - (btc["c"][bi] / btc["c"][bi - 16] - 1)
        down1h = (not h1["up"][j]) and h1["c"][j] < h1["mb"][j]
        f = dict(sar15_dn=not d["up"][i], below_mb15=c_[i] < d["mb"][i], macd15_neg=d["dif"][i] < d["dea"][i],
                 sar1h_dn=not h1["up"][j], below_mb1h=h1["c"][j] < h1["mb"][j], macd1h_neg=h1["dif"][j] < h1["dea"][j],
                 rsi15_hi=d["rsi"][i] >= 65, rsi1h_hi=h1["rsi"][j] >= 65, rsi15_lo=d["rsi"][i] <= 35,
                 pump4h=c_[i] / c_[i - 16] - 1 >= 0.03, near_ub15=c_[i] >= d["ub"][i] * 0.995, red_vol2=c_[i] < o_[i] and vr >= 2,
                 weak_rs=rs <= -0.01, btc_dn4h=btc["c"][bi] / btc["c"][bi - 16] - 1 <= -0.01,
                 upwick=(h_[i] - max(o_[i], c_[i])) >= 0.6 * (h_[i] - l_[i]) if h_[i] > l_[i] else False)
        fwd = c_[i + H] / c_[i] - 1; maxup = max(h_[i + 1:i + 1 + H]) / c_[i] - 1
        allfeat.append((f, fwd))
        if fwd <= -0.03 and maxup <= 0.01 and t - last.get("drop", 0) >= H * 900:
            last["drop"] = t; drops.append((name, t, fwd, maxup, f, d["rsi"][i], h1["rsi"][j], vr))
        # 비교기준: 4봉마다 숏
        if i % 4 == 0: add("비교기준(임의 숏)", "전체", t, short_outcome(d, i, max(h_[i - 3:i + 1]) * 1.001))
        cands = []
        # R1 펌핑 후 시가 이탈
        if c_[i] < o_[i]:
            for k in range(i - 1, i - 17, -1):
                if c_[k] > o_[k] and M.vratio(d, k) >= 3 and h_[k] >= d["ub"][k]:
                    if c_[i] < o_[k] <= c_[i - 1]: cands.append(("R1 급등봉 시가 이탈", max(h_[k:i + 1]) * 1.001))
                    break
        # R2 음봉 2회 고점 저항
        if c_[i] < o_[i] and vr >= 1.5:
            for k in range(i - 3, i - 17, -1):
                if not c_[k] < o_[k]: continue
                top = max(h_[k], h_[i])
                if abs(h_[i] - h_[k]) > 0.5 * a: continue
                if max(h_[k:i + 1]) > top + 0.1 * a or max(c_[k:i + 1]) > top: continue
                if min(l_[k + 1:i]) > top - 1.0 * a: continue
                if max(h_[k - 6:k]) > top + 0.1 * a: continue
                cands.append(("R2 음봉 2회 고점 저항", top * 1.001)); break
        # R3 하락 돌파
        if (c_[i] < o_[i] and c_[i] < min(l_[i - 12:i]) and d["vma"][i] and d["v"][i] >= 2 * d["vma"][i]
                and c_[i] <= d["lb"][i] * 1.005 and not d["up"][i] and d["dif"][i] < d["dea"][i]):
            cands.append(("R3 거래량 동반 하락 돌파", d["sar"][i]))
        # R4 SAR 하락 전환 + 약세
        if d["up"][i - 1] and not d["up"][i] and rs <= -0.005 and c_[i] < d["mb"][i]:
            cands.append(("R4 SAR 전환+BTC대비 약세", d["sar"][i]))
        # R5 과열 후 첫 장대음봉
        body = o_[i] - c_[i]; avgb = sum(abs(o_[q] - c_[q]) for q in range(i - 10, i)) / 10
        if body > 0 and avgb > 0 and body >= 2 * avgb and vr >= 2 and max(d["rsi"][i - 8:i]) >= 70:
            cands.append(("R5 과열 후 첫 장대음봉", max(h_[i - 8:i + 1]) * 1.001))
        for nm, stop in cands:
            if t - last.get(nm, 0) < 8 * 900: continue
            last[nm] = t; o = short_outcome(d, i, stop)
            add(nm, "전체", t, o)
            if down1h: add(nm, "1시간 하락추세", t, o)
            if not down1h: add(nm, "1시간 비하락", t, o)

allt = sorted(t for v in rules.values() for t, _ in v); cut = allt[int(len(allt) * 0.7)]
fmt = lambda z: f"n={len(z)} R={sum(z)/len(z):+.3f}" if z else "n=0"
print("== 숏 규칙 성과 (30일, 16종목, 손절=규칙별 고점, 목표 2R, 4시간) 분할기준", datetime.fromtimestamp(cut, M.KST).strftime("%m/%d %H:%M"))
for (nm, flt), v in sorted(rules.items()):
    a = [o for t, o in v if t < cut]; b = [o for t, o in v if t >= cut]
    print(f" {nm} | {flt} | 하루 {len(v)/30:.1f} | 앞70% {fmt(a)} | 뒤30% {fmt(b)}")

print(f"\n== 4시간 내 -3% 이상 하락(반등 +1% 이내) 사례 {len(drops)}건")
keys = list(allfeat[0][0].keys()); base = {k: sum(f[k] for f, _ in allfeat) / len(allfeat) for k in keys}
dropf = {k: sum(x[4][k] for x in drops) / len(drops) for k in keys} if drops else {}
print("지표 | 하락사례 비율 | 전체 비율 | 배수")
for k in sorted(keys, key=lambda k: -(dropf.get(k, 0) / base[k] if base[k] else 0)):
    print(f" {k} | {dropf.get(k,0)*100:.0f}% | {base[k]*100:.0f}% | {dropf.get(k,0)/base[k] if base[k] else 0:.2f}")
print("\n대표 사례 (하락폭 큰 순 12건)")
for name, t, fwd, mu, f, r15, r1, vr in sorted(drops, key=lambda x: x[2])[:12]:
    on = [k for k, v in f.items() if v]
    print(f" {name} {datetime.fromtimestamp(t, M.KST):%m/%d %H:%M} | 4h {fwd*100:+.1f}% 최대반등 {mu*100:+.1f}% | RSI15 {r15:.0f} RSI1h {r1:.0f} 거래 {vr*100:.0f}% | {','.join(on)}")
