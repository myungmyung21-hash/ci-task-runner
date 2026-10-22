import statistics as st
from datetime import datetime
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300
def agg4h(r1):
    out={}; 
    for t,o,h,l,c,v in r1:
        b=t//14400*14400
        if b not in out: out[b]=[b,o,h,l,c,v]
        else: x=out[b]; x[2]=max(x[2],h); x[3]=min(x[3],l); x[4]=c; x[5]+=v
    rows=[tuple(x) for k,x in sorted(out.items())]
    return rows[:-1]
res={}; s2res={}
for name in BV:
    if name=="BTC": continue
    r1,_=fetch_bv(name,"1h",DAYS+20); r4=agg4h(r1); d=M.indicators(r4); c=d["c"]; n=len(c)
    flips=[]  # (마감시각, 방향)
    for i in range(45,n-18):
        if d["mb"][i-20] is None: continue
        side=[1 if c[q]>d["mb"][q] else -1 for q in range(i-20,i+1)]
        run=0
        for q in range(len(side)-2,-1,-1):
            if side[q]==side[-2]: run+=1
            else: break
        cross = side[-1]!=side[-2]
        sruns=0
        for q in range(i-1,i-30,-1):
            if d["up"][q]==d["up"][i-1]: sruns+=1
            else: break
        sflip = d["up"][i]!=d["up"][i-1]
        def add(nm,dirn):
            e=c[i]; r4h=(c[i+1]/e-1)*100*dirn; r24=(c[i+6]/e-1)*100*dirn; r72=(c[i+18]/e-1)*100*dirn
            fav=(max(d["h"][i+1:i+7])/e-1)*100 if dirn==1 else (1-min(d["l"][i+1:i+7])/e)*100
            adv=(1-min(d["l"][i+1:i+7])/e)*100 if dirn==1 else (max(d["h"][i+1:i+7])/e-1)*100
            res.setdefault(nm,[]).append((r4[i][0],r4h,r24,r72,fav,adv))
        if i%3==0: add("비교: 아무 4시간봉 롱",1); add("비교: 아무 4시간봉 short",-1)
        if cross:
            dirn=side[-1]
            add(f"중심선 돌파 {'상향' if dirn==1 else '하향'} (직전 같은쪽 {'10봉+' if run>=10 else '10봉 미만'})",dirn)
            if run>=10: flips.append((r4[i][0]+14400,dirn))
        if sflip:
            dirn=1 if d["up"][i] else -1
            add(f"SAR 전환 {'상승' if dirn==1 else '하락'} (직전 {'10봉+' if sruns>=10 else '10봉 미만'} 유지)",dirn)
    # 15분 [단독]과 4시간 전환 동조 여부
    r15,_=fetch_bv(name,"15m",DAYS); d15=M.indicators(r15); m15=len(r15); s1=[False]*m15; last=0
    for i in range(120,m15-16):
        sig=M.detect(d15,i)
        if sig and sig[0]==1: s1[i]=True
        t=r15[i][0]
        if not(sig and sig[0]==2 and any(s1[i-12:i])) or t-last<8*900: continue
        last=t; fin=(d15["c"][i+16]/d15["c"][i]-1)*100
        rec=[f for f in flips if 0<=t+900-f[0]<=86400]
        tag="4시간 상향 전환 후 24시간 안" if any(f[1]==1 for f in rec) else ("4시간 하향 전환 후 24시간 안" if any(f[1]==-1 for f in rec) else "최근 4시간 전환 없음")
        s2res.setdefault(tag,[]).append((t,fin))
def blocks(v,key):
    t0=min(x[0] for x in v); w=(max(x[0] for x in v)-t0)/5 or 1
    return [[x[key] for x in v if min(4,int((x[0]-t0)/w))==b] for b in range(5)]
print(f"바이낸스 4시간봉(1시간 합성) {DAYS}일 12종목 / 수익은 신호 방향 기준 %")
print(" 신호 | 건수 | 4h후 | 24h후 | 72h후 | 24h 유리최대 | 24h 역행최대 | 24h후 5구간 | 플러스")
for nm in sorted(res):
    v=res[nm]; bl=blocks(v,2)
    print(f" {nm} | {len(v)} | {st.mean(x[1] for x in v):+.2f} | {st.mean(x[2] for x in v):+.2f} | {st.mean(x[3] for x in v):+.2f} | {st.mean(x[4] for x in v):.2f} | {st.mean(x[5] for x in v):.2f} | "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
print("\n15분 [단독] 알람 × 4시간 중심선 전환(직전 10봉+ 유지 후) 동조 여부 (알람 후 4시간 %)")
for k,v in s2res.items():
    bl=blocks(v,1)
    print(f" {k} | n={len(v)} | {st.mean(x[1] for x in v):+.2f} | 5구간 "+" ".join(f"{st.mean(b):+.2f}" if b else "-" for b in bl)+f" | {sum(1 for b in bl if b and st.mean(b)>0)}/5")
