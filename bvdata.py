import io, zipfile, csv, time, requests
from datetime import datetime, timedelta, timezone
BV = {"HBAR":"HBARUSDT","SUI":"SUIUSDT","ETH":"ETHUSDT","PEPE":"1000PEPEUSDT","WLD":"WLDUSDT","SOL":"SOLUSDT",
      "ADA":"ADAUSDT","XRP":"XRPUSDT","DOGE":"DOGEUSDT","SHIB":"1000SHIBUSDT","ONDO":"ONDOUSDT","TRUMP":"TRUMPUSDT","BTC":"BTCUSDT"}
def _rows(url):
    r = requests.get(url, timeout=60)
    if r.status_code != 200: return None
    z = zipfile.ZipFile(io.BytesIO(r.content)); out = []
    for ln in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
        if not ln or not ln[0].isdigit(): continue
        out.append((int(ln[0]) // 1000, float(ln[1]), float(ln[2]), float(ln[3]), float(ln[4]), float(ln[7])))
    return out
def fetch_bv(name, tf="15m", days=300):
    sym = BV[name]; now = datetime.now(timezone.utc); start = now - timedelta(days=days); rows = []; miss = 0
    m = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    while (m.year, m.month) < (now.year, now.month):
        u = f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/{tf}/{sym}-{tf}-{m:%Y-%m}.zip"
        r = _rows(u)
        if r is None: miss += 1
        else: rows += r
        m = datetime(m.year + (m.month // 12), m.month % 12 + 1, 1, tzinfo=timezone.utc)
    d = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    while d.date() < now.date():
        u = f"https://data.binance.vision/data/futures/um/daily/klines/{sym}/{tf}/{sym}-{tf}-{d:%Y-%m-%d}.zip"
        r = _rows(u)
        if r is not None: rows += r
        d += timedelta(days=1)
    rows = sorted({r[0]: r for r in rows if r[0] >= start.timestamp()}.values())
    return rows, miss
