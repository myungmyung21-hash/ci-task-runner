import time, statistics as st
from datetime import datetime
import monitor as M
from bvdata import fetch_bv, BV
from research6 import fetch, rsi
DAYS=300; H=16
def so(d,i,stop):
    e=d["c"][i]; R=stop-e
    if R<=0 or R/e>0.06 or i+H>=len(d["c"]): return None
    for k in range(i+1,i+1+H):
        if d["h"][k]>=stop: return -1.0
        if d["l"][k]<=e-2*R: return 2.0
    return max(-1.0,min(2.0,(e-d["c"][i+H])/R))
def pct(d,i): e=d["c"][i]; return (1-d["c"][i+H]/e)*100, (1-min(d["l"][i+1:i+1+H])/e)*100, (max(d["h"][i+1:i+1+H])/e-1)*100
# A. 오늘 WLD (Gate)
m,_=M.resolve(); k,s=m["WLD"]; r=fetch(k,s,"15m",2); d=M.indicators(r); d["t"]=[x[0] for x in r]; rr=rsi(d["c"])
print("WLD Gate 15분봉 10/19 15:00~ (봉시작 KST | O C | 거래% | MB | SAR | 히스토 | RSI | 신호)")
s1=[False]*len(r)
for i in range(60,len(r)):
    sig=M.detect(d,i)
    if sig and sig[0]==1: s1[i]=True
    t=datetime.fromtimestamp(d["t"][i],M.KST)
    if t.strftime("%m/%d")=="10/19" and t.hour>=15:
        tags=[]
        if sig and sig[0]==2 and any(s1[i-12:i]): tags.append("단독"+("(1면)" if M.strong_s2(d,i) else ""))
        if M.recl(d,i): tags.append("속보")
        print(f" {t:%H:%M} | {d['o'][i]:.4f} {d['c'][i]:.4f} | {M.vratio(d,i)*100:.0f}% | {d['mb'][i]:.4f} | {d['sar'][i]:.4f}{'U' if d['up'][i] else 'D'} | {d['hist'][i]:+.4f} | {rr[i]:.0f} | {','.join(tags)}")
# B. 300일 숏 후보
data={}
for name in BV:
    r15,_=fetch_bv(name,"15m",DAYS); r1h,_=fetch_bv(name,"1h",DAYS+5)
    dd=M.indicators(r15); dd["t"]=[x[0] for x in r15]; h=M.indicators(r1h); h["t"]=[x[0] for x in r1h]
    data[name]=(dd,h)
res={}
for name,(d,h) in data.items():
    if name=="BTC": continue
    c=d["c"]; n=len(c); s1=[False]*n; last={}; hj=0; s2_at=-999; s2_low=None; s2_hi=None; top_i=-999
    for i in range(80,n-H):
        t=d["t"][i]
        while hj+1<len(h["t"]) and h["t"][hj+1]+3600<=t+900: hj+=1
        up1h = hj>30 and h["up"][hj] and h["mb"][hj] and h["c"][hj]>h["mb"][hj]
        sig=M.detect(d,i)
        if sig and sig[0]==1: s1[i]=True
        if sig and sig[0]==2 and any(s1[i-12:i]): s2_at=i; s2_low=d["l"][i]
        if d["h"][i]>=d["ub"][i] and d["h"][i]>=max(d["h"][i-24:i]): top_i=i
        vr=M.vratio(d,i); red=c[i]<d["o"][i]; cs=[]
        # SA: 2단계 돌파 후 16봉 안에 알람봉 저가 밑으로 음봉 종가 = 돌파 실패
        if s2_at>0 and 0<i-s2_at<=16 and red and c[i]<s2_low and c[i-1]>=s2_low:
            stop=max(d["h"][s2_at:i+1]); cs.append(("SA 2단계돌파 실패(알람봉 저가 이탈)",stop))
            if vr>=2: cs.append(("SB SA+거래 200%+",stop))
        # SC: 24봉 고점(상단밴드 터치) 후 24봉 안, SAR 하락 상태에서 거래 200%+ 음봉이 중심선 아래로 마감
        if 0<i-top_i<=24 and red and vr>=2 and (not d["up"][i]) and c[i]<d["mb"][i] and c[i-1]>=d["mb"][i-1]:
            stop=max(d["h"][top_i:i+1]); cs.append(("SC 고점 후 거래동반 중심선 이탈",stop))
            if up1h: cs.append(("SD SC+1시간 상승추세 중",stop))
            if sig is None and d["hist"][i]<0: cs.append(("SE SC+MACD 히스토 음수",stop))
        for nm,stop in cs:
            if t-last.get(nm,0)<8*900: continue
            last[nm]=t; o=so(d,i,stop*1.001)
            if o is not None: res.setdefault(nm,[]).append((t,o)+pct(d,i))
        if i%8==0 and d["mb"][i]:
            o=so(d,i,max(d["h"][i-16:i])*1.001)
            if o is not None: res.setdefault("비교: 아무봉 short",[]).append((t,o)+pct(d,i))
allt=[x[0] for v in res.values() for x in v]; t0,t1=min(allt),max(allt); w=(t1-t0)/5
print(f"\n바이낸스 선물 15분봉 {DAYS}일 12종목 short 후보 (R: 손절=고점 위, 목표 2R, 4시간 / %: 하락이 +)")
print(" 규칙 | 건수 | 하루 | R 평균 | 5구간 R | 4h후 % | 유리최대 % | 역행최대 % | 플러스구간")
for nm in sorted(res):
    v=res[nm]; R=[x[1] for x in v]
    bl=[[x[1] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
    print(f" {nm} | {len(v)} | {len(v)/DAYS:.2f} | {st.mean(R):+.3f} | "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+
          f" | {st.mean(x[2] for x in v):+.2f} | {st.mean(x[3] for x in v):.2f} | {st.mean(x[4] for x in v):.2f} | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
