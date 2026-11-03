"""Independent fully declared lifecycle software fixture; original examples stay intact."""
from pathlib import Path
from fractions import Fraction
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational,produce_debt_service
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.project_cash import CheckedClosingEvidence,reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot,ProjectReturnBinding
from miniuw_foundation.refinance_capacity import RefinanceInputs,size_refinance
from miniuw_foundation.capacity_project_returns import CapacityProjectBinding,assemble_capacity_checked_returns
from miniuw_foundation.preopening_cash import reconcile_preopening_cash
from miniuw_foundation.opening_debt import reconcile_opening_debt
from miniuw_foundation.lifecycle_returns import assemble_lifecycle_returns
from demo_preopening_cash import claim,make_binding as cash_binding

ROOT=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((ROOT/'templates'/name).read_bytes())
def q(n):return rational(Fraction(n))


def project_sources():
    return dict(nois=[read('synthetic-project-'+tag+'-noi.json')for tag in ['pre-refi','post-refi']],
        ops=[read('synthetic-project-'+tag+'-operation.json')for tag in ['pre-refi','post-refi']],
        closings=[read('synthetic-project-'+tag+'-closing.json')for tag in ['refinance','sale']],
        loans=[[read('synthetic-project-'+tag+'-loan.json')]for tag in ['refinance','sale']],
        debt_specs=[read('synthetic-project-'+tag+'-debt-binding.json')for tag in ['refinance','sale']],
        manifest=read('synthetic-project-cash-manifest.json'))


def build_project(d):
    periods=[];closings=[];m=copy.deepcopy(d['manifest']);binds={}
    for n,s in zip(d['nois'],d['ops']):
        nr=raw(n);noi=produce_operating_noi(nr);s=copy.deepcopy(s);s.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256);sr=raw(s);cash=reconcile_operating_cash(nr,noi,sr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash));binds[s['period_ref']]=dict(source_sha256=sha(sr),run_sha256=cash.sha256,upstream_source_sha256=sha(nr),upstream_run_sha256=noi.sha256)
    for i,(c,terms,b)in enumerate(zip(d['closings'],d['loans'],d['debt_specs'])):
        cr=raw(c);closing=produce_closing_cash(cr);loans=[];b=copy.deepcopy(b);b.update(closing_source_sha256=sha(cr),closing_run_sha256=closing.sha256)
        for term in terms:
            lr=raw(term);loan=produce_debt_service(lr,());loans.append(DatedLoanEvidence(loan_raw=lr,windows=(),run=loan))
            for row in b['loans']:
                if row['loan_id']==term['loan_id']:row.update(loan_source_sha256=sha(lr),loan_run_sha256=loan.sha256)
        br=raw(b);debt=reconcile_debt_closing(tuple(loans),cr,closing,br);cid=m['nodes'][1 if i==0 else -1]['node_id']
        closings.append(CheckedClosingEvidence(closing_id=cid,closing_raw=cr,closing_run=closing,loans=tuple(loans),debt_spec_raw=br,debt_run=debt))
        binds[cid]=dict(source_sha256=sha(cr),run_sha256=closing.sha256,upstream_source_sha256=sha(br),upstream_run_sha256=debt.sha256)
    for row in m['nodes']:
        if row['node_id']in binds:row.update(binds[row['node_id']])
    periods,closings=tuple(periods),tuple(closings);mr=raw(m)
    return periods,closings,mr,reconcile_project_cash(periods,closings,mr)


def preopening_source(context):
    rows=[('2026-10-01','initial_equity_contribution',1000,None),('2026-10-01','acquisition_payment',300,None),
        ('2026-11-01','additional_equity_contribution',400,None),('2026-11-01','construction_payment',200,None),
        ('2026-12-01','loan_draw',120,'SYNTHETIC-project-old-loan'),('2026-12-01','soft_cost_payment',20,None)]
    return dict(schema='miniuw.synthetic-preopening-cash.v1',profile='SYNTHETIC-ZERO-OPENING-PREOPERATING-CASH-v1',context=context,currency='USD',start_date='2026-10-01',opening_operation_date='2027-01-01',
        inventory_declared_complete=True,zero_opening_basis_ref='SYNTHETIC-zero-cash-and-principal-not-asset-verification',classification_basis_ref='SYNTHETIC-disjoint-declared-cash-categories',boundary_basis_ref='SYNTHETIC-cutoff-events-before-opening-operation',loan_ids=['SYNTHETIC-project-old-loan'],
        events=[dict(event_id='SYNTHETIC-lifecycle-pre-'+str(i),date=date,category=category,loan_id=loan,amount=claim(value))for i,(date,category,value,loan)in enumerate(rows)],
        terminal_claims=dict(free_cash=claim(1000),restricted_cash=claim(0),loan_principal={'SYNTHETIC-project-old-loan':claim(120)}))


def make_case(pre_change=None,project_change=None,bank_noi=2000,investor_change=None,opening_change=None,binding_change=None,include_refinance_cash_in=False):
    d=project_sources()
    if project_change:project_change(d)
    periods,closings,mr,p=build_project(d);pre=preopening_source(p.payload['context'])
    if pre_change:pre_change(pre)
    pr=raw(pre);history=reconcile_preopening_cash(pr);cb=raw(cash_binding(pr,history,periods[0]))
    opening_spec=dict(schema='miniuw.synthetic-opening-debt.v1',profile='SYNTHETIC-SINGLE-FULL-DRAW-REGULAR-PAYMENTS-BEFORE-OPENING-v1',
        preopening_source_sha256=sha(pr),preopening_run_sha256=history.sha256,project_manifest_sha256=sha(mr),project_cash_run_sha256=p.sha256,cash_binding_sha256=sha(cb),
        payment_basis_ref='SYNTHETIC-regular-service-before-opening-opening-date-belongs-to-operations',debt_change_scope_basis_ref='SYNTHETIC-full-draw-only-no-capitalization-other-principal-changes-or-unmodeled-accrual',
        loans=[dict(loan_id=e.run.payload['loan_id'],loan_source_sha256=sha(e.loan_raw),loan_run_sha256=e.run.sha256)for e in closings[0].loans])
    if opening_change:opening_change(opening_spec)
    oa=(pr,history,periods,closings,mr,p,cb,raw(opening_spec));opening=reconcile_opening_debt(*oa)
    vr=raw(read('synthetic-capacity-project-valuation-noi.json'));bank=read('synthetic-capacity-project-bank-noi.json');bank['income_rows'][0]['value']=q(bank_noi);br=raw(bank)
    cr=closings[0].closing_raw;loan=closings[1].loans[0];inputs=RefinanceInputs(valuation_noi_raw=vr,valuation_noi_run=produce_operating_noi(vr),bank_noi_raw=br,bank_noi_run=produce_operating_noi(br),new_loan=loan,closing_raw=cr,closing_run=closings[0].closing_run)
    spec=read('synthetic-capacity-project-spec.json');spec.update(valuation_noi_source_sha256=sha(vr),valuation_noi_run_sha256=inputs.valuation_noi_run.sha256,bank_noi_source_sha256=sha(br),bank_noi_run_sha256=inputs.bank_noi_run.sha256,new_loan_source_sha256=sha(loan.loan_raw),new_loan_run_sha256=loan.run.sha256,closing_source_sha256=sha(cr),closing_run_sha256=inputs.closing_run.sha256)
    sr=raw(spec);capacity=size_refinance(inputs,sr);window_source=read('synthetic-project-investor-slots.json')
    if include_refinance_cash_in:window_source['events'].append(dict(event_id='refi-in',date='2027-04-01',kind='contribution',category='refinance_cash_in',amount=None,currency='USD',source_ref=None))
    window=raw(window_source)
    slots=tuple(ProjectEventSlot(node_id=n['node_id'],distribution_event_id=e,contribution_event_id='refi-in'if include_refinance_cash_in and n['kind']=='refinance'else None)for n,e in zip(p.payload['nodes'],['op-before','refi','op-after','sale']))
    inner=ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',manifest_source_sha256=sha(mr),project_run_sha256=p.sha256,investor_source_sha256=sha(window),opening_contribution_event_ids=('initial',),slots=slots)
    capbinding=CapacityProjectBinding(profile_id='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1',capacity_spec_sha256=sha(sr),capacity_run_sha256=capacity.sha256,refinance_node_id=closings[0].closing_id,project_return_binding=inner)
    ca=(periods,closings,mr,p,inputs,sr,capacity,window,capbinding);caprun=assemble_capacity_checked_returns(*ca)
    investor=copy.deepcopy(window_source);investor['grid']['dates']=['2026-10-01','2026-11-01','2026-12-01']+investor['grid']['dates']
    investor['events']=investor['events'][1:];pre_slots=[]
    for e in history.payload['exportable_equity_movements']or []:
        eid='history-'+e['event_id'];investor['events'].append({k:e[k]for k in ['date','kind','category','currency']}|dict(event_id=eid,amount=None,source_ref=None));pre_slots.append(dict(source_event_id=e['event_id'],investor_event_id=eid))
    investor['normalization']=dict(reference_amount=q(10),contribution_event_ids=[e['event_id']for e in investor['events']if e['kind']=='contribution'],basis_ref='SYNTHETIC-all-declared-gross-contributions-not-LP-allocation')
    investor['annual_cash_bases']=[]
    if investor_change:investor_change(investor)
    ir=raw(investor);binding=dict(schema='miniuw.synthetic-lifecycle-return-link.v1',opening_debt_run_sha256=opening.sha256,capacity_project_run_sha256=caprun.sha256,investor_source_sha256=sha(ir),equity_scope_basis_ref='SYNTHETIC-all-preopening-and-cash-window-equity-no-extra-opening-seed',calendar_basis_ref='SYNTHETIC-regular-monthly-exact-dates-no-bucket-inference',preopening_slots=pre_slots,operating_slots=[dict(source_event_id=e['event_id'],investor_event_id=e['event_id'])for e in window_source['events'][1:]])
    if binding_change:binding_change(binding)
    lr=raw(binding);run=assemble_lifecycle_returns(oa,opening,ca,caprun,ir,lr)
    return oa,opening,ca,caprun,ir,lr,run
