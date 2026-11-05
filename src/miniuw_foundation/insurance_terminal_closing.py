"""T107 source-bound on-cut nominal insurance payments already included in T29."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .debt_service import _date,_fraction,rational
from .expense_cash_detail import _json,_exact
from .operating_noi import _bounded,ArithmeticBudgetError
from .scheduled_expense_case import sha
from .deferred_insurance_settlement import reconcile_deferred_insurance_settlement
from .closing_cash import parse_closing_cash,produce_closing_cash

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T107.md'
SCHEMA='miniuw.synthetic-insurance-terminal-closing-binding.v1'
ASSUMPTIONS=dict(other_cash_uses='only_all_on_cut_payments_of_this_insurance_item',
    payment_representation='already_in_supplied_closing_no_second_deduction',
    future_payments='unsupported_no_acceleration',accounting_balances='not_derived_from_nominal_tail')


def parse_insurance_terminal_binding(raw):
    p=_json(raw)
    _exact(p,{'schema','context','currency','settlement_date','economic_item_id','plan_source_sha256','closing_source_sha256',
        'source_ref','classification_basis_ref','payment_inventory_declared_complete','assumptions','payments'})
    if p['schema']!=SCHEMA:raise ValidationError('exact synthetic insurance terminal binding required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    for k in('currency','economic_item_id'):nonempty(p[k],k)
    if not p['economic_item_id'].startswith('SYNTHETIC-'):raise ValidationError('synthetic item required')
    if p['settlement_date']is not None:_date(p['settlement_date'])
    for k in('plan_source_sha256','closing_source_sha256'):
        value=p[k]
        if value is not None and(type(value)is not str or len(value)!=64 or any(c not in'0123456789abcdef'for c in value)):raise ValidationError('SHA256 or pending source hash required')
    for k in('source_ref','classification_basis_ref'):
        if p[k]is not None:nonempty(p[k],k)
    if p['payment_inventory_declared_complete']is not None and type(p['payment_inventory_declared_complete'])is not bool:raise ValidationError('complete inventory boolean or pending required')
    _exact(p['assumptions'],ASSUMPTIONS)
    if p['assumptions']!=ASSUMPTIONS:raise ValidationError('unsupported insurance closing assumptions')
    if type(p['payments'])is not list or len(p['payments'])>256:raise ValidationError('bounded payment binding inventory required')
    seen=set()
    for row in p['payments']:
        _exact(row,{'payment_id','installment_id','amount','payment_date','source_ref'})
        for k in('payment_id','installment_id'):nonempty(row[k],k)
        if row['payment_id']in seen:raise ValidationError('duplicate terminal payment binding')
        seen.add(row['payment_id']);_fraction(row['amount'])
        if row['payment_date']is not None:_date(row['payment_date'])
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    return p


@dataclass(frozen=True)
class InsuranceTerminalClosingRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_insurance_terminal_closing(plan_raw,closing_raw,binding_raw):
    p=parse_insurance_terminal_binding(binding_raw);plan=reconcile_deferred_insurance_settlement(plan_raw);s=plan.payload
    closing_source=parse_closing_cash(closing_raw);closing=produce_closing_cash(closing_raw);c=closing.payload
    blockers=[];rows=[];summary=None
    if s['totals']is None:blockers.append('nominal_plan_blocked')
    if c['state']!='computed_synthetic_closing':blockers.append('closing_cash_blocked')
    for key,raw in(('plan_source_sha256',plan_raw),('closing_source_sha256',closing_raw)):
        if p[key]!=sha(raw):blockers.append(key+'_missing_or_mismatch')
    if not(p['context']==s['context']==c['context']):blockers.append('exact_plan_closing_binding_context_required')
    if not(p['currency']==s['currency']==c['currency']):blockers.append('same_currency_required')
    if p['economic_item_id']!=s['source']['economic_item_id']:blockers.append('insurance_item_mismatch')
    if not(p['settlement_date']==s['cutoff_date']==c['closing_date']):blockers.append('exact_plan_cut_and_sale_settlement_date_required')
    if c['kind']!='sale':blockers.append('sale_only_profile_required')
    for k in('source_ref','classification_basis_ref'):
        if p[k]is None:blockers.append(k+'_missing')
    if p['payment_inventory_declared_complete']is not True:blockers.append('complete_terminal_inventory_required')
    expected={row['payment_id']:(i,row)for i,row in enumerate(s['source']['planned_payments'])if row['payment_date']==s['cutoff_date']}
    if any(row['payment_date']>s['cutoff_date']for row in s['source']['planned_payments']):blockers.append('after_cut_plan_payment_requires_other_profile_no_acceleration')
    if {r['payment_id']for r in p['payments']}!=set(expected):blockers.append('exact_all_on_cut_payment_inventory_required')
    try:
        total=F(0)
        for index,row in enumerate(p['payments']):
            issues=[];value=_fraction(row['amount']);parent=expected.get(row['payment_id'])
            if value is None or value<0:issues.append('payment_amount_missing_or_negative')
            else:total=_bounded(total+value)
            if row['payment_date']!=s['cutoff_date']:issues.append('payment_not_at_plan_cut')
            if row['source_ref']is None:issues.append('payment_source_missing')
            if parent:
                original=parent[1]
                if row['installment_id']!=original['installment_id']:issues.append('payment_installment_identity_mismatch')
                if value is None or value!=_fraction(original['amount']):issues.append('payment_amount_differs_from_source_plan')
                if row['payment_date']!=original['payment_date']:issues.append('payment_date_differs_from_source_plan')
            else:issues.append('unknown_or_pre_cut_payment_not_a_terminal_payment')
            blockers.extend(row['payment_id']+':'+issue for issue in issues)
            rows.append(dict(binding_pointer='/payments/'+str(index),plan_payment_pointer=None if parent is None else'/planned_payments/'+str(parent[0]),blockers=issues))
        if s['totals']is not None:
            for key,target in(('nominal_tail',s['totals']['nominal_not_settled_before_cut']),('on_cut_cash',s['totals']['cash_by_cut_bucket']['on_cut'])):
                if total!=_fraction(target,1300):blockers.append('bound_payment_sum_differs_from_'+key)
        other=_fraction(closing_source['amounts']['other_cash_uses']['value'])
        if other is None or total!=other:blockers.append('bound_payment_sum_differs_from_closing_other_cash_uses')
        if not blockers:
            remaining=_bounded(_fraction(s['totals']['nominal_not_settled_before_cut'],1300)-total)
            summary=dict(allocated_expense=s['totals']['allocated_expense'],planned_cash_before_cut=s['totals']['cash_by_cut_bucket']['before_cut'],
                nominal_before_cut=s['totals']['nominal_not_settled_before_cut'],bound_payment_sum=rational(total),
                nominal_after_supplied_cut_payments=rational(remaining),closing_other_cash_uses=closing_source['amounts']['other_cash_uses']['value'],
                net_residual_after_retention=c['net_residual_after_retention'],exportable_equity_distribution=c['exportable_equity_distribution'],
                exportable_equity_contribution=c['exportable_equity_contribution'],total_cash_conservation_residual=c['total_cash_conservation_residual'])
    except ArithmeticBudgetError:blockers.append('terminal_binding_exact_arithmetic_budget_exceeded');summary=None
    result=dict(component='T107',scope='synthetic_on_cut_insurance_payment_to_supplied_sale_cash_only',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),source_hashes=dict(plan=sha(plan_raw),closing=sha(closing_raw),binding=sha(binding_raw)),
        source_run_hashes=dict(plan=plan.sha256,closing=closing.sha256),context=p['context'],currency=p['currency'],settlement_date=p['settlement_date'],
        economic_item_id=p['economic_item_id'],binding_source=p,payment_checks=rows,summary=summary,blockers=sorted(set(blockers)),
        state='matched_synthetic_insurance_terminal_closing'if summary is not None else'PENDING',no_additional_deduction_applied=True,
        accounting_balances_derived=False,nominal_tail_is_approved_legal_liability=False,actual_bank_payments_verified=False,
        funding_availability_verified=False,payer_or_buyer_transfer_inferred=False,source_authority_verified=False,
        full_operating_sale_return_integration_completed=False,personal_investor_return_verified=False,
        new_external_PDF_created=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    text=canonical(result);return InsuranceTerminalClosingRun(text,digest(text))


def verify_insurance_terminal_closing(plan_raw,closing_raw,binding_raw,run):
    if type(run)is not InsuranceTerminalClosingRun or reconcile_insurance_terminal_closing(plan_raw,closing_raw,binding_raw)!=run:raise ValidationError('terminal insurance closing differs from exact three-source replay')
    return run
