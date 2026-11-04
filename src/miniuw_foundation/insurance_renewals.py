"""T93 explicit sequential insurance policy costs and grouped due installments."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .debt_service import _date,_fraction,rational
from .expense_cash_detail import _json,_exact
from .expense_schedule import parse_expense_schedule,produce_expense_schedule
from .operating_noi import _bounded,ArithmeticBudgetError
from .evidence_currency import _sha

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T93-T95.md'


def parse_policy_book(raw):
    p=_json(raw,2*1024*1024)
    _exact(p,{'schema','context','currency','schedule_id','economic_item_id','aggregate_source_sha256','policy_inventory_declared_complete','group_inventory_declared_complete','relationship_basis_ref','payment_window_start','payment_window_end','policies','installment_groups'})
    if p['schema']!='miniuw.synthetic-insurance-renewal-book.v1':raise ValidationError('supported policy renewal book required')
    if type(p['context'])is not dict:raise ValidationError('explicit policy context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic policy context required')from error
    for k in ('currency','schedule_id','economic_item_id'):nonempty(p[k],k)
    _sha(p['aggregate_source_sha256'])
    if _date(p['payment_window_start'])>=_date(p['payment_window_end']):raise ValidationError('increasing policy payment window required')
    for k in ('policy_inventory_declared_complete','group_inventory_declared_complete'):
        if p[k]is not None and type(p[k])is not bool:raise ValidationError('explicit policy completeness required')
    if p['relationship_basis_ref']is not None:nonempty(p['relationship_basis_ref'],'relationship_basis_ref')
    if type(p['policies'])is not list or not 1<=len(p['policies'])<=32:raise ValidationError('one to 32 supplied policies required')
    ids=set();references=set()
    for row in p['policies']:
        _exact(row,{'policy_id','coverage_start','coverage_end','premium','source_ref','allocation_basis_ref','allocations','installments'})
        nonempty(row['policy_id'],'policy_id')
        if row['policy_id']in ids:raise ValidationError('duplicate policy identity')
        ids.add(row['policy_id'])
        if _date(row['coverage_start'])>=_date(row['coverage_end']):raise ValidationError('increasing coverage dates required')
        _fraction(row['premium'])
        for k in ('source_ref','allocation_basis_ref'):
            if row[k]is not None:nonempty(row[k],k)
        if type(row['allocations'])is not list or len(row['allocations'])>64:raise ValidationError('bounded policy allocation inventory required')
        periods=set()
        for a in row['allocations']:
            _exact(a,{'period_ref','start_date','end_date','fraction','source_ref'});nonempty(a['period_ref'],'period_ref')
            if a['period_ref']in periods:raise ValidationError('duplicate policy allocated period')
            periods.add(a['period_ref']);_fraction(a['fraction'])
            if _date(a['start_date'])>=_date(a['end_date']):raise ValidationError('increasing allocated coverage interval required')
            if a['source_ref']is not None:nonempty(a['source_ref'],'source_ref')
        if type(row['installments'])is not list or len(row['installments'])>128:raise ValidationError('bounded policy installments required')
        installments=set()
        for a in row['installments']:
            _exact(a,{'installment_id','due_date','amount','source_ref'});nonempty(a['installment_id'],'installment_id');_date(a['due_date']);_fraction(a['amount'])
            if a['installment_id']in installments:raise ValidationError('duplicate installment within policy')
            installments.add(a['installment_id'])
            if a['source_ref']is not None:
                nonempty(a['source_ref'],'source_ref')
                if a['source_ref']in references:raise ValidationError('policy installment source reused without split profile')
                references.add(a['source_ref'])
    if type(p['installment_groups'])is not list or len(p['installment_groups'])>128:raise ValidationError('bounded aggregate groups required')
    groups=set();mapped=set()
    for row in p['installment_groups']:
        _exact(row,{'aggregate_installment_id','policy_installments','source_ref'});nonempty(row['aggregate_installment_id'],'aggregate_installment_id')
        if row['aggregate_installment_id']in groups:raise ValidationError('duplicate aggregate group')
        groups.add(row['aggregate_installment_id'])
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
        if type(row['policy_installments'])is not list or not 1<=len(row['policy_installments'])<=4096:raise ValidationError('explicit nonempty group member inventory required')
        for link in row['policy_installments']:
            _exact(link,{'policy_id','installment_id'})
            for k,v in link.items():nonempty(v,k)
            key=(link['policy_id'],link['installment_id'])
            if key in mapped:raise ValidationError('policy installment mapped more than once')
            mapped.add(key)
    return p


@dataclass(frozen=True)
class InsuranceRenewalRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_insurance_renewals(aggregate_raw,book_raw):
    aggregate=parse_expense_schedule(aggregate_raw);parent=produce_expense_schedule(aggregate_raw);ap=parent.payload;p=parse_policy_book(book_raw)
    blockers=[];rows=[];groups=[];period_totals={a['period_ref']:Fraction(0)for a in aggregate['allocations']};premiums=Fraction(0);all_installments={};previous=aggregate['service_start_date']
    if p['aggregate_source_sha256']!=hashlib.sha256(aggregate_raw).hexdigest():blockers.append('aggregate_source_hash_mismatch')
    if aggregate['kind']!='insurance':blockers.append('insurance_aggregate_required')
    for k in ('context','currency','schedule_id','economic_item_id'):
        if p[k]!=aggregate[k]:blockers.append(k+'_mismatch')
    if (p['payment_window_start'],p['payment_window_end'])!=(aggregate['service_start_date'],aggregate['service_end_date']):blockers.append('complete_operating_payment_window_required')
    if p['policy_inventory_declared_complete']is not True or p['group_inventory_declared_complete']is not True or p['relationship_basis_ref']is None:blockers.append('policy_or_group_inventory_or_relationship_basis_pending')
    if ap['state']!='computed_synthetic_full_window_expense_schedule':blockers+=['aggregate_schedule_blocked']+ap['blockers']
    try:
        for policy in p['policies']:
            issues=[];premium=_fraction(policy['premium']);fractions=Fraction(0);expense=Fraction(0);dues=Fraction(0);allocations=[]
            if policy['coverage_start']!=previous or policy['coverage_start']<aggregate['service_start_date']or policy['coverage_end']>aggregate['service_end_date']:issues.append('coverage_gap_overlap_or_outside_window')
            previous=policy['coverage_end']
            if premium is None or premium<0:issues.append('premium_missing_or_negative')
            else:premiums=_bounded(premiums+premium)
            for k in ('source_ref','allocation_basis_ref'):
                if policy[k]is None:issues.append(k+'_missing')
            expected=[(a['period_ref'],max(a['start_date'],policy['coverage_start']),min(a['end_date'],policy['coverage_end']))for a in aggregate['allocations']if max(a['start_date'],policy['coverage_start'])<min(a['end_date'],policy['coverage_end'])]
            if [(a['period_ref'],a['start_date'],a['end_date'])for a in policy['allocations']]!=expected:issues.append('exact_policy_operating_intersections_required')
            for a in policy['allocations']:
                f=_fraction(a['fraction']);allocated=None
                if f is None or f<0 or f>1:issues.append('allocation_fraction_missing_or_outside_zero_one')
                else:
                    fractions=_bounded(fractions+f)
                    if premium is not None and premium>=0:
                        allocated=_bounded(premium*f);expense=_bounded(expense+allocated)
                        if a['period_ref']in period_totals:period_totals[a['period_ref']]=_bounded(period_totals[a['period_ref']]+allocated)
                if a['source_ref']is None:issues.append('allocation_source_missing')
                allocations.append(dict(**a,allocated_expense=None if allocated is None else rational(allocated)))
            if fractions!=1:issues.append('policy_allocation_fractions_must_sum_one')
            for a in policy['installments']:
                amount=_fraction(a['amount']);all_installments[(policy['policy_id'],a['installment_id'])]=a
                if amount is None or amount<0:issues.append('installment_amount_missing_or_negative')
                else:dues=_bounded(dues+amount)
                if not p['payment_window_start']<=a['due_date']<p['payment_window_end']:issues.append('due_outside_operating_payment_window')
                if a['source_ref']is None:issues.append('installment_source_missing')
            if premium is not None and dues!=premium:issues.append('policy_installment_sum_differs_from_premium')
            rows.append(dict(policy_id=policy['policy_id'],coverage_start=policy['coverage_start'],coverage_end=policy['coverage_end'],allocations=allocations,expense=rational(expense),installments=rational(dues),blockers=sorted(set(issues))))
            blockers.extend(policy['policy_id']+':'+s for s in issues)
        if previous!=aggregate['service_end_date']:blockers.append('complete_successive_policy_window_required')
        if _fraction(aggregate['total_cost'])is None or premiums!=_fraction(aggregate['total_cost']):blockers.append('policy_premiums_differ_from_aggregate_cost')
        for a in ap['allocations']:
            if a['allocated_expense']is None or period_totals[a['period_ref']]!=_fraction(a['allocated_expense'],1300):blockers.append(a['period_ref']+':policy_expense_differs_from_aggregate_period')
        by_aggregate={a['installment_id']:a for a in aggregate['installments']};mapped=set()
        if {g['aggregate_installment_id']for g in p['installment_groups']}!=set(by_aggregate):blockers.append('exact_aggregate_installment_group_inventory_required')
        for group in p['installment_groups']:
            amount=Fraction(0);issues=[];target=by_aggregate.get(group['aggregate_installment_id'])
            if target is None:issues.append('unknown_aggregate_installment')
            if group['source_ref']is None:issues.append('group_source_missing')
            for link in group['policy_installments']:
                key=(link['policy_id'],link['installment_id']);mapped.add(key);a=all_installments.get(key)
                if a is None:issues.append('unknown_policy_installment');continue
                value=_fraction(a['amount'])
                if value is None or value<0:issues.append('group_member_amount_missing_or_negative')
                else:amount=_bounded(amount+value)
                if target is not None and a['due_date']!=target['due_date']:issues.append('group_member_due_date_mismatch')
            if target is not None and (target['amount']is None or amount!=_fraction(target['amount'])):issues.append('group_sum_differs_from_exact_aggregate_installment')
            groups.append(dict(aggregate_installment_id=group['aggregate_installment_id'],sum=rational(amount),blockers=sorted(set(issues))));blockers.extend(group['aggregate_installment_id']+':'+s for s in issues)
        if mapped!=set(all_installments):blockers.append('exact_all_policy_installment_mapping_required')
    except ArithmeticBudgetError:blockers.append('exact_arithmetic_budget_exceeded')
    if blockers:
        for row in rows:
            row['expense']=None;row['installments']=None
            for a in row['allocations']:a['allocated_expense']=None
        for group in groups:group['sum']=None
    result=dict(component='T93',engine_sha256=ENGINE_SHA256,definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),aggregate_source_sha256=hashlib.sha256(aggregate_raw).hexdigest(),aggregate_run_sha256=parent.sha256,policy_book_sha256=hashlib.sha256(book_raw).hexdigest(),context=p['context'],currency=p['currency'],schedule_id=p['schedule_id'],economic_item_id=p['economic_item_id'],policy_rows=rows,installment_groups=groups,
        totals=None if blockers else dict(premiums=rational(premiums),expense_by_period={k:rational(v)for k,v in period_totals.items()}),blockers=sorted(set(blockers)),state='matched_synthetic_successive_insurance_policies'if not blockers else'PENDING',
        coverage_adequacy_verified=False,contract_or_payment_authority_verified=False,day_count_or_accounting_policy_adopted=False,new_expense_or_payment_generated=False,decision='PENDING',financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False)
    text=canonical(result);return InsuranceRenewalRun(text,digest(text))
