"""T69 fill only explicit empty debt-cash slots, then reconcile unchanged T57."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .construction_draws import ConstructionDrawRun,produce_construction_draws
from .preopening_cash import PreopeningCashRun,parse_preopening_cash,reconcile_preopening_cash,_object,LOAN_CATEGORIES

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T68-T69.md'


@dataclass(frozen=True,kw_only=True)
class ConstructionLoanEvidence:
    raw:bytes
    run:ConstructionDrawRun
    def __post_init__(self):
        if type(self.raw)is not bytes or type(self.run)is not ConstructionDrawRun:raise ValidationError('immutable complete staged loan source/run required')


@dataclass(frozen=True)
class ConstructionCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        value=self.payload['compiled_preopening_json'];return None if value is None else value.encode()
    @property
    def preopening_run(self):
        value=self.payload['preopening_run'];return None if value is None else PreopeningCashRun(**value)


def assemble_construction_cash(loans,preopening_raw,binding_raw):
    if type(loans)is not tuple or not 1<=len(loans)<=32 or any(type(e)is not ConstructionLoanEvidence for e in loans):raise ValidationError('one to 32 immutable staged loan evidence records required')
    if sum(len(e.raw)for e in loans)>8_388_608:raise ValidationError('staged loan source transport budget exceeded')
    sources={}
    for e in loans:
        if produce_construction_draws(e.raw)!=e.run:raise ValidationError('all staged loan source/results must fully reproduce')
        loan=e.run.payload['loan_id']
        if loan in sources:raise ValidationError('duplicate staged loan identity')
        sources[loan]=e
    pre=parse_preopening_cash(preopening_raw);b=_object(binding_raw);keys={'schema','preopening_source_sha256','scope_basis_ref','loans','event_slots'}
    if type(b)is not dict or set(b)!=keys or b['schema']!='miniuw.synthetic-construction-cash-link.v1':raise ValidationError('exact staged-loan to preopening binding required')
    def sha(value):
        if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source/run hash required')
    sha(b['preopening_source_sha256']);blockers=[];bindings={};slots={};targets=set();proposed=[];changes=[];compiled=None;run=None;loan_blockers={}
    if b['preopening_source_sha256']!=hashlib.sha256(preopening_raw).hexdigest():blockers.append('preopening_source_sha256_mismatch')
    if b['scope_basis_ref']is None:blockers.append('staged_cash_scope_basis_missing')
    else:nonempty(b['scope_basis_ref'],'scope_basis_ref')
    if type(b['loans'])is not list or len(b['loans'])>32:raise ValidationError('bounded exact staged loan binding inventory required')
    for row in b['loans']:
        if type(row)is not dict or set(row)!={'loan_id','source_sha256','run_sha256'}:raise ValidationError('exact staged loan binding required')
        nonempty(row['loan_id'],'loan_id');sha(row['source_sha256']);sha(row['run_sha256'])
        if row['loan_id']in bindings:raise ValidationError('duplicate staged loan binding')
        bindings[row['loan_id']]=row
    if set(bindings)!=set(sources)or set(sources)!=set(pre['loan_ids']):blockers.append('complete_staged_loan_inventory_mismatch')
    if type(b['event_slots'])is not list or len(b['event_slots'])>256:raise ValidationError('bounded complete debt cash event mapping required')
    for row in b['event_slots']:
        if type(row)is not dict or set(row)!={'loan_id','period_id','category','target_event_id'}:raise ValidationError('exact loan/period/category/target mapping required')
        for key,value in row.items():nonempty(value,key)
        key=(row['loan_id'],row['period_id'],row['category'])
        if key in slots or row['target_event_id']in targets:raise ValidationError('unique debt source and target cash event identities required')
        slots[key]=row['target_event_id'];targets.add(row['target_event_id'])
    events={e['event_id']:e for e in pre['events']};debt_targets={e['event_id']for e in pre['events']if e['category']in LOAN_CATEGORIES}
    if targets!=debt_targets:blockers.append('all_and_only_preopening_debt_events_must_be_bound')
    expected=set()
    for loan,e in sources.items():
        p=e.run.payload;loan_blockers[loan]=p['blockers'];binding=bindings.get(loan)
        if binding is not None:
            if binding['source_sha256']!=hashlib.sha256(e.raw).hexdigest()or binding['run_sha256']!=e.run.sha256:blockers.append(loan+':source_or_run_binding_mismatch')
        if p['state']!='computed_synthetic_construction_draw_plan':blockers.append(loan+':staged_draw_plan_blocked')
        if p['context']!=pre['context']or p['currency']!=pre['currency']:blockers.append(loan+':preopening_context_or_currency_mismatch')
        if p['start_date']<pre['start_date']or p['end_date']!=pre['opening_operation_date']:blockers.append(loan+':staged_horizon_does_not_end_at_preopening_boundary')
        for row in p['exportable_proposed_debt_cash_events']or []:
            key=(loan,row['period_id'],row['category']);expected.add(key);target=events.get(slots.get(key))
            if target is None:continue
            if target['loan_id']!=loan or target['category']!=row['category']or target['date']!=row['date']or target['amount']['currency']!=row['currency']:blockers.append(target['event_id']+':debt_cash_metadata_or_date_mismatch')
            if target['amount']['value']is not None:blockers.append(target['event_id']+':debt_target_not_empty')
            proposed.append((target,row,e.run.sha256))
    if set(slots)!=expected:blockers.append('complete_staged_debt_event_inventory_mismatch')
    if not blockers:
        for target,row,source_run in proposed:
            before=json.loads(canonical(target));target['amount']['value']=row['amount'];target['amount']['source_ref']='miniuw:construction-draws:'+source_run+'#'+row['source_pointer']
            changes.append(dict(source_run_sha256=source_run,source_pointer=row['source_pointer'],before=before,after=json.loads(canonical(target))))
        compiled=canonical(pre)
        try:run=reconcile_preopening_cash(compiled.encode())
        except ValidationError:blockers.append('compiled_staged_cash_outside_preopening_contract');compiled=None;changes=[]
        if run is not None and run.payload['state']!='reconciled_synthetic_preopening_cash':blockers.append('compiled_preopening_cash_or_principal_blocked')
    result={'component':'T69','purpose':'synthetic_staged_debt_cash_to_preopening','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'preopening_source_sha256':hashlib.sha256(preopening_raw).hexdigest(),'binding_source_sha256':hashlib.sha256(binding_raw).hexdigest(),'context':pre['context'],'currency':pre['currency'],
        'staged_loan_run_sha256s':{k:e.run.sha256 for k,e in sources.items()},'compiled_preopening_json':compiled,'compiled_preopening_source_sha256':None if compiled is None else hashlib.sha256(compiled.encode()).hexdigest(),
        'preopening_run':None if run is None else asdict(run),'changes':changes,'loan_blockers':loan_blockers,'cash_blockers':[]if run is None else run.payload['blockers'],'blockers':sorted(set(blockers)),
        'state':'reconciled_synthetic_staged_preopening_cash'if run is not None and not blockers else'blocked','original_sources_overwritten':False,
        'equity_or_draws_generated_to_cover_deficit':False,'downstream_operating_debt_transition_connected':False,'actual_bank_funding_or_payments_verified':False,
        'whole_project_return_connected':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return ConstructionCashRun(encoded,digest(encoded))
