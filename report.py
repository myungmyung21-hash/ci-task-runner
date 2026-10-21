import os, sys, time, json, requests
from datetime import datetime, timedelta
import monitor as M

LABEL = {"s2": "2단계돌파", "s2s": "2단계돌파(강:15분RSI70+·1시간RSI65+)", "short": "short(SAR전환·약세)"}

def fetch_range(kind, sym, start, end):
    rows, a = [], start
    while a < end:
        b = min(a + 900 * M.BAR, end)
        rows += M.candles(kind, sym, a, b); a = b; time.sleep(0.12)
    return sorted({r[0]: r for r in rows}.values())

def fetch_1h(kind, sym, start, end):
    rows, a = [], start
    while a < end:
        b = min(a + 900 * 3600, end)
        if kind == "fut":
            d = M.get("/futures/usdt/candlesticks", contract=sym, interval="1h", **{"from": a, "to": b}) or []
            rows += [(int(x["t"]), float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"]), float(x.get("sum") or 0)) for x in d]
        else:
            d = M.get("/spot/candlesticks", currency_pair=sym, interval="1h", **{"from": a, "to": b}) or []
            rows += [(int(x[0]), float(x[5]), float(x[3]), float(x[4]), float(x[2]), float(x[1])) for x in d]
        a = b; time.sleep(0.12)
    return sorted({r[0]: r for r in rows}.values())

def replay(start_t, end_t):
    """감시 코드와 같은 규칙(120봉 창, 같은 순서·중복제거)으로 알람을 재현"""
    m, _ = M.resolve()
    f0 = start_t - 140 * M.BAR; now = int(time.time())
    btc = fetch_range(*m["BTC"], f0, now); bidx = {r[0]: i for i, r in enumerate(btc)}
    alerts = []; data = {}
    for name, (k, s) in m.items():
        if name == "BTC": continue
        rows = fetch_range(k, s, f0, now); data[name] = rows; state = {}
        h1 = fetch_1h(k, s, f0 - 70 * 3600, now)
        for i in range(119, len(rows)):
            t = rows[i][0]; ct = t + M.BAR
            if ct < start_t or ct > end_t: continue
            bi = bidx.get(t)
            if bi is None or bi < 16: continue
            btc_ret = btc[bi][4] / btc[bi - 16][4] - 1
            ret = rows[i][4] / rows[i - 16][4] - 1; rs = ret - btc_ret
            d = M.indicators(rows[i - 119:i + 1]); j = 119
            vr = M.vratio(d, j)
            def add(key, typ, stop):
                if t - state.get(key, 0) < 8 * M.BAR: return
                state[key] = t; alerts.append(dict(name=name, typ=typ, i=i, t=ct, entry=rows[i][4], stop=stop))
            sh = M.short_sig(d, j, rs)
            if sh and t - state.get("s", 0) >= 8 * M.BAR:
                hh = [r for r in h1 if r[0] + 3600 <= ct][-60:]
                if M.down_1h(hh): add("s", "short", sh["stop"])
            rc = M.recl(d, j)
            # [속보] 투매후회복 중지
            hd = M.hold2(d, j)
            # 양봉2회방어 알람 중지(300일 검증 손실)
            sig = M.detect(d, j)
            if not sig: continue
            st, info = sig
            if st == 1:
                continue
            else:
                if not any((M.detect(d, q) or (0,))[0] == 1 for q in range(j - 12, j)): continue
                g2 = M.s2_grade(d, j, [r for r in h1 if r[0] + 3600 <= ct][-100:])
                if g2: add("2", "s2s" if g2 == "strong" else "s2", info["sar"])
    for a in alerts:
        rows = data[a["name"]]; fut = rows[a["i"] + 1:]; e = a["entry"]
        if not fut: a.update(up=None); continue
        a["up"] = (max(r[2] for r in fut) / e - 1) * 100
        a["dn"] = (min(r[3] for r in fut) / e - 1) * 100
        a["now"] = (fut[-1][4] / e - 1) * 100
        res = "진행"
        if a["typ"] == "short":
            R = a["stop"] - e
            if R > 0:
                for r in fut:
                    if r[2] >= a["stop"]: res = "손절"; break
                    if r[3] <= e - 2 * R: res = "목표"; break
        else:
            R = e - a["stop"]
            if R > 0:
                for r in fut:
                    if r[3] <= a["stop"]: res = "손절"; break
                    if r[2] >= e + 2 * R: res = "목표"; break
        a["res"] = res
        a["dir"] = "하락" if (a["now"] < 0 and -a["dn"] > a["up"]) else "상승"
    return sorted(alerts, key=lambda x: x["t"])

def chunks(head, lines, lim=195):
    out, cur = [], head
    for ln in lines:
        if len(cur) + 1 + len(ln) > lim: out.append(cur); cur = ln
        else: cur = cur + "\n" + ln if cur else ln
    if cur: out.append(cur)
    return out

def morning(alerts):
    done = [a for a in alerts if a.get("up") is not None]
    head = f"[코인 알람 아침 정리] 지난 24시간 {len(done)}건"
    lines = []
    for a in done:
        tk = datetime.fromtimestamp(a["t"], M.KST).strftime("%H:%M")
        lines.append(f"{tk} {a['name']} {LABEL[a['typ']]} 진입{M.fmt(a['entry'])} 최고{a['up']:+.1f}% 최저{a['dn']:+.1f}% 현재{a['now']:+.1f}% {a['res']}·{a['dir']}")
    if not lines: lines = ["해당 시간대 알람 없음"]
    return chunks(head, lines)

def noon(alerts):
    done = [a for a in alerts if a.get("up") is not None]
    head = f"[코인 알람 정오 통계] 아침 정리 {len(done)}건 기준(%)"
    lines = []
    longs = [a for a in done if a["typ"] != "short"]
    groups = [("롱 전체", longs)] + [(LABEL[k], [a for a in done if a["typ"] == k]) for k in LABEL if k != "short"]
    for nm, g in groups:
        if not g: continue
        ups = [a["up"] for a in g]; dns = [a["dn"] for a in g]
        lines.append(f"{nm} {len(g)}건 평균최고{sum(ups)/len(ups):+.1f} 최대{max(ups):+.1f} 최소{min(ups):+.1f} 평균최저{sum(dns)/len(dns):+.1f} 목표{sum(a["res"]=="목표" for a in g)} 손절{sum(a["res"]=="손절" for a in g)}")
    sh = [a for a in done if a["typ"] == "short"]
    if sh:
        dns = [a["dn"] for a in sh]; ups = [a["up"] for a in sh]
        lines.append(f"short {len(sh)}건 평균최저{sum(dns)/len(dns):+.1f} 최대하락{min(dns):+.1f} 최소하락{max(dns):+.1f} 평균역행{sum(ups)/len(ups):+.1f} 목표{sum(a['res']=='목표' for a in sh)} 손절{sum(a['res']=='손절' for a in sh)}")
    if not lines: lines = ["집계할 알람 없음"]
    return chunks(head, lines)

def kakao_send(msgs):
    key = os.environ.get("KAKAO_REST_KEY"); rt = os.environ.get("KAKAO_REFRESH")
    if not (key and rt): print("[kakao 미설정]"); return False
    data = {"grant_type": "refresh_token", "client_id": key, "refresh_token": rt}
    if os.environ.get("KAKAO_SECRET"): data["client_secret"] = os.environ["KAKAO_SECRET"]
    tok = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=15).json()
    if "access_token" not in tok: print("token fail", tok); return False
    if tok.get("refresh_token"): open("new_refresh.txt", "w").write(tok["refresh_token"])
    ok = True
    for t in msgs:
        tpl = {"object_type": "text", "text": t, "link": {"web_url": "https://m.daum.net", "mobile_web_url": "https://m.daum.net"}}
        r = requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send",
                          headers={"Authorization": "Bearer " + tok["access_token"]}, data={"template_object": json.dumps(tpl, ensure_ascii=False)}, timeout=15)
        print("kakao", r.status_code); ok &= r.status_code == 200; time.sleep(0.5)
    return ok

if __name__ == "__main__":
    mode = sys.argv[1]; dry = "--dry" in sys.argv
    now = int(time.time())
    if mode == "morning":
        start, end = now - 86400, now
    else:
        kst = datetime.fromtimestamp(now, M.KST)
        ref = kst.replace(hour=7, minute=45, second=0, microsecond=0)
        if kst < ref: ref -= timedelta(days=1)
        end = int(ref.timestamp()); start = end - 86400
    alerts = replay(start, end)
    msgs = morning(alerts) if mode == "morning" else noon(alerts)
    open("report_out.txt", "w").write("\n=====\n".join(msgs))
    print("\n=====\n".join(msgs))
    if not dry: kakao_send(msgs)
