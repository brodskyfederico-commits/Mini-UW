"""Per-item money limits and their own explicit-time source gate; synthetic only."""
from dataclasses import asdict
from pathlib import Path
from fractions import Fraction
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale,verify_bounded_exit_sale,BoundedExitSaleRun
from miniuw_foundation.current_bounded_exit_output import (required_bounded_exit_sources,assemble_current_bounded_exit_output,
    verify_current_bounded_exit_output,CurrentBoundedExitOutputRun)
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from demo_evidence_currency import make_arguments
from demo_costed_exit_sale import cost_source

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def make_bounded_arguments(price=400,original_bank=False,conflict=False):
    e,nr,n,vr,v,cr,c,sr=make_arguments(original_bank)
    if not original_bank and price!=400:
        value_spec=json.loads(vr);value_spec['cap_rate']['value']=rational(Fraction(40,price))
        value_spec['cap_rate']['source_ref']='SYNTHETIC-explicit-price-point-cap-not-market-default'
        vr=raw(value_spec);v=produce_exit_value(nr,n,vr);cr=raw(cost_source(v));c=produce_sale_costs(cr)
    rules=[]
    for item in c.payload['cost_rows']:
        row=item['claim'];fee=row['cost_id']=='fee'
        def bound(enabled,amount,key):
            return dict(enabled=enabled,value=None if amount is None else rational(Fraction(amount)),currency=c.payload['currency'],as_of_date=c.payload['sale_date'],source_ref='SYNTHETIC-explicit-'+row['cost_id']+'-'+key)
        rules.append(dict(cost_id=row['cost_id'],rule_basis_ref='SYNTHETIC-per-item-money-clamp-not-contract-authentication',
            minimum=bound(fee,50 if fee and conflict else 25 if fee else None,'minimum'),maximum=bound(fee,40 if fee else None,'maximum')))
    bounds=dict(schema='miniuw.synthetic-per-item-sale-cost-bounds.v1',profile='SYNTHETIC-PER-ITEM-CLAMP-TO-EXPLICIT-MONEY-LIMITS-v1',
        cost_source_sha256=sha(cr),cost_run_sha256=c.sha256,rule_inventory_declared_complete=True,
        rule_inventory_basis_ref='SYNTHETIC-all-included-items-have-explicit-limit-status',rules=rules)
    br=raw(bounds);bounded=produce_bounded_sale_costs(cr,c,br)
    spec=json.loads(sr);spec.update(schema='miniuw.synthetic-bounded-exit-sale.v1',revision_id='SYNTHETIC-bounded-cost-demo-'+str(price),
        exit_spec_sha256=sha(vr),exit_run_sha256=v.sha256,cost_source_sha256=sha(cr),cost_run_sha256=c.sha256,
        bounds_source_sha256=sha(br),bounded_run_sha256=bounded.sha256)
    return(e,nr,n,vr,v,cr,c,br,bounded,raw(spec))


def make_bounded_registry(arguments):
    requirements=required_bounded_exit_sources(arguments)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=arguments[4].payload['context'],
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-complete-bounded-cost-transport-bindings-not-original-document-authentication',
        requirements=requirements,evidence=[dict(req,evidence_id='SYNTHETIC-bounded-evidence-'+str(i),
            issued_at='2027-06-01T00:00:00Z',valid_from='2027-07-01T00:00:00Z',valid_until='2027-08-01T00:00:00Z',
            review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,
            basis_ref='SYNTHETIC-provided-validity-and-status-not-authenticated-review')for i,req in enumerate(requirements)])


def main():
    cases=[]
    descriptions=[('floor-price-200',200,False,False),('floor-price-400',400,False,False),('cap-tie-price-800',800,False,False),
        ('cap-price-2000',2000,False,False),('minimum-maximum-conflict',400,False,True),('original-bank-blocked',500,True,False),
        ('only-bounds-expired',400,False,False),('only-bounds-review-pending',400,False,False)]
    for name,price,original,conflict in descriptions:
        args=make_bounded_arguments(price,original,conflict);base=assemble_bounded_exit_sale(*args)
        verify_bounded_exit_sale(*args,BoundedExitSaleRun(**json.loads(json.dumps(asdict(base)))))
        registry=make_bounded_registry(args)
        proof=next(r for r in registry['evidence']if r['requirement_id']=='/exit/cost_bounds')
        if name=='only-bounds-expired':proof['valid_until']='2027-07-01T12:00:00Z'
        if name=='only-bounds-review-pending':proof['review_status']='pending'
        rr=raw(registry);at='2027-07-01T12:00:00Z';currency=evaluate_evidence_currency(rr,at)
        current=assemble_current_bounded_exit_output(args,base,rr,currency,at)
        verify_current_bounded_exit_output(args,base,rr,currency,at,CurrentBoundedExitOutputRun(**json.loads(json.dumps(asdict(current)))))
        p=current.payload;summary=p['current_project_return_summary']
        cases.append(dict(case_id=name,independent_software_fixture=not original,exit_spec_json=args[3].decode(),original_cost_source_json=args[5].decode(),
            bounds_spec_json=args[7].decode(),bounded_exit_spec_json=args[9].decode(),
            gross_price=args[4].payload['candidate_value'],original_formula_cost=args[6].payload['total_closing_cost'],
            bounded_closing_cost=args[8].payload['total_closing_cost'],adjusted_cost_rows=args[8].payload['adjusted_costs'],
            calculation_state=base.payload['state'],calculation_blockers=base.payload['blockers'],bounds_blockers=base.payload['bounded_cost_blockers'],
            current_state=p['state'],current_blockers=p['blockers'],evidence_blockers=p['evidence_blockers'],
            current_project_net_cash_profit=None if summary is None else summary['net_cash_profit'],
            bounded_cost_run_sha256=args[8].sha256,bounded_exit_run_sha256=base.sha256,current_output_run_sha256=current.sha256,
            registry_source_sha256=sha(rr),registry_run_sha256=currency.sha256,required_source_bindings=len(p['required_source_bindings']),
            every_report_serialization_roundtrip_replayed=True,decision='PENDING'))
    return dict(purpose='synthetic_bounded_sale_costs_and_current_exit_output_demo',cases=cases,
        independent_fixture_note='Compatible branch uses separate declared bank NOI 2000, empty contribution target and closing without valuation claim. Original bank NOI 50 and valuation 500 remain unchanged.',
        explicit_fee_hypothesis='5% of gross sale price, minimum 25, maximum 40, plus separate fixed cost 10; synthetic software values only',
        all_limits_are_supplied_hypotheses_not_verified_contracts=True,global_affine_recovery_analysis_produced=False,
        personal_investor_return=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
