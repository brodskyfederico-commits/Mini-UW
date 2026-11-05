"""T106 supplied nominal insurance dues/payment plans after the service cut."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .debt_service import _date,_fraction,rational
from .expense_cash_detail import _json,_exact
from .operating_noi import _bounded,ArithmeticBudgetError
from .scheduled_expense_case import sha

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T106.md'
SCHEMA='miniuw.synthetic-deferred-insurance-settlement.v1'
ASSUMPTIONS=dict(fractions='supplied_not_derived_from_days',settlement_scope='entire_nominal_cost_no_opening_credit',
    refunds_credits_interest_fees=False,cutoff='before_all_events_on_cutoff_date',
    planned_payments='supplied_not_actual_bank_history',rounding='none_exact')


def parse_deferred_insurance_settlement(raw):
    p=_json(raw)
    _exact(p,{'schema','context','currency','schedule_id','economic_item_id','kind','service_start_date','service_end_date',
        'cutoff_date','total_cost','source_ref','allocation_basis_ref','settlement_basis_ref','period_inventory_declared_complete',
        'installment_inventory_declared_complete','payment_inventory_declared_complete','assumptions','allocations','due_installments','planned_payments'})
    if p['schema']!=SCHEMA or p['kind']!='insurance':raise ValidationError('supported synthetic insurance settlement profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    for key in('currency','schedule_id','economic_item_id'):nonempty(p[key],key)
    if not p['schedule_id'].startswith('SYNTHETIC-')or not p['economic_item_id'].startswith('SYNTHETIC-'):raise ValidationError('synthetic schedule/item IDs required')
    if _date(p['service_start_date'])>=_date(p['service_end_date']):raise ValidationError('increasing full service window required')
    _date(p['cutoff_date']);_fraction(p['total_cost'])
    for key in('source_ref','allocation_basis_ref','settlement_basis_ref'):
        if p[key]is not None:nonempty(p[key],key)
    for key in('period_inventory_declared_complete','installment_inventory_declared_complete','payment_inventory_declared_complete'):
        if p[key]is not None and type(p[key])is not bool:raise ValidationError('boolean or pending inventory declaration required')
    _exact(p['assumptions'],ASSUMPTIONS)
    if any(type(p['assumptions'][k])is not type(v)or p['assumptions'][k]!=v for k,v in ASSUMPTIONS.items()):raise ValidationError('unsupported insurance settlement assumptions')
    for family,maximum in(('allocations',64),('due_installments',128),('planned_payments',256)):
        if type(p[family])is not list or len(p[family])>maximum:raise ValidationError('bounded explicit settlement inventories required')
    seen=set()
    for row in p['allocations']:
        _exact(row,{'period_ref','start_date','end_date','fraction','source_ref'});nonempty(row['period_ref'],'period_ref')
        if row['period_ref']in seen:raise ValidationError('duplicate allocated period')
        seen.add(row['period_ref'])
        if _date(row['start_date'])>=_date(row['end_date']):raise ValidationError('increasing allocation window required')
        _fraction(row['fraction'])
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    for family,identity,keys,date_key in(('due_installments','installment_id',{'installment_id','due_date','amount','source_ref'},'due_date'),
        ('planned_payments','payment_id',{'payment_id','installment_id','payment_date','amount','source_ref'},'payment_date')):
        seen=set()
        for row in p[family]:
            _exact(row,keys);nonempty(row[identity],identity)
            if row[identity]in seen:raise ValidationError('duplicate settlement row identity')
            seen.add(row[identity]);_date(row[date_key]);_fraction(row['amount'])
            if family=='planned_payments':nonempty(row['installment_id'],'installment_id')
            if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    return p


def _bucket(day,cut):return'before_cut'if day<cut else'on_cut'if day==cut else'after_cut'


def _calculate(p):
    blockers=[];allocation_rows=[];due_rows=[];payment_rows=[];q=rational
    cost=_fraction(p['total_cost']);fractions=expense=nominal=paid=F(0);previous=p['service_start_date'];cut=p['cutoff_date']
    due_totals={k:F(0)for k in('before_cut','on_cut','after_cut')};cash_totals=dict(due_totals)
    if cost is None or cost<0:blockers.append('total_cost_missing_or_negative')
    if cut!=p['service_end_date']:blockers.append('cutoff_must_equal_full_service_window_end')
    for key in('source_ref','allocation_basis_ref','settlement_basis_ref'):
        if p[key]is None:blockers.append(key+'_missing')
    for key in('period_inventory_declared_complete','installment_inventory_declared_complete','payment_inventory_declared_complete'):
        if p[key]is not True:blockers.append(key+'_not_explicitly_complete')
    if not p['allocations']:blockers.append('complete_allocated_periods_required')
    for index,row in enumerate(p['allocations']):
        f=_fraction(row['fraction']);issues=[];value=None
        if row['start_date']!=previous or row['start_date']<p['service_start_date']or row['end_date']>p['service_end_date']:issues.append('period_gap_overlap_or_outside_window')
        previous=row['end_date']
        if f is None or not 0<=f<=1:issues.append('fraction_missing_or_outside_zero_one')
        else:
            fractions=_bounded(fractions+f)
            if cost is not None and cost>=0:value=_bounded(cost*f);expense=_bounded(expense+value)
        if row['source_ref']is None:issues.append('allocation_source_missing')
        blockers.extend(row['period_ref']+':'+i for i in issues)
        allocation_rows.append(dict(**row,source_pointer='/allocations/'+str(index),allocated_expense=None if value is None else q(value),blockers=issues))
    if previous!=p['service_end_date']:blockers.append('complete_service_partition_required')
    if fractions!=1:blockers.append('supplied_fractions_must_sum_exactly_one')
    by_id={row['installment_id']:row for row in p['due_installments']};payments={key:[]for key in by_id}
    for index,row in enumerate(p['planned_payments']):
        value=_fraction(row['amount']);issues=[];bucket=_bucket(row['payment_date'],cut)
        if value is None or value<0:issues.append('payment_amount_missing_or_negative')
        else:paid=_bounded(paid+value);cash_totals[bucket]=_bounded(cash_totals[bucket]+value)
        if row['payment_date']<p['service_start_date']:issues.append('pre_service_payment_requires_opening_balance_profile')
        if row['source_ref']is None:issues.append('payment_source_missing')
        if row['installment_id']not in by_id:issues.append('unknown_installment_reference')
        else:payments[row['installment_id']].append((index,row,value))
        blockers.extend(row['payment_id']+':'+i for i in issues)
        payment_rows.append(dict(**row,source_pointer='/planned_payments/'+str(index),time_bucket=bucket,blockers=issues))
    overdue=future=F(0)
    for index,row in enumerate(p['due_installments']):
        value=_fraction(row['amount']);issues=[];bucket=_bucket(row['due_date'],cut);total=before=F(0)
        if value is None or value<0:issues.append('installment_amount_missing_or_negative')
        else:nominal=_bounded(nominal+value);due_totals[bucket]=_bounded(due_totals[bucket]+value)
        if row['due_date']<p['service_start_date']:issues.append('pre_service_due_requires_opening_obligation_profile')
        if row['source_ref']is None:issues.append('installment_source_missing')
        for _,payment,amount in payments[row['installment_id']]:
            if amount is not None and amount>=0:
                total=_bounded(total+amount)
                if payment['payment_date']<cut:before=_bounded(before+amount)
        if value is not None and value>=0 and total!=value:issues.append('planned_payments_do_not_settle_this_installment_exactly')
        remaining=None if value is None or value<0 else _bounded(value-before)
        if remaining is not None:
            if bucket=='before_cut':overdue=_bounded(overdue+remaining)
            else:future=_bounded(future+remaining)
        blockers.extend(row['installment_id']+':'+i for i in issues)
        due_rows.append(dict(**row,source_pointer='/due_installments/'+str(index),time_bucket=bucket,
            payment_indices=[i for i,_,_ in payments[row['installment_id']]],planned_total=q(total),planned_before_cut=q(before),
            nominal_not_settled_before_cut=None if remaining is None else q(remaining),blockers=issues))
    if cost is not None and cost>=0:
        if nominal!=cost:blockers.append('complete_installment_sum_differs_from_total_cost')
        if paid!=cost:blockers.append('complete_payment_sum_differs_from_total_cost')
    totals=None
    if not blockers:
        remaining=_bounded(cost-cash_totals['before_cut'])
        if remaining!=_bounded(cash_totals['on_cut']+cash_totals['after_cut'])or remaining!=_bounded(overdue+future):raise ValidationError('nominal settlement cut identities differ')
        totals=dict(allocated_expense=q(expense),fraction_sum=q(fractions),nominal_installments=q(nominal),planned_payments=q(paid),
            due_by_cut_bucket={k:q(v)for k,v in due_totals.items()},cash_by_cut_bucket={k:q(v)for k,v in cash_totals.items()},
            nominal_not_settled_before_cut=q(remaining),due_before_cut_not_settled=q(overdue),not_due_before_cut_not_prepaid=q(future))
    return blockers,allocation_rows,due_rows,payment_rows,totals


@dataclass(frozen=True)
class DeferredInsuranceSettlementRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_deferred_insurance_settlement(raw):
    p=parse_deferred_insurance_settlement(raw)
    try:blockers,allocations,dues,payments,totals=_calculate(p)
    except ArithmeticBudgetError:blockers=['exact_arithmetic_budget_exceeded'];allocations=dues=payments=[];totals=None
    if blockers:
        for row in allocations:row['allocated_expense']=None
        for row in dues:
            for key in('planned_total','planned_before_cut','nominal_not_settled_before_cut'):row[key]=None
    tail=None if totals is None else _fraction(totals['nominal_not_settled_before_cut'],1300)
    result=dict(component='T106',scope='synthetic_declared_nominal_insurance_settlement_plan_only',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),source=p,context=p['context'],currency=p['currency'],
        service_window=dict(start=p['service_start_date'],end=p['service_end_date']),cutoff_date=p['cutoff_date'],
        cutoff_includes_same_date_events=False,allocations=allocations,due_installments=dues,planned_payments=payments,totals=totals,
        blockers=sorted(set(blockers)),state='reconciled_synthetic_nominal_settlement_plan'if totals is not None else'PENDING',
        integration_state='PENDING_SOURCE_OR_PLAN_BLOCKERS'if tail is None else'PENDING_TERMINAL_SETTLEMENT_SOURCE'if tail>0 else'PENDING_FINANCIAL_INTEGRATION',
        terminal_settlement_source_required=None if tail is None else tail>0,nominal_tail_is_approved_legal_liability=False,
        actual_bank_payments_verified=False,source_or_due_date_authority_verified=False,insurance_coverage_sufficiency_verified=False,
        tax_or_accounting_policy_adopted=False,penalties_or_prepayment_rights_verified=False,case_or_cash_or_return_modified=False,
        full_case_financial_integration_completed=False,automatic_funding_or_buyer_transfer_created=False,
        new_external_PDF_created=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(result);return DeferredInsuranceSettlementRun(value,digest(value))


def verify_deferred_insurance_settlement(raw,run):
    if type(run)is not DeferredInsuranceSettlementRun or reconcile_deferred_insurance_settlement(raw)!=run:raise ValidationError('nominal insurance settlement differs from exact source replay')
    return run
