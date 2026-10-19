import statistics as st
import monitor as M
from bvdata import fetch_bv, BV
DAYS=300; H=16
ev=[]
for name in BV:
    if name=="BTC": continue
    r,_=fetch_bv(name,"15m",DAYS); d=M.indicators(r); last=0
    for i in range(80,len(r)-H-1):
        if not M.recl(d,i) or r[i][0]-last<8*900: continue
        last=r[i][0]; e=d["c"][i]
        ev.append((name,[(d["h"][k]/e-1)*100 for k in range(i+1,i+1+H)],[(d["l"][k]/e-1)*100 for k in range(i+1,i+1+H)],(d["c"][i+H]/e-1)*100))
def sim(g,tp,sl):
    w=l=0; tot=0.0
    for _,hs,ls,fin in g:
        res=None
        for hh,ll in zip(hs,ls):
            if ll<=-sl: res=-sl; l+=1; break
            if hh>=tp: res=tp; w+=1; break
        tot+= res if res is not None else fin
    return w/len(g)*100,l/len(g)*100,tot/len(g)
for lbl,g in (("전체 12종목",ev),("ADA만",[e for e in ev if e[0]=="ADA"])):
    print(f"\n== [속보] 투매후 시가회복 {lbl} {len(g)}건 (알람봉 종가 진입, 4시간 안 결과, 같은 봉에서 둘 다 닿으면 손절로 계산, %)")
    print(" 4시간 안 역방향 최대폭: " + " | ".join(f"-{x}% 이상 {sum(min(ls)<=-x for _,_,ls,_ in g)/len(g)*100:.1f}%" for x in (0.5,1,2,3,4.25)))
    print(" 4시간 안 상승 최대폭: " + " | ".join(f"+{x}% 이상 {sum(max(hs)>=x for _,hs,_,_ in g)/len(g)*100:.1f}%" for x in (0.3,0.5,0.8,1,1.5,2,3)))
    print(" 익절/손절 | 익절 먼저 | 손절 먼저 | 1건당 평균")
    rows=[]
    for tp in (0.3,0.5,0.8,1.0,1.5,2.0):
        for sl in (0.5,0.8,1.0,1.5,2.0):
            w,l,ev_=sim(g,tp,sl); rows.append((ev_,tp,sl,w,l))
            print(f"  +{tp}/-{sl} | {w:.0f}% | {l:.0f}% | {ev_:+.3f}")
    print(" 평균 상위 3:", ", ".join(f"+{tp}/-{sl}({e:+.3f})" for e,tp,sl,_,_ in sorted(rows,reverse=True)[:3]))
