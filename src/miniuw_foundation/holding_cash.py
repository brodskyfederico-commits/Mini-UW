"""T27 declared contiguous operating-period cash plans; no full-project closure."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .operating_cash import OperatingCashRun,parse_operating_cash,reconcile_operating_cash,WORKING,FLOWS
from .operating_cash import definition_sources as cash_definition_sources
from .operating_noi import OperatingNoiRun,_bounded,ArithmeticBudgetError
from .investor_returns import _date
from .debt_service import _fraction,rational

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-holding-cash.v1'
MAX_SOURCE_BYTES=8_388_608


@dataclass(frozen=True,kw_only=True)
class OperatingPeriodEvidence:
    noi_raw:bytes
    noi_run:OperatingNoiRun
    spec_raw:bytes
    cash_run:OperatingCashRun
    def __post_init__(self):
        if type(self.noi_raw)is not bytes or type(self.spec_raw)is not bytes:raise ValidationError('immutable explicit period source bytes required')
        if type(self.noi_run)is not OperatingNoiRun or type(self.cash_run)is not OperatingCashRun:raise ValidationError('typed NOI and cash runs required')


def parse_holding_cash(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit holding manifest required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid holding manifest JSON')from error
    keys={'schema','profile','context','currency','start_date','end_date','calendar_basis_ref','scope_inventory_declared_complete','periods'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA or p['profile']!='contiguous_operating_plans_only':raise ValidationError('exact operating-only holding profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    nonempty(p['currency'],'currency')
    if p['calendar_basis_ref']is not None:nonempty(p['calendar_basis_ref'],'calendar_basis_ref')
    if p['scope_inventory_declared_complete']is not None and type(p['scope_inventory_declared_complete'])is not bool:raise ValidationError('explicit scope declaration or null required')
    if not _date(p['start_date'])<_date(p['end_date']):raise ValidationError('positive explicit holding horizon required')
    if type(p['periods'])is not list or not 1<=len(p['periods'])<=65:raise ValidationError('one to 65 explicit ordered operating periods required')
    seen=set()
    for row in p['periods']:
        if type(row)is not dict or set(row)!={'period_ref','start_date','end_date','cash_date','noi_source_sha256','noi_run_sha256','spec_source_sha256','cash_run_sha256'}:raise ValidationError('exact ordered source/run period inventory required')
        nonempty(row['period_ref'],'period_ref')
        if row['period_ref']in seen:raise ValidationError('duplicate calendar period identity')
        seen.add(row['period_ref'])
        if not _date(row['start_date'])<=_date(row['cash_date'])<_date(row['end_date']):raise ValidationError('cash point outside half-open period')
        for key in ['noi_source_sha256','noi_run_sha256','spec_source_sha256','cash_run_sha256']:
            if type(row[key])is not str or not re.fullmatch('[a-f0-9]{64}',row[key]):raise ValidationError('explicit exact source/run SHA-256 required')
    return p


def definition_sources():return cash_definition_sources()


def verify_period_evidence(periods):
    if type(periods)is not tuple or len(periods)>65 or any(type(e)is not OperatingPeriodEvidence for e in periods):raise ValidationError('bounded immutable tuple of explicit period evidence required')
    if sum(len(e.noi_raw)+len(e.spec_raw)for e in periods)>MAX_SOURCE_BYTES:raise ValidationError('holding source transport budget exceeded')
    sources={}
    for e in periods:
        spec=parse_operating_cash(e.spec_raw);key=spec['period_ref']
        if key in sources:raise ValidationError('duplicate supplied period evidence')
        if reconcile_operating_cash(e.noi_raw,e.noi_run,e.spec_raw)!=e.cash_run:raise ValidationError('every supplied cash period must reproduce, including blocked or extra periods')
        sources[key]=(e,spec)
    return sources


@dataclass(frozen=True)
class HoldingCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_holding_cash(periods,manifest_raw):
    m=parse_holding_cash(manifest_raw);sources=verify_period_evidence(periods);blockers=[];rows=[];checks=[];totals=None;conservation=None;exports=None
    expected={r['period_ref']for r in m['periods']}
    for key in sorted(expected-set(sources)):blockers.append(key+':period_evidence_missing')
    for key in sorted(set(sources)-expected):blockers.append(key+':extra_period_evidence_not_in_calendar')
    if m['calendar_basis_ref']is None:blockers.append('calendar_basis_missing')
    if m['scope_inventory_declared_complete']is not True:blockers.append('operating_calendar_scope_not_declared_complete')
    if m['periods'][0]['start_date']!=m['start_date']:blockers.append('first_period_does_not_start_at_horizon')
    if m['periods'][-1]['end_date']!=m['end_date']:blockers.append('last_period_does_not_end_at_horizon')
    for index,row in enumerate(m['periods']):
        key=row['period_ref'];found=sources.get(key)
        if index and m['periods'][index-1]['end_date']!=row['start_date']:blockers.append(key+':calendar_gap_overlap_or_wrong_order')
        local=[];cash=None
        if found is not None:
            e,spec=found;cash=e.cash_run.payload
            actual={'noi_source_sha256':hashlib.sha256(e.noi_raw).hexdigest(),'noi_run_sha256':e.noi_run.sha256,
                'spec_source_sha256':hashlib.sha256(e.spec_raw).hexdigest(),'cash_run_sha256':e.cash_run.sha256,
                'start_date':cash['start_date'],'end_date':cash['end_date'],'cash_date':cash['cash_date']}
            for field,value in actual.items():
                if row[field]!=value:local.append(field+'_mismatch')
            if cash['context']!=m['context']:local.append('holding_context_mismatch')
            if cash['currency']!=m['currency']:local.append('holding_currency_mismatch')
            if cash['state']!='reconciled_synthetic_plan':local.append('period_cash_plan_blocked')
        rows.append({'period_ref':key,'manifest_entry':row,'cash_run_sha256':None if found is None else found[0].cash_run.sha256,
            'cash_state':None if cash is None else cash['state'],'cash_blockers':[]if cash is None else cash['blockers'],
            'binding_blockers':local,'net_operating_cash':None if cash is None else cash['net_operating_cash'],
            'proposed_distribution':None if cash is None else cash['exportable_operating_distribution'],
            'equity_contribution':None if cash is None else cash['exportable_equity_contribution']})
        blockers.extend(key+':'+b for b in local)
    for previous,current in zip(m['periods'],m['periods'][1:]):
        a=sources.get(previous['period_ref']);b=sources.get(current['period_ref'])
        if a is None or b is None or a[0].cash_run.payload['state']!='reconciled_synthetic_plan'or b[0].cash_run.payload['state']!='reconciled_synthetic_plan':
            blockers.append(current['period_ref']+':balance_continuity_unverifiable');continue
        pairs=[(name,a[1]['working_balances'][name]['closing'],b[1]['working_balances'][name]['opening'])for name in WORKING]
        pairs.extend([(name,a[1]['amounts'][close],b[1]['amounts'][opening])for name,close,opening in [
            ('free_cash','closing_free_cash_claim','opening_free_cash'),('restricted_cash','closing_restricted_cash_claim','opening_restricted_cash')]])
        for name,close,opening in pairs:
            same=_fraction(close['value'])==_fraction(opening['value'])
            checks.append({'previous_period_ref':previous['period_ref'],'next_period_ref':current['period_ref'],'balance':name,
                'previous_closing_claim':close,'next_opening_claim':opening,'equal_exact_value':same})
            if not same:blockers.append(current['period_ref']+':'+name+':opening_does_not_equal_previous_close')
    if not blockers:
        try:
            totals={key:Fraction(0)for key in ['operating_receipts','operating_payments','net_operating_cash']+list(FLOWS)}
            for row in m['periods']:
                e,spec=sources[row['period_ref']];cash=e.cash_run.payload
                for key,output in [('operating_receipts','expected_operating_receipts'),('operating_payments','expected_operating_payments'),('net_operating_cash','net_operating_cash')]:totals[key]=_bounded(totals[key]+_fraction(cash[output],1300))
                for key in FLOWS:totals[key]=_bounded(totals[key]+_fraction(spec['amounts'][key]['value']))
            first=sources[m['periods'][0]['period_ref']][1]['amounts'];last=sources[m['periods'][-1]['period_ref']][1]['amounts']
            for key in ['opening_free_cash','opening_restricted_cash']:totals[key]=_fraction(first[key]['value'])
            for key in ['closing_free_cash_claim','closing_restricted_cash_claim']:totals[key]=_fraction(last[key]['value'])
            conservation=_bounded(totals['opening_free_cash']+totals['opening_restricted_cash']+totals['operating_receipts']+totals['nonfinancing_other_cash_receipt']+totals['equity_contribution']-totals['operating_payments']-totals['debt_principal_payment']-totals['debt_interest_payment']-totals['debt_fee_payment']-totals['capital_expenditure']-totals['other_cash_payment']-totals['planned_operating_distribution']-totals['closing_free_cash_claim']-totals['closing_restricted_cash_claim'])
            if conservation!=0:blockers.append('whole_declared_operating_plan_cash_conservation_mismatch')
            else:exports=[{'period_ref':row['period_ref'],'cash_date':row['cash_date'],'cash_run_sha256':sources[row['period_ref']][0].cash_run.sha256,
                'distribution':sources[row['period_ref']][0].cash_run.payload['exportable_operating_distribution'],
                'contribution':sources[row['period_ref']][0].cash_run.payload['exportable_equity_contribution']}for row in m['periods']]
        except ArithmeticBudgetError:blockers.append('holding_exact_arithmetic_budget_exceeded');totals=None;conservation=None;exports=None
    p={'component':'T27','purpose':'synthetic_declared_operating_period_continuity','engine_sha256':ENGINE_SHA256,
        'manifest_source_sha256':hashlib.sha256(manifest_raw).hexdigest(),'definition_sources':definition_sources(),
        'context':m['context'],'currency':m['currency'],'start_date':m['start_date'],'end_date':m['end_date'],'periods':rows,
        'continuity_checks':checks,'totals':None if totals is None else{k:rational(v)for k,v in totals.items()},
        'cash_conservation_residual':None if conservation is None else rational(conservation),'exportable_equity_movements':exports,
        'blockers':sorted(set(blockers)),'state':'reconciled_synthetic_operating_chain'if exports is not None and not blockers else'blocked',
        'all_supplied_periods_replayed':True,'declared_plan_continuity_reconciled':exports is not None and not blockers,
        'opening_balance_sources_financially_verified':False,'actual_period_inventory_verified':False,'whole_project_cash_reconciled':False,
        'intraperiod_liquidity_verified':False,'debt_cash_schedule_verified':False,'distribution_authorized':False,
        'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return HoldingCashRun(encoded,digest(encoded))
