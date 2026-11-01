from fractions import Fraction as F
from pathlib import Path
import json
checks={"reduced_tdc_residual":0,"debt_recurrence_vs_expansion":0,"degenerate_domain_cases":0}
for C in [F(1),F(10)]:
 for ltc in [F(0),F(1,2),F(4,5)]:
  for fee in [F(0),F(1,10)]:
   for carry in [F(0),F(1,5)]:
    q=ltc*(fee+carry);assert 0<=q<1
    T=C/(1-q);L=ltc*T;E=(1-ltc)*T
    assert T==C+fee*L+carry*L and T==L+E
    checks["reduced_tdc_residual"]+=1
# Synthetic convention ONLY: interest on opening principal capitalizes at explicit period rate.
# Compare iterative ledger to direct expansion, not a production day-count convention.
for opening in [F(0),F(5)]:
 for rate in [F(0),F(1,10)]:
  for flows in [[F(2),F(0),F(-1)],[F(0),F(3),F(1)]]:
   B=opening
   for d in flows:B=(1+rate)*B+d
   expanded=opening*(1+rate)**len(flows)+sum(d*(1+rate)**(len(flows)-i-1) for i,d in enumerate(flows))
   assert B==expanded
   checks["debt_recurrence_vs_expansion"]+=1
# Zero cost, singular no-solution, singular indeterminacy, inadmissible positive-cost branch.
assert F(0)/(1-F(1,2))==0;checks["degenerate_domain_cases"]+=1
assert all(T!=F(1)+T for T in [F(0),F(1),F(10)]);checks["degenerate_domain_cases"]+=1
assert all(T==F(0)+T for T in [F(0),F(1),F(10)]);checks["degenerate_domain_cases"]+=1
assert F(1)/(1-F(2))<0;checks["degenerate_domain_cases"]+=1
result={"status":"passed","arithmetic":"exact rational","checks":checks,"total":sum(checks.values()),"scope":"Reduced synthetic algebra and explicitly assumed opening-balance capitalization; not production finance, actual loan terms, independent audit, global convergence or recovery of historical references."}
Path(__file__).with_name("m5-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
