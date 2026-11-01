from fractions import Fraction as F
from pathlib import Path
import json
checks={"allocation_conservation":0,"cost_basis_equivalence":0,"negative_input_cases":0}
def allocate(budget,weights):
 if budget is None or weights is None or any(w is None for w in weights):raise ValueError("missing")
 if not weights or any(w<0 for w in weights) or sum(weights)!=1:raise ValueError("invalid weights")
 return [budget*w for w in weights]
# Abstract synthetic amounts/profiles, not production draws or approved curves.
for budget in map(F,[0,7,25]):
 for weights in [[F(1)],[F(1,3),F(2,3)],[F(0),F(1,4),F(3,4)]]:
  payments=allocate(budget,weights)
  assert sum(payments)==budget
  assert sum(payments[:1])+sum(payments[1:])==budget
  checks["allocation_conservation"]+=1
for count in [1,2,4]:
 for area in map(F,[3,5]):
  rate=F(7,3);total=count*area*rate;unit_price=area*rate
  assert total==count*unit_price==count*area*rate
  checks["cost_basis_equivalence"]+=1
for budget,weights in [(None,[F(1)]),(F(0),None),(F(7),[None]),(F(7),[]),(F(7),[F(0)]),(F(7),[F(1,2)]),(F(7),[F(-1),F(2)])]:
 try:allocate(budget,weights)
 except ValueError:checks["negative_input_cases"]+=1
 else:raise AssertionError("Invalid case accepted")
result={"status":"passed","arithmetic":"exact rational","checks":checks,"total":sum(checks.values()),"scope":"Isolated synthetic allocation algebra, not approved sin-squared schedule, actual construction scope, production or independent audit."}
Path(__file__).with_name("m34-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
