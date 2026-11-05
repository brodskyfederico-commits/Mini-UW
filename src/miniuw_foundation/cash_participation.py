"""T104 hypothetical supplied constant-share gross cash, no verified personal return."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import json
from .drafts import ValidationError,canonical,digest,nonempty
from .expense_cash_detail import _json,_exact
from .debt_service import _fraction,rational
from .investor_returns import _date,CATEGORIES
from .operating_noi import _bounded,ArithmeticBudgetError
from .scheduled_expense_case import sha
from .worksheet_case_output import WorksheetCaseRun,assemble_worksheet_case
from .primitive_periodic_returns import isolate_primitive_periodic_returns,ENGINE_SHA256 as ROOT_ENGINE_SHA256
from .irr_checked_output import _current_annual_roots,ENGINE_SHA256 as ANNUAL_ENGINE_SHA256

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T104.md'
SCHEMA='miniuw.synthetic-cash-participation-terms.v1'
PROFILE='constant_fraction_of_every_project_equity_cash_event'
ASSUMPTIONS=dict(same_fraction_for_all_contributions_and_distributions=True,
    fees_promotes_taxes_or_priority_adjustments=False,amounts_are='hypothetical_gross_cash_only')


def parse_terms(raw):
    p=_json(raw,65536)
    _exact(p,{'schema','profile','terms_id','terms_revision','source_hashes','worksheet_run_sha256','context',
        'currency','allocation_start_date','allocation_end_date','share_unit','participant_inventory_complete',
        'whole_ledger_scope_ref','source_ref','assumptions','participants'})
    if p['schema']!=SCHEMA or p['profile']!=PROFILE:raise ValidationError('explicit supported synthetic cash-share profile required')
    nonempty(p['terms_id'],'terms_id')
    if not p['terms_id'].startswith('SYNTHETIC-')or type(p['terms_revision'])is not int or p['terms_revision']<1:raise ValidationError('synthetic terms and explicit revision required')
    _exact(p['source_hashes'],{'case','workbook','binding'})
    for value in [p['worksheet_run_sha256'],*p['source_hashes'].values()]:
        if type(value)is not str or len(value)!=64 or any(c not in'0123456789abcdef'for c in value):raise ValidationError('exact lowercase source/run SHA256 required')
    if type(p['context'])is not dict:raise ValidationError('explicit context required')
    for key in('currency','share_unit','whole_ledger_scope_ref','source_ref'):
        if p[key]is not None:nonempty(p[key],key)
    for key in('allocation_start_date','allocation_end_date'):
        if p[key]is not None:_date(p[key])
    if p['participant_inventory_complete']is not None and type(p['participant_inventory_complete'])is not bool:raise ValidationError('boolean or pending participant inventory required')
    _exact(p['assumptions'],set(ASSUMPTIONS))
    for key in('same_fraction_for_all_contributions_and_distributions','fees_promotes_taxes_or_priority_adjustments'):
        if p['assumptions'][key]is not None and type(p['assumptions'][key])is not bool:raise ValidationError('explicit boolean or pending cash-share assumptions required')
    if p['assumptions']['amounts_are']is not None:nonempty(p['assumptions']['amounts_are'],'amounts_are')
    if type(p['participants'])is not list or not 1<=len(p['participants'])<=4:raise ValidationError('one to four explicit synthetic participants required')
    ids=set()
    for row in p['participants']:
        _exact(row,{'participant_id','share_fraction','source_ref'})
        nonempty(row['participant_id'],'participant_id')
        if not row['participant_id'].startswith('SYNTHETIC-')or row['participant_id']in ids:raise ValidationError('unique synthetic participant IDs required')
        ids.add(row['participant_id']);_fraction(row['share_fraction'])
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    return p


def _blockers(p,parent):
    view=parent.payload;story=view['current_project_return_story'];issues=[];shares=[]
    if p['source_hashes']!=view['worksheet_reconciliation']['source_hashes']:issues.append('exact_case_workbook_binding_hashes_mismatch')
    if p['worksheet_run_sha256']!=parent.sha256:issues.append('exact_current_worksheet_run_mismatch')
    if p['context']!=view['context']:issues.append('context_mismatch')
    if p['share_unit']!='fraction':issues.append('explicit_fraction_unit_required')
    if p['participant_inventory_complete']is not True:issues.append('complete_participant_inventory_required')
    if p['whole_ledger_scope_ref']is None:issues.append('whole_ledger_allocation_scope_missing')
    if p['source_ref']is None:issues.append('declared_terms_source_missing')
    for key,value in ASSUMPTIONS.items():
        if canonical(p['assumptions'][key])!=canonical(value):issues.append('missing_or_unsupported_assumption:'+key)
    if story is None:issues.append('current_project_cash_unavailable')
    else:
        if p['currency']!=story['currency']:issues.append('currency_missing_or_mismatch')
        if p['allocation_start_date']!=story['cash_horizon']['start']or p['allocation_end_date']!=story['cash_horizon']['end']:
            issues.append('complete_identical_cash_window_required')
    for row in p['participants']:
        f=_fraction(row['share_fraction']);shares.append(f)
        if f is None:issues.append(row['participant_id']+':share_missing')
        elif not 0<=f<=1:issues.append(row['participant_id']+':share_outside_zero_one')
        if row['source_ref']is None:issues.append(row['participant_id']+':source_ref_missing')
    if all(f is not None for f in shares)and _bounded(sum(shares,F(0)))!=1:issues.append('supplied_shares_must_sum_exactly_one')
    return sorted(set(issues)),shares


def _allocate(story,evidence,terms,shares):
    dates=evidence['grid']['dates'];params=evidence['parameters'];outputs=[]
    categories=sorted(k for values in CATEGORIES.values()for k in values)
    q=rational
    for index,(participant,fraction)in enumerate(zip(terms['participants'],shares)):
        events=[];flows={d:F(0)for d in dates};totals={key:F(0)for key in categories}
        years={y:dict(contributions=F(0),distributions=F(0),operating_distributions=F(0))for y in
            range(_date(story['cash_horizon']['start']).year,_date(story['cash_horizon']['end']).year+1)}
        a=d=F(0)
        for i,event in enumerate(story['dated_events']):
            amount=_bounded(_fraction(event['amount'],1300)*fraction);sign=1 if event['kind']=='distribution'else-1
            events.append(dict(event,amount=q(amount),project_event_pointer='/current_project_return_story/dated_events/'+str(i),
                project_amount=event['amount'],allocation_share_pointer='/participants/'+str(index)+'/share_fraction'))
            flows[event['date']]=_bounded(flows[event['date']]+sign*amount)
            totals[event['category']]=_bounded(totals[event['category']]+amount)
            year=years[_date(event['date']).year]
            if sign<0:a=_bounded(a+amount);year['contributions']=_bounded(year['contributions']+amount)
            else:
                d=_bounded(d+amount);year['distributions']=_bounded(year['distributions']+amount)
                if event['category']=='operating_distribution':year['operating_distributions']=_bounded(year['operating_distributions']+amount)
        source_flows=evidence['dated_net_flows']
        if [r['date']for r in source_flows]!=dates or any(flows[r['date']]!=_bounded(_fraction(r['net'],1300)*fraction)for r in source_flows):
            raise ValidationError('allocated gross ledger does not reproduce full dated scalar identity')
        roots=isolate_primitive_periodic_returns([flows[date]for date in dates],_fraction(params['max_periodic_rate_interval_width']),params['split_budget'],params['operation_budget'])
        annual,attempted,annual_blockers=_current_annual_roots(roots,params['periods_per_year'],evidence['grid']['step_months'])
        outputs.append(dict(participant_id=participant['participant_id'],scope='hypothetical_cash_allocation_not_verified_personal_return',
            share_fraction=q(fraction),source_ref=participant['source_ref'],currency=story['currency'],cash_horizon=story['cash_horizon'],
            dated_events=events,dated_net_flows=[dict(date=date,net=q(flows[date]))for date in dates],
            gross_contributions=q(a),gross_distributions=q(d),net_cash_profit=q(_bounded(d-a)),equity_multiple=q(_bounded(d/a))if a>0 else None,
            equity_multiple_state='computed_synthetic'if a>0 else'undefined_zero_contributions',cash_by_category={k:q(v)for k,v in totals.items()},
            annual_cash=[dict(calendar_cash_receipt_year=y,gross_contributions=q(v['contributions']),gross_distributions=q(v['distributions']),
                net_cash_profit=q(_bounded(v['distributions']-v['contributions'])),operating_distributions_only=q(v['operating_distributions']))for y,v in years.items()],
            periodic_IRR=roots,annual_IRR_roots=annual,attempted_annual_IRR_roots=attempted,annualization_blockers=annual_blockers,
            positive_scalar_net_flow_identity_verified=fraction>0,selected_IRR=None,capital_still_invested=None,retained_equity_value=None,
            conditional_CoC=None,verified_personal_investor_return=None,verified_personal_investor_return_state='PENDING'))
    checks=[]
    for i,event in enumerate(story['dated_events']):
        amount=_bounded(sum((_fraction(row['dated_events'][i]['amount'],1300)for row in outputs),F(0)))
        if amount!=_fraction(event['amount'],1300):raise ValidationError('participant gross allocations do not reconcile by event')
        checks.append(dict(project_event_id=event['event_id'],project_event_index=i,project_amount=event['amount'],allocated_amount=q(amount)))
    totals={key:q(_bounded(sum((_fraction(row[key],1300)for row in outputs),F(0))))for key in('gross_contributions','gross_distributions','net_cash_profit')}
    if any(totals[k]!=story[k]for k in totals):raise ValidationError('participant gross/net totals do not reconcile to project')
    annual_checks=[]
    for index,year in enumerate(story['annual_cash_receipts']):
        mapping={'gross_contributions':'gross_contributions','gross_distributions':'gross_distributions',
            'net_cash_profit':'net_equity_cash','operating_distributions_only':'operating_distributions_only'}
        values={key:q(_bounded(sum((_fraction(row['annual_cash'][index][key],1300)for row in outputs),F(0))))for key in mapping}
        if any(row['annual_cash'][index]['calendar_cash_receipt_year']!=year['calendar_cash_receipt_year']for row in outputs)or any(values[k]!=year[v]for k,v in mapping.items()):
            raise ValidationError('participant annual cash does not reconcile to project year')
        annual_checks.append(dict(year=year['calendar_cash_receipt_year'],allocated=values))
    category_totals={key:q(_bounded(sum((_fraction(row['cash_by_category'][key],1300)for row in outputs),F(0))))for key in categories}
    if category_totals!=story['cash_by_category']:raise ValidationError('participant categories do not reconcile to project')
    return outputs,dict(event_checks=checks,totals=totals,annual_checks=annual_checks,category_totals=category_totals,
        all_events_allocated_once_per_participant=True,every_project_event_reconciled=True,
        project_cash_modified=False,rounding_policy_adopted=False)


@dataclass(frozen=True)
class CashParticipationRun:
    payload_json:str
    sha256:str
    parent_run:WorksheetCaseRun
    @property
    def payload(self):return json.loads(self.payload_json)


def _from_verified_parent(terms_raw,parent):
    terms=parse_terms(terms_raw);view=parent.payload;outputs=reconciliation=None
    try:
        blockers,shares=_blockers(terms,parent)
        if not blockers:outputs,reconciliation=_allocate(view['current_project_return_story'],view['irr_recalculation'],terms,shares)
    except ArithmeticBudgetError:
        blockers=['cash_allocation_exact_arithmetic_budget_exceeded'];outputs=reconciliation=None
    result=dict(component='T104',scope='hypothetical_explicit_cash_participation_only',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),root_engine_sha256=ROOT_ENGINE_SHA256,annual_engine_sha256=ANNUAL_ENGINE_SHA256,
        terms_sha256=sha(terms_raw),terms=terms,parent_worksheet_run_sha256=parent.sha256,context=view['context'],
        state='computed_synthetic_cash_allocation'if outputs is not None else'PENDING',blockers=blockers,
        participants=outputs,reconciliation=reconciliation,parent_current_story_available=view['current_project_return_story']is not None,
        new_criteria_applied=False,participant_or_fraction_selected=False,parent_case_or_worksheet_modified=False,
        source_or_contract_authority_authenticated=False,allocation_terms_adopted=False,personal_investor_return_verified=False,
        verified_personal_investor_return=None,verified_personal_investor_return_state='PENDING',
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(result);return CashParticipationRun(value,digest(value),parent)


def assemble_cash_participation(case_raw,workbook_raw,binding_raw,terms_raw):
    parse_terms(terms_raw)
    return _from_verified_parent(terms_raw,assemble_worksheet_case(case_raw,workbook_raw,binding_raw))
