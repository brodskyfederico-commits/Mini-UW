"""Explicit synthetic operating-phase contract linked to saved construction evidence."""
from pathlib import Path
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.construction_bundle import recover_construction_bundle,export_construction_bundle
from miniuw_foundation.operating_debt_phase import produce_operating_debt_phase
from miniuw_foundation.staged_operating_window import reconcile_staged_operating_window
from miniuw_foundation.staged_lifecycle_returns import assemble_staged_lifecycle_returns
from miniuw_foundation.debt_service import produce_debt_service,DateWindow
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.project_cash import CheckedClosingEvidence
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from miniuw_foundation.hold_sale_cash import reconcile_hold_sale_cash
from miniuw_foundation.hold_sale_returns import holding_equity_events
from hold_sale_demo_support import sources as holding_sources,read,q
from construction_demo_support import sources as construction_sources,build as construction_build
from demo_preopening_cash import make_binding as cash_binding

ROOT=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def make_case(construction_change=None,terms_change=None,phase_change=None,holding_change=None,window_change=None,investor_change=None,binding_change=None):
    if construction_change:
        data=construction_sources();construction_change(data);construction=export_construction_bundle(*construction_build(data))
    else:construction=(ROOT/'templates/synthetic-construction-cash-bundle-example.json').read_bytes()
    recovered=recover_construction_bundle(construction);ctx=recovered.run.payload['context'];old=recovered.loans[0];loan_id=old.run.payload['loan_id']
    terms=read('synthetic-project-refinance-loan.json');terms.update(context=copy.deepcopy(ctx),loan_id=loan_id,principal=q(200),periodic_rate=q(0),amortization_payments=10,maturity_payment=6,payments_per_year=12,origination_date='2027-01-01',payment_dates=['2027-0'+str(i)+'-01'for i in range(2,8)],rate_interval_ref='SYNTHETIC-explicit-operating-phase-interval',annual_equivalent_ref='SYNTHETIC-phase-sizing-not-funding')
    if terms_change:terms_change(terms)
    contract=dict(schema='miniuw.synthetic-operating-debt-phase.v1',profile='SYNTHETIC-SAME-LIABILITY-NO-NEW-CASH-NO-EXTENSION-v1',construction_bundle_sha256=sha(construction),construction_cash_run_sha256=recovered.run.sha256,phase_basis_ref='SYNTHETIC-supplied-same-liability-phase-contract-not-authenticated',loan_phases=[dict(loan_id=loan_id,construction_loan_source_sha256=sha(old.raw),construction_loan_run_sha256=old.run.sha256,same_liability_declared=True,no_new_cash_declared=True,no_principal_adjustments_declared=True,prior_interest_fees_settled_declared=True,continuity_basis_ref='SYNTHETIC-no-cash-only-amortization-phase',settlement_basis_ref='SYNTHETIC-paid-as-proposed-at-construction-boundary-not-bank-proof',schedule_source_utf8=raw(terms).decode(),windows=[])])
    if phase_change:phase_change(contract)
    phase_raw=raw(contract);phase=produce_operating_debt_phase(construction,phase_raw)
    d=holding_sources();d['loans']=[terms]
    for n,s in zip(d['nois'],d['ops']):n['context']=copy.deepcopy(ctx);s['context']=copy.deepcopy(ctx)
    for i,(opening,closing,principal)in enumerate([(590,440,40),(440,300,60)]):
        for key,value in dict(opening_free_cash=opening,closing_free_cash_claim=closing,debt_principal_payment=principal).items():d['ops'][i]['amounts'][key]['value']=q(value)
    d['sale']['context']=copy.deepcopy(ctx);d['sale']['amounts']['opening_free_cash']['value']=q(300);d['debt']['context']=copy.deepcopy(ctx)
    for row in d['sale']['old_debts']:
        row['loan_id']=loan_id
        for suffix in ['due','paid']:row['principal_'+suffix]['value']=q(100)
    for row in d['debt']['loans']:row['loan_id']=loan_id
    d['investor']['context']=copy.deepcopy(ctx)
    if holding_change:holding_change(d)
    periods=[];calendar=[]
    for n,s in zip(d['nois'],d['ops']):
        nr=raw(n);noi=produce_operating_noi(nr);s=copy.deepcopy(s);s.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256);sr=raw(s);cash=reconcile_operating_cash(nr,noi,sr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash));calendar.append(dict(period_ref=s['period_ref'],start_date=s['start_date'],end_date=s['end_date'],cash_date=s['cash_date'],noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256,spec_source_sha256=sha(sr),cash_run_sha256=cash.sha256))
    periods=tuple(periods);manifest=dict(schema='miniuw.synthetic-holding-cash.v1',profile='contiguous_operating_plans_only',context=ctx,currency='USD',start_date='2027-01-01',end_date='2027-07-01',calendar_basis_ref='SYNTHETIC-staged-same-debt-operations',scope_inventory_declared_complete=True,periods=calendar)
    hr=raw(manifest);holding=reconcile_holding_cash(periods,hr);cr=raw(d['sale']);closing=produce_closing_cash(cr);loans=[]
    for t in d['loans']:
        lr=raw(t);loans.append(DatedLoanEvidence(loan_raw=lr,windows=(),run=produce_debt_service(lr,())))
    loans=tuple(loans);debt=copy.deepcopy(d['debt']);debt.update(closing_source_sha256=sha(cr),closing_run_sha256=closing.sha256)
    for row,e in zip(debt['loans'],loans):row.update(loan_source_sha256=sha(e.loan_raw),loan_run_sha256=e.run.sha256)
    dr=raw(debt);sale=CheckedClosingEvidence(closing_id='SYNTHETIC-staged-sale',closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr))
    hs=dict(schema='miniuw.synthetic-hold-sale-cash.v1',profile='SYNTHETIC-OPERATING-HOLD-TERMINAL-SALE-NO-REFINANCE-v1',holding_source_sha256=sha(hr),holding_run_sha256=holding.sha256,sale_id=sale.closing_id,sale_source_sha256=sha(cr),sale_run_sha256=closing.sha256,debt_binding_source_sha256=sha(dr),debt_run_sha256=sale.debt_run.sha256,scope_inventory_declared_complete=True,cash_boundary_basis_ref='SYNTHETIC-carry-free-restricted',loan_continuity_basis_ref='SYNTHETIC-no-new-funding-after-construction',terminal_working_balance_basis_ref='SYNTHETIC-no-unsettled-working-balances')
    ha=(periods,sale,hr,holding,raw(hs));hold=reconcile_hold_sale_cash(*ha)
    pre=recovered.run.preopening_run;pre_raw=recovered.run.compiled_raw
    if pre_raw is None:
        # Input remains a declared blocked draft; it is never turned into a zero-cash seed.
        pre_raw=recovered.preopening_raw
    cb=raw(cash_binding(pre_raw,pre if pre is not None else recovered.run,periods[0]))
    window_spec=dict(schema='miniuw.synthetic-staged-operating-window.v1',construction_bundle_sha256=sha(construction),phase_run_sha256=phase.sha256,holding_manifest_sha256=sha(hr),hold_sale_spec_sha256=sha(ha[4]),hold_sale_run_sha256=hold.sha256,cash_binding_sha256=sha(cb),same_cash_and_liability_basis_ref='SYNTHETIC-one-cash-one-liability-no-new-phase-funding')
    if window_change:window_change(window_spec)
    wa=(construction,phase_raw,phase,ha,hold,cb,raw(window_spec));window=reconcile_staged_operating_window(*wa)
    investor=copy.deepcopy(d['investor']);investor['events']=[];mapping={}
    records={'preopening_slots':[]if pre is None else pre.payload['exportable_equity_movements']or [],'operating_slots':holding_equity_events(hold)}
    for family,rows in records.items():
        mapping[family]=[]
        for i,e in enumerate(rows):
            eid=family+'-'+str(i);mapping[family].append(dict(source_event_id=e['event_id'],investor_event_id=eid));investor['events'].append(dict(event_id=eid,**{k:e[k]for k in ['date','kind','category','currency']},amount=None,source_ref=None))
    if not investor['events']:investor['events']=[dict(event_id='SYNTHETIC-pending-input',kind='contribution',category='initial_capital',date='2026-10-01',currency='USD',amount=None,source_ref=None)]
    investor['normalization']=dict(reference_amount=q(10),contribution_event_ids=[e['event_id']for e in investor['events']if e['kind']=='contribution'],basis_ref='SYNTHETIC-all-declared-gross-equity')
    if investor_change:investor_change(investor)
    ir=raw(investor);binding=dict(schema='miniuw.synthetic-staged-lifecycle-return-link.v1',window_run_sha256=window.sha256,investor_source_sha256=sha(ir),scope_basis_ref='SYNTHETIC-construction-through-sale-no-phase-cash-or-principal-as-equity',calendar_basis_ref='SYNTHETIC-explicit-monthly-grid',**mapping)
    if binding_change:binding_change(binding)
    br=raw(binding);return wa,window,ir,br,assemble_staged_lifecycle_returns(wa,window,ir,br)
