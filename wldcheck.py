from datetime import datetime
import monitor as M
m,_=M.resolve(); k,s=m["WLD"]; r=M.candles(k,s,limit=120); d=M.indicators(r)
out=["WLD Gate 15분봉 최근 (봉시작 KST | 종가 | SAR | 상태)"]
for i in range(len(r)-12,len(r)):
    flip = "← 상승 전환" if (d["up"][i] and not d["up"][i-1]) else ("← 하락 전환" if (not d["up"][i] and d["up"][i-1]) else "")
    out.append(f" {datetime.fromtimestamp(r[i][0],M.KST):%m/%d %H:%M} | {d['c'][i]:.4f} | {d['sar'][i]:.4f} | {'상승' if d['up'][i] else '하락'} {flip}")
open("wldcheck.txt","w").write("\n".join(out)); print("\n".join(out))
