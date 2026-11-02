"""T34 one investor ledger compiled only after the full declared cash window matches."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .project_cash import ProjectCashRun,reconcile_project_cash
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .debt_service import _fraction
from .operating_noi import _bounded,ArithmeticBudgetError
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True,kw_only=True)
class ProjectEventSlot:
    node_id:str
    distribution_event_id:str
    contribution_event_id:str|None
    def __post_init__(self):
        nonempty(self.node_id,'node_id');nonempty(self.distribution_event_id,'distribution_event_id')
        if self.contribution_event_id is not None:nonempty(self.contribution_event_id,'contribution_event_id')


@dataclass(frozen=True,kw_only=True)
class ProjectReturnBinding:
    profile_id:str
    manifest_source_sha256:str
    project_run_sha256:str
    investor_source_sha256:str
    opening_contribution_event_ids:tuple[str,...]
    slots:tuple[ProjectEventSlot,...]
    def __post_init__(self):
        if self.profile_id!='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1':raise ValidationError('explicit opening-cash-equity and node-event profile required')
        for key in ['manifest_source_sha256','project_run_sha256','investor_source_sha256']:
            value=getattr(self,key)
            if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source/run SHA-256 required')
        if type(self.opening_contribution_event_ids)is not tuple or not 1<=len(self.opening_contribution_event_ids)<=64:raise ValidationError('explicit immutable initial contribution IDs required')
        for value in self.opening_contribution_event_ids:nonempty(value,'opening_contribution_event_id')
        if type(self.slots)is not tuple or not 4<=len(self.slots)<=65 or any(type(s)is not ProjectEventSlot for s in self.slots):raise ValidationError('explicit immutable cash-node slot inventory required')
        nodes=[s.node_id for s in self.slots];events=list(self.opening_contribution_event_ids)+[eid for s in self.slots for eid in [s.distribution_event_id,s.contribution_event_id]if eid is not None]
        if len(set(nodes))!=len(nodes)or len(set(events))!=len(events):raise ValidationError('all node and investor event identities must be unique')


def binding_from_record(p):
    if type(p)is not dict or set(p)!={'profile_id','manifest_source_sha256','project_run_sha256','investor_source_sha256','opening_contribution_event_ids','slots'}or type(p['slots'])is not list or type(p['opening_contribution_event_ids'])is not list:raise ValidationError('exact archived project return binding required')
    return ProjectReturnBinding(**dict(p,opening_contribution_event_ids=tuple(p['opening_contribution_event_ids']),slots=tuple(ProjectEventSlot(**s)for s in p['slots'])))


@dataclass(frozen=True)
class ProjectReturnRun:
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


def assemble_project_returns(periods,closings,manifest_raw,project_run,investor_raw,binding):
    if type(binding)is not ProjectReturnBinding:raise ValidationError('explicit typed project-return binding required')
    source=parse_investor_returns(investor_raw)
    if type(project_run)is not ProjectCashRun or reconcile_project_cash(periods,closings,manifest_raw)!=project_run:raise ValidationError('entire operating/refinance/sale chain must reproduce')
    p=project_run.payload;blockers=[];changes=[];compiled=None;run=None;seed_total=None;seed_claim=None
    for key,actual in [('manifest_source_sha256',p['manifest_source_sha256']),('project_run_sha256',project_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if getattr(binding,key)!=actual:blockers.append(key+'_mismatch')
    if p['state']!='reconciled_synthetic_cash_window':blockers.append('project_cash_window_blocked')
    if source['context']!=p['context']:blockers.append('investor_project_context_mismatch')
    if source['currency']!=p['currency']:blockers.append('investor_project_currency_mismatch')
    if source['grid']['dates'][0]!=p['opening_date']or source['grid']['dates'][-1]!=p['terminal_date']:blockers.append('investor_grid_does_not_cover_exact_declared_cash_window')
    slots={s.node_id:s for s in binding.slots};events={e['event_id']:e for e in source['events']}
    if set(slots)!={n['node_id']for n in p['nodes']}:blockers.append('event_slot_inventory_does_not_match_cash_nodes')
    bound=set(binding.opening_contribution_event_ids)|{eid for s in binding.slots for eid in [s.distribution_event_id,s.contribution_event_id]if eid is not None}
    if set(events)!=bound:blockers.append('investor_event_inventory_not_exactly_seed_and_bound_node_events')
    try:
        seed_total=Fraction(0);valid_seed=True
        for eid in binding.opening_contribution_event_ids:
            event=events.get(eid)
            if event is None:blockers.append(eid+':opening_contribution_event_missing');valid_seed=False;continue
            value=_fraction(event['amount'])
            if event['kind']!='contribution'or event['category']!='initial_capital'or event['date']!=p['opening_date']or event['currency']!=p['currency']or event['source_ref']is None or value is None or value<0:blockers.append(eid+':opening_contribution_metadata_or_value_invalid');valid_seed=False
            else:seed_total=_bounded(seed_total+value)
        if not valid_seed:seed_total=None
        if p['totals']is not None:
            seed_claim=_bounded(_fraction(p['totals']['opening_free_cash'],1300)+_fraction(p['totals']['opening_restricted_cash'],1300))
            if seed_total is not None and seed_total!=seed_claim:blockers.append('initial_contributions_do_not_match_declared_opening_cash')
    except ArithmeticBudgetError:blockers.append('project_opening_equity_arithmetic_budget_exceeded');seed_total=None
    targets=[]
    for row in p['exportable_equity_movements']or []:
        slot=slots.get(row['node_id'])
        if slot is None:continue
        kind=row['kind'];D={'operation':'operating_distribution','refinance':'net_refinance_distribution','sale':'net_sale_distribution'}[kind]
        A='refinance_cash_in'if kind=='refinance'else'additional_capital'
        if row['date']not in source['grid']['dates']:blockers.append(row['node_id']+':cash_date_not_bound_to_investor_grid')
        prefix='miniuw:operating-cash:'if kind=='operation'else'miniuw:closing-cash:'
        refs=[(slot.distribution_event_id,'distribution',D,'distribution','exportable_operating_distribution'if kind=='operation'else'exportable_equity_distribution')]
        if slot.contribution_event_id is not None:refs.append((slot.contribution_event_id,'contribution',A,'contribution','exportable_equity_contribution'))
        elif _fraction(row['contribution'],1300)>0:blockers.append(row['node_id']+':positive_contribution_requires_separate_gross_slot')
        for eid,event_kind,category,field,pointer in refs:
            e=events.get(eid)
            if e is None:blockers.append(eid+':target_event_missing');continue
            if e['kind']!=event_kind or e['category']!=category or e['date']!=row['date']or e['currency']!=p['currency']:blockers.append(eid+':cash_event_classification_date_or_currency_mismatch')
            if e['amount']is not None:blockers.append(eid+':target_not_empty_no_implicit_override')
            targets.append((e,row,field,prefix,pointer))
    if not blockers:
        for e,row,field,prefix,pointer in targets:
            before=json.loads(canonical(e));e['amount']=row[field];e['source_ref']=prefix+row['run_sha256']+'#/'+pointer
            changes.append({'node_id':row['node_id'],'event_id':e['event_id'],'before':before,'after':json.loads(canonical(e)),'source_run_sha256':row['run_sha256'],'output_pointer':'/'+pointer})
        compiled=canonical(source)
        try:run=produce_investor_returns(compiled.encode())
        except ValidationError:compiled=None;blockers.append('compiled_investor_source_outside_consumer_contract')
    result={'component':'T34','purpose':'synthetic_integrated_cash_window_to_investor_return','engine_sha256':ENGINE_SHA256,'binding':asdict(binding),'context':p['context'],'project_run_sha256':project_run.sha256,
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'opening_contributions':None if seed_total is None else{'numerator':str(seed_total.numerator),'denominator':str(seed_total.denominator)},
        'declared_opening_cash':None if seed_claim is None else{'numerator':str(seed_claim.numerator),'denominator':str(seed_claim.denominator)},'compiled_investor_json':compiled,'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),'investor_run':None if run is None else asdict(run),'changes':changes,
        'blockers':sorted(set(blockers)),'project_cash_blockers':p['blockers'],'state':'compiled_synthetic'if compiled is not None else'blocked','all_sources_replayed':True,'original_source_overwritten':False,'whole_project_cash_reconciled':False,'whole_investor_story_complete':False,'actual_cash_and_payment_history_verified':False,'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(result);return ProjectReturnRun(encoded,digest(encoded))
