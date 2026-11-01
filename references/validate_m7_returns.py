from fractions import Fraction as F
from pathlib import Path
import json
counts={"exit_cash_conservation":0,"gross_vs_net_ledger":0,"equity_multiple":0,"irr_factored_cases":0,"regular_annualization":0,"undefined_and_invalid_cases":0}
def multiple(A,D):
 if any(x is None for x in A+D):raise ValueError("missing")
 if any(x<0 for x in A+D):raise ValueError("gross sign")
 return None if sum(A)==0 else sum(D)/sum(A)
def npv_q(flows,q):return sum(F(c)*q**i for i,c in enumerate(flows))
for price in [F(0),F(10),F(30)]:
 for fee in [F(0),F(1,10)]:
  for debt in [F(0),F(12)]:
   for reserve in [F(0),F(2)]:
    sources=price+reserve;uses=price*fee+debt;Z=sources-uses
    D=max(Z,0);A=max(-Z,0)
    assert sources+A==uses+D and D-A==Z and D*A==0
    counts["exit_cash_conservation"]+=1
# Identical net monthly flows, distinct economically evidenced gross ledgers and EM.
A1=[F(100),F(10)];D1=[F(0),F(20)]
A2=[F(100),F(30)];D2=[F(0),F(40)]
assert [d-a for a,d in zip(A1,D1)]==[d-a for a,d in zip(A2,D2)]
assert multiple(A1,D1)!=multiple(A2,D2);counts["gross_vs_net_ledger"]+=1
for A,D in [([F(5)],[F(0)]),([F(5),F(2)],[F(1),F(9)]),([F(3)],[F(3)])]:
 em=multiple(A,D);assert em*sum(A)==sum(D);counts["equity_multiple"]+=1
# Explicit polynomial factors establish properties of THESE examples, not a general root solver.
for q in [F(1,2),F(5,6),F(10,11),F(1),F(3,2)]:
 assert npv_q([-100,230,-132],q)==-100*(1-F(11,10)*q)*(1-F(6,5)*q)
 assert npv_q([-1,3,-3,1],q)==(q-1)**3
 assert npv_q([-1,2,-1],q)==-(q-1)**2
 assert npv_q([1,-1,1],q)==(q-F(1,2))**2+F(3,4)>0
 counts["irr_factored_cases"]+=4
for rate in [F(1,10),F(1,5)]:
 assert npv_q([-100,230,-132],1/(1+rate))==0
 counts["irr_factored_cases"]+=1
assert npv_q([-1,3,-3,1],F(1))==0
assert npv_q([-1,2,-1],F(1))==0 and npv_q([-1,2,-1],F(1,2))<0 and npv_q([-1,2,-1],F(3,2))<0
counts["irr_factored_cases"]+=2
for rate in [F(-1,10),F(0),F(1,100)]:
 for periods in [1,2,12]:
  equivalent=(1+rate)**periods-1
  capital=F(7)
  for _ in range(periods):capital*=1+rate
  assert capital==7*(1+equivalent)
  counts["regular_annualization"]+=1
assert multiple([F(0)],[F(2)]) is None;counts["undefined_and_invalid_cases"]+=1
for q in [F(1,2),F(1),F(2)]:assert npv_q([0,0,0],q)==0
counts["undefined_and_invalid_cases"]+=1
for A,D in [([None],[F(0)]),([F(-1)],[F(0)])]:
 try:multiple(A,D)
 except ValueError:counts["undefined_and_invalid_cases"]+=1
 else:raise AssertionError("invalid gross ledger accepted")
result={"status":"passed","arithmetic":"exact rational","checks":counts,"total":sum(counts.values()),"scope":"Synthetic exit cash, gross equity ledgers, regular compounding and factored IRR examples only. No general root-isolation solver, XIRR, real-deal validation, independent audit, production or recovery of historical application."}
Path(__file__).with_name("m7-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
