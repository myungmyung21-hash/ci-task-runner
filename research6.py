import time, math
from datetime import datetime
import monitor as M

def fetch(kind, sym, tf, days):
    step = {"15m": 900, "1h": 3600}[tf]
    end = int(time.time()) // step * step; start = end - days * 86400 - 80 * step
    rows = []
    for a in range(start, end, 900 * step):
        b = min(a + 900 * step, end)
        if kind == "fut":
            d = M.get("/futures/usdt/candlesticks", contract=sym, interval=tf, **{"from": a, "to": b}) or []
            rows += [(int(x["t"]), float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"]), float(x.get("sum") or x.get("v") or 0)) for x in d]
        else:
            d = M.get("/spot/candlesticks", currency_pair=sym, interval=tf, **{"from": a, "to": b}) or []
            rows += [(int(x[0]), float(x[5]), float(x[3]), float(x[4]), float(x[2]), float(x[1])) for x in d]
        time.sleep(0.12)
    rows = sorted({r[0]: r for r in rows}.values())
    return [r for r in rows if r[0] + step <= time.time()]

def rsi(c, n=14):
    out = [50.0] * len(c); g = l = 0.0
    for i in range(1, len(c)):
        ch = c[i] - c[i-1]; up, dn = max(ch, 0), max(-ch, 0)
        if i <= n: g += up / n; l += dn / n
        else: g = (g * (n-1) + up) / n; l = (l * (n-1) + dn) / n
        out[i] = 100 - 100 / (1 + g / l) if l > 0 else 100
    return out

FEATS = ["vr_low","vr_bounce","vr_last3","cap_vx","cap_ago","exhaust","tests","lower_low","hist_div",
         "rsi","lb_dist","mb_dist","bw","drop","sar_up","rs","macd_gc"]

def events(name, rows, d, btc, bidx, H=16):
    o,h,l,c = d["o"],d["h"],d["l"],d["c"]; n=len(rows); r_ = rsi(c); out=[]; last=-99
    for i in range(60, n):
        j = i if l[i] <= l[i-1] else i-1
        if l[j] != min(l[j-11:j+1]): continue
        if not (c[i] > o[i] and c[i] > (h[j]+l[j])/2): continue
        if i - last < 4: continue
        a = M.atr(d, i); low = l[j]
        if a <= 0 or d["mb"][i] is None: continue
        stop = low * 0.999; R = c[i] - stop
        if R <= 0 or R / c[i] > 0.05: continue
        last = i
        reds = [(M.vratio(d,k), k) for k in range(i-24, i+1) if c[k] < o[k]]
        cap_vx, cap_k = max(reds) if reds else (0, i)
        pl = [k for k in range(i-24, i-4) if l[k] == min(l[k-5:k+6])]
        tests = sum(1 for k in pl if abs(l[k]-low) <= 0.5*a)
        lower_low = 1 if pl and low < min(l[k] for k in pl) - 0.3*a else 0
        prior_min_hist = min(d["hist"][i-24:i-3])
        hist_div = 1 if (low < min(l[i-24:i-3]) and d["hist"][i] > prior_min_hist) else 0
        gc = 1 if any(d["dif"][k-1] <= d["dea"][k-1] and d["dif"][k] > d["dea"][k] for k in range(i-3, i+1)) else 0
        bi = bidx.get(rows[i][0]); rs = 0.0
        if bi and bi >= 16: rs = (c[i]/c[i-16]-1) - (btc["c"][bi]/btc["c"][bi-16]-1)
        f = dict(vr_low=M.vratio(d,j), vr_bounce=M.vratio(d,i), vr_last3=sum(M.vratio(d,k) for k in range(i-2,i+1))/3,
                 cap_vx=cap_vx, cap_ago=i-cap_k, exhaust=M.vratio(d,j)/cap_vx if cap_vx else 1, tests=tests,
                 lower_low=lower_low, hist_div=hist_div, rsi=r_[i], lb_dist=(low-d["lb"][i])/a, mb_dist=(c[i]-d["mb"][i])/a,
                 bw=(d["ub"][i]-d["lb"][i])/d["mb"][i]*100, drop=(max(h[i-24:i])-low)/a, sar_up=1 if d["up"][i] else 0, rs=rs*100, macd_gc=gc)
        y = None; res = None
        if i + H < n:
            res = 0.0
            for k in range(i+1, i+1+H):
                if l[k] <= stop: res = -1.0; break
                if h[k] >= c[i] + 2*R: res = 2.0; break
            else: res = max(-1, min(2, (c[i+H]-c[i])/R))
            y = 1 if res == 2.0 else 0
        out.append(dict(name=name, t=rows[i][0], i=i, f=f, y=y, res=res, price=c[i], low=low))
    return out

def run(tf, days):
    m, _ = M.resolve(); data = {}
    for name,(k,s) in m.items():
        rows = fetch(k, s, tf, days); data[name] = (rows, M.indicators(rows))
    btc = data["BTC"][1]; bidx = {r[0]: i for i, r in enumerate(data["BTC"][0])}
    ev = []
    for name,(rows,d) in data.items():
        if name != "BTC" and len(rows) > 100: ev += events(name, rows, d, btc, bidx)
    lab = sorted([e for e in ev if e["y"] is not None], key=lambda e: e["t"])
    return data, ev, lab

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import roc_auc_score

def analyze(tf, days):
    data, ev, lab = run(tf, days)
    X = np.array([[e["f"][k] for k in FEATS] for e in lab]); y = np.array([e["y"] for e in lab]); R = np.array([e["res"] for e in lab])
    cut = int(len(lab) * 0.7)
    print(f"\n===== {tf} {days}일 | 바닥반등 후보 {len(lab)}건 (학습 {cut} / 검증 {len(lab)-cut}) | 전체 기대값R={R.mean():+.3f} 2R승률={y.mean()*100:.1f}%")
    gb = GradientBoostingClassifier(max_depth=2, n_estimators=150, learning_rate=0.05, subsample=0.8, random_state=0).fit(X[:cut], y[:cut])
    p = gb.predict_proba(X[cut:])[:,1]
    print(f"검증 AUC={roc_auc_score(y[cut:], p):.3f}")
    q = np.quantile(p, [0.5, 0.8, 0.9])
    for nm, th in (("상위50%",q[0]),("상위20%",q[1]),("상위10%",q[2])):
        sel = p >= th
        print(f" 검증 {nm} | n={sel.sum()} | 2R승률={y[cut:][sel].mean()*100:.1f}% | 기대값R={R[cut:][sel].mean():+.3f}")
    print(f" 검증 전체 | n={len(p)} | 2R승률={y[cut:].mean()*100:.1f}% | 기대값R={R[cut:].mean():+.3f}")
    imp = sorted(zip(FEATS, gb.feature_importances_), key=lambda x: -x[1])[:8]
    print("중요 변수:", ", ".join(f"{k} {v:.2f}" for k, v in imp))
    tr = DecisionTreeClassifier(max_depth=3, min_samples_leaf=max(30, cut//40), random_state=0).fit(X[:cut], y[:cut])
    print("규칙 트리(학습구간):"); print(export_text(tr, feature_names=FEATS, decimals=2))
    leaf_tr = tr.apply(X[:cut]); leaf_te = tr.apply(X[cut:])
    print("잎별 성과 (학습 → 검증):")
    for lf in sorted(set(leaf_tr)):
        a = leaf_tr == lf; b = leaf_te == lf
        if b.sum() == 0: continue
        print(f" leaf{lf} | 학습 n={a.sum()} R={R[:cut][a].mean():+.3f} | 검증 n={b.sum()} R={R[cut:][b].mean():+.3f}")
    gb_all = GradientBoostingClassifier(max_depth=2, n_estimators=150, learning_rate=0.05, subsample=0.8, random_state=0).fit(X, y)
    print("KAIA 10/18 08시~ 바닥반등 후보 (KST 봉시작 | 종가 | 저점 | 모델확률 | 결과R | 주요값)")
    for e in ev:
        if e["name"] == "KAIA" and e["t"] >= 1792278000:
            pr = gb_all.predict_proba(np.array([[e["f"][k] for k in FEATS]]))[0,1]
            f = e["f"]
            print(f"  {datetime.fromtimestamp(e['t'], M.KST):%m/%d %H:%M} | {e['price']:.5f} | {e['low']:.5f} | {pr*100:.0f}% | {e['res']} | "
                  f"저점봉부하 {f['vr_low']*100:.0f}% 반등봉 {f['vr_bounce']*100:.0f}% 투매 {f['cap_vx']*100:.0f}%({f['cap_ago']}봉전) 소진 {f['exhaust']:.2f} "
                  f"테스트 {f['tests']} 신저점 {f['lower_low']} MACD다이버 {f['hist_div']} RSI {f['rsi']:.0f}")
    return gb_all

if __name__ == "__main__":
    analyze("1h", 90)
    analyze("15m", 30)
