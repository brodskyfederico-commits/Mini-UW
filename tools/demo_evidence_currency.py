"""Explicit-time source currency gate; no real review, renewal authority or monitor."""
from dataclasses import asdict
from pathlib import Path
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_exit_output import (required_exit_sources,assemble_current_exit_output,
                                                  verify_current_exit_output,CurrentExitOutputRun)
from demo_project_sale_revisions import load_evidence
from demo_costed_exit_sale import cost_source

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def make_arguments(original_bank=False):
    root=Path(__file__).resolve().parents[1]
    e=load_evidence(not original_bank,None if original_bank else 'synthetic-exit-test-sale-closing.json')
    nr=(root/'templates/synthetic-exit-forward-noi.json').read_bytes();n=produce_operating_noi(nr)
    spec=json.loads((root/'templates/synthetic-exit-value-spec.json').read_bytes())
    if original_bank:spec['cap_rate']['value']={'numerator':'2','denominator':'25'}
    vr=raw(spec);v=produce_exit_value(nr,n,vr);cr=raw(cost_source(v));c=produce_sale_costs(cr)
    b=dict(schema='miniuw.synthetic-costed-exit-sale.v1',revision_id='SYNTHETIC-source-currency-demo',
        base_evidence_sha256=evidence_fingerprint(e),exit_spec_sha256=sha(vr),exit_run_sha256=v.sha256,
        sale_node_id='SYNTHETIC-project-sale',sale_at_value_hypothesis_ref='SYNTHETIC-explicit-sale-hypothesis-not-actual-receipt',
        unchanged_other_sources_basis_ref='SYNTHETIC-other-sources-frozen',equity_funding_assumption_ref=None,
        cost_source_sha256=sha(cr),cost_run_sha256=c.sha256)
    return(e,nr,n,vr,v,cr,c,raw(b))


def make_registry(arguments):
    requirements=required_exit_sources(arguments)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=arguments[4].payload['context'],
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-complete-transport-bindings-not-original-document-authentication',
        requirements=requirements,evidence=[dict(req,evidence_id='SYNTHETIC-evidence-'+str(i),
            issued_at='2027-06-01T00:00:00Z',valid_from='2027-07-01T00:00:00Z',valid_until='2027-08-01T00:00:00Z',
            review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,
            basis_ref='SYNTHETIC-provided-validity-and-status-not-authenticated-review')for i,req in enumerate(requirements)])


def main():
    arguments=make_arguments();base=assemble_costed_exit_sale(*arguments);initial=make_registry(arguments)
    cases=[]
    for name in ['current','expired','pending-review','estimated-value','superseded','explicit-renewed-test','known-bank-blocker']:
        args=make_arguments(True)if name=='known-bank-blocker'else arguments
        calculation=assemble_costed_exit_sale(*args)if name=='known-bank-blocker'else base
        registry=make_registry(args)if name=='known-bank-blocker'else copy.deepcopy(initial)
        at='2027-08-01T00:00:00Z'if name in ['expired','explicit-renewed-test']else'2027-07-01T12:00:00Z'
        if name=='pending-review':registry['evidence'][0]['review_status']='pending'
        if name=='estimated-value':registry['evidence'][0]['value_status']='estimate'
        if name=='superseded':registry['evidence'][0]['superseded_by_sha256']='a'*64
        if name=='explicit-renewed-test':
            for record in registry['evidence']:
                record['evidence_id']+='-explicit-new-version';record['valid_until']='2027-09-01T00:00:00Z';record['basis_ref']+='-new-synthetic-declaration'
        rr=raw(registry);currency=evaluate_evidence_currency(rr,at)
        result=assemble_current_exit_output(args,calculation,rr,currency,at)
        verify_current_exit_output(args,calculation,rr,currency,at,CurrentExitOutputRun(**json.loads(json.dumps(asdict(result)))))
        p=result.payload;s=p['current_project_return_summary']
        cases.append(dict(case_id=name,evaluated_as_of_UTC=at,registry_source_sha256=sha(rr),registry_run_sha256=currency.sha256,
            base_costed_run_sha256=calculation.sha256,current_output_run_sha256=result.sha256,
            state=p['state'],exposed_project_net_cash_profit=None if s is None else s['net_cash_profit'],
            blockers=p['blockers'],calculation_blockers=p['calculation_blockers'],evidence_blockers=p['evidence_blockers'],
            required_source_binding_count=len(p['required_source_bindings']),report_serialization_roundtrip_replayed=True,decision='PENDING'))
    assert cases[0]['exposed_project_net_cash_profit']is not None and cases[1]['exposed_project_net_cash_profit']is None
    assert cases[0]['base_costed_run_sha256']==cases[1]['base_costed_run_sha256']==cases[5]['base_costed_run_sha256']
    return dict(purpose='explicit_time_synthetic_evidence_currency_and_return_gate',
        base_registry_example_path='templates/synthetic-evidence-currency-example.json',cases=cases,
        independent_software_fixture_note='Compatible branch is the separate declared bank NOI 2000/closing-without-valuation fixture. Original bank NOI 50 and its blocker remain unchanged.',
        historic_math_preserved_across_expiry_and_explicit_test_renewal=True,
        review_or_source_authentication_claimed=False,live_monitor_enabled=False,
        decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
