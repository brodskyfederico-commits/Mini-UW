"""Preserve original financing failure; exercise independent explicit software fixture."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json

from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.debt_closing import DatedLoanEvidence, reconcile_debt_closing
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.project_cash import CheckedClosingEvidence, reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot, ProjectReturnBinding
from miniuw_foundation.refinance_capacity import RefinanceInputs, size_refinance
from miniuw_foundation.capacity_project_returns import CapacityProjectBinding, assemble_capacity_checked_returns
from miniuw_foundation.project_sale_revision import (CapacityProjectEvidence, evidence_fingerprint,
    revise_project_sale, recover_sale_revision, ProjectSaleRevisionRun)
from miniuw_foundation.project_sale_comparison import (compare_project_sales, verify_sale_comparison,
                                                       ProjectSaleComparisonRun)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def raw(value):return canonical(value).encode()


def load_evidence(independent_test_fixture=False, sale_closing_source_name=None):
    root=Path(__file__).resolve().parents[1]
    def read(name):return (root/'templates'/name).read_bytes()
    periods=[];closings=[]
    for tag in ['pre-refi','post-refi']:
        nr=read('synthetic-project-'+tag+'-noi.json');sr=read('synthetic-project-'+tag+'-operation.json')
        noi=produce_operating_noi(nr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=reconcile_operating_cash(nr,noi,sr)))
    for kind in ['refinance','sale']:
        lr=read('synthetic-project-'+kind+'-loan.json');cr=read('synthetic-project-'+kind+'-closing.json')
        br=read('synthetic-project-'+kind+'-debt-binding.json')
        if kind=='sale' and sale_closing_source_name is not None:
            cr=read(sale_closing_source_name)
        loans=(DatedLoanEvidence(loan_raw=lr,windows=(),run=produce_debt_service(lr,())),)
        closing=produce_closing_cash(cr)
        if kind=='sale' and sale_closing_source_name is not None:
            bound=json.loads(br);bound.update(closing_source_sha256=sha(cr),closing_run_sha256=closing.sha256);br=raw(bound)
        closings.append(CheckedClosingEvidence(closing_id='SYNTHETIC-project-'+kind,closing_raw=cr,
            closing_run=closing,loans=loans,debt_spec_raw=br,debt_run=reconcile_debt_closing(loans,cr,closing,br)))
    periods=tuple(periods);closings=tuple(closings)
    manifest=read('synthetic-project-cash-manifest.json')
    if sale_closing_source_name is not None:
        m=json.loads(manifest);c=closings[1]
        node=next(n for n in m['nodes']if n['node_id']==c.closing_id)
        node.update(source_sha256=sha(c.closing_raw),run_sha256=c.closing_run.sha256,
            upstream_source_sha256=sha(c.debt_spec_raw),upstream_run_sha256=c.debt_run.sha256)
        manifest=raw(m)
    project=reconcile_project_cash(periods,closings,manifest)
    vr=read('synthetic-capacity-project-valuation-noi.json')
    bank_name='synthetic-sale-revision-test-bank-noi.json' if independent_test_fixture else 'synthetic-capacity-project-bank-noi.json'
    br=read(bank_name);loan=closings[1].loans[0];refi=closings[0]
    inputs=RefinanceInputs(valuation_noi_raw=vr,valuation_noi_run=produce_operating_noi(vr),
        bank_noi_raw=br,bank_noi_run=produce_operating_noi(br),new_loan=loan,
        closing_raw=refi.closing_raw,closing_run=refi.closing_run)
    spec=json.loads(read('synthetic-capacity-project-spec.json'))
    # Bind exact bytes/runs of the expressly selected fixture; no numeric repair.
    spec.update(valuation_noi_source_sha256=sha(vr),valuation_noi_run_sha256=inputs.valuation_noi_run.sha256,
        bank_noi_source_sha256=sha(br),bank_noi_run_sha256=inputs.bank_noi_run.sha256,
        new_loan_source_sha256=sha(loan.loan_raw),new_loan_run_sha256=loan.run.sha256,
        closing_source_sha256=sha(refi.closing_raw),closing_run_sha256=refi.closing_run.sha256)
    sr=raw(spec);capacity=size_refinance(inputs,sr)
    investor_name='synthetic-sale-revision-test-investor-slots.json' if independent_test_fixture else 'synthetic-project-investor-slots.json'
    investor=read(investor_name)
    slots=tuple(ProjectEventSlot(node_id=n['node_id'],distribution_event_id=eid,
        contribution_event_id='sale-cash-in' if independent_test_fixture and n['kind']=='sale' else None)
        for n,eid in zip(json.loads(manifest)['nodes'],['op-before','refi','op-after','sale']))
    inner=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',
        manifest_source_sha256=sha(manifest),project_run_sha256=project.sha256,investor_source_sha256=sha(investor),
        opening_contribution_event_ids=('initial',),slots=slots)
    binding=CapacityProjectBinding(profile_id='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1',
        capacity_spec_sha256=sha(sr),capacity_run_sha256=capacity.sha256,
        refinance_node_id='SYNTHETIC-project-refinance',project_return_binding=inner)
    guarded=assemble_capacity_checked_returns(periods,closings,manifest,project,inputs,sr,capacity,investor,binding)
    return CapacityProjectEvidence(periods,closings,manifest,project,inputs,sr,capacity,investor,binding,guarded)


def branch(evidence, include_cash_in=False):
    specs=[];cases=[('SYNTHETIC-sale-0',0,20,None),('SYNTHETIC-sale-200',200,20,None),('SYNTHETIC-sale-400',400,20,None)]
    if include_cash_in:cases.append(('SYNTHETIC-sale-funding-required',0,500,'SYNTHETIC-explicit-funding-hypothesis-not-available-funds'))
    for identity,proceeds,costs,funding in cases:
        claims=json.loads(evidence.closings[1].closing_raw)['amounts']
        claims={key:claims[key] for key in ['gross_proceeds','closing_costs_paid']}
        for key,number in [('gross_proceeds',proceeds),('closing_costs_paid',costs)]:
            claims[key]['value']={'numerator':str(number),'denominator':'1'}
            claims[key]['source_ref']=identity+'#/'+key
        specs.append(raw(dict(schema='miniuw.synthetic-project-sale-source-revision.v1',revision_id=identity,
            base_evidence_sha256=evidence_fingerprint(evidence),sale_node_id='SYNTHETIC-project-sale',
            unchanged_other_sources_basis_ref='SYNTHETIC-fixed-date-and-other-input-source-hypothesis',
            equity_funding_assumption_ref=funding,replacement_claims=claims)))
    specs=tuple(specs)
    inventory=raw(dict(schema='miniuw.synthetic-project-sale-comparison.v1',base_evidence_sha256=evidence_fingerprint(evidence),
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-explicit-demo-inventory',
        revisions=[dict(revision_id=json.loads(s)['revision_id'],spec_sha256=sha(s))for s in specs]))
    report=compare_project_sales(evidence,specs,inventory)
    verify_sale_comparison(evidence,specs,inventory,ProjectSaleComparisonRun(**json.loads(json.dumps(asdict(report)))))
    details=[]
    for spec in specs:
        run=revise_project_sale(evidence,spec)
        recovered=recover_sale_revision(evidence,spec,ProjectSaleRevisionRun(**json.loads(json.dumps(asdict(run)))))
        assert recovered is not None and evidence_fingerprint(recovered)==run.payload['revised_evidence_sha256']
        p=run.payload
        details.append(dict(spec_json=spec.decode(),revision_run_sha256=run.sha256,
            revised_evidence_sha256=p['revised_evidence_sha256'],state=p['state'],changes=p['changes'],
            stage_run_sha256s={name:None if p[name] is None else p[name]['sha256']
                for name in ['closing_run','debt_run','project_run','guarded_run','risk_run']}))
    return dict(inventory_json=inventory.decode(),comparison=asdict(report),revision_details=details,
                every_report_serialization_roundtrip_replayed=True,
                full_revision_reports_regenerated_from_preserved_sources_and_specs=True)


def main():
    original=load_evidence();test=load_evidence(True)
    assert original.guarded_run.compiled_raw is None and test.guarded_run.compiled_raw is not None
    return dict(purpose='synthetic_sale_source_revision_and_guarded_return_demo',
        original_project_branch=branch(original),independent_software_fixture_branch=branch(test,True),
        independent_software_fixture_note='Separate declared bank NOI 2000 and explicit empty sale cash-in slot; not a repair, adopted rule or new valuation of the original project. Original bank NOI 50 and financing failure remain unchanged.',
        original_bank_source_preserved=True,personal_investor_return=None,final_economic_capital_loss=None,
        downside_policy_adopted=False,complete_market_scenarios_recomputed=False,
        decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
