"""Explicit supplied price tests; no automatic investment input selection."""
import json
from fractions import Fraction
from miniuw_foundation.debt_service import rational
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.drafts import canonical
import hashlib
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def reprice(arguments,price,fee=None):
    args=list(arguments);spec=json.loads(args[3]);spec['cap_rate']['value']=rational(Fraction(40)/Fraction(price))
    spec['cap_rate']['source_ref']='SYNTHETIC-explicit-case-price-not-investment-target'
    args[3]=raw(spec);args[4]=produce_exit_value(args[1],args[2],args[3])
    source=json.loads(args[5]);source['gross_price'].update(value=args[4].payload['candidate_value'],source_ref='miniuw:synthetic-exit-value:'+args[4].sha256+'#/candidate_value')
    if fee is not None:source['costs'][1]['value']=rational(Fraction(fee))
    args[5]=raw(source);args[6]=produce_sale_costs(args[5]);bounds=json.loads(args[7])
    bounds.update(cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256)
    args[7]=raw(bounds);args[8]=produce_bounded_sale_costs(args[5],args[6],args[7]);spec=json.loads(args[9])
    spec.update(exit_spec_sha256=sha(args[3]),exit_run_sha256=args[4].sha256,cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256,bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256,revision_id='SYNTHETIC-explicit-case-'+str(price))
    args[9]=raw(spec);result=tuple(args)
    return result,assemble_bounded_exit_sale(*result)

from pathlib import Path
from dataclasses import asdict
from demo_bounded_exit_sale import make_bounded_arguments
from demo_bounded_sale_recovery import make_spec
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery
from miniuw_foundation.recovery_case_check import check_recovery_case,verify_recovery_case,RecoveryCaseCheckRun

def main():
    args=make_bounded_arguments();base=assemble_bounded_exit_sale(*args);sr=raw(make_spec(base));curve=analyze_bounded_sale_recovery(args,base,sr)
    cases=[]
    for price in [Fraction('115.0803'),Fraction('116.0803'),Fraction('117.0803'),Fraction(500),Fraction(800),Fraction(2000),Fraction(2001)]:
        candidate,run=reprice(args,price);report=check_recovery_case(args,base,sr,curve,candidate,run)
        verify_recovery_case(args,base,sr,curve,candidate,run,RecoveryCaseCheckRun(**json.loads(json.dumps(asdict(report)))))
        cases.append(dict(explicit_candidate_price=rational(price),candidate_exit_spec_json=candidate[3].decode(),candidate_cost_source_json=candidate[5].decode(),candidate_bounds_json=candidate[7].decode(),candidate_bridge_json=candidate[9].decode(),report=asdict(report),report_serialization_roundtrip_replayed=True))
    candidate,run=reprice(args,400,Fraction(1,10));report=check_recovery_case(args,base,sr,curve,candidate,run)
    cases.append(dict(label='changed-fee-needs-new-curve',report=asdict(report)))
    return dict(purpose='synthetic_supplied_case_full_replay_against_recovery_curve',recovery_spec_json=sr.decode(),reference_bounded_run_sha256=base.sha256,recovery_run_sha256=curve.sha256,cases=cases,
        prices_are_explicit_software_tests_not_automatically_selected_investment_targets=True,
        fixture_note='Separate synthetic bank NOI 2000 / no prior closing valuation fixture; original bank NOI 50/value 500 preserved.',decision='PENDING',production_authorized=False)

if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
