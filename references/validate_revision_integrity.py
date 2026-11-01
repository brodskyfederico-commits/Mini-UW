"""Pure synthetic dependency/version reference. No database, authentication or publication."""
from dataclasses import dataclass,FrozenInstanceError
from pathlib import Path
import json

def build_graph():
 g={"source.program":(),"source.shared_fact":()}
 for s in ["base","down"]:
  g[s+".inputs"]=("source.program","source.shared_fact")
  g[s+".bank"]=()
  g[s+".criteria"]=()
  g[s+".operation"]=(s+".inputs",)
  g[s+".budget"]=(s+".inputs",)
  g[s+".calendar"]=(s+".inputs",)
  # The financial iteration is one explicitly unresolved calculation block, not a fake acyclic solver.
  g[s+".finance_closed"]=(s+".budget",s+".calendar",s+".bank")
  g[s+".refi"]=(s+".operation",s+".finance_closed",s+".bank")
  g[s+".hold"]=(s+".operation",s+".refi")
  g[s+".price"]=(s+".inputs",s+".hold",s+".criteria")
  g[s+".compare"]=(s+".hold",s+".criteria")
 g["decision"]=("base.compare","down.compare","base.price","down.price")
 g["pdf_candidate"]=("decision",)
 g["render_audit"]=("pdf_candidate",)
 return g

def ancestors(g,target):
 seen=set();active=set()
 def visit(n):
  if n not in g:raise ValueError("unknown dependency")
  if n in active:raise ValueError("cycle needs explicit financial block")
  if n in seen:return
  active.add(n)
  for d in g[n]:visit(d)
  active.remove(n);seen.add(n)
 visit(target);return seen

def invalidated(g,changed):
 if any(n not in g for n in changed):raise ValueError("unknown changed node")
 return {n for n in g if ancestors(g,n).intersection(changed)}

@dataclass(frozen=True)
class Candidate:
 context:tuple
 target:str
 closure_versions:tuple

def freeze_candidate(g,target,context,versions):
 if len(context)!=3 or any(not x for x in context):raise ValueError("deal/scenario/run absent")
 closure=ancestors(g,target)
 if any(versions.get(n) is None for n in closure):raise ValueError("missing revision")
 return Candidate(tuple(context),target,tuple(sorted((n,versions[n]) for n in closure)))

def reusable(candidate,expected_context,current):
 return (candidate.context==tuple(expected_context) and all(current.get(n)==v for n,v in candidate.closure_versions))

def exact_input_slots(required,actual):
 # Inputs are explicit node IDs, not an untyped positional list. No fallback from Base.
 return set(required)==set(actual) and all(actual[n] is not None for n in required)

checks=[]
def check(name,result):
 assert result,name;checks.append(name)
g=build_graph();current={n:"revision-1" for n in g};frozen=dict(current)
criteria=invalidated(g,{"base.criteria"})
check("criteria_invalidate_compare_price_and_report",{"base.criteria","base.compare","base.price","decision","pdf_candidate","render_audit"}==criteria)
check("criteria_preserve_independent_cash",not criteria.intersection({"base.operation","base.finance_closed","base.refi","base.hold"}))
check("criteria_do_not_invalidate_other_scenario",not any(n.startswith("down.") for n in criteria))
base_change=invalidated(g,{"base.inputs"})
check("input_changes_flow_to_finance_returns_price",{"base.operation","base.budget","base.calendar","base.finance_closed","base.refi","base.hold","base.price","base.compare","decision","pdf_candidate","render_audit"}.issubset(base_change))
check("scenario_input_change_isolated",not any(n.startswith("down.") for n in base_change))
shared=invalidated(g,{"source.shared_fact"})
check("explicit_shared_fact_invalidates_both",{"base.inputs","down.inputs","base.hold","down.hold","pdf_candidate"}.issubset(shared))
bank=invalidated(g,{"base.bank"})
check("bank_change_invalidates_debt_and_returns",{"base.finance_closed","base.refi","base.hold","base.price","base.compare"}.issubset(bank))
check("bank_change_preserves_independent_operation",not bank.intersection({"base.operation","base.budget","base.calendar"}))
context=("SYNTHETIC-DEAL","combined","run-A")
c=freeze_candidate(g,"pdf_candidate",context,current)
check("same_revision_reusable",reusable(c,context,current))
for source in ["base.criteria","base.bank","base.inputs","source.program","down.criteria"]:
 changed=dict(current);changed[source]="revision-2"
 check("stale_ancestor_rejected_"+source,not reusable(c,context,changed))
check("different_deal_rejected",not reusable(c,("OTHER-DEAL","combined","run-A"),current))
check("different_run_rejected",not reusable(c,("SYNTHETIC-DEAL","combined","run-B"),current))
check("different_scenario_context_rejected",not reusable(c,("SYNTHETIC-DEAL","base","run-A"),current))
try:c.target="decision"
except FrozenInstanceError:checks.append("frozen_record_rejects_mutation")
else:raise AssertionError("mutable snapshot")
check("source_map_unchanged_by_reference",current==frozen)
check("base_slot_explicitly_filled",exact_input_slots(["base.inputs"],{"base.inputs":"revision-1"}))
check("downside_cannot_read_base_slot",not exact_input_slots(["down.inputs"],{"base.inputs":"revision-1"}))
check("missing_slot_no_default",not exact_input_slots(["down.inputs"],{}))
check("none_slot_not_explicit_zero",not exact_input_slots(["down.inputs"],{"down.inputs":None}))
check("explicit_zero_not_missing",exact_input_slots(["down.inputs"],{"down.inputs":0}))
for name,graph,target in [("unknown_dependency",{"a":("missing",)},"a"),("unclosed_cycle",{"a":("b",),"b":("a",)},"a")]:
 try:ancestors(graph,target)
 except ValueError:checks.append(name+"_rejected")
 else:raise AssertionError("invalid graph accepted")
missing=dict(current);missing["source.program"]=None
try:freeze_candidate(g,"pdf_candidate",context,missing)
except ValueError:checks.append("missing_revision_rejected")
else:raise AssertionError("missing version accepted")
# A successful comparison is only an instant-in-time observation; no atomic publication is implemented.
head=dict(current);check("pre_edit_candidate_matches",reusable(c,context,head));head["base.inputs"]="revision-2"
check("subsequent_edit_invalidates_prior_observation",not reusable(c,context,head))
result={"status":"passed","fixture":"SYNTHETIC-DEPENDENCY-REFERENCE-01","checks":checks,"total":len(checks),"scope":"Pure in-memory synthetic graph, snapshot identity and input-slot checks. Not actual financial dependency discovery, database atomicity, race-condition proof, authentication, persistent review or production integration."}
Path(__file__).with_name("revision-integrity-validation.json").write_text(json.dumps(result,indent=2)+"\n")
Path(__file__).with_name("dependency-graph-reference.json").write_text(json.dumps({"scope":"Illustrative node graph; financial iteration is a single explicitly unresolved block.","dependencies":g},indent=2)+"\n")
print(json.dumps(result))
