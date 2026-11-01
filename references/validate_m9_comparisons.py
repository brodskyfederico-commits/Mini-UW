from fractions import Fraction as F
from pathlib import Path
import json,itertools
counts={"explicit_comparators":0,"missing_band_conflict":0,"unrounded_boundary":0,"hypothetical_aggregation":0}
def compare(v,t,op):
 if v is None or t is None:return None
 if op==">=":return v>=t
 if op==">":return v>t
 if op=="<=":return v<=t
 if op=="<":return v<t
 raise ValueError("operator missing/unknown")
for op,expected in [(">=",[False,True,True]),(">",[False,False,True]),("<=",[True,True,False]),("<",[True,False,False])]:
 for v,e in zip([F(0),F(1),F(2)],expected):
  assert compare(v,F(1),op)==e;counts["explicit_comparators"]+=1
def band(v,p,f):
 a=compare(v,p,">=");b=compare(v,f,"<")
 if a is None or b is None:return "PENDING"
 if a and b:return "CONFLICT"
 return "PASS_CONDITION" if a else "FAIL_CONDITION" if b else "BAND"
for v,p,f,expected in [(None,F(2),F(1),"PENDING"),(F(1),None,F(0),"PENDING"),(F(1),F(2),None,"PENDING"),(F(3,2),F(2),F(1),"BAND"),(F(2),F(2),F(1),"PASS_CONDITION"),(F(0),F(2),F(1),"FAIL_CONDITION"),(F(3,2),F(1),F(2),"CONFLICT")]:
 assert band(v,p,f)==expected;counts["missing_band_conflict"]+=1
assert round(float(F(999,1000)),2)==round(float(F(1)),2)
assert compare(F(999,1000),F(1),">=") is False
counts["unrounded_boundary"]+=1
# Supplied hypothetical aggregation policy ONLY; no house rule or authenticated approval.
def hypothetical(states,rule_supplied):
 if not rule_supplied or any(s in ["PENDING","BAND","CONFLICT"] for s in states):return "PENDING"
 if not states:return "PENDING"
 return "PASS" if all(s=="PASS_CONDITION" for s in states) else "FAIL"
labels=["PASS_CONDITION","FAIL_CONDITION","PENDING","BAND","CONFLICT"]
for pair in itertools.product(labels,repeat=2):
 result=hypothetical(pair,True)
 if any(s in ["PENDING","BAND","CONFLICT"] for s in pair):assert result=="PENDING"
 elif pair==("PASS_CONDITION","PASS_CONDITION"):assert result=="PASS"
 else:assert result=="FAIL"
 assert hypothetical(pair,False)=="PENDING"
 counts["hypothetical_aggregation"]+=1
assert hypothetical([],True)=="PENDING";counts["hypothetical_aggregation"]+=1
result={"status":"passed","arithmetic":"exact rational except illustrative display rounding","checks":counts,"total":sum(counts.values()),"scope":"Isolated comparator truth tables and hypothetical explicit aggregation; not activated house decision policy, authentication, transactional publication, independent audit or production."}
Path(__file__).with_name("m9-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
