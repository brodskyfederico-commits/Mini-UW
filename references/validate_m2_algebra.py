from fractions import Fraction as F
import json
from pathlib import Path
checks={"tax_equation":0,"breakeven_equivalence":0,"rent_dimensions":0}
# Synthetic abstract amounts and coefficients, not underwriting inputs or defaults.
for A in map(F,[-10,0,4,12]):
 for floor in map(F,[0,2,6]):
  for k in [F(0),F(1,4),F(2)]:
   N=min(A-floor,A/(1+k))
   assert N==A-max(floor,k*N)
   checks["tax_equation"]+=1
for slope in map(F,[-3,0,5]):
 for intercept in map(F,[-2,4]):
  for floor in map(F,[0,2]):
   for k in [F(0),F(1,2)]:
    for ds in map(F,[0,3]):
     for q in [F(0),F(1,3),F(1)]:
      A=slope*q+intercept;N=min(A-floor,A/(1+k))
      assert (N>=ds)==(A>=ds+max(floor,k*ds))
      checks["breakeven_equivalence"]+=1
for n in [0,1,3]:
 for area in [F(10),F(25)]:
  per_sf=F(7,3);per_unit=per_sf*area
  assert n*per_unit==n*area*per_sf
  assert 12*n*per_unit==n*area*(12*per_sf)
  checks["rent_dimensions"]+=1
result={"status":"passed","arithmetic":"exact rational","checks":checks,"total":sum(checks.values()),"scope":"Isolated synthetic algebra; not approved tax policy, recovered product, historical reference reproduction, independent audit or deal validation."}
Path(__file__).with_name("m2-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
