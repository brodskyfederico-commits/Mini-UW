"""Explicit bounded synthetic recovery observations; no automatic scenario or PASS."""
from dataclasses import asdict
from pathlib import Path
import json
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale
from miniuw_foundation.sale_recovery import analyze_sale_recovery,verify_sale_recovery,SaleRecoveryRun
from demo_project_sale_revisions import load_evidence
from demo_costed_exit_sale import main as costed_demo

def raw(p):return canonical(p).encode()


def main():
    root=Path(__file__).resolve().parents[1];nr=(root/'templates/synthetic-exit-forward-noi.json').read_bytes();n=produce_operating_noi(nr)
    cases=[]
    for item in costed_demo()['cases']:
        independent=item['independent_software_fixture']
        e=load_evidence(independent,'synthetic-exit-test-sale-closing.json'if independent else None)
        vr=item['exit_spec_json'].encode();v=produce_exit_value(nr,n,vr)
        cr=item['cost_source_json'].encode();c=produce_sale_costs(cr);br=item['bridge_spec_json'].encode()
        arguments=(e,nr,n,vr,v,cr,c,br);base=assemble_costed_exit_sale(*arguments)
        spec=dict(schema='miniuw.synthetic-affine-sale-cash-recovery.v1',base_costed_run_sha256=base.sha256,
            gross_price_domain=dict(lower={'numerator':'0','denominator':'1'},upper={'numerator':'1000','denominator':'1'}),
            cost_profile_domain_basis_ref='SYNTHETIC-fixed-plus-gross-fraction-profile-assumed-only-on-explicit-domain',
            other_sources_fixed_basis_ref='SYNTHETIC-fixed-cash-debt-dates-not-independent-market-scenarios')
        spec_raw=raw(spec);report=analyze_sale_recovery(arguments,base,spec_raw)
        verify_sale_recovery(arguments,base,spec_raw,SaleRecoveryRun(**json.loads(json.dumps(asdict(report)))))
        cases.append(dict(case_id=item['case_id'],independent_software_fixture=independent,
            recovery_spec_json=spec_raw.decode(),base_costed_run_sha256=base.sha256,recovery_run_sha256=report.sha256,
            state=report.payload['state'],blockers=report.payload['blockers'],analysis=report.payload['analysis'],
            report_serialization_roundtrip_replayed=True,decision='PENDING'))
    successful=[x['analysis']for x in cases if x['analysis']is not None]
    assert len(successful)==3
    assert all(x['cash_profit_zero_price']==successful[0]['cash_profit_zero_price']for x in successful)
    return dict(purpose='conditional_synthetic_affine_price_cap_cash_recovery_demo',
        base_sources_and_specs='docs/review/synthetic-costed-exit-sale-demo.json',cases=cases,
        same_boundary_reproduced_from_three_full_price_cost_return_revisions=True,
        scope='Fixed date/debt/other cash with explicit affine charges on [0,1000]; not market/financing/tax approval or a personal return',
        no_new_scenarios_generated=True,investment_criterion_adopted=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
