import time
from datetime import datetime
import monitor as M
from research import fetch_all, outcome
data = fetch_all(30)
def ratio(v,i,n=20): 
    a=sum(v[i-n:i])/n; return v[i]/a if a>0 else 0
# 1) HBAR 10/18 실측
rows,d = data["HBAR"]; v=d["v"]
print("HBAR 10/18 15:00~18:30 KST (거래대금USDT, 직전20봉평균 대비, 직전봉 대비, 판정)")
for i,r in enumerate(rows):
    t=datetime.fromtimestamp(r[0]+M.BAR,M.KST)
    if t.strftime("%m/%d")=="10/18" and 15<=t.hour<=18:
        hd=M.hold2(d,i); s=M.detect(d,i)
        print(f" {t:%H:%M} C={d['c'][i]:.5f} {'양' if d['c'][i]>d['o'][i] else '음'} vol={v[i]:,.0f} 평균대비={ratio(v,i)*100:.0f}% 직전봉대비={v[i]/v[i-1]*100 if v[i-1] else 0:.0f}% hold2={'Y' if hd else '-'} stage={s[0] if s else '-'}")
# 2) 양봉2회방어: 신호봉 거래량 배수 구간별 성과
B=[(0,0.8),(0.8,1.2),(1.2,1.5),(1.5,2),(2,3),(3,99)]
res={("신호봉",b):[] for b in B}; res.update({("다음봉",b):[] for b in B}); res.update({("2번째/1번째",b):[] for b in B})
for name,(rows,d) in data.items():
    if name=="BTC": continue
    v=d["v"]; n=len(rows); last=0
    for i in range(60,n-17):
        hd=M.hold2(d,i)
        if not hd or rows[i][0]-last<8*M.BAR: continue
        last=rows[i][0]; k=hd["first"]
        o=outcome(d,i,hd["sup"]*0.999)
        if o is None: continue
        for key,val in (("신호봉",ratio(v,i)),("2번째/1번째",v[i]/v[k] if v[k] else 0)):
            for b in B:
                if b[0]<=val<b[1]: res[(key,b)].append(o)
        # 다음봉 진입 버전: 신호 다음 봉 거래량이 터지고 양봉이면 그 종가 진입
        j=i+1; rj=ratio(v,j)
        if d["c"][j]>d["o"][j] and d["c"][j]>hd["sup"]:
            oj=outcome(d,j,hd["sup"]*0.999)
            if oj is not None:
                for b in B:
                    if b[0]<=rj<b[1]: res[("다음봉",b)].append(oj)
print("\n양봉2회방어 거래량 구간별 성과 (기준: 직전 20봉 평균 거래대금)")
for (key,b),vals in res.items():
    if not vals: print(f" {key} {b[0]*100:.0f}~{b[1]*100 if b[1]<99 else 999:.0f}% | n=0"); continue
    w=sum(1 for x in vals if x==2.0); lo=sum(1 for x in vals if x==-1.0)
    print(f" {key} {b[0]*100:.0f}~{b[1]*100 if b[1]<99 else 999:.0f}% | n={len(vals)} | 하루={len(vals)/30:.1f} | 2R승={w} | 손절={lo} | 기대값R={sum(vals)/len(vals):+.3f}")
