"""T63 explicit operating holding plans through one terminal sale without refinance."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import _object
from .holding_cash import HoldingCashRun,reconcile_holding_cash,parse_holding_cash
from .project_cash import CheckedClosingEvidence,verify_project_sources
from .operating_cash import WORKING
from .debt_closing import parse_debt_closing
from .debt_service import _fraction,rational,parse_loan_terms
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T63-T65.md'


@dataclass(frozen=True)
class HoldSaleCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_hold_sale_cash(periods,sale,holding_raw,holding_run,spec_raw):
    if type(holding_run)is not HoldingCashRun or reconcile_holding_cash(periods,holding_raw)!=holding_run:raise ValidationError('all supplied holding source/NOI/cash evidence must reproduce')
    if type(sale)is not CheckedClosingEvidence:raise ValidationError('one complete debt-checked sale required')
    sources=verify_project_sources(periods,(sale,));m=parse_holding_cash(holding_raw);h=holding_run.payload;s=_object(spec_raw);c=sources[sale.closing_id];closing=c['run'];cs=c['spec']
    keys={'schema','profile','holding_source_sha256','holding_run_sha256','sale_id','sale_source_sha256','sale_run_sha256','debt_binding_source_sha256','debt_run_sha256','scope_inventory_declared_complete','cash_boundary_basis_ref','loan_continuity_basis_ref','terminal_working_balance_basis_ref'}
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-hold-sale-cash.v1'or s['profile']!='SYNTHETIC-OPERATING-HOLD-TERMINAL-SALE-NO-REFINANCE-v1':raise ValidationError('exact no-refinance holding/sale profile required')
    actual={'holding_source_sha256':hashlib.sha256(holding_raw).hexdigest(),'holding_run_sha256':holding_run.sha256,
        'sale_source_sha256':hashlib.sha256(sale.closing_raw).hexdigest(),'sale_run_sha256':sale.closing_run.sha256,
        'debt_binding_source_sha256':hashlib.sha256(sale.debt_spec_raw).hexdigest(),'debt_run_sha256':sale.debt_run.sha256}
    blockers=[];checks=[];service=[];totals=None;residual=None;exports=None
    for key,value in actual.items():
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact source/run hash required')
        if s[key]!=value:blockers.append(key+'_mismatch')
    nonempty(s['sale_id'],'sale_id')
    if s['sale_id']!=sale.closing_id:blockers.append('sale_identity_mismatch')
    if s['scope_inventory_declared_complete']is not None and type(s['scope_inventory_declared_complete'])is not bool:raise ValidationError('explicit scope declaration or null required')
    if s['scope_inventory_declared_complete']is not True:blockers.append('hold_sale_scope_inventory_not_declared_complete')
    for key in ['cash_boundary_basis_ref','loan_continuity_basis_ref','terminal_working_balance_basis_ref']:
        if s[key]is None:blockers.append(key+'_missing')
        else:nonempty(s[key],key)
    if h['state']!='reconciled_synthetic_operating_chain':blockers.append('holding_cash_chain_blocked')
    if c['kind']!='sale':blockers.append('terminal_closing_is_not_sale_no_refinance_allowed')
    if closing['state']!='computed_synthetic_closing'or sale.debt_run.payload['state']!='matched_synthetic_debt_assumptions':blockers.append('debt_checked_sale_blocked')
    if closing['context']!=h['context']or closing['currency']!=h['currency']:blockers.append('holding_sale_context_or_currency_mismatch')
    if closing['closing_date']!=h['end_date']:blockers.append('sale_date_does_not_match_holding_end')
    ordered=[sources.get(row['period_ref'])for row in m['periods']]
    if not blockers:
        for account in ['free','restricted']:
            a=ordered[-1]['spec']['amounts']['closing_'+account+'_cash_claim'];b=cs['amounts']['opening_'+account+'_cash'];equal=_fraction(a['value'])==_fraction(b['value'])
            checks.append({'account':account,'holding_terminal_claim':a,'sale_opening_claim':b,'equal_exact_value':equal})
            if not equal:blockers.append(account+':sale_opening_cash_does_not_match_holding_close')
        for family in WORKING:
            if _fraction(ordered[-1]['spec']['working_balances'][family]['closing']['value'])!=0:blockers.append(family+':terminal_working_balance_requires_settlement_profile')
        debt_spec=parse_debt_closing(sale.debt_spec_raw)
        if any(row['payment_cutoff']!='before_regular_payment'for row in debt_spec['loans']):blockers.append('hold_sale_requires_before_regular_payment_cutoff')
        try:
            for e in sale.loans:
                terms=parse_loan_terms(e.loan_raw)
                if terms['origination_date']is None or terms['origination_date']>h['start_date']:blockers.append(terms['loan_id']+':loan_origin_inside_holding_requires_draw_profile')
            for op in ordered:
                principal=interest=Fraction(0);selected=[]
                for e in sale.loans:
                    for row in e.run.payload['schedule']:
                        if op['run']['start_date']<=row['date']<op['run']['end_date']:
                            principal=_bounded(principal+_fraction(row['principal_due'],1300));interest=_bounded(interest+_fraction(row['interest_due'],1300))
                            selected.append({'loan_id':e.run.payload['loan_id'],'payment_index':row['payment_index'],'date':row['date']})
                            if _fraction(row['balloon_due'],1300)!=0:blockers.append(op['spec']['period_ref']+':balloon_inside_holding_requires_separate_cash_profile')
                a=op['spec']['amounts'];equal=principal==_fraction(a['debt_principal_payment']['value'])and interest==_fraction(a['debt_interest_payment']['value'])and _fraction(a['debt_fee_payment']['value'])==0
                service.append({'period_ref':op['spec']['period_ref'],'scheduled_principal':rational(principal),'scheduled_interest':rational(interest),'selected_regular_payments':selected,'equal_with_zero_unmodeled_fee':equal})
                if not equal:blockers.append(op['spec']['period_ref']+':operating_debt_cash_differs_from_schedule_or_has_unmodeled_fee')
            if not blockers:
                q=lambda k:_fraction(h['totals'][k],1300);a=cs['amounts'];v=lambda k:_fraction(a[k]['value'])
                totals={k:q(k)for k in ['opening_free_cash','opening_restricted_cash','operating_receipts','operating_payments','nonfinancing_other_cash_receipt','other_cash_payment','capital_expenditure']}
                totals.update(sale_proceeds=v('gross_proceeds'),closing_other_sources=v('other_cash_sources'),closing_other_uses=v('other_cash_uses'),closing_costs=v('closing_costs_paid'),
                    equity_contributions=_bounded(q('equity_contribution')+_fraction(closing['exportable_equity_contribution'],1300)),equity_distributions=_bounded(q('planned_operating_distribution')+_fraction(closing['exportable_equity_distribution'],1300)),
                    terminal_free_cash=v('retained_free_cash'),terminal_restricted_cash=v('closing_restricted_cash_claim'),
                    reserve_deposits=_bounded(q('reserve_deposit')+v('new_reserve')),reserve_releases=_bounded(q('reserve_release')+v('reserve_release')))
                for key,operating in [('principal','debt_principal_payment'),('interest','debt_interest_payment'),('fees','debt_fee_payment')]:totals['debt_'+key]=_bounded(q(operating)+_fraction(closing['payoff_totals'][key],1300))
                totals['debt_other']=_fraction(closing['payoff_totals']['other'],1300)
                residual=_bounded(sum((totals[k]for k in ['opening_free_cash','opening_restricted_cash','operating_receipts','nonfinancing_other_cash_receipt','closing_other_sources','sale_proceeds','equity_contributions']),Fraction(0))-sum((totals[k]for k in ['operating_payments','other_cash_payment','capital_expenditure','closing_other_uses','closing_costs','equity_distributions','terminal_free_cash','terminal_restricted_cash','debt_principal','debt_interest','debt_fees','debt_other']),Fraction(0)))
                if residual!=0:blockers.append('hold_sale_cash_conservation_mismatch')
                else:
                    exports=[{'node_id':row['period_ref'],'kind':'operation','date':row['cash_date'],'source_run_sha256':row['cash_run_sha256'],'distribution':row['distribution'],'contribution':row['contribution']}for row in h['exportable_equity_movements']]
                    exports.append({'node_id':sale.closing_id,'kind':'sale','date':closing['closing_date'],'source_run_sha256':sale.closing_run.sha256,'distribution':closing['exportable_equity_distribution'],'contribution':closing['exportable_equity_contribution']})
        except ArithmeticBudgetError:blockers.append('hold_sale_exact_arithmetic_budget_exceeded');totals=None;residual=None;exports=None
    result={'component':'T63','purpose':'synthetic_operating_hold_and_sale_without_refinance','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'source_bindings':actual,'context':h['context'],'currency':h['currency'],'opening_date':h['start_date'],'terminal_date':h['end_date'],
        'cash_boundary_checks':checks,'operating_debt_checks':service,'totals':None if totals is None else{k:rational(v)for k,v in totals.items()},'cash_conservation_residual':None if residual is None else rational(residual),
        'exportable_equity_movements':exports,'holding_blockers':h['blockers'],'sale_blockers':closing['blockers'],'sale_debt_blockers':sale.debt_run.payload['blockers'],'blockers':sorted(set(blockers)),
        'state':'reconciled_synthetic_no_refinance_cash'if exports is not None and not blockers else'blocked',
        'refinance_or_loan_extension_generated':False,'actual_payments_and_credit_verified':False,'intraperiod_liquidity_verified':False,'asset_basis_and_complete_TDC_verified':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return HoldSaleCashRun(encoded,digest(encoded))
