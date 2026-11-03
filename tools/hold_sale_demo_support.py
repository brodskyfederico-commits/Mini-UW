"""Independently supplied no-refinance software examples; never an automatic extension."""
from pathlib import Path
import json,copy,hashlib
from fractions import Fraction
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational,produce_debt_service
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.project_cash import CheckedClosingEvidence
from miniuw_foundation.preopening_cash import reconcile_preopening_cash
from miniuw_foundation.hold_sale_cash import reconcile_hold_sale_cash
from miniuw_foundation.hold_sale_opening import reconcile_hold_sale_opening
from miniuw_foundation.hold_sale_returns import assemble_hold_sale_returns,holding_equity_events
from demo_preopening_cash import claim,make_binding
from lifecycle_demo_support import preopening_source

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'templates'/name).read_bytes())
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def q(n):return rational(Fraction(n))
def replace_strings(p,mapping):
    if type(p)is dict:return {k:replace_strings(v,mapping)for k,v in p.items()}
    if type(p)is list:return [replace_strings(v,mapping)for v in p]
    return mapping.get(p,p)if type(p)is str else p


def sources(unlevered=False):
    context=dict(deal_id='SYNTHETIC-hold-sale-demo',scenario_id='SYNTHETIC-no-refinance-independent-case',run_id='SYNTHETIC-hold-sale-run',definition_set_revision='SYNTHETIC-hold-sale-v1')
    pre=preopening_source(context);loan_id='SYNTHETIC-hold-sale-loan';pre['loan_ids']=[]if unlevered else[loan_id]
    for e in pre['events']:
        if e['loan_id']is not None:e['loan_id']=loan_id
    if unlevered:
        pre['events']=[e for e in pre['events']if e['category']!='loan_draw'];pre['events'][3]['amount']=claim(100);pre['events'][4]['amount']=claim(0)
    pre['terminal_claims']['loan_principal']={}if unlevered else{loan_id:claim(120)}
    nois=[];ops=[]
    for i,tag in enumerate(['pre-refi','post-refi']):
        n=read('synthetic-project-'+tag+'-noi.json');s=read('synthetic-project-'+tag+'-operation.json');old=n['period_ref'];new='SYNTHETIC-hold-'+str(i+1)
        mapping={old:new,'OPENING:'+old:'OPENING:'+new,'CLOSING:'+old:'CLOSING:'+new};n=replace_strings(n,mapping);s=replace_strings(s,mapping);n['context']=context;s['context']=context
        for row in n['income_rows']+n['expense_rows']+[n['tax_floor']]:row['value']=q(0)
        n['income_rows'][0]['value']=q(60 if i==0 else 90);n['tax_coefficient']['value']=q(0)
        for row in s['working_balances'].values():
            for cutoff in ['opening','closing']:row[cutoff]['value']=q(0)
        for row in s['amounts'].values():row['value']=q(0)
        values=dict(operating_receipts_claim=60 if i==0 else 90,debt_principal_payment=0 if unlevered else 30,capital_expenditure=20,reserve_deposit=50,planned_operating_distribution=100,
            opening_free_cash=1000 if i==0 else(890 if unlevered else 860),opening_restricted_cash=0 if i==0 else 50,
            closing_free_cash_claim=(890 if i==0 else 810)if unlevered else(860 if i==0 else 750),closing_restricted_cash_claim=50 if i==0 else 100)
        for key,value in values.items():s['amounts'][key]['value']=q(value)
        nois.append(n);ops.append(s)
    loan=read('synthetic-project-refinance-loan.json');loan.update(context=context,loan_id=loan_id,maturity_payment=7,payment_dates=['2027-0'+str(i)+'-01'for i in range(1,8)])
    sale=read('synthetic-project-sale-closing.json');sale.update(context=context,new_loan=None)
    for key,value in dict(gross_proceeds=400,opening_free_cash=810 if unlevered else 750,opening_restricted_cash=100,reserve_release=100,new_reserve=0,closing_costs_paid=20,other_cash_sources=0,other_cash_uses=0,retained_free_cash=0,closing_restricted_cash_claim=0).items():sale['amounts'][key]['value']=q(value)
    old=read('synthetic-project-refinance-closing.json')['old_debts'][0];old['loan_id']=loan_id
    for key,row in old.items():
        if type(row)is dict:row.update(as_of_date='2027-07-01',value=q(60 if key.startswith('principal')else 10 if key.startswith('fees')else 0))
    sale['old_debts']=[]if unlevered else[old]
    if sale['valuation_claim']is not None:sale['valuation_claim']['value']=None
    debt=read('synthetic-project-refinance-debt-binding.json');debt['context']=context
    for row in debt['loans']:row['loan_id']=loan_id
    if unlevered:debt['loans']=[]
    investor=read('synthetic-project-investor-slots.json');investor.update(context=context,events=[],capital_snapshots=[],annual_cash_bases=[])
    investor['grid']['dates']=['2026-10-01','2026-11-01','2026-12-01']+investor['grid']['dates']
    return dict(pre=pre,nois=nois,ops=ops,loans=[]if unlevered else[loan],sale=sale,debt=debt,investor=investor)


def build(data,hold_change=None,opening_change=None,investor_change=None,binding_change=None):
    periods=[];calendar=[]
    for n,s in zip(data['nois'],data['ops']):
        nr=raw(n);noi=produce_operating_noi(nr);s=copy.deepcopy(s);s.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256);sr=raw(s);cash=reconcile_operating_cash(nr,noi,sr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash));calendar.append(dict(period_ref=s['period_ref'],start_date=s['start_date'],end_date=s['end_date'],cash_date=s['cash_date'],noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256,spec_source_sha256=sha(sr),cash_run_sha256=cash.sha256))
    context=data['pre']['context'];periods=tuple(periods)
    manifest=dict(schema='miniuw.synthetic-holding-cash.v1',profile='contiguous_operating_plans_only',context=context,currency='USD',start_date='2027-01-01',end_date='2027-07-01',calendar_basis_ref='SYNTHETIC-two-complete-periods-no-refinance',scope_inventory_declared_complete=True,periods=calendar)
    hr=raw(manifest);holding=reconcile_holding_cash(periods,hr);cr=raw(data['sale']);closing=produce_closing_cash(cr);loans=tuple(DatedLoanEvidence(loan_raw=raw(t),windows=(),run=produce_debt_service(raw(t),()))for t in data['loans'])
    b=copy.deepcopy(data['debt']);b.update(closing_source_sha256=sha(cr),closing_run_sha256=closing.sha256)
    for row,e in zip(b['loans'],loans):row.update(loan_source_sha256=sha(e.loan_raw),loan_run_sha256=e.run.sha256)
    dr=raw(b);sale=CheckedClosingEvidence(closing_id='SYNTHETIC-hold-sale',closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr))
    hs=dict(schema='miniuw.synthetic-hold-sale-cash.v1',profile='SYNTHETIC-OPERATING-HOLD-TERMINAL-SALE-NO-REFINANCE-v1',holding_source_sha256=sha(hr),holding_run_sha256=holding.sha256,sale_id=sale.closing_id,sale_source_sha256=sha(cr),sale_run_sha256=closing.sha256,debt_binding_source_sha256=sha(dr),debt_run_sha256=sale.debt_run.sha256,scope_inventory_declared_complete=True,cash_boundary_basis_ref='SYNTHETIC-free-and-restricted-no-reset',loan_continuity_basis_ref='SYNTHETIC-supplied-loans-only-no-refinance-or-unmodeled-draw',terminal_working_balance_basis_ref='SYNTHETIC-no-unsettled-terminal-working-balances')
    if hold_change:hold_change(hs)
    hsr=raw(hs);hold=reconcile_hold_sale_cash(periods,sale,hr,holding,hsr);pr=raw(data['pre']);pre=reconcile_preopening_cash(pr);cb=raw(make_binding(pr,pre,periods[0]))
    opening=dict(schema='miniuw.synthetic-hold-sale-opening.v1',profile='SYNTHETIC-SINGLE-FULL-DRAW-NO-REFINANCE-OPENING-v1',preopening_source_sha256=sha(pr),preopening_run_sha256=pre.sha256,hold_sale_spec_sha256=sha(hsr),hold_sale_run_sha256=hold.sha256,cash_binding_sha256=sha(cb),payment_basis_ref='SYNTHETIC-prior-service-only-opening-date-in-operations',debt_change_scope_basis_ref='SYNTHETIC-no-capitalized-or-undocumented-principal-change',loans=[dict(loan_id=e.run.payload['loan_id'],loan_source_sha256=sha(e.loan_raw),loan_run_sha256=e.run.sha256)for e in loans])
    if opening_change:opening_change(opening)
    oa=(pr,pre,periods,sale,hr,holding,hsr,hold,cb,raw(opening));o=reconcile_hold_sale_opening(*oa)
    investor=copy.deepcopy(data['investor']);mapping={};all_records={'preopening_slots':pre.payload['exportable_equity_movements']or [],'holding_slots':holding_equity_events(hold)}
    for family,records in all_records.items():
        mapping[family]=[]
        for i,e in enumerate(records):
            eid=family+'-'+str(i);investor['events'].append(dict(event_id=eid,**{k:e[k]for k in ['date','kind','category','currency']},amount=None,source_ref=None));mapping[family].append(dict(source_event_id=e['event_id'],investor_event_id=eid))
    if not investor['events']:
        # An invalid proof can have no exports; keep a declared empty-slot input for diagnostics, never a zero result.
        investor['events']=[dict(event_id='SYNTHETIC-pending-input',date='2026-10-01',kind='contribution',category='initial_capital',currency='USD',amount=None,source_ref=None)]
    investor['normalization']=dict(reference_amount=q(10),contribution_event_ids=[e['event_id']for e in investor['events']if e['kind']=='contribution'],basis_ref='SYNTHETIC-all-declared-gross-contributions')
    if investor_change:investor_change(investor)
    ir=raw(investor);binding=dict(schema='miniuw.synthetic-hold-sale-return-link.v1',opening_run_sha256=o.sha256,investor_source_sha256=sha(ir),scope_basis_ref='SYNTHETIC-full-declared-no-refinance-gross-equity-no-opening-seed',calendar_basis_ref='SYNTHETIC-explicit-monthly-grid',**mapping)
    if binding_change:binding_change(binding)
    br=raw(binding);return oa,o,ir,br,assemble_hold_sale_returns(oa,o,ir,br)
