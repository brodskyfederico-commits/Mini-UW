"""Create an internal readable review from independently replayed synthetic cases."""
from fractions import Fraction
from pathlib import Path
import json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case
from miniuw_foundation.current_recovery_case import assemble_current_recovery_case
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.recovery_case_inventory import RecoveryReviewCase,assemble_recovery_case_inventory
from miniuw_foundation.investor_review import render_investor_review
from demo_bounded_exit_sale import make_bounded_arguments,make_bounded_registry
from demo_bounded_sale_recovery import make_spec,make_registry
from demo_recovery_case_check import reprice

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    ref=make_bounded_arguments();base=assemble_bounded_exit_sale(*ref);sr=raw(make_spec(base));curve=analyze_bounded_sale_recovery(ref,base,sr)
    rr=raw(make_registry(ref,sr));at='2027-07-01T12:00:00Z';r=evaluate_evidence_currency(rr,at);cases=[]
    for name,price,expired in [('Caso sintético: precio 200',200,False),('Caso sintético: evidencia vencida',100,True)]:
        candidate,run=reprice(ref,price);check_args=(ref,base,sr,curve,candidate,run);check=check_recovery_case(*check_args)
        registry=make_bounded_registry(candidate)
        if expired:next(e for e in registry['evidence']if e['requirement_id']=='/exit/cost_bounds')['valid_until']=at
        cr=raw(registry);c=evaluate_evidence_currency(cr,at);inputs=(check_args,check,rr,r,cr,c,at)
        cases.append(RecoveryReviewCase(name,inputs,assemble_current_recovery_case(*inputs)))
    cases=tuple(cases);inventory=dict(schema='miniuw.synthetic-recovery-case-inventory.v1',as_of_UTC=at,reference_bounded_run_sha256=base.sha256,
        recovery_run_sha256=curve.sha256,reference_registry_source_sha256=sha(rr),inventory_declared_complete=True,
        inventory_basis_ref='SYNTHETIC-explicit-internal-review-not-market-scenarios',cases=[dict(case_id=c.case_id,current_case_run_sha256=c.run.sha256)for c in cases])
    ir=raw(inventory);run=assemble_recovery_case_inventory(cases,ir);report=render_investor_review(cases,ir,run)
    root=Path(__file__).resolve().parents[1]
    (root/'docs/review/MiniUW_Revision_Interna_Retorno_T56.md').write_text(report.payload['markdown'])
    return dict(purpose='internal_synthetic_investor_story_review_demo',inventory_json=ir.decode(),inventory_run_sha256=run.sha256,
        report_run_sha256=report.sha256,markdown_sha256=report.payload['markdown_sha256'],
        report_path='docs/review/MiniUW_Revision_Interna_Retorno_T56.md',
        fixture_note='Separate software bank NOI 2000/no prior closing valuation; original bank NOI 50/value 500 remain unchanged.',
        personal_investor_return=None,external_decision_pdf_produced=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
