from fractions import Fraction as F
from pathlib import Path
import json
counts={"driver_units":0,"reduced_price_constraints":0,"discrete_quote_and_next":0,"domain_boundaries":0,"nonmonotone_example":0,"missing_inputs":0}
def transform(base,value,unit):
 if base is None or value is None:raise ValueError("missing")
 if unit=="relative":return base*(1+value)
 if unit=="points":return base+value/100
 if unit=="bps":return base+value/10000
 if unit=="months":return base+value
 if unit=="replace":return value
 raise ValueError("unknown operator")
assert transform(F(1,20),F(10),"points")==F(3,20)
assert transform(F(1,20),F(1,10),"relative")==F(11,200)
assert transform(F(1,20),F(100),"bps")==F(3,50)
assert transform(F(6),F(2),"months")==8
assert transform(F(6),F(0),"replace")==0
assert transform(F(6),F(0),"relative")==6
counts["driver_units"]+=6
# Abstract synthetic reduced objective branch, not underwriting parameters/defaults.
for a in [F(1),F(2)]:
 for b in [F(1),F(2)]:
  for N in [F(1),F(3)]:
   for y in [F(1,4),F(1,2)]:
    H=F(10);target=F(1,4);cap_y=(N/y-a)/b;cap_r=(H/(1+target)-a)/b
    bound=min(F(10),cap_y,cap_r)
    for P in [F(0),F(1),F(2),F(10)]:
     C=a+b*P
     exact=(N/C>=y and H/C-1>=target)
     assert exact==(P<=min(cap_y,cap_r))
     counts["reduced_price_constraints"]+=1
    if bound>=0:
     step=F(1,2);quote=(bound//step)*step
     assert 0<=quote<=bound and quote+step>bound
     assert N/(a+b*quote)>=y and H/(a+b*quote)-1>=target
     next_price=quote+step
     assert next_price>10 or N/(a+b*next_price)<y or H/(a+b*next_price)-1<target
     counts["discrete_quote_and_next"]+=1
# Closed [0,1] attains 1; open [0,1) has supremum 1 but no maximum.
assert F(1)<=1;counts["domain_boundaries"]+=1
for n in [2,3,10]:
 P=1-F(1,n);larger=(P+1)/2
 assert 0<=P<larger<1
 counts["domain_boundaries"]+=1
assert min(F(-1),F(2))<0 # empty under domain P>=0 and upper bound -1
counts["domain_boundaries"]+=1
for P in [F(0),F(1),F(2),F(3),F(4)]:
 feasible=(P-1)*(P-3)>=0
 assert feasible==(P<=1 or P>=3)
 counts["nonmonotone_example"]+=1
for base,value,unit in [(None,F(0),"relative"),(F(1),None,"bps"),(F(1),F(0),"unknown")]:
 try:transform(base,value,unit)
 except ValueError:counts["missing_inputs"]+=1
 else:raise AssertionError("missing/unknown operator accepted")
result={"status":"passed","arithmetic":"exact rational","checks":counts,"total":sum(counts.values()),"scope":"Isolated synthetic transformations, two-objective affine-cost/single-return branch, discrete/open domain examples and nonmonotone counterexample. Not production scenarios, global price solver, approved RLV, general IRR or independent audit."}
Path(__file__).with_name("m8-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
