"""Separate source currency for a reference curve and an explicit candidate."""
from fractions import Fraction
from dataclasses import asdict
import copy,json
from miniuw_foundation.drafts import canonical
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_recovery_case import assemble_current_recovery_case,verify_current_recovery_case,CurrentRecoveryCaseRun
from demo_bounded_exit_sale import make_bounded_arguments,make_bounded_registry
from demo_bounded_sale_recovery import make_spec,make_registry
from demo_recovery_case_check import reprice

def raw(p):return canonical(p).encode()


def main():
    args=make_bounded_arguments();base=assemble_bounded_exit_sale(*args);sr=raw(make_spec(base));recovery=analyze_bounded_sale_recovery(args,base,sr)
    cases=[]
    for name in ['both-current','reference-domain-expired','candidate-bounds-expired','reference-review-pending','candidate-fee-changed']:
        price=Fraction('116.0803') if name!='candidate-fee-changed' else 400
        fee=Fraction(1,10) if name=='candidate-fee-changed' else None
        candidate,run=reprice(args,price,fee)
        check_args=(args,base,sr,recovery,candidate,run);check=check_recovery_case(*check_args)
        ref=make_registry(args,sr);cand=make_bounded_registry(candidate);at='2027-07-01T12:00:00Z'
        if name=='reference-domain-expired':next(r for r in ref['evidence']if r['requirement_id']=='/recovery/piecewise_spec')['valid_until']=at
        if name=='candidate-bounds-expired':next(r for r in cand['evidence']if r['requirement_id']=='/exit/cost_bounds')['valid_until']=at
        if name=='reference-review-pending':ref['evidence'][0]['review_status']='pending'
        rr=raw(ref);cr=raw(cand);r=evaluate_evidence_currency(rr,at);c=evaluate_evidence_currency(cr,at)
        result=assemble_current_recovery_case(check_args,check,rr,r,cr,c,at)
        verify_current_recovery_case(check_args,check,rr,r,cr,c,at,CurrentRecoveryCaseRun(**json.loads(json.dumps(asdict(result)))))
        p=result.payload;current=p['current_matched_case']
        cases.append(dict(case_id=name,evaluated_as_of_UTC=at,state=p['state'],blockers=p['blockers'],comparison_blockers=p['comparison_blockers'],
            reference_blockers=p['reference_blockers'],candidate_blockers=p['candidate_blockers'],reference_evidence_blockers=p['reference_evidence_blockers'],candidate_evidence_blockers=p['candidate_evidence_blockers'],
            exposed_net_cash_profit=None if current is None else current['comparison']['replayed_net_cash_profit'],
            comparison_run_sha256=check.sha256,current_run_sha256=result.sha256,reference_registry_source_sha256=p['reference_registry_source_sha256'],candidate_registry_source_sha256=p['candidate_registry_source_sha256'],
            reference_binding_count=p['reference_source_binding_count'],candidate_binding_count=p['candidate_source_binding_count'],report_serialization_roundtrip_replayed=True,decision='PENDING'))
    return dict(purpose='synthetic_current_reference_candidate_recovery_match',cases=cases,
        fixture_note='Separate synthetic bank NOI 2000 / closing without valuation fixture; original bank NOI 50/value 500 remain unchanged.',
        actual_review_or_contract_authenticated=False,live_monitor_enabled=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
