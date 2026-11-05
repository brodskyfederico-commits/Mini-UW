"""T108 exact T76 stock/payment bridge to T106/T107 insurance settlement."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import json
from .drafts import ValidationError,canonical,digest,nonempty
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError,parse_operating_noi
from .operating_cash import parse_operating_cash,WORKING
from .holding_cash import parse_holding_cash
from .expense_cash_detail import _json,_exact,parse_expense_cash_detail,reconcile_expense_cash_detail
from .expense_checked_lifecycle import _utf8
from .scheduled_expense_case import sha
from .deferred_insurance_settlement import reconcile_deferred_insurance_settlement
from .insurance_terminal_closing import reconcile_insurance_terminal_closing

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T108.md'


@dataclass(frozen=True)
class SettledExpenseBoundaryRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_settled_expense_boundary(periods,sale,holding_raw,raw):
    p=_json(raw,8*1024*1024);_exact(p,{'schema','context','currency','economic_item_id','source_ref','classification_basis_ref',
        'inventory_declared_complete','plan_source_utf8','terminal_binding_source_utf8','periods','payment_map','accounting'})
    if p['schema']!='miniuw.synthetic-settled-expense-boundary.v1':raise ValidationError('exact synthetic settled expense boundary required')
    for key in('economic_item_id','currency'):nonempty(p[key],key)
    for key in('source_ref','classification_basis_ref'):
        if p[key]is not None:nonempty(p[key],key)
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('complete boundary inventory boolean or pending required')
    if type(p['periods'])is not list or not 1<=len(p['periods'])<=64:raise ValidationError('bounded complete expense periods required')
    if type(p['payment_map'])is not list or len(p['payment_map'])>256:raise ValidationError('bounded complete payment mapping required')
    accounting=p['accounting'];_exact(accounting,{'basis_ref','before_payables','after_payables','before_prepaid','after_prepaid'})
    if accounting['basis_ref']is not None:nonempty(accounting['basis_ref'],'accounting basis')
    for key in('before_payables','after_payables','before_prepaid','after_prepaid'):_fraction(accounting[key])
    plan_raw=_utf8(p['plan_source_utf8'],1048576);binding_raw=_utf8(p['terminal_binding_source_utf8'],1048576)
    plan=reconcile_deferred_insurance_settlement(plan_raw);terminal=reconcile_insurance_terminal_closing(plan_raw,sale.closing_raw,binding_raw)
    ps=plan.payload;ts=terminal.payload;calendar=parse_holding_cash(holding_raw);blockers=[];rows=[];checks=[];items_by_period={};previous=None;all_payments={};seen_refs=set()
    if ps['totals']is None:blockers.append('nominal_insurance_plan_blocked')
    if ts['summary']is None:blockers.append('terminal_insurance_closing_blocked')
    if not(p['context']==calendar['context']==ps['context']==ts['context']):blockers.append('boundary_context_mismatch')
    if not(p['currency']==calendar['currency']==ps['currency']==ts['currency']):blockers.append('boundary_currency_mismatch')
    if p['economic_item_id']!=ps['source']['economic_item_id']:blockers.append('boundary_insurance_item_mismatch')
    if calendar['start_date']!=ps['service_window']['start']or calendar['end_date']!=ps['cutoff_date']:blockers.append('exact_full_service_and_operating_window_required')
    for key in('source_ref','classification_basis_ref'):
        if p[key]is None:blockers.append(key+'_missing')
    if accounting['basis_ref']is None:blockers.append('accounting_basis_missing')
    if p['inventory_declared_complete']is not True:blockers.append('complete_boundary_inventory_required')
    ordered=[r['period_ref']for r in calendar['periods']];evidence={e.cash_run.payload['period_ref']:e for e in periods}
    for row in p['periods']:_exact(row,{'period_ref','detail_source_utf8'})
    if [r['period_ref']for r in p['periods']]!=ordered:blockers.append('exact_all_ordered_expense_periods_required')
    for index,row in enumerate(p['periods']):
        period=row['period_ref'];e=evidence.get(period)
        if e is None:blockers.append('unknown_expense_period');continue
        dr=_utf8(row['detail_source_utf8'],1048576);source=parse_expense_cash_detail(dr);run=reconcile_expense_cash_detail(e.noi_raw,e.noi_run,e.spec_raw,e.cash_run,dr);d=run.payload
        if source['period_ref']!=period or d['state']!='matched_synthetic_expense_cash_detail':blockers.append(period+':expense_detail_blocked_or_wrong_period')
        current={};noi=parse_operating_noi(e.noi_raw)
        if d['state']=='matched_synthetic_expense_cash_detail':
            for item in source['items']:
                pointer=item['noi_pointer'];identity='/property_tax'if pointer=='/property_tax'else noi['expense_rows'][int(pointer.rsplit('/',1)[1])]['item_id']
                current[item['item_id']]=(item['kind'],identity,item)
                for pay in item['payments']:
                    key=(period,pay['payment_id'])
                    if pay['payment_id']in{v[1]['payment_id']for v in all_payments.values()}or pay['source_ref']in seen_refs:blockers.append(period+':payment_id_or_reference_reused')
                    all_payments[key]=(item['item_id'],pay);seen_refs.add(pay['source_ref'])
            if previous is not None:
                if set(previous)!=set(current):blockers.append(period+':fixed_item_inventory_changed')
                for item_id in sorted(set(previous)&set(current)):
                    a,b=previous[item_id],current[item_id];same=a[:2]==b[:2];payable=_fraction(a[2]['closing_payables'])==_fraction(b[2]['opening_payables']);prepaid=_fraction(a[2]['closing_prepaid'])==_fraction(b[2]['opening_prepaid'])
                    checks.append(dict(period_ref=period,item_id=item_id,same_economic_item=same,payables_match=payable,prepaid_match=prepaid))
                    if not(same and payable and prepaid):blockers.append(period+':'+item_id+':per_item_continuity_mismatch')
            previous=current;items_by_period[period]=current
        rows.append(dict(period_ref=period,source_sha256=sha(dr),run_sha256=run.sha256,state=d['state'],blockers=d['blockers']))
    # Explicit allocation and payment identities, never a comparison of aggregate totals alone.
    allocations=ps['source']['allocations'];computed_allocations={r['period_ref']:r for r in ps['allocations']}
    if [r['period_ref']for r in allocations]!=ordered:blockers.append('exact_nominal_allocation_period_inventory_required')
    for a in allocations:
        period=a['period_ref'];item=items_by_period.get(period,{}).get(p['economic_item_id']);e=evidence.get(period)
        if item is None or e is None:blockers.append(period+':insurance_item_missing');continue
        cs=parse_operating_cash(e.spec_raw)
        if item[0]!='insurance'or(a['start_date'],a['end_date'])!=(cs['start_date'],cs['end_date']):blockers.append(period+':insurance_kind_or_allocation_window_mismatch')
        expected=computed_allocations.get(period,{}).get('allocated_expense')
        if expected is None or _fraction(item[2]['expense_amount'])!=_fraction(expected,1300):blockers.append(period+':insurance_accrual_differs_from_nominal_plan')
    expected_plan={r['payment_id']:r for r in ps['source']['planned_payments']if r['payment_date']<ps['cutoff_date']};mapped=set();targets=set()
    for row in p['payment_map']:
        _exact(row,{'plan_payment_id','period_ref','detail_payment_id'});a=row['plan_payment_id'];target=(row['period_ref'],row['detail_payment_id'])
        for k in row:nonempty(row[k],k)
        if a in mapped or target in targets:raise ValidationError('unique one-to-one pre-cut payment identities required')
        mapped.add(a);targets.add(target);original=expected_plan.get(a);actual=all_payments.get(target)
        if original is None or actual is None or actual[0]!=p['economic_item_id']:blockers.append('unknown_or_wrong_item_payment_mapping');continue
        if original['payment_date']!=actual[1]['date']or _fraction(original['amount'])!=_fraction(actual[1]['amount']):blockers.append(a+':pre_cut_payment_date_or_amount_mismatch')
    if mapped!=set(expected_plan)or targets!={k for k,v in all_payments.items()if v[0]==p['economic_item_id']}:blockers.append('complete_exact_pre_cut_insurance_payment_mapping_required')
    first=items_by_period.get(ordered[0],{}).get(p['economic_item_id']);last=items_by_period.get(ordered[-1],{}).get(p['economic_item_id']);summary=None
    values={k:_fraction(accounting[k])for k in('before_payables','after_payables','before_prepaid','after_prepaid')}
    if any(v is None or v<0 for v in values.values()):blockers.append('accounting_balances_missing_or_negative')
    if first is None or last is None:blockers.append('opening_or_terminal_insurance_detail_missing')
    else:
        if any(_fraction(first[2][k])!=0 for k in('opening_payables','opening_prepaid')):blockers.append('insurance_opening_stock_requires_other_profile')
        if values['before_payables']!=_fraction(last[2]['closing_payables'])or values['before_prepaid']!=_fraction(last[2]['closing_prepaid']):blockers.append('terminal_accounting_stock_differs_from_T76')
    if any(values[k]!=0 for k in('after_payables','before_prepaid','after_prepaid')):blockers.append('explicit_zero_post_settlement_payables_and_prepaid_required')
    for item_id,row in items_by_period.get(ordered[-1],{}).items():
        if item_id!=p['economic_item_id']and any(_fraction(row[2][k])!=0 for k in('closing_payables','closing_prepaid')):blockers.append(item_id+':other_terminal_obligation_requires_other_profile')
    final=evidence.get(ordered[-1])
    if final:
        cs=parse_operating_cash(final.spec_raw)
        for family in WORKING:
            target=values['before_payables']if family=='payables'else F(0)
            if _fraction(cs['working_balances'][family]['closing']['value'])!=target:blockers.append(family+':terminal_aggregate_not_exact_supported_settlement')
    try:
        if not blockers:
            paid=_bounded(values['before_payables']-values['after_payables']+values['after_prepaid']-values['before_prepaid'])
            if paid!=_fraction(ts['summary']['bound_payment_sum'],1300):blockers.append('accounting_settlement_cash_differs_from_nominal_and_sale')
            else:summary=dict(before_payables=rational(values['before_payables']),after_payables=rational(values['after_payables']),before_prepaid=rational(values['before_prepaid']),after_prepaid=rational(values['after_prepaid']),settlement_cash=rational(paid))
    except ArithmeticBudgetError:blockers.append('boundary_exact_arithmetic_budget_exceeded')
    result=dict(component='T108-boundary',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),
        plan_run_sha256=plan.sha256,terminal_run_sha256=terminal.sha256,context=calendar['context'],currency=calendar['currency'],periods=rows,
        item_continuity_checks=checks,summary=summary,blockers=sorted(set(blockers)),state='matched_synthetic_settled_expense_boundary'if summary is not None else'PENDING',
        accounting_stocks_inferred_from_nominal_tail=False,actual_accounting_or_legal_liability_verified=False,financial_publication_authorized=False,decision='PENDING')
    text=canonical(result);return SettledExpenseBoundaryRun(text,digest(text))
