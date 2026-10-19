import os, sys, json, time, math
from datetime import datetime, timezone, timedelta
import requests

API = "https://api.gateio.ws/api/v4"
KST = timezone(timedelta(hours=9))
TOPIC = os.environ.get("NTFY_TOPIC", "")
WATCH = ["HBAR", "SUI", "ETH", "PEPE", "BTC", "WLD", "SOL", "TSLA", "ADA", "XRP",
         "GOOGL", "DOGE", "SHIB", "ONDO", "SPCX", "TRUMP"]  # KAIA·MBABYDOGE·BRETT 제외(무변동봉 과다)
BAR = 900
CODE = {"HBAR": "한겨레", "SUI": "서울경제", "ETH": "이데일리", "PEPE": "파이낸셜뉴스", "BTC": "매일경제",
        "WLD": "Washington Post", "SOL": "세계일보", "TSLA": "The Times", "ADA": "아시아경제", "XRP": "Reuters",
        "GOOGL": "The Guardian", "DOGE": "동아일보", "SHIB": "중앙일보", "ONDO": "오마이뉴스", "SPCX": "조선일보",
        "TRUMP": "The Telegraph"}
S = requests.Session()
S.headers["Accept"] = "application/json"


def get(path, **params):
    for i in range(3):
        try:
            r = S.get(API + path, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + i * 2)
                continue
            return None
        except Exception:
            time.sleep(1 + i)
    return None


def resolve():
    """즐겨찾기 이름 -> Gate 계약명. 선물 우선, 없으면 현물."""
    fut = get("/futures/usdt/contracts") or []
    names = {c["name"] for c in fut if not c.get("in_delisting")}
    spot = get("/spot/currency_pairs") or []
    pairs = {p["id"] for p in spot if p.get("trade_status") == "tradable"}
    out, miss = {}, []
    for w in WATCH:
        cands = [f"{w}_USDT", f"{w}X_USDT", f"1000{w}_USDT"]
        hit = next((c for c in cands if c in names), None)
        if hit:
            out[w] = ("fut", hit); continue
        hit = next((c for c in cands if c in pairs), None)
        if hit:
            out[w] = ("spot", hit); continue
        miss.append(w)
    return out, miss


def candles(kind, sym, frm=None, to=None, limit=200):
    if kind == "fut":
        p = {"contract": sym, "interval": "15m"}
        if frm: p.update({"from": frm, "to": to})
        else: p["limit"] = limit
        d = get("/futures/usdt/candlesticks", **p) or []
        rows = [(int(x["t"]), float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"]),
                 float(x.get("sum") or x.get("v") or 0)) for x in d]
    else:
        p = {"currency_pair": sym, "interval": "15m"}
        if frm: p.update({"from": frm, "to": to})
        else: p["limit"] = limit
        d = get("/spot/candlesticks", **p) or []
        rows = [(int(x[0]), float(x[5]), float(x[3]), float(x[4]), float(x[2]), float(x[1])) for x in d]
    now = time.time()
    rows = sorted({r[0]: r for r in rows}.values())
    return [r for r in rows if r[0] + BAR <= now]  # 마감된 봉만


def ema(a, n):
    k, out, e = 2 / (n + 1), [], None
    for x in a:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out


def sar(h, l, step=0.02, mx=0.2):
    n = len(h); out = [None] * n; up = [True] * n
    if n < 2: return out, up
    bull = h[1] >= h[0]; af = step
    ep = h[0] if bull else l[0]; s = l[0] if bull else h[0]
    for i in range(1, n):
        s = s + af * (ep - s)
        if bull:
            s = min(s, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < s:
                bull, s, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, mx)
        else:
            s = max(s, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > s:
                bull, s, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(af + step, mx)
        out[i], up[i] = s, bull
    return out, up


def indicators(rows):
    o = [r[1] for r in rows]; h = [r[2] for r in rows]; l = [r[3] for r in rows]
    c = [r[4] for r in rows]; v = [r[5] for r in rows]
    n = len(c); mb = [None] * n; ub = [None] * n; lb = [None] * n; vma = [None] * n
    for i in range(19, n):
        w = c[i - 19:i + 1]; m = sum(w) / 20
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
        mb[i], ub[i], lb[i] = m, m + 2 * sd, m - 2 * sd
    for i in range(9, n):
        vma[i] = sum(v[i - 9:i + 1]) / 10
    e12, e26 = ema(c, 12), ema(c, 26)
    dif = [a - b for a, b in zip(e12, e26)]; dea = ema(dif, 9)
    hist = [a - b for a, b in zip(dif, dea)]
    s, up = sar(h, l)
    return dict(o=o, h=h, l=l, c=c, v=v, mb=mb, ub=ub, lb=lb, vma=vma, dif=dif, dea=dea, hist=hist, sar=s, up=up)


def detect(d, i):
    """i번째 마감봉 기준 신호. 반환: (stage, info) 또는 None"""
    if i < 40 or d["mb"][i] is None: return None
    o, h, l, c, v = d["o"], d["h"], d["l"], d["c"], d["v"]
    mb, ub, up = d["mb"][i], d["ub"][i], d["up"]
    macd_ok = d["dif"][i] > d["dea"][i] or (d["hist"][i] > d["hist"][i - 1] > d["hist"][i - 2])
    # 2단계: 돌파 확인
    if (c[i] > o[i] and c[i] > max(h[i - 12:i]) and d["vma"][i] and v[i] >= 2 * d["vma"][i]
            and c[i] >= ub * 0.995 and up[i] and d["dif"][i] > d["dea"][i]):
        return 2, dict(price=c[i], volx=v[i] / d["vma"][i], ub=ub, sar=d["sar"][i])
    # 1단계: 장대음봉 털기 후 SAR 미반전 + MB 지지
    if not all(up[i - 2:i + 1]): return None
    if not (c[i] >= mb * 0.997 and min(l[i - 3:i + 1]) <= mb * 1.005 and c[i] < ub): return None
    if not macd_ok: return None
    for j in range(i - 8, i):
        body = o[j] - c[j]
        avg = sum(abs(o[k] - c[k]) for k in range(j - 10, j)) / 10
        if body > 0 and avg > 0 and body >= 2 * avg and all(up[j:i + 1]):
            return 1, dict(price=c[i], mb=mb, sar=d["sar"][i])
    return None


def atr(d, i, n=14):
    h, l, c = d["h"], d["l"], d["c"]
    tr = [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(i - n + 1, i + 1)]
    return sum(tr) / n


def hold2(d, i, win=16):
    """저점을 양봉으로 2회 지킴: 이번 봉(양봉)이 두 번째 방어"""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    if i < win + 20: return None
    if not c[i] > o[i]: return None
    a = atr(d, i)
    if a <= 0: return None
    for k in range(i - 3, i - win - 1, -1):
        if not c[k] > o[k]: continue
        sup = min(l[k], l[i])
        if abs(l[i] - l[k]) > 0.5 * a: continue
        if min(l[k:i + 1]) < sup - 0.1 * a: continue          # 사이에 지지선 이탈 없음
        if min(c[k:i + 1]) < sup: continue                    # 종가 이탈 없음
        if max(h[k + 1:i]) < sup + 1.0 * a: continue          # 두 번 사이에 반등이 있어야 2회
        if min(l[k - 6:k]) < sup - 0.1 * a: continue          # 첫 방어도 그 구간 저점이어야 함
        return dict(price=c[i], sup=sup, first=k)
    return None


def vratio(d, i, n=20):
    a = sum(d["v"][i - n:i]) / n
    return d["v"][i] / a if a > 0 else 0


def recl(d, i, vx=3.0, win=16):
    """투매(20봉평균 거래대금 vx배 이상 음봉이 하단밴드 이탈) 후 바닥, 투매 첫 음봉 시가를 양봉 종가로 회복"""
    o, l, c = d["o"], d["l"], d["c"]
    if i < win + 25 or not c[i] > o[i]: return None
    for k in range(i - 2, i - win - 1, -1):
        if not (c[k] < o[k] and vratio(d, k) >= vx and l[k] <= d["lb"][k]): continue
        ks = [j for j in (k - 1, k, k + 1) if c[j] < o[j] and vratio(d, j) >= vx * 0.66]
        lvl = max(o[j] for j in ks)
        a = atr(d, i); base = min(l[k - 1:min(k + 2, i) + 1])
        if min(l[k:i + 1]) < base - 0.5 * a: return None
        if c[i] > lvl and c[i - 1] <= lvl:
            return dict(price=c[i], lvl=lvl, low=min(l[k - 1:i + 1]), cvx=vratio(d, k))
        return None
    return None


def candles_1h(kind, sym, limit=60):
    if kind == "fut":
        d = get("/futures/usdt/candlesticks", contract=sym, interval="1h", limit=limit) or []
        rows = [(int(x["t"]), float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"]), float(x.get("sum") or x.get("v") or 0)) for x in d]
    else:
        d = get("/spot/candlesticks", currency_pair=sym, interval="1h", limit=limit) or []
        rows = [(int(x[0]), float(x[5]), float(x[3]), float(x[4]), float(x[2]), float(x[1])) for x in d]
    now = time.time()
    return [r for r in sorted({r[0]: r for r in rows}.values()) if r[0] + 3600 <= now]


def short_sig(d, i, rs):
    """15분봉 SAR 하락 전환 + BTC 대비 약세 + 중심선 아래 (1시간 하락추세는 따로 확인)"""
    if i < 2 or d["mb"][i] is None: return None
    if d["up"][i - 1] and not d["up"][i] and rs <= -0.005 and d["c"][i] < d["mb"][i]:
        return dict(price=d["c"][i], stop=d["sar"][i])
    return None


def down_1h(rows1h):
    if len(rows1h) < 30: return False
    h = indicators(rows1h); j = len(rows1h) - 1
    return (not h["up"][j]) and h["mb"][j] is not None and h["c"][j] < h["mb"][j]


def hold_ok(d, i):
    """양봉2회방어 필터: 볼린저 하단 절반(%B 0.5 이하) + MACD 히스토그램 3봉 전보다 상승"""
    ub, lb = d["ub"][i], d["lb"][i]
    if ub is None or ub <= lb: return False
    return (d["c"][i] - lb) / (ub - lb) <= 0.5 and d["hist"][i] > d["hist"][i - 3]


def rsi_last(c, n=14):
    g = l = 0.0
    for i in range(1, len(c)):
        ch = c[i] - c[i - 1]; up, dn = max(ch, 0), max(-ch, 0)
        if i <= n: g += up / n; l += dn / n
        else: g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
    return 100 - 100 / (1 + g / l) if l > 0 else 100


def strong_s2(d, i):
    """[1면 단독]: 2단계 돌파 중 밴드폭 4% 이상 또는 RSI 70 이상"""
    bw = (d["ub"][i] - d["lb"][i]) / d["mb"][i] * 100 if d["mb"][i] else 0
    return bw >= 4 or rsi_last(d["c"][:i + 1]) >= 70


def fmt(x):
    if x and abs(x) < 0.01:
        return f"{x:.12f}".rstrip("0")[:12]
    return f"{x:.6g}"


def message(name, stage, info, t, rs=0.0):
    cn = CODE.get(name, name)
    if stage == 1:
        if rs >= 0.02:
            return f"[주요 분석] {cn}", "주요 분석 기사가 올라왔습니다."
        return f"[분석] {cn}", "분석 기사가 올라왔습니다."
    return f"[단독] {cn}", "단독 기사가 올라왔습니다."


def message_hold(name, info, t, rs=0.0):
    return f"[종합] {CODE.get(name, name)}", "종합 기사가 올라왔습니다."


def message_recl(name, info, t, rs, vr):
    return f"[속보] {CODE.get(name, name)}", "속보가 들어왔습니다."


def notify(title, body, prio=4, tag="newspaper", topic=None):
    if not TOPIC:
        print("[no topic]", title, body); return
    try:
        S.post("https://ntfy.sh/", json={"topic": topic or TOPIC, "title": title, "message": body,
                                         "priority": prio, "tags": [tag]}, timeout=10)
    except Exception as e:
        print("ntfy fail", e)


def backtest(days=30):
    m, miss = resolve()
    print("RESOLVED", json.dumps(m, ensure_ascii=False)); print("MISSING", miss)
    end = int(time.time()) // BAR * BAR; start = end - days * 86400 - 60 * BAR
    stats = {1: [0, 0, 0], 2: [0, 0, 0]}; recent = []
    for name, (kind, sym) in m.items():
        rows = []
        for a in range(start, end, 900 * BAR):
            rows += candles(kind, sym, a, min(a + 900 * BAR, end))
            time.sleep(0.15)
        rows = sorted({r[0]: r for r in rows}.values())
        if len(rows) < 60: print("SHORT", name, len(rows)); continue
        d = indicators(rows); last = {}
        cnt = {1: 0, 2: 0}
        for i in range(40, len(rows) - 8):
            sig = detect(d, i)
            if not sig: continue
            st, info = sig
            if rows[i][0] - last.get(st, 0) < 8 * BAR: continue
            last[st] = rows[i][0]; cnt[st] += 1
            e = d["c"][i]; res = 0
            for k in range(i + 1, i + 9):
                if d["l"][k] <= e * 0.99: res = -1; break
                if d["h"][k] >= e * 1.02: res = 1; break
            stats[st][0] += 1; stats[st][1] += res == 1; stats[st][2] += res == -1
            if rows[i][0] > end - 2 * 86400:
                recent.append((name, st, datetime.fromtimestamp(rows[i][0] + BAR, KST).strftime("%m/%d %H:%M"), e))
        print("SYM", name, len(rows), "s1", cnt[1], "s2", cnt[2])
    for st in (1, 2):
        n, w, lo = stats[st]
        print(f"STAGE{st} signals={n} win(+2%first)={w} loss(-1%first)={lo} none={n - w - lo}"
              + (f" winrate={w / n * 100:.1f}%" if n else ""))
    print("RECENT48H")
    for r in sorted(recent, key=lambda x: x[2]): print(" ", r)


def live(hours=5.75):
    m, miss = resolve()
    print("RESOLVED", m, "MISSING", miss)
    stfile = "state.json"
    try: state = json.load(open(stfile))
    except Exception: state = {}
    if os.environ.get("EVENT") == "workflow_dispatch":
        notify("[알림] 뉴스 구독 시작", "구독한 언론사 기사를 알려드립니다.", 3, "newspaper")
    order = ["BTC"] + [n for n in m if n != "BTC"]
    stop = time.time() + hours * 3600
    while time.time() < stop:
        nxt = (int(time.time()) // BAR + 1) * BAR + 8
        time.sleep(max(1, nxt - time.time()))
        btc_ret = None
        for name in order:
            kind, sym = m[name]
            rows = candles(kind, sym, limit=120)
            if len(rows) < 60: continue
            c = [r[4] for r in rows]
            ret = c[-1] / c[-17] - 1
            if name == "BTC":
                btc_ret = ret; continue
            d = indicators(rows); i = len(rows) - 1
            vr = vratio(d, i)
            rc = recl(d, i)
            if rc and btc_ret is not None and rows[i][0] - state.get(f"{name}:r", 0) >= 8 * BAR:
                state[f"{name}:r"] = rows[i][0]
                title, body = message_recl(name, rc, rows[i][0], ret - btc_ret, vr)
                notify(title, body, 5, "newspaper")
                print("ALERT", title, body.replace("\n", " | "))
            sh = short_sig(d, i, ret - btc_ret) if btc_ret is not None else None
            if sh and rows[i][0] - state.get(f"{name}:s", 0) >= 8 * BAR and down_1h(candles_1h(kind, sym)):
                state[f"{name}:s"] = rows[i][0]
                title = f"short [해설] {CODE.get(name, name)}"
                notify(title, "해설 기사가 올라왔습니다.", 4, "newspaper", TOPIC + "-s")
                print("ALERT", title)
            hd = hold2(d, i)
            if False and hd and vr >= 1.5 and hold_ok(d, i) and btc_ret is not None and rows[i][0] - state.get(f"{name}:h", 0) >= 8 * BAR:
                state[f"{name}:h"] = rows[i][0]
                title, body = message_hold(name, hd, rows[i][0], ret - btc_ret)
                notify(title, body, 4, "newspaper")
                print("ALERT", title, body.replace("\n", " | "))
            sig = detect(d, i)
            if not sig or btc_ret is None: continue
            st, info = sig; t = rows[i][0]
            rs = ret - btc_ret
            if st == 1:
                state[f"{name}:s1seen"] = t
                continue  # 1단계 눌림 알람 중지(60일 검증 하위)
            if st == 2 and not any((detect(d, j) or (0,))[0] == 1 for j in range(i - 12, i)): continue
            key = f"{name}:{st}"
            if t - state.get(key, 0) < 8 * BAR: continue
            state[key] = t
            title, body = message(name, st, info, t, rs)
            prio = 4
            if st == 2 and strong_s2(d, i):
                title, body, prio = f"[1면 단독] {CODE.get(name, name)}", "1면 단독 기사가 올라왔습니다.", 5
            notify(title, body, prio, "newspaper")
            print("ALERT", title, body.replace("\n", " | "))
        json.dump(state, open(stfile, "w"))
    json.dump(state, open(stfile, "w"))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "live"
    if mode == "backtest":
        backtest(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
        notify("[알림] 연결 확인", "뉴스 알림 연결이 정상입니다.", 3, "newspaper")
    else:
        live()
