"""T58 replayed cash boundary and full-draw scheduled opening debt carry."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import PreopeningCashRun,reconcile_preopening_cash,link_preopening_to_operation,_object
from .project_cash import ProjectCashRun,reconcile_project_cash
from .operating_cash import parse_operating_cash
from .debt_service import parse_loan_terms,_fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T58.md'


@dataclass(frozen=True)
class OpeningDebtRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_opening_debt(pre_raw,pre_run,periods,closings,manifest_raw,project_run,cash_binding_raw,spec_raw):
    if type(pre_run)is not PreopeningCashRun or reconcile_preopening_cash(pre_raw)!=pre_run:raise ValidationError('complete preopening cash proof must reproduce')
    if type(project_run)is not ProjectCashRun or reconcile_project_cash(periods,closings,manifest_raw)!=project_run:raise ValidationError('entire operating/refinance/sale cash window must reproduce')
    pre=pre_run.payload;p=project_run.payload;s=_object(spec_raw)
    keys={'schema','profile','preopening_source_sha256','preopening_run_sha256','project_manifest_sha256','project_cash_run_sha256','cash_binding_sha256','payment_basis_ref','debt_change_scope_basis_ref','loans'}
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-opening-debt.v1'or s['profile']!='SYNTHETIC-SINGLE-FULL-DRAW-REGULAR-PAYMENTS-BEFORE-OPENING-v1':raise ValidationError('exact single-draw scheduled opening debt profile required')
    actual={'preopening_source_sha256':hashlib.sha256(pre_raw).hexdigest(),'preopening_run_sha256':pre_run.sha256,'project_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'project_cash_run_sha256':project_run.sha256,'cash_binding_sha256':hashlib.sha256(cash_binding_raw).hexdigest()}
    blockers=[];rows=[];link=None
    for key,value in actual.items():
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact source/run SHA-256 required')
        if s[key]!=value:blockers.append(key+'_mismatch')
    for key in ['payment_basis_ref','debt_change_scope_basis_ref']:
        if s[key]is None:blockers.append(key+'_missing')
        else:nonempty(s[key],key)
    if type(s['loans'])is not list or len(s['loans'])>32:raise ValidationError('bounded explicit opening loan binding inventory required')
    bindings={}
    for b in s['loans']:
        if type(b)is not dict or set(b)!={'loan_id','loan_source_sha256','loan_run_sha256'}:raise ValidationError('exact opening loan binding required')
        nonempty(b['loan_id'],'loan_id')
        if b['loan_id']in bindings:raise ValidationError('duplicate opening loan binding')
        for key in ['loan_source_sha256','loan_run_sha256']:
            if type(b[key])is not str or not re.fullmatch('[a-f0-9]{64}',b[key]):raise ValidationError('exact loan source/run hash required')
        bindings[b['loan_id']]=b
    if pre['state']!='reconciled_synthetic_preopening_cash':blockers.append('preopening_cash_blocked')
    if p['state']!='reconciled_synthetic_cash_window':blockers.append('project_cash_window_blocked')
    first_id=p['nodes'][0]['node_id'];first=next((e for e in periods if parse_operating_cash(e.spec_raw)['period_ref']==first_id),None)
    if first is None:blockers.append('first_operating_period_evidence_missing')
    else:
        link=link_preopening_to_operation(pre_raw,pre_run,first,cash_binding_raw)
        if link.payload['state']!='matched_synthetic_cash_only':blockers.append('preopening_operating_cash_boundary_blocked')
    first_closing=next((n for n in p['nodes']if n['kind']!='operation'),None)
    close=None if first_closing is None else next((c for c in closings if c.closing_id==first_closing['node_id']),None)
    if close is None:blockers.append('first_debt_checked_closing_missing')
    evidence={}if close is None else{e.run.payload['loan_id']:e for e in close.loans}
    pre_loans=set(json.loads(pre_raw)['loan_ids'])
    if set(evidence)!=pre_loans or set(bindings)!=pre_loans:blockers.append('opening_loan_inventories_do_not_match_exactly')
    if not blockers:
        try:
            for loan,e in evidence.items():
                local=[];terms=parse_loan_terms(e.loan_raw);schedule=e.run.payload;b=bindings[loan]
                for key,value in [('loan_source_sha256',hashlib.sha256(e.loan_raw).hexdigest()),('loan_run_sha256',e.run.sha256)]:
                    if b[key]!=value:local.append(key+'_mismatch')
                if terms['context']!=pre['context']or terms['currency']!=pre['currency']:local.append('opening_loan_context_or_currency_mismatch')
                origin=terms['origination_date'];at=p['opening_date']
                if origin is None or not pre['start_date']<=origin<=at:local.append('loan_origin_outside_preopening_history')
                dated=schedule['schedule_state']=='computed_synthetic'and schedule['schedule']and all(row['date']is not None for row in schedule['schedule'])
                if not dated:local.append('complete_dated_schedule_unavailable')
                events=[event for event in pre['events']if event['loan_id']==loan]
                draws=[event for event in events if event['category']=='loan_draw']
                if len(draws)!=1 or draws[0]['date']!=origin or _fraction(draws[0]['amount']['value'])!=_fraction(terms['principal']):local.append('single_full_draw_does_not_match_origination')
                expected={};paid={};payments=[];balance=None
                if dated:
                    balance=_fraction(terms['principal'])
                    for row in schedule['schedule']:
                        if row['date']>=at:continue
                        if _fraction(row['balloon_due'],1300)!=0:local.append('balloon_before_operation_requires_separate_profile')
                        balance=_bounded(balance-_fraction(row['principal_due'],1300))
                        for category,key in [('loan_principal_repayment','principal_due'),('debt_interest_payment','interest_due')]:expected[(row['date'],category)]=_fraction(row[key],1300)
                    for event in events:
                        if event['category']not in {'loan_principal_repayment','debt_interest_payment'}:continue
                        key=(event['date'],event['category']);paid[key]=_bounded(paid.get(key,Fraction(0))+_fraction(event['amount']['value']))
                    for key in sorted(set(expected)|set(paid)):
                        need=expected.get(key,Fraction(0));got=paid.get(key,Fraction(0));equal=need==got
                        payments.append({'date':key[0],'category':key[1],'scheduled':rational(need),'supplied_paid':rational(got),'equal_exact_value':equal})
                        if not equal:local.append(key[0]+':'+key[1]+':cash_payment_differs_from_preopening_regular_schedule')
                actual_balance=_fraction(pre['date_close_balances'][-1]['loan_principal'][loan],1300)
                if balance is not None and actual_balance!=balance:local.append('preopening_principal_differs_from_scheduled_opening_balance')
                rows.append({'loan_id':loan,'loan_source_sha256':hashlib.sha256(e.loan_raw).hexdigest(),'loan_run_sha256':e.run.sha256,
                    'payment_checks':payments,'scheduled_opening_principal':None if balance is None else rational(balance),'preopening_closing_principal':rational(actual_balance),
                    'opening_date_payment_belongs_to_operation':True,'blockers':sorted(set(local))})
                blockers.extend(loan+':'+b for b in local)
        except ArithmeticBudgetError:blockers.append('opening_debt_exact_arithmetic_budget_exceeded');rows=[]
    result={'component':'T58','purpose':'synthetic_preopening_to_dated_operating_debt','engine_sha256':ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'source_bindings':actual,
        'context':pre['context'],'currency':pre['currency'],'opening_date':p['opening_date'],'opening_cash_link_run':None if link is None else asdict(link),
        'loan_checks':rows,'preopening_blockers':pre['blockers'],'project_cash_blockers':p['blockers'],'blockers':sorted(set(blockers)),
        'state':'matched_synthetic_opening_debt_and_cash'if not blockers else'blocked','all_sources_replayed':True,
        'actual_bank_payments_verified':False,'commitment_and_funds_available_verified':False,'asset_basis_and_complete_TDC_verified':False,
        'professional_review_authenticated':False,'whole_investor_return_connected':False,'decision':'PENDING','production_authorized':False}
    encoded=canonical(result);return OpeningDebtRun(encoded,digest(encoded))
