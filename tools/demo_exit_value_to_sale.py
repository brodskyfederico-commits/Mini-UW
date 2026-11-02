"""Conditional forward NOI value to guarded sale; original bank failure preserved."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.exit_sale_bridge import assemble_exit_sale, verify_exit_sale, ExitSaleBridgeRun
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from demo_project_sale_revisions import load_evidence


def sha(b):return hashlib.sha256(b).hexdigest()
def raw(p):return canonical(p).encode()


def main():
    root=Path(__file__).resolve().parents[1]
    nr=(root/'templates/synthetic-exit-forward-noi.json').read_bytes();noi=produce_operating_noi(nr)
    initial_spec=json.loads((root/'templates/synthetic-exit-value-spec.json').read_bytes())
    branches=[]
    for separate_test in [False,True]:
        evidence=load_evidence(separate_test,'synthetic-exit-test-sale-closing.json' if separate_test else None);cases=[]
        for numerator,denominator in [(1,20),(2,25),(1,10),(1,5)]:
            spec=json.loads(canonical(initial_spec))
            spec['cap_rate']['value']={'numerator':str(numerator),'denominator':str(denominator)}
            spec['cap_rate']['source_ref']='SYNTHETIC-explicit-demo-cap-'+str(numerator)+'-over-'+str(denominator)+'-not-market-policy'
            vr=raw(spec);value=produce_exit_value(nr,noi,vr)
            cost=json.loads(evidence.closings[1].closing_raw)['amounts']['closing_costs_paid']
            bridge=dict(schema='miniuw.synthetic-exit-value-to-sale.v1',revision_id='SYNTHETIC-cap-'+str(numerator)+'-over-'+str(denominator),
                base_evidence_sha256=evidence_fingerprint(evidence),exit_spec_sha256=sha(vr),exit_run_sha256=value.sha256,
                sale_node_id='SYNTHETIC-project-sale',sale_at_value_hypothesis_ref='SYNTHETIC-sell-at-conditional-value-not-market-evidence',
                unchanged_other_sources_basis_ref='SYNTHETIC-fixed-dates-other-inputs-and-supplied-cost-not-price-function',
                equity_funding_assumption_ref=None,closing_cost_claim=cost)
            br=raw(bridge);run=assemble_exit_sale(evidence,nr,noi,vr,value,br)
            recovered=ExitSaleBridgeRun(**json.loads(json.dumps(asdict(run))))
            verify_exit_sale(evidence,nr,noi,vr,value,br,recovered)
            guarded=run.sale_revision_run.guarded_run if run.sale_revision_run is not None else None
            investor=None if guarded is None or guarded.investor_run is None else guarded.investor_run.payload
            cases.append(dict(exit_spec_json=vr.decode(),bridge_spec_json=br.decode(),
                exit_value_run_sha256=value.sha256,exit_sale_run_sha256=run.sha256,
                sale_revision_run_sha256=None if run.sale_revision_run is None else run.sale_revision_run.sha256,
                state=run.payload['state'],candidate_value=value.payload['candidate_value'],blockers=run.payload['blockers'],
                gross_contributions=None if investor is None else investor['gross_contributions'],
                gross_distributions=None if investor is None else investor['gross_distributions'],
                net_cash_profit=None if investor is None else investor['net_cash_profit'],
                equity_multiple=None if investor is None else investor['equity_multiple'],
                annual_irr_roots=None if investor is None else investor['annual_irr_roots'],
                upstream_story_blockers=None if investor is None else investor['story_blockers'],
                decision='PENDING',report_serialization_roundtrip_replayed=True))
        branches.append(dict(independent_software_fixture=separate_test,
            fixture_note='Separate explicit bank NOI 2000, empty sale contribution slot and separate closing source without a valuation claim; not original project repair' if separate_test else 'Original bank NOI 50, valuation claim 500 and financing blocker preserved',
            base_evidence_sha256=evidence_fingerprint(evidence),cases=cases))
    return dict(purpose='synthetic_forward_noi_exit_value_to_guarded_sale_demo',
        noi_source_path='templates/synthetic-exit-forward-noi.json',noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256,
        forward_noi=noi.payload['noi'],branches=branches,caps_are_explicit_synthetic_inputs_not_market_defaults=True,
        price_dependent_costs_implemented=False,actual_sale_or_funding_verified=False,
        personal_investor_return=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
