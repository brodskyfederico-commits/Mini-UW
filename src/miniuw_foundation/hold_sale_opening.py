"""T64 opening cash and scheduled loan carry for the explicit no-refinance profile."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import PreopeningCashRun,reconcile_preopening_cash,link_preopening_to_operation,_object
from .hold_sale_cash import HoldSaleCashRun,reconcile_hold_sale_cash
from .holding_cash import parse_holding_cash
from .operating_cash import parse_operating_cash
from .debt_service import parse_loan_terms,_fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T63-T65.md'


def scheduled_opening_checks(pre,at,loans,bindings):
    """Reduced one-full-draw profile; caller has replayed all debt and cash sources."""
    rows=[];blockers=[]
    for e in loans:
        terms=parse_loan_terms(e.loan_raw);loan=terms['loan_id'];local=[];schedule=e.run.payload;b=bindings[loan]
        for key,value in [('loan_source_sha256',hashlib.sha256(e.loan_raw).hexdigest()),('loan_run_sha256',e.run.sha256)]:
            if b[key]!=value:local.append(key+'_mismatch')
        if terms['context']!=pre['context']or terms['currency']!=pre['currency']:local.append('opening_loan_context_or_currency_mismatch')
        origin=terms['origination_date']
        if origin is None or not pre['start_date']<=origin<=at:local.append('loan_origin_outside_preopening_history')
        dated=schedule['schedule_state']=='computed_synthetic'and schedule['schedule']and all(r['date']is not None for r in schedule['schedule'])
        if not dated:local.append('complete_dated_schedule_unavailable')
        events=[event for event in pre['events']if event['loan_id']==loan];draws=[event for event in events if event['category']=='loan_draw']
        if len(draws)!=1 or draws[0]['date']!=origin or _fraction(draws[0]['amount']['value'])!=_fraction(terms['principal']):local.append('single_full_draw_does_not_match_origination')
        balance=None;checks=[]
        if dated:
            balance=_fraction(terms['principal']);expected={};paid={}
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
                checks.append({'date':key[0],'category':key[1],'scheduled':rational(need),'supplied_paid':rational(got),'equal_exact_value':equal})
                if not equal:local.append(key[0]+':'+key[1]+':cash_payment_differs_from_preopening_regular_schedule')
        actual=_fraction(pre['date_close_balances'][-1]['loan_principal'][loan],1300)
        if balance is not None and actual!=balance:local.append('preopening_principal_differs_from_scheduled_opening_balance')
        rows.append({'loan_id':loan,'scheduled_opening_principal':None if balance is None else rational(balance),'preopening_closing_principal':rational(actual),'payment_checks':checks,'blockers':sorted(set(local))})
        blockers.extend(loan+':'+b for b in local)
    return rows,blockers


@dataclass(frozen=True)
class HoldSaleOpeningRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_hold_sale_opening(pre_raw,pre_run,periods,sale,holding_raw,holding_run,hold_spec_raw,hold_run,cash_binding_raw,spec_raw):
    if type(pre_run)is not PreopeningCashRun or reconcile_preopening_cash(pre_raw)!=pre_run:raise ValidationError('entire preopening proof must reproduce')
    if type(hold_run)is not HoldSaleCashRun or reconcile_hold_sale_cash(periods,sale,holding_raw,holding_run,hold_spec_raw)!=hold_run:raise ValidationError('entire no-refinance holding/sale proof must reproduce')
    p=pre_run.payload;h=hold_run.payload;s=_object(spec_raw)
    keys={'schema','profile','preopening_source_sha256','preopening_run_sha256','hold_sale_spec_sha256','hold_sale_run_sha256','cash_binding_sha256','payment_basis_ref','debt_change_scope_basis_ref','loans'}
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-hold-sale-opening.v1'or s['profile']!='SYNTHETIC-SINGLE-FULL-DRAW-NO-REFINANCE-OPENING-v1':raise ValidationError('exact no-refinance opening profile required')
    actual={'preopening_source_sha256':hashlib.sha256(pre_raw).hexdigest(),'preopening_run_sha256':pre_run.sha256,'hold_sale_spec_sha256':hashlib.sha256(hold_spec_raw).hexdigest(),'hold_sale_run_sha256':hold_run.sha256,'cash_binding_sha256':hashlib.sha256(cash_binding_raw).hexdigest()}
    blockers=[];checks=[];link=None
    for key,value in actual.items():
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact opening source/run hash required')
        if s[key]!=value:blockers.append(key+'_mismatch')
    for key in ['payment_basis_ref','debt_change_scope_basis_ref']:
        if s[key]is None:blockers.append(key+'_missing')
        else:nonempty(s[key],key)
    if type(s['loans'])is not list or len(s['loans'])>32:raise ValidationError('bounded complete opening loan inventory required')
    bindings={}
    for row in s['loans']:
        if type(row)is not dict or set(row)!={'loan_id','loan_source_sha256','loan_run_sha256'}:raise ValidationError('exact loan identity/source/run required')
        nonempty(row['loan_id'],'loan_id')
        if row['loan_id']in bindings:raise ValidationError('duplicate opening loan identity')
        for key in ['loan_source_sha256','loan_run_sha256']:
            if type(row[key])is not str or not re.fullmatch('[a-f0-9]{64}',row[key]):raise ValidationError('exact loan hash required')
        bindings[row['loan_id']]=row
    if p['state']!='reconciled_synthetic_preopening_cash':blockers.append('preopening_cash_blocked')
    if h['state']!='reconciled_synthetic_no_refinance_cash':blockers.append('hold_sale_cash_or_debt_blocked')
    m=parse_holding_cash(holding_raw);first_id=m['periods'][0]['period_ref'];first=next((e for e in periods if parse_operating_cash(e.spec_raw)['period_ref']==first_id),None)
    if first is None:blockers.append('first_operating_period_evidence_missing')
    else:
        link=link_preopening_to_operation(pre_raw,pre_run,first,cash_binding_raw)
        if link.payload['state']!='matched_synthetic_cash_only':blockers.append('preopening_operating_cash_boundary_blocked')
    loan_ids={e.run.payload['loan_id']for e in sale.loans};pre_ids=set(json.loads(pre_raw)['loan_ids'])
    if loan_ids!=pre_ids or set(bindings)!=pre_ids:blockers.append('preopening_and_sale_loan_inventories_do_not_match_exactly')
    if not blockers:
        try:checks,local=scheduled_opening_checks(p,h['opening_date'],sale.loans,bindings);blockers.extend(local)
        except ArithmeticBudgetError:blockers.append('no_refinance_opening_exact_arithmetic_budget_exceeded');checks=[]
    result={'component':'T64','purpose':'synthetic_preopening_to_no_refinance_holding','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'source_bindings':actual,'context':p['context'],'currency':p['currency'],
        'opening_cash_link_run':None if link is None else asdict(link),'opening_loan_checks':checks,'preopening_blockers':p['blockers'],'hold_sale_blockers':h['blockers'],
        'blockers':sorted(set(blockers)),'state':'matched_synthetic_no_refinance_opening'if not blockers else'blocked',
        'actual_funding_payments_or_assets_verified':False,'refinance_or_extension_generated':False,'decision':'PENDING','production_authorized':False}
    encoded=canonical(result);return HoldSaleOpeningRun(encoded,digest(encoded))
