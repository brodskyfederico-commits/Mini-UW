"""T74 staged construction through same-debt operations and sale, without funding twice."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import _object
from .construction_bundle import recover_construction_bundle
from .staged_operating_window import StagedOperatingWindowRun,reconcile_staged_operating_window
from .hold_sale_returns import holding_equity_events
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .cash_risk import summarize_cash_risk

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T72-T75.md'


@dataclass(frozen=True)
class StagedLifecycleReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        v=self.payload['compiled_investor_json'];return None if v is None else v.encode()
    @property
    def investor_run(self):
        v=self.payload['investor_run'];return None if v is None else InvestorReturnsRun(**v)


def assemble_staged_lifecycle_returns(window_args,window_run,investor_raw,binding_raw):
    if type(window_args)is not tuple or len(window_args)!=7 or type(window_run)is not StagedOperatingWindowRun or reconcile_staged_operating_window(*window_args)!=window_run:raise ValidationError('complete staged-construction/operating/debt/sale window must reproduce')
    recovered=recover_construction_bundle(window_args[0]);construction=recovered.run;pre=construction.preopening_run;p=window_run.payload;h=window_args[4].payload;source=parse_investor_returns(investor_raw);b=_object(binding_raw)
    keys={'schema','window_run_sha256','investor_source_sha256','scope_basis_ref','calendar_basis_ref','preopening_slots','operating_slots'}
    if type(b)is not dict or set(b)!=keys or b['schema']!='miniuw.synthetic-staged-lifecycle-return-link.v1':raise ValidationError('exact staged full-lifecycle investor binding required')
    blockers=[];changes=[];compiled=None;run=None;risk=None;maps={};targets=set()
    for key,value in [('window_run_sha256',window_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if type(b[key])is not str or not re.fullmatch('[a-f0-9]{64}',b[key]):raise ValidationError('exact window/investor source hash required')
        if b[key]!=value:blockers.append(key+'_mismatch')
    for key in ['scope_basis_ref','calendar_basis_ref']:
        if b[key]is None:blockers.append(key+'_missing')
        else:nonempty(b[key],key)
    for family in ['preopening_slots','operating_slots']:
        if type(b[family])is not list or len(b[family])>256:raise ValidationError('bounded complete event mapping required')
        maps[family]={}
        for row in b[family]:
            if type(row)is not dict or set(row)!={'source_event_id','investor_event_id'}:raise ValidationError('exact source/target event IDs required')
            a,c=row['source_event_id'],row['investor_event_id'];nonempty(a,'source_event_id');nonempty(c,'investor_event_id')
            if a in maps[family]or c in targets:raise ValidationError('unique source and globally unique target event IDs required')
            maps[family][a]=c;targets.add(c)
    if p['state']!='matched_synthetic_staged_operating_window':blockers.append('staged_operating_cash_or_debt_window_blocked')
    if source['context']!=p['context']or source['currency']!=p['currency']:blockers.append('staged_investor_context_or_currency_mismatch')
    pre_source=json.loads(recovered.preopening_raw)
    if source['grid']['dates'][0]!=pre_source['start_date']or source['grid']['dates'][-1]!=h['terminal_date']:blockers.append('staged_investor_grid_does_not_cover_purchase_to_sale')
    events={e['event_id']:e for e in source['events']}
    if set(events)!=targets:blockers.append('staged_investor_event_inventory_not_exactly_all_gross_events')
    proposed=[]
    if not blockers:
        records={'preopening_slots':[(e,'/exportable_equity_movements/'+str(i))for i,e in enumerate(pre.payload['exportable_equity_movements'])],
            'operating_slots':[(e,e['source_pointer'])for e in holding_equity_events(window_args[4])]}
        hashes={'preopening_slots':pre.sha256,'operating_slots':window_args[4].sha256}
        for family,rows in records.items():
            if set(maps[family])!={e['event_id']for e,_ in rows}:blockers.append(family+':incomplete_gross_source_mapping');continue
            for e,pointer in rows:
                target=events.get(maps[family][e['event_id']])
                if target is None:continue
                if any(target[k]!=e[k]for k in ['kind','category','date','currency']):blockers.append(target['event_id']+':event_metadata_or_date_mismatch')
                if target['amount']is not None:blockers.append(target['event_id']+':target_not_empty')
                if e['date']not in source['grid']['dates']:blockers.append(target['event_id']+':event_not_on_declared_grid')
                proposed.append((target,e,pointer,hashes[family]))
    if not blockers:
        for target,e,pointer,source_run in proposed:
            before=json.loads(canonical(target));target['amount']=e['amount'];target['source_ref']='miniuw:staged-lifecycle:'+source_run+'#'+pointer
            changes.append(dict(source_event_id=e['event_id'],source_run_sha256=source_run,source_pointer=pointer,before=before,after=json.loads(canonical(target))))
        compiled=canonical(source)
        try:
            run=produce_investor_returns(compiled.encode())
            if run.payload['cash_metrics_state']!='computed_synthetic':blockers.append('compiled_staged_investor_cash_blocked')
            else:risk=summarize_cash_risk(compiled.encode(),run)
        except ValidationError:blockers.append('compiled_staged_investor_outside_consumer_contract')
        if blockers:compiled=None;run=None;risk=None;changes=[]
    result={'component':'T74','purpose':'synthetic_staged_construction_to_sale_equity_returns','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'window_run_sha256':window_run.sha256,'binding_source_sha256':hashlib.sha256(binding_raw).hexdigest(),'investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'context':p['context'],'currency':p['currency'],
        'compiled_investor_json':compiled,'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),'investor_run':None if run is None else asdict(run),'cash_risk_run':None if risk is None else asdict(risk),
        'changes':changes,'blockers':sorted(set(blockers)),'window_blockers':p['blockers'],'phase_blockers':p['phase_blockers'],'construction_blockers':p['construction_blockers']+p['construction_cash_blockers'],
        'operating_blockers':p['holding_blockers']+p['sale_debt_blockers'],'state':'compiled_synthetic_staged_purchase_to_sale'if compiled is not None else'blocked',
        'phase_principal_or_opening_cash_counted_as_new_equity':False,'maturity_extension_or_new_funding_generated':False,'personal_investor_return':None,
        'actual_contract_assets_funding_or_payments_verified':False,'financial_model_complete':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return StagedLifecycleReturnRun(encoded,digest(encoded))
