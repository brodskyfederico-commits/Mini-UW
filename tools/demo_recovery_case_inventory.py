"""Explicit price-case review; no default downside or best-case selection."""
from fractions import Fraction
from dataclasses import asdict
import json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case
from miniuw_foundation.current_recovery_case import assemble_current_recovery_case
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.recovery_case_inventory import RecoveryReviewCase,assemble_recovery_case_inventory,verify_recovery_case_inventory,RecoveryCaseInventoryRun
from demo_bounded_exit_sale import make_bounded_arguments,make_bounded_registry
from demo_bounded_sale_recovery import make_spec,make_registry
from demo_recovery_case_check import reprice

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    ref=make_bounded_arguments();base=assemble_bounded_exit_sale(*ref);sr=raw(make_spec(base));curve=analyze_bounded_sale_recovery(ref,base,sr)
    rr=raw(make_registry(ref,sr));at='2027-07-01T12:00:00Z';r=evaluate_evidence_currency(rr,at);proofs=[]
    for name,price in [('lower-price',100),('cash-recovery-point',Fraction('116.0803')),('higher-price',200)]:
        candidate,run=reprice(ref,price);args=(ref,base,sr,curve,candidate,run);check=check_recovery_case(*args)
        cr=raw(make_bounded_registry(candidate));c=evaluate_evidence_currency(cr,at)
        inputs=(args,check,rr,r,cr,c,at);proofs.append(RecoveryReviewCase(name,inputs,assemble_current_recovery_case(*inputs)))
    outputs=[]
    for name in ['all-current','one-candidate-evidence-expired']:
        cases=list(proofs)
        if name!='all-current':
            inputs=list(cases[1].arguments);registry=json.loads(inputs[4]);next(row for row in registry['evidence']if row['requirement_id']=='/exit/cost_bounds')['valid_until']=at
            inputs[4]=raw(registry);inputs[5]=evaluate_evidence_currency(inputs[4],at);inputs=tuple(inputs)
            cases[1]=RecoveryReviewCase(cases[1].case_id,inputs,assemble_current_recovery_case(*inputs))
        cases=tuple(cases)
        inventory=dict(schema='miniuw.synthetic-recovery-case-inventory.v1',as_of_UTC=at,reference_bounded_run_sha256=base.sha256,recovery_run_sha256=curve.sha256,
            reference_registry_source_sha256=sha(rr),inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-three-explicit-price-tests-not-market-scenarios',
            cases=[dict(case_id=c.case_id,current_case_run_sha256=c.run.sha256)for c in cases])
        ir=raw(inventory);result=assemble_recovery_case_inventory(cases,ir)
        verify_recovery_case_inventory(cases,ir,RecoveryCaseInventoryRun(**json.loads(json.dumps(asdict(result)))))
        p=result.payload;rows=[]
        for row in p['case_rows']:
            current=row['current_matched_case']
            rows.append(dict(case_id=row['case_id'],state=row['state'],current_case_run_sha256=row['current_case_run_sha256'],
                current_net_cash_profit=None if current is None else current['comparison']['replayed_net_cash_profit'],
                current_equity_multiple=None if current is None else current['comparison']['equity_multiple'],
                blockers=row['blockers'],candidate_evidence_blockers=row['candidate_evidence_blockers'],decision='PENDING'))
        outputs.append(dict(label=name,inventory_json=ir.decode(),inventory_run_sha256=result.sha256,state=p['state'],
            all_declared_cases_current_and_matched=p['all_declared_cases_current_and_matched'],blockers=p['blockers'],case_rows=rows,report_serialization_roundtrip_replayed=True,decision='PENDING'))
    return dict(purpose='synthetic_declared_price_case_inventory_review',reviews=outputs,reference_recovery_spec_json=sr.decode(),
        fixture_note='Separate bank NOI 2000/closing without valuation software fixture; original bank NOI 50/value 500 preserved.',
        no_downside_policy_or_approval_inferred=True,best_case_selected=False,personal_investor_return=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
