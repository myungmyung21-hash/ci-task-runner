import os, sys, json, time, math
from datetime import datetime, timezone, timedelta
import requests

API = "https://api.gateio.ws/api/v4"
KST = timezone(timedelta(hours=9))
TOPIC = os.environ.get("NTFY_TOPIC", "")
WATCH = ["HBAR", "SUI", "ETH", "PEPE", "BTC", "WLD", "SOL", "TSLA", "ADA", "XRP",
         "GOOGL", "DOGE", "SHIB", "ONDO", "SPCX", "BRETT", "MBABYDOGE", "TRUMP", "KAIA"]
BAR = 900
CODE = {"HBAR": "Hazel", "SUI": "Sunny", "ETH": "Echo", "PEPE": "Pepper", "BTC": "Bravo",
        "WLD": "Willow", "SOL": "Solar", "TSLA": "Tango", "ADA": "Aurora", "XRP": "Xenon",
        "GOOGL": "Gamma", "DOGE": "Delta", "SHIB": "Shadow", "ONDO": "Orbit", "SPCX": "Spark",
        "BRETT": "Berry", "MBABYDOGE": "Mango", "TRUMP": "Tulip", "KAIA": "Kite"}
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


def fmt(x):
    return f"{x:.6g}"


def message(name, stage, info, t, rs=0.0):
    tk = datetime.fromtimestamp(t + BAR, KST).strftime("%H:%M")
    cn = CODE.get(name, name)
    if stage == 1:
        head = "긴급 리뷰 요청" if rs >= 0.02 else "리뷰 요청"
        title = f"[Coding task] {cn} {head}"
        body = (f"{tk} 빌드 · 현재값 {fmt(info['price'])}\n"
                f"기준선 {fmt(info['mb'])} · 하한 {fmt(info['sar'])} · 점수 {rs*100:+.2f}")
    else:
        title = f"[AI 테스트] {cn} 배포 완료"
        body = (f"{tk} 빌드 · 현재값 {fmt(info['price'])}\n"
                f"부하 {info['volx']:.1f}x · 상한 {fmt(info['ub'])} · 하한 {fmt(info['sar'])} · 점수 {rs*100:+.2f}")
    return title, body


def notify(title, body, prio=4, tag="robot"):
    if not TOPIC:
        print("[no topic]", title, body); return
    try:
        S.post("https://ntfy.sh/", json={"topic": TOPIC, "title": title, "message": body,
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
        notify("[News summary] 구독 시작", f"{len(m)}개 채널 요약을 15분마다 확인합니다" + (f"\n미연결: {len(miss)}개" if miss else ""), 3, "newspaper")
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
            sig = detect(d, i)
            if not sig or btc_ret is None: continue
            st, info = sig; t = rows[i][0]
            rs = ret - btc_ret
            if st == 1:
                state[f"{name}:s1seen"] = t
                if rs < 0.01: continue
            if st == 2 and not any((detect(d, j) or (0,))[0] == 1 for j in range(i - 12, i)): continue
            key = f"{name}:{st}"
            if t - state.get(key, 0) < 8 * BAR: continue
            state[key] = t
            title, body = message(name, st, info, t, rs)
            notify(title, body, 5 if (st == 1 and rs >= 0.02) else 4, "computer" if st == 1 else "robot")
            print("ALERT", title, body.replace("\n", " | "))
        json.dump(state, open(stfile, "w"))
    json.dump(state, open(stfile, "w"))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "live"
    if mode == "backtest":
        backtest(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
        notify("[AI 테스트] 연결 확인", "테스트 환경 연결이 정상입니다.", 3, "white_check_mark")
    else:
        live()
