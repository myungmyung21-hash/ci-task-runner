import time, statistics as st
from datetime import datetime
import monitor as M
from bvdata import fetch_bv, BV
from research6 import rsi, fetch
DAYS=300; H=16
def so(d,i,stop):
    e=d["c"][i]; R=stop-e
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["h"][k]>=stop: return -1.0
        if d["l"][k]<=e-2*R: return 2.0
    return max(-1.0,min(2.0,(e-d["c"][i+H])/R))
def flags(d,i,rr,h,hj,rs):
    c,o,hh,ll=d["c"],d["o"],d["h"],d["l"]; out=[]
    down1h = hj>30 and (not h["up"][hj]) and h["mb"][hj] and h["c"][hj]<h["mb"][hj]
    flip = d["up"][i-1] and not d["up"][i]
    if flip and rs is not None and rs<=-0.005 and c[i]<d["mb"][i] and down1h: out.append(("현재 short(늦음)", d["sar"][i]))
    if flip and c[i]>=d["mb"][i]:
        out.append(("E1 SAR 전환(중심선 위, 고점 직후)", d["sar"][i]))
        if max(rr[i-8:i+1])>=70: out.append(("E2 E1+직전 2시간 RSI70+", d["sar"][i]))
        if max(hh[i-8:i+1])>=max(d["ub"][q] for q in range(i-8,i+1))*0.999: out.append(("E3 E1+직전 2시간 상단밴드 터치", d["sar"][i]))
    rng=hh[i]-ll[i]
    touch = hh[i]>=d["ub"][i]*0.998 and c[i]<o[i] and rng>0 and (hh[i]-max(o[i],c[i]))/rng>=0.4
    mbfall = d["mb"][i]<d["mb"][i-4]
    if touch and mbfall:
        out.append(("E4 하락중 상단밴드 윗꼬리 음봉", hh[i]))
        if down1h: out.append(("E5 E4+1시간 하락추세", hh[i]))
        if M.vratio(d,i)>=1.5: out.append(("E6 E4+거래 150%+", hh[i]))
    return out
# A. 오늘 TRUMP (Gate)
m,_=M.resolve(); k,s=m["TRUMP"]; r=fetch(k,s,"15m",2); d=M.indicators(r); rr=rsi(d["c"])
kb,sb=m["BTC"]; rb=fetch(kb,sb,"15m",2); bidx={x[0]:j for j,x in enumerate(rb)}
r1=M.candles_1h(k,s,200); h=M.indicators(r1); h["t"]=[x[0] for x in r1]
print("TRUMP Gate 15분봉 오늘 (봉시작 KST | 종가 | SAR | MB/UB | 신호)")
hj=0
for i in range(60,len(r)):
    t=r[i][0]
    while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
    bi=bidx.get(t); rs=(d["c"][i]/d["c"][i-16]-1)-(rb[bi][4]/rb[bi-16][4]-1) if bi and bi>=16 else None
    tt=datetime.fromtimestamp(t,M.KST)
    if tt.strftime("%m/%d")==datetime.now(M.KST).strftime("%m/%d"):
        f=[x[0].split(" ")[0] for x in flags(d,i,rr,h,hj,rs)]
        print(f" {tt:%H:%M} | {d['c'][i]:.3f} | {d['sar'][i]:.3f}{'U' if d['up'][i] else 'D'} | {d['mb'][i]:.3f}/{d['ub'][i]:.3f} | {','.join(f)}")
# B. 300일
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    dd=M.indicators(r15); dd["t"]=[x[0] for x in r15]; dd["rsi"]=rsi(dd["c"]); hh_=M.indicators(r1h); hh_["t"]=[x[0] for x in r1h]
    data[name]=(dd,hh_)
btc=data["BTC"][0]; bidx={t:i for i,t in enumerate(btc["t"])}
res={}
for name,(d,h) in data.items():
    if name=="BTC": continue
    last={}; hj=0
    for i in range(80,len(d["c"])-H):
        t=d["t"][i]; bi=bidx.get(t)
        while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
        rs=(d["c"][i]/d["c"][i-16]-1)-(btc["c"][bi]/btc["c"][bi-16]-1) if bi and bi>=16 else None
        for nm,stop in flags(d,i,d["rsi"],h,hj,rs):
            if t-last.get(nm,0)<8*900: continue
            last[nm]=t; o=so(d,i,stop*1.001)
            if o is None: continue
            e=d["c"][i]; late=(1-e/max(d["h"][i-16:i+1]))*100
            res.setdefault(nm,[]).append((t,o,(1-d["c"][i+H]/e)*100,(1-min(d["l"][i+1:i+1+H])/e)*100,(max(d["h"][i+1:i+1+H])/e-1)*100,late))
        if i%8==0:
            o=so(d,i,max(d["h"][i-3:i+1])*1.001)
            if o is not None: res.setdefault("비교: 아무봉 short",[]).append((d["t"][i],o,(1-d["c"][i+H]/d["c"][i])*100,0,0,(1-d["c"][i]/max(d["h"][i-16:i+1]))*100))
allt=[x[0] for v in res.values() for x in v]; t0,t1=min(allt),max(allt); w=(t1-t0)/5
print(f"\n바이낸스 300일 12종목 short 타이밍 비교 (R: 손절=직전 고점 위, 2R, 4시간 / 4h후 %는 하락이 +)")
print(" 규칙 | 건수 | 하루 | 고점대비 진입위치 | R | 5구간 R | 4h후 | 유리최대 | 역행최대 | 플러스구간")
for nm in sorted(res):
    v=res[nm]; bl=[[x[1] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
    print(f" {nm} | {len(v)} | {len(v)/DAYS:.2f} | -{st.mean(x[5] for x in v):.2f}% | {st.mean(x[1] for x in v):+.3f} | "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+
          f" | {st.mean(x[2] for x in v):+.2f} | {st.mean(x[3] for x in v):.2f} | {st.mean(x[4] for x in v):.2f} | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
