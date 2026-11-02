"""T26 fill explicitly bound empty investor-event slots from replayed T25 output."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .operating_cash import OperatingCashRun,reconcile_operating_cash
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .debt_service import _fraction

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class OperatingReturnBinding:
    profile_id:str
    investor_source_sha256:str
    cash_spec_sha256:str
    cash_run_sha256:str
    distribution_event_id:str
    contribution_event_id:str|None
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-EMPTY-OPERATING-EQUITY-SLOTS-v1':raise ValidationError('explicit empty-slot-only profile required')
        for key in ['investor_source_sha256','cash_spec_sha256','cash_run_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source/run hashes required')
        nonempty(self.distribution_event_id,'distribution_event_id')
        if self.contribution_event_id is not None:nonempty(self.contribution_event_id,'contribution_event_id')
        if self.distribution_event_id==self.contribution_event_id:raise ValidationError('distinct gross equity slots required')


@dataclass(frozen=True)
class OperatingReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        source=self.payload['compiled_investor_json'];return None if source is None else source.encode()
    @property
    def investor_run(self):
        run=self.payload['investor_run'];return None if run is None else InvestorReturnsRun(**run)


def assemble_operating_returns(noi_raw,noi_run,cash_spec_raw,cash_run,investor_raw,binding):
    if type(binding)is not OperatingReturnBinding:raise ValidationError('explicit operating/investor event binding required')
    if type(cash_run)is not OperatingCashRun or reconcile_operating_cash(noi_raw,noi_run,cash_spec_raw)!=cash_run:raise ValidationError('cash source, upstream NOI and exact run must reproduce')
    source=parse_investor_returns(investor_raw);p=cash_run.payload;blockers=[];compiled=None;run=None;changes=[]
    for key,actual in [('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest()),('cash_spec_sha256',p['spec_source_sha256']),('cash_run_sha256',cash_run.sha256)]:
        if getattr(binding,key)!=actual:blockers.append(key+'_mismatch')
    if source['context']!=p['context']:blockers.append('investor_cash_context_mismatch')
    if source['currency']!=p['currency']:blockers.append('investor_cash_currency_mismatch')
    if p['cash_date']not in source['grid']['dates']:blockers.append('cash_date_not_bound_to_investor_grid')
    if p['state']!='reconciled_synthetic_plan':blockers.append('operating_cash_plan_blocked')
    events={e['event_id']:e for e in source['events']}
    targets=[(binding.distribution_event_id,'distribution',{'operating_distribution'},'exportable_operating_distribution')]
    if binding.contribution_event_id is not None:targets.append((binding.contribution_event_id,'contribution',{'additional_capital'},'exportable_equity_contribution'))
    elif p['exportable_equity_contribution']is not None and _fraction(p['exportable_equity_contribution'],1300)!=0:blockers.append('positive_contribution_requires_explicit_additional_capital_slot')
    for eid,kind,categories,field in targets:
        event=events.get(eid)
        if event is None:blockers.append(eid+':target_event_missing');continue
        if event['kind']!=kind or event['category']not in categories:blockers.append(eid+':wrong_equity_slot_classification')
        if event['date']!=p['cash_date']:blockers.append(eid+':cash_date_mismatch')
        if event['currency']!=p['currency']:blockers.append(eid+':currency_mismatch')
        if event['amount']is not None:blockers.append(eid+':target_amount_not_empty_no_implicit_override')
    if not blockers:
        for eid,kind,categories,field in targets:
            event=events[eid];before=json.loads(canonical(event));event['amount']=p[field]
            event['source_ref']='miniuw:operating-cash:'+cash_run.sha256+'#/'+field
            changes.append({'event_id':eid,'before':before,'after':json.loads(canonical(event)),'cash_output_pointer':'/'+field})
        compiled=canonical(source);compiled_raw=compiled.encode()
        try:run=produce_investor_returns(compiled_raw)
        except ValidationError:compiled=None;blockers.append('compiled_investor_source_outside_consumer_contract')
    payload={'component':'T26','purpose':'synthetic_operating_cash_to_explicit_investor_slots','engine_sha256':ENGINE_SHA256,
        'binding':asdict(binding),'context':p['context'],'cash_run_sha256':cash_run.sha256,
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),
        'compiled_investor_json':compiled,'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'investor_run':None if run is None else asdict(run),'changes':changes,'blockers':sorted(set(blockers)),
        'cash_blockers':p['blockers'],'state':'compiled_synthetic'if compiled is not None else'blocked',
        'cash_producer_replayed':True,'original_source_overwritten':False,'whole_investor_story_complete':False,
        'distribution_authorized':False,'financially_validated':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(payload);return OperatingReturnRun(encoded,digest(encoded))
