"""Declared fixed/percentage sale charges; unknown tax blocks full cost export."""
from dataclasses import asdict
from pathlib import Path
import json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale,verify_costed_exit_sale,CostedExitSaleRun
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from demo_project_sale_revisions import load_evidence

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def cost_source(value_run,unresolved_tax=False):
    p=value_run.payload
    source=dict(schema='miniuw.synthetic-fixed-and-gross-percent-sale-costs.v1',context=p['context'],currency=p['currency'],sale_date=p['valuation_date'],
        gross_price=dict(value=p['candidate_value'],currency=p['currency'],as_of_date=p['valuation_date'],basis='projected_gross_sale_price',source_ref='miniuw:synthetic-exit-value:'+value_run.sha256+'#/candidate_value'),
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-selected-cost-inventory-not-real-completeness',nonoverlap_basis_ref='SYNTHETIC-no-overlap-with-each-other-or-bank-payoffs',costs=[])
    for identity,kind,value,unit in [('fixed','fixed',{'numerator':'10','denominator':'1'},'currency'),('fee','percent_of_gross',{'numerator':'1','denominator':'20'},'fraction_of_gross_price')]:
        source['costs'].append(dict(cost_id=identity,classification='transaction_cost',kind=kind,applicability='included',applicability_basis_ref='SYNTHETIC-explicit-charge-not-adopted',value=value,unit=unit,currency=p['currency'],as_of_date=p['valuation_date'],source_ref='SYNTHETIC-explicit-cost:'+identity))
    if unresolved_tax:
        source['costs'].append(dict(cost_id='tax-unresolved',classification='tax',kind='fixed',applicability='unresolved',applicability_basis_ref=None,value=None,unit='currency',currency=p['currency'],as_of_date=p['valuation_date'],source_ref='SYNTHETIC-pending-tax-scope-not-zero'))
    return source


def main():
    root=Path(__file__).resolve().parents[1]
    nr=(root/'templates/synthetic-exit-forward-noi.json').read_bytes();n=produce_operating_noi(nr)
    initial=json.loads((root/'templates/synthetic-exit-value-spec.json').read_bytes());cases=[]
    for name,num,den,independent,missing_tax in [('original-bank-blocked',2,25,False,False),('price-800',1,20,True,False),('price-400',1,10,True,False),('price-200',1,5,True,False),('tax-pending',1,10,True,True)]:
        e=load_evidence(independent,'synthetic-exit-test-sale-closing.json'if independent else None)
        spec=json.loads(canonical(initial));spec['cap_rate']['value']={'numerator':str(num),'denominator':str(den)}
        vr=raw(spec);v=produce_exit_value(nr,n,vr);cr=raw(cost_source(v,missing_tax));c=produce_sale_costs(cr)
        b=dict(schema='miniuw.synthetic-costed-exit-sale.v1',revision_id='SYNTHETIC-costed-'+name,
            base_evidence_sha256=evidence_fingerprint(e),exit_spec_sha256=sha(vr),exit_run_sha256=v.sha256,
            sale_node_id='SYNTHETIC-project-sale',sale_at_value_hypothesis_ref='SYNTHETIC-explicit-sale-at-value-not-real-collection',
            unchanged_other_sources_basis_ref='SYNTHETIC-other-cash-debt-dates-fixed',equity_funding_assumption_ref=None,
            cost_source_sha256=sha(cr),cost_run_sha256=c.sha256)
        br=raw(b);run=assemble_costed_exit_sale(e,nr,n,vr,v,cr,c,br)
        verify_costed_exit_sale(e,nr,n,vr,v,cr,c,br,CostedExitSaleRun(**json.loads(json.dumps(asdict(run)))))
        investor=None
        if run.payload['state']=='compiled_synthetic':investor=run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
        cases.append(dict(case_id=name,independent_software_fixture=independent,exit_spec_json=vr.decode(),cost_source_json=cr.decode(),bridge_spec_json=br.decode(),
            candidate_value=v.payload['candidate_value'],computed_closing_cost=c.payload['total_closing_cost'],state=run.payload['state'],blockers=run.payload['blockers'],cost_blockers=c.payload['blockers'],
            cost_run_sha256=c.sha256,bridge_run_sha256=run.sha256,net_cash_profit=None if investor is None else investor['net_cash_profit'],equity_multiple=None if investor is None else investor['equity_multiple'],
            upstream_story_blockers=None if investor is None else investor['story_blockers'],report_serialization_roundtrip_replayed=True,decision='PENDING'))
    return dict(purpose='synthetic_price_dependent_sale_cost_to_guarded_returns',cases=cases,
        separate_fixture_note='Compatible software branch uses separate bank NOI 2000, explicit empty sale contribution slot and separate closing source without valuation claim. Original bank NOI 50, valuation 500 and blocker remain unchanged.',
        rates_are_explicit_synthetic_hypotheses_not_market_or_tax_defaults=True,tax_rule_verified=False,
        personal_investor_return=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
