from fractions import Fraction as F
from pathlib import Path
import json
counts={"payment_vs_present_value":0,"balance_recurrence_vs_closed_form":0,"sizing_constraints_and_ties":0,"cash_conservation":0,"reserve_delta":0,"invalid_domain":0}
def payment_unit(i,n):
 if i is None or n is None:raise ValueError("missing")
 if i<0 or not isinstance(n,int) or n<=0:raise ValueError("domain")
 return F(1,n) if i==0 else i/(1-(1+i)**(-n))
for i in [F(0),F(1,100),F(1,10)]:
 for n in [1,3,6]:
  a=payment_unit(i,n)
  assert sum(a/(1+i)**k for k in range(1,n+1))==1
  counts["payment_vs_present_value"]+=1
  for L in [F(0),F(7)]:
   B=L
   for k in range(n+1):
    closed=L*(1+i)**k-a*L*sum((1+i)**j for j in range(k))
    assert B==closed
    if k==n:assert B==0
    if L>0 and k<n:assert B>0
    counts["balance_recurrence_vs_closed_form"]+=1
    B=B*(1+i)-a*L
for V in [F(10),F(20)]:
 for ltv in [F(0),F(1,2)]:
  for N in [F(0),F(3),F(5)]:
   d=F(3,2);K=F(1,5);lv=ltv*V;ld=N/(d*K);L=min(lv,ld)
   assert L<=lv and d*K*L<=N
   active=[name for name,value in [("LTV",lv),("DSCR",ld)] if value==L]
   assert len(active)==(2 if lv==ld else 1)
   counts["sizing_constraints_and_ties"]+=1
for L in [F(0),F(12)]:
 for payoff in [F(0),F(10),F(20)]:
  for reserve in [F(0),F(3)]:
   fee=L/F(10);released=F(1);free=F(2);sources=L+released+free;uses=payoff+fee+reserve
   Z=sources-uses;D=max(Z,0);A=max(-Z,0)
   assert sources+A==uses+D and D-A==Z and D*A==0
   counts["cash_conservation"]+=1
   extra=F(2);Z2=sources-(uses+extra)
   assert Z2==Z-extra
   counts["reserve_delta"]+=1
for i,n in [(None,3),(F(0),None),(F(-1,10),3),(F(0),0),(F(0),F(3,2))]:
 try:payment_unit(i,n)
 except ValueError:counts["invalid_domain"]+=1
 else:raise AssertionError("invalid case accepted")
result={"status":"passed","arithmetic":"exact rational","checks":counts,"total":sum(counts.values()),"scope":"Synthetic regular end-period fixed-rate amortization, isolated loan sizing and unconstrained distributable cash. Not approved bank terms, independent audit, stable floating-point implementation, production or real-deal validation."}
Path(__file__).with_name("m6-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
