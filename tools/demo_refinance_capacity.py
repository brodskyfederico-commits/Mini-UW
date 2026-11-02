"""Independent tied capacity and an unchanged cash-balanced project blocked by sizing."""
from pathlib import Path
import json,hashlib,tempfile
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.project_cash import CheckedClosingEvidence,reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot,ProjectReturnBinding
from miniuw_foundation.refinance_capacity import RefinanceInputs,size_refinance
from miniuw_foundation.capacity_project_returns import CapacityProjectBinding,assemble_capacity_checked_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    def read(name):return (root/'templates'/name).read_bytes()
    branches=[]
    for case in ['tie','project']:
        vr=read(f'synthetic-capacity-{case}-valuation-noi.json');br=read(f'synthetic-capacity-{case}-bank-noi.json');lr=read('synthetic-capacity-tie-loan.json'if case=='tie'else'synthetic-project-sale-loan.json');cr=read('synthetic-capacity-tie-closing.json'if case=='tie'else'synthetic-project-refinance-closing.json');s=read(f'synthetic-capacity-{case}-spec.json')
        inputs=RefinanceInputs(valuation_noi_raw=vr,valuation_noi_run=produce_operating_noi(vr),bank_noi_raw=br,bank_noi_run=produce_operating_noi(br),new_loan=DatedLoanEvidence(loan_raw=lr,windows=(),run=produce_debt_service(lr,())),closing_raw=cr,closing_run=produce_closing_cash(cr));branches.append((inputs,s,size_refinance(inputs,s)))
    ops=[];closes=[]
    for tag in ['pre-refi','post-refi']:
        nr=read(f'synthetic-project-{tag}-noi.json');sr=read(f'synthetic-project-{tag}-operation.json');n=produce_operating_noi(nr);ops.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=n,spec_raw=sr,cash_run=reconcile_operating_cash(nr,n,sr)))
    for kind in ['refinance','sale']:
        lr=read(f'synthetic-project-{kind}-loan.json');cr=read(f'synthetic-project-{kind}-closing.json');s=read(f'synthetic-project-{kind}-debt-binding.json');loans=(DatedLoanEvidence(loan_raw=lr,windows=(),run=produce_debt_service(lr,())),);c=produce_closing_cash(cr);r=reconcile_debt_closing(loans,cr,c,s)
        closes.append(CheckedClosingEvidence(closing_id='SYNTHETIC-project-'+kind,closing_raw=cr,closing_run=c,loans=loans,debt_spec_raw=s,debt_run=r))
    ops=tuple(ops);closes=tuple(closes);m=read('synthetic-project-cash-manifest.json');p=reconcile_project_cash(ops,closes,m);i=read('synthetic-project-investor-slots.json')
    slots=tuple(ProjectEventSlot(node_id=n['node_id'],distribution_event_id=eid,contribution_event_id=None)for n,eid in zip(json.loads(m)['nodes'],['op-before','refi','op-after','sale']))
    inner=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',manifest_source_sha256=hashlib.sha256(m).hexdigest(),project_run_sha256=p.sha256,investor_source_sha256=hashlib.sha256(i).hexdigest(),opening_contribution_event_ids=('initial',),slots=slots)
    inputs,s,c=branches[1];b=CapacityProjectBinding(profile_id='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1',capacity_spec_sha256=hashlib.sha256(s).hexdigest(),capacity_run_sha256=c.sha256,refinance_node_id='SYNTHETIC-project-refinance',project_return_binding=inner)
    result=assemble_capacity_checked_returns(ops,closes,m,p,inputs,s,c,i,b)
    assert branches[0][2].payload['binding_limit_ids']==['DSCR','LTV']and branches[0][2].payload['state']=='compatible_synthetic_refinance_capacity'
    assert p.payload['state']=='reconciled_synthetic_cash_window'and c.payload['state']=='blocked'and result.compiled_raw is None
    with tempfile.TemporaryDirectory()as t:
        path=Path(t)/'capacity.sqlite3'
        with EvidenceArchive(path)as a:
            keys=[a.save_refinance_capacity(*branch)for branch in branches];gated=a.save_capacity_project_returns(ops,closes,m,p,inputs,s,c,i,b,result)
        with EvidenceArchive(path)as a:
            for key,branch in zip(keys,branches):assert a.load_refinance_capacity(key).run==branch[2]
            recovered=a.load_capacity_project_returns(gated);assert recovered.run==result and recovered.run.compiled_raw is None
            assert a.get_investor_returns_source(recovered.payload['investor_source_sha256'])==i
    return {'purpose':'synthetic_capacity_and_selected_draw_control_without_tuning_existing_project',
        'independent_tie_example':branches[0][2].payload,'unchanged_project_sizing':c.payload,
        'prior_cash_window_reconciled':True,'capacity_checked_project_state':result.payload['state'],'project_blockers':result.payload['blockers'],
        'new_investor_return_generated':False,'old_project_inputs_and_previous_demo_preserved':True,'capacity_bundle_sha256s':keys,'gated_project_bundle_sha256':gated,
        'all_three_bundles_replayed_after_reopen':True,'original_investor_source_preserved':True,'runtime_database_retained':False,
        'bank_credit_approved':False,'bank_policy_adopted':False,'funds_available_verified':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
