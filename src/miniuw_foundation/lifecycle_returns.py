"""T59 declared purchase-to-sale gross equity, excluding the operating cash seed."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import _object
from .opening_debt import OpeningDebtRun,reconcile_opening_debt
from .capacity_project_returns import CapacityProjectReturnRun,assemble_capacity_checked_returns
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .cash_risk import summarize_cash_risk

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T59.md'


@dataclass(frozen=True)
class LifecycleReturnRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        value=self.payload['compiled_investor_json'];return None if value is None else value.encode()
    @property
    def investor_run(self):
        value=self.payload['investor_run'];return None if value is None else InvestorReturnsRun(**value)


def assemble_lifecycle_returns(opening_args,opening_run,capacity_args,capacity_run,investor_raw,binding_raw):
    if type(opening_args)is not tuple or len(opening_args)!=8 or type(capacity_args)is not tuple or len(capacity_args)!=9:raise ValidationError('complete immutable opening and capacity argument tuples required')
    if type(opening_run)is not OpeningDebtRun or reconcile_opening_debt(*opening_args)!=opening_run:raise ValidationError('complete opening debt/cash proof must reproduce')
    if type(capacity_run)is not CapacityProjectReturnRun or assemble_capacity_checked_returns(*capacity_args)!=capacity_run:raise ValidationError('complete capacity-checked operating return must reproduce')
    source=parse_investor_returns(investor_raw);binding=_object(binding_raw)
    keys={'schema','opening_debt_run_sha256','capacity_project_run_sha256','investor_source_sha256','equity_scope_basis_ref','calendar_basis_ref','preopening_slots','operating_slots'}
    if type(binding)is not dict or set(binding)!=keys or binding['schema']!='miniuw.synthetic-lifecycle-return-link.v1':raise ValidationError('exact lifecycle return binding required')
    blockers=[];changes=[];compiled=None;run=None;risk=None
    for key,value in [('opening_debt_run_sha256',opening_run.sha256),('capacity_project_run_sha256',capacity_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if type(binding[key])is not str or not re.fullmatch('[a-f0-9]{64}',binding[key]):raise ValidationError('exact lifecycle source/run hash required')
        if binding[key]!=value:blockers.append(key+'_mismatch')
    for key in ['equity_scope_basis_ref','calendar_basis_ref']:
        if binding[key]is None:blockers.append(key+'_missing')
        else:nonempty(binding[key],key)
    maps={};targets=set()
    for key in ['preopening_slots','operating_slots']:
        if type(binding[key])is not list or len(binding[key])>256:raise ValidationError('bounded explicit source-to-target event mapping required')
        maps[key]={}
        for row in binding[key]:
            if type(row)is not dict or set(row)!={'source_event_id','investor_event_id'}:raise ValidationError('exact source/target event IDs required')
            a,b=row['source_event_id'],row['investor_event_id'];nonempty(a,'source_event_id');nonempty(b,'investor_event_id')
            if a in maps[key]or b in targets:raise ValidationError('unique source and globally unique target events required')
            maps[key][a]=b;targets.add(b)
    pre=opening_args[1].payload;p=opening_args[5].payload
    if opening_run.payload['state']!='matched_synthetic_opening_debt_and_cash':blockers.append('opening_debt_or_cash_blocked')
    if capacity_run.payload['state']!='compiled_synthetic':blockers.append('capacity_checked_operating_return_blocked')
    if opening_args[2:6]!=capacity_args[:4]:blockers.append('opening_and_capacity_project_sources_or_runs_differ')
    if source['context']!=pre['context']or source['currency']!=pre['currency']:blockers.append('lifecycle_investor_context_or_currency_mismatch')
    if source['grid']['dates'][0]!=pre['start_date']or source['grid']['dates'][-1]!=p['terminal_date']:blockers.append('lifecycle_investor_grid_does_not_cover_exact_purchase_to_sale_horizon')
    events={e['event_id']:e for e in source['events']}
    if set(events)!=targets:blockers.append('lifecycle_event_inventory_not_exactly_all_bound_gross_events')
    proposed=[]
    if not blockers:
        old=capacity_run.investor_run
        if old is None or old.payload['cash_metrics_state']!='computed_synthetic':blockers.append('operating_investor_cash_metrics_blocked')
        else:
            inner=capacity_args[8].project_return_binding
            node_ids={eid for slot in inner.slots for eid in [slot.distribution_event_id,slot.contribution_event_id]if eid is not None}
            records={'preopening_slots':{e['event_id']:(e,'/exportable_equity_movements/'+str(i))for i,e in enumerate(pre['exportable_equity_movements'])},
                'operating_slots':{e['event_id']:(e,'/events/'+str(i))for i,e in enumerate(old.payload['events'])if e['event_id']in node_ids}}
            source_runs={'preopening_slots':opening_args[1].sha256,'operating_slots':old.sha256}
            for key,rows in records.items():
                if set(maps[key])!=set(rows):blockers.append(key+':source_inventory_not_exactly_all_equity_movements');continue
                for eid,(original,pointer) in rows.items():
                    target_id=maps[key][eid];target=events.get(target_id)
                    if target is None:continue
                    if any(target[k]!=original[k]for k in ['kind','category','date','currency']):blockers.append(target_id+':gross_event_metadata_or_date_mismatch')
                    if target['amount']is not None:blockers.append(target_id+':target_not_empty_no_implicit_override')
                    if original['date']not in source['grid']['dates']:blockers.append(target_id+':date_not_on_declared_lifecycle_grid')
                    proposed.append((target,original,key,source_runs[key],pointer))
    if not blockers:
        for target,original,key,source_run,pointer in proposed:
            before=json.loads(canonical(target));target['amount']=original['amount']
            target['source_ref']='miniuw:lifecycle:'+source_run+'#'+pointer
            changes.append({'source_family':key,'source_event_id':original['event_id'],'source_run_sha256':source_run,'source_pointer':pointer,'before':before,'after':json.loads(canonical(target))})
        compiled=canonical(source)
        try:
            run=produce_investor_returns(compiled.encode())
            if run.payload['cash_metrics_state']!='computed_synthetic':blockers.append('lifecycle_investor_cash_metrics_blocked')
            else:risk=summarize_cash_risk(compiled.encode(),run)
        except ValidationError:blockers.append('compiled_lifecycle_outside_investor_consumer_contract')
        if blockers:compiled=None;run=None;risk=None;changes=[]
    result={'component':'T59','purpose':'synthetic_declared_purchase_to_sale_equity_cash','engine_sha256':ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'binding_source_sha256':hashlib.sha256(binding_raw).hexdigest(),
        'opening_debt_run_sha256':opening_run.sha256,'capacity_project_run_sha256':capacity_run.sha256,
        'original_investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),'context':pre['context'],'currency':pre['currency'],
        'compiled_investor_json':compiled,'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'investor_run':None if run is None else asdict(run),'cash_risk_run':None if risk is None else asdict(risk),'changes':changes,
        'opening_blockers':opening_run.payload['blockers'],'capacity_blockers':capacity_run.payload['blockers'],'blockers':sorted(set(blockers)),
        'state':'compiled_synthetic_purchase_to_sale'if compiled is not None else'blocked','operating_opening_cash_counted_as_new_equity':False,
        'declared_purchase_to_sale_cash_scope_connected':compiled is not None,'all_sources_replayed':True,
        'asset_basis_and_full_economic_close_verified':False,'actual_payments_and_funding_verified':False,'personal_investor_return':None,
        'financial_model_complete':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return LifecycleReturnRun(encoded,digest(encoded))
