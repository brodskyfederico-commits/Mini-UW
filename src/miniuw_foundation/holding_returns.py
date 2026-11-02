"""T28 atomic-in-memory empty-slot compilation from one replayed holding chain."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .holding_cash import HoldingCashRun,reconcile_holding_cash
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .debt_service import _fraction

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class HoldingEventSlot:
    period_ref:str
    distribution_event_id:str
    contribution_event_id:str|None
    def __post_init__(self):
        nonempty(self.period_ref,'period_ref');nonempty(self.distribution_event_id,'distribution_event_id')
        if self.contribution_event_id is not None:nonempty(self.contribution_event_id,'contribution_event_id')


@dataclass(frozen=True,kw_only=True)
class HoldingReturnBinding:
    profile_id:str
    manifest_source_sha256:str
    holding_run_sha256:str
    investor_source_sha256:str
    slots:tuple[HoldingEventSlot,...]
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-HOLDING-EMPTY-EQUITY-SLOTS-v1':raise ValidationError('explicit holding empty-slot-only profile required')
        for key in ['manifest_source_sha256','holding_run_sha256','investor_source_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source/run hashes required')
        if type(self.slots)is not tuple or not 1<=len(self.slots)<=65 or any(type(s)is not HoldingEventSlot for s in self.slots):raise ValidationError('immutable explicit event-slot inventory required')
        periods=[s.period_ref for s in self.slots];events=[eid for s in self.slots for eid in [s.distribution_event_id,s.contribution_event_id]if eid is not None]
        if len(set(periods))!=len(periods)or len(set(events))!=len(events):raise ValidationError('period/event slots must be unique across the entire chain')


def binding_from_record(p):
    if type(p)is not dict or set(p)!={'profile_id','manifest_source_sha256','holding_run_sha256','investor_source_sha256','slots'}or type(p['slots'])is not list:raise ValidationError('exact archived holding binding required')
    return HoldingReturnBinding(**dict(p,slots=tuple(HoldingEventSlot(**s)for s in p['slots'])))


@dataclass(frozen=True)
class HoldingReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        p=self.payload['compiled_investor_json'];return None if p is None else p.encode()
    @property
    def investor_run(self):
        p=self.payload['investor_run'];return None if p is None else InvestorReturnsRun(**p)


def assemble_holding_returns(periods,manifest_raw,holding_run,investor_raw,binding):
    if type(binding)is not HoldingReturnBinding:raise ValidationError('explicit holding-to-investor binding required')
    if type(holding_run)is not HoldingCashRun or reconcile_holding_cash(periods,manifest_raw)!=holding_run:raise ValidationError('full holding plan and all supplied periods must reproduce')
    source=parse_investor_returns(investor_raw);h=holding_run.payload;blockers=[];changes=[];compiled=None;run=None
    for key,actual in [('manifest_source_sha256',h['manifest_source_sha256']),('holding_run_sha256',holding_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if getattr(binding,key)!=actual:blockers.append(key+'_mismatch')
    if h['state']!='reconciled_synthetic_operating_chain':blockers.append('holding_chain_blocked')
    if source['context']!=h['context']:blockers.append('investor_holding_context_mismatch')
    if source['currency']!=h['currency']:blockers.append('investor_holding_currency_mismatch')
    expected={p['period_ref']for p in h['periods']};slots={s.period_ref:s for s in binding.slots}
    if set(slots)!=expected:blockers.append('event_binding_inventory_does_not_match_calendar')
    events={e['event_id']:e for e in source['events']};targets=[];bound_ids={eid for s in binding.slots for eid in [s.distribution_event_id,s.contribution_event_id]if eid is not None}
    for event in source['events']:
        if h['start_date']<=event['date']<h['end_date']and event['category']in {'operating_distribution','additional_capital'}and event['event_id']not in bound_ids:blockers.append(event['event_id']+':unbound_operating_or_additional_equity_event_in_horizon')
    outside=[e['event_id']for e in source['events']if e['event_id']not in bound_ids]
    for row in h['exportable_equity_movements']or []:
        slot=slots.get(row['period_ref'])
        if slot is None:continue
        if row['cash_date']not in source['grid']['dates']:blockers.append(row['period_ref']+':cash_date_not_bound_to_investor_grid')
        refs=[(slot.distribution_event_id,'distribution','operating_distribution','distribution','exportable_operating_distribution')]
        if slot.contribution_event_id is not None:refs.append((slot.contribution_event_id,'contribution','additional_capital','contribution','exportable_equity_contribution'))
        elif _fraction(row['contribution'],1300)!=0:blockers.append(row['period_ref']+':positive_contribution_requires_explicit_additional_capital_slot')
        for eid,kind,category,field,pointer in refs:
            e=events.get(eid)
            if e is None:blockers.append(eid+':target_event_missing');continue
            if e['kind']!=kind or e['category']!=category:blockers.append(eid+':wrong_equity_slot_classification')
            if e['date']!=row['cash_date']:blockers.append(eid+':cash_date_mismatch')
            if e['currency']!=h['currency']:blockers.append(eid+':currency_mismatch')
            if e['amount']is not None:blockers.append(eid+':target_amount_not_empty_no_implicit_override')
            targets.append((e,row,field,pointer))
    if not blockers:
        for event,row,field,pointer in targets:
            before=json.loads(canonical(event));event['amount']=row[field];event['source_ref']='miniuw:operating-cash:'+row['cash_run_sha256']+'#/'+pointer
            changes.append({'period_ref':row['period_ref'],'event_id':event['event_id'],'before':before,'after':json.loads(canonical(event)),'cash_run_sha256':row['cash_run_sha256'],'cash_output_pointer':'/'+pointer})
        compiled=canonical(source)
        try:run=produce_investor_returns(compiled.encode())
        except ValidationError:compiled=None;blockers.append('compiled_investor_source_outside_consumer_contract')
    p={'component':'T28','purpose':'synthetic_holding_operating_equity_to_returns','engine_sha256':ENGINE_SHA256,
        'binding':asdict(binding),'holding_run_sha256':holding_run.sha256,'context':h['context'],
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'compiled_investor_json':compiled,
        'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'investor_run':None if run is None else asdict(run),'changes':changes,'events_outside_this_operating_binding':outside,
        'blockers':sorted(set(blockers)),'holding_blockers':h['blockers'],'state':'compiled_synthetic'if compiled is not None else'blocked',
        'all_operating_targets_checked_before_compilation':True,'original_source_overwritten':False,
        'whole_project_cash_reconciled':False,'whole_investor_story_complete':False,'distribution_authorized':False,
        'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return HoldingReturnRun(encoded,digest(encoded))
