"""T65 gross purchase-to-sale equity for a separately supplied no-refinance path."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import _object
from .hold_sale_opening import HoldSaleOpeningRun,reconcile_hold_sale_opening
from .investor_returns import parse_investor_returns,produce_investor_returns,InvestorReturnsRun
from .cash_risk import summarize_cash_risk

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T63-T65.md'


def holding_equity_events(hold_run):
    result=[];p=hold_run.payload
    for i,row in enumerate(p['exportable_equity_movements']or []):
        for kind,field in [('distribution','distribution'),('contribution','contribution')]:
            result.append({'event_id':row['node_id']+':'+kind,'date':row['date'],'kind':kind,
                'category':('operating_distribution'if row['kind']=='operation'else'net_sale_distribution')if kind=='distribution'else'additional_capital',
                'currency':p['currency'],'amount':row[field],'source_pointer':'/exportable_equity_movements/'+str(i)+'/'+field})
    return result


@dataclass(frozen=True)
class HoldSaleReturnRun:
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


def assemble_hold_sale_returns(opening_args,opening_run,investor_raw,binding_raw):
    if type(opening_args)is not tuple or len(opening_args)!=10 or type(opening_run)is not HoldSaleOpeningRun or reconcile_hold_sale_opening(*opening_args)!=opening_run:raise ValidationError('complete no-refinance opening/cash/debt proof must reproduce')
    source=parse_investor_returns(investor_raw);b=_object(binding_raw);p=opening_args[1].payload;h=opening_args[7].payload
    keys={'schema','opening_run_sha256','investor_source_sha256','scope_basis_ref','calendar_basis_ref','preopening_slots','holding_slots'}
    if type(b)is not dict or set(b)!=keys or b['schema']!='miniuw.synthetic-hold-sale-return-link.v1':raise ValidationError('exact no-refinance equity source/target binding required')
    blockers=[];changes=[];compiled=None;run=None;risk=None;maps={};targets=set()
    for key,value in [('opening_run_sha256',opening_run.sha256),('investor_source_sha256',hashlib.sha256(investor_raw).hexdigest())]:
        if type(b[key])is not str or not re.fullmatch('[a-f0-9]{64}',b[key]):raise ValidationError('exact investor/opening source hash required')
        if b[key]!=value:blockers.append(key+'_mismatch')
    for key in ['scope_basis_ref','calendar_basis_ref']:
        if b[key]is None:blockers.append(key+'_missing')
        else:nonempty(b[key],key)
    for key in ['preopening_slots','holding_slots']:
        if type(b[key])is not list or len(b[key])>256:raise ValidationError('bounded exact gross event mapping required')
        maps[key]={}
        for row in b[key]:
            if type(row)is not dict or set(row)!={'source_event_id','investor_event_id'}:raise ValidationError('exact event mapping fields required')
            a,c=row['source_event_id'],row['investor_event_id'];nonempty(a,'source_event_id');nonempty(c,'investor_event_id')
            if a in maps[key]or c in targets:raise ValidationError('unique source and globally unique investor target IDs required')
            maps[key][a]=c;targets.add(c)
    if opening_run.payload['state']!='matched_synthetic_no_refinance_opening':blockers.append('no_refinance_opening_or_cash_or_debt_blocked')
    if source['context']!=p['context']or source['currency']!=p['currency']:blockers.append('no_refinance_investor_context_or_currency_mismatch')
    if source['grid']['dates'][0]!=p['start_date']or source['grid']['dates'][-1]!=h['terminal_date']:blockers.append('no_refinance_investor_horizon_mismatch')
    events={e['event_id']:e for e in source['events']}
    if set(events)!=targets:blockers.append('investor_event_inventory_not_exactly_all_gross_bound_movements')
    proposed=[]
    if not blockers:
        records={'preopening_slots':[(e,'/exportable_equity_movements/'+str(i))for i,e in enumerate(p['exportable_equity_movements'])],
            'holding_slots':[(e,e['source_pointer'])for e in holding_equity_events(opening_args[7])]}
        runs={'preopening_slots':opening_args[1].sha256,'holding_slots':opening_args[7].sha256}
        for family,rows in records.items():
            if set(maps[family])!={e['event_id']for e,_ in rows}:blockers.append(family+':incomplete_gross_source_mapping');continue
            for e,pointer in rows:
                target=events.get(maps[family][e['event_id']])
                if target is None:continue
                if any(target[k]!=e[k]for k in ['kind','category','date','currency']):blockers.append(target['event_id']+':target_metadata_or_date_mismatch')
                if target['amount']is not None:blockers.append(target['event_id']+':target_not_empty')
                if e['date']not in source['grid']['dates']:blockers.append(target['event_id']+':date_not_on_declared_grid')
                proposed.append((target,e,pointer,runs[family]))
    if not blockers:
        for target,e,pointer,source_run in proposed:
            before=json.loads(canonical(target));target['amount']=e['amount'];target['source_ref']='miniuw:no-refinance:'+source_run+'#'+pointer
            changes.append({'source_event_id':e['event_id'],'source_run_sha256':source_run,'source_pointer':pointer,'before':before,'after':json.loads(canonical(target))})
        compiled=canonical(source)
        try:
            run=produce_investor_returns(compiled.encode())
            if run.payload['cash_metrics_state']!='computed_synthetic':blockers.append('compiled_no_refinance_investor_cash_blocked')
            else:risk=summarize_cash_risk(compiled.encode(),run)
        except ValidationError:blockers.append('compiled_no_refinance_outside_consumer_contract')
        if blockers:compiled=None;run=None;risk=None;changes=[]
    result={'component':'T65','purpose':'synthetic_declared_purchase_hold_sale_no_refinance','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'binding_source_sha256':hashlib.sha256(binding_raw).hexdigest(),'opening_run_sha256':opening_run.sha256,'investor_source_sha256':hashlib.sha256(investor_raw).hexdigest(),
        'context':p['context'],'currency':p['currency'],'compiled_investor_json':compiled,'compiled_investor_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'investor_run':None if run is None else asdict(run),'cash_risk_run':None if risk is None else asdict(risk),'changes':changes,'blockers':sorted(set(blockers)),
        'opening_blockers':opening_run.payload['blockers'],'holding_blockers':h['holding_blockers'],'sale_blockers':h['sale_blockers'],'sale_debt_blockers':h['sale_debt_blockers'],'hold_sale_blockers':h['blockers'],
        'state':'compiled_synthetic_no_refinance_return'if compiled is not None else'blocked','opening_cash_counted_as_new_equity':False,'refinance_or_extension_generated':False,
        'financial_scenario_comparison_or_ranking':False,'actual_funding_payments_or_assets_verified':False,'personal_investor_return':None,'financial_model_complete':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return HoldSaleReturnRun(encoded,digest(encoded))
