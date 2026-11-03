"""Exact conditional piecewise recovery and its additional domain-source gate."""
from dataclasses import asdict
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from miniuw_foundation.bounded_sale_recovery import analyze_bounded_sale_recovery,verify_bounded_sale_recovery,BoundedSaleRecoveryRun
from miniuw_foundation.current_bounded_recovery import (required_bounded_recovery_sources,assemble_current_bounded_recovery,
    verify_current_bounded_recovery,CurrentBoundedRecoveryRun)
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from demo_bounded_exit_sale import make_bounded_arguments

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def make_spec(base,upper=2000,budget=129):
    return dict(schema='miniuw.synthetic-piecewise-bounded-sale-recovery.v1',base_bounded_run_sha256=base.sha256,
        gross_price_domain=dict(lower=dict(numerator='0',denominator='1'),upper=dict(numerator=str(upper),denominator='1')),
        cost_profile_domain_basis_ref='SYNTHETIC-per-item-clamp-assumed-only-over-explicit-domain',
        other_sources_fixed_basis_ref='SYNTHETIC-fixed-dated-cash-debt-not-market-scenarios',segment_budget=budget)


def make_registry(arguments,spec_raw):
    requirements=required_bounded_recovery_sources(arguments,spec_raw)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=arguments[4].payload['context'],
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-complete-piecewise-domain-and-transport-bindings-not-authentication',
        requirements=requirements,evidence=[dict(req,evidence_id='SYNTHETIC-piecewise-evidence-'+str(i),
            issued_at='2027-06-01T00:00:00Z',valid_from='2027-07-01T00:00:00Z',valid_until='2027-08-01T00:00:00Z',
            review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,
            basis_ref='SYNTHETIC-explicit-time-status-not-professional-approval')for i,req in enumerate(requirements)])


def main():
    cases=[]
    descriptions=[('base-price-400',400,False),('repriced-base-200',200,False),('only-domain-expired',400,False),
        ('only-domain-review-pending',400,False),('domain-binding-missing',400,False),('changed-domain-with-stale-evidence',400,False),
        ('segment-budget-insufficient',400,False),('original-bank-blocked',500,True)]
    for name,price,original in descriptions:
        args=make_bounded_arguments(price,original);base=assemble_bounded_exit_sale(*args)
        spec=make_spec(base,budget=2 if name=='segment-budget-insufficient' else 129)
        sr=raw(spec);registry=make_registry(args,sr)
        if name=='changed-domain-with-stale-evidence':spec=make_spec(base,upper=1800);sr=raw(spec)
        if name=='domain-binding-missing':
            registry['requirements']=[r for r in registry['requirements']if r['requirement_id']!='/recovery/piecewise_spec']
            registry['evidence']=[r for r in registry['evidence']if r['requirement_id']!='/recovery/piecewise_spec']
        else:
            proof=next(r for r in registry['evidence']if r['requirement_id']=='/recovery/piecewise_spec')
            if name=='only-domain-expired':proof['valid_until']='2027-07-01T12:00:00Z'
            if name=='only-domain-review-pending':proof['review_status']='pending'
        analysis=analyze_bounded_sale_recovery(args,base,sr)
        verify_bounded_sale_recovery(args,base,sr,BoundedSaleRecoveryRun(**json.loads(json.dumps(asdict(analysis)))))
        rr=raw(registry);at='2027-07-01T12:00:00Z';currency=evaluate_evidence_currency(rr,at)
        current=assemble_current_bounded_recovery(args,base,sr,analysis,rr,currency,at)
        verify_current_bounded_recovery(args,base,sr,analysis,rr,currency,at,CurrentBoundedRecoveryRun(**json.loads(json.dumps(asdict(current)))))
        p=current.payload
        cases.append(dict(case_id=name,independent_software_fixture=not original,base_bounded_exit_run_sha256=base.sha256,
            exit_spec_json=args[3].decode(),cost_source_json=args[5].decode(),bounds_spec_json=args[7].decode(),bounded_exit_spec_json=args[9].decode(),
            recovery_spec_json=sr.decode(),recovery_run_sha256=analysis.sha256,current_recovery_run_sha256=current.sha256,
            registry_source_sha256=sha(rr),registry_run_sha256=currency.sha256,state=p['state'],blockers=p['blockers'],
            calculation_analysis_state=analysis.payload['state'],calculation_analysis=analysis.payload['analysis'],
            current_recovery_analysis=p['current_recovery_analysis'],recovery_blockers=p['recovery_blockers'],
            underlying_calculation_blockers=p['underlying_calculation_blockers'],evidence_blockers=p['evidence_blockers'],
            source_binding_count=len(p['required_source_bindings']),every_report_serialization_roundtrip_replayed=True,decision='PENDING'))
    a,b=cases[:2]
    for key in ['segments','recovering_price_intervals','recovering_exit_cap_intervals','zero_cash_profit_price_intervals']:
        assert a['calculation_analysis'][key]==b['calculation_analysis'][key]
    return dict(purpose='synthetic_piecewise_bounded_cost_cash_recovery_and_current_domain_gate',cases=cases,
        same_recovery_set_from_two_fully_replayed_price_cost_return_bases=True,
        fixture_note='Compatible separate software fixture has bank NOI 2000 and no closing valuation claim. Original bank NOI 50/value 500 and all their blockers remain unchanged.',
        synthetic_charge_hypothesis='fixed 10 plus 5% gross with monetary minimum 25 / maximum 40, fixed other cash/debt/dates and explicit price domain [0,2000]',
        new_scenario_or_investor_ledger_generated=False,investment_criterion_adopted=False,personal_investor_return=None,
        final_economic_capital_loss=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
