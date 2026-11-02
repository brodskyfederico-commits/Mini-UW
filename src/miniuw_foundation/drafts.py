"""Raw literal claims and fresh synthetic drafts; financial normalization remains blocked."""
from dataclasses import dataclass, asdict, field
from pathlib import Path
import hashlib,json,re

class ValidationError(ValueError):pass

def nonempty(value,name):
    if type(value) is not str or not value.strip():raise ValidationError(name+' must be explicit nonempty text')

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

@dataclass(frozen=True,kw_only=True)
class ContextSeed:
    deal_id:str
    scenario_id:str
    run_id:str
    definition_set_revision:str
    def __post_init__(self):
        for key,value in asdict(self).items():nonempty(value,key)
        if not self.deal_id.startswith('SYNTHETIC-'):raise ValidationError('T01 accepts synthetic development contexts only')

@dataclass(frozen=True,kw_only=True)
class RawClaim:
    claim_id:str
    slot_kind:str
    slot_id:str
    literal:str|None
    unit_literal:str|None
    currency_literal:str|None
    period_literal:str|None
    source_sha256:str
    locator:str
    definition_ref:str|None
    claim_kind:str=field(default='synthetic_fixture',init=False)
    def __post_init__(self):
        for name in ['claim_id','slot_id','locator']:nonempty(getattr(self,name),name)
        if self.slot_kind not in ['input','criterion']:raise ValidationError('unknown slot kind')
        for name in ['literal','unit_literal','currency_literal','period_literal','definition_ref']:
            if getattr(self,name) is not None and type(getattr(self,name)) is not str:raise ValidationError(name+' must preserve source text or null')
        if type(self.source_sha256) is not str or not re.fullmatch('[a-f0-9]{64}',self.source_sha256):raise ValidationError('explicit source SHA-256 required; not an authenticity claim')
    def record(self):return asdict(self)

def template():
    raw=(Path(__file__).parent/'data/project-draft-empty.json').read_bytes()
    doc=json.loads(raw)
    slots=doc['project_inputs']+doc['financing_inputs']+doc['requested_alternatives']
    if len(slots)!=55 or any(s['value'] is not None for s in slots) or len(doc['investment_criteria'])!=10 or any(c['threshold'] is not None for c in doc['investment_criteria']):raise ValidationError('bundled empty template changed')
    return doc,hashlib.sha256(raw).hexdigest()

def fresh_payload(draft_id,seed):
    nonempty(draft_id,'draft_id')
    if type(seed) is not ContextSeed:raise ValidationError('explicit synthetic context seed required')
    doc,sha=template();slots=doc['project_inputs']+doc['financing_inputs']+doc['requested_alternatives']
    return {'component':'T01','purpose':'synthetic_development_only','authorization':'not_granted','draft_id':draft_id,'revision':0,'context':dict(asdict(seed),input_revision=draft_id+'@0'),'source_template_sha256':sha,'input_claims':{s['field_id']:[] for s in slots},'criterion_claims':{c['metric_id']:[] for c in doc['investment_criteria']},'run_ready':False,'decision':'PENDING','blockers':['financial_normalization_not_implemented','applicable_criteria_and_rules_not_adopted','financial_engine_not_implemented','review_not_verified','production_not_authorized']}

def append_claims(payload,claims,new_revision):
    # The caller supplies an isolated JSON copy; no mutation of a stored snapshot.
    seen={c['claim_id'] for family in ['input_claims','criterion_claims'] for records in payload[family].values() for c in records}
    for claim in claims:
        if type(claim) is not RawClaim:raise ValidationError('RawClaim instances required')
        family='input_claims' if claim.slot_kind=='input' else 'criterion_claims'
        if claim.slot_id not in payload[family]:raise ValidationError('unknown slot; no automatic schema expansion')
        if claim.claim_id in seen:raise ValidationError('claim ID already present; use operation ID for an exact retry')
        seen.add(claim.claim_id);payload[family][claim.slot_id].append(claim.record())
    payload['revision']=new_revision;payload['context']['input_revision']=payload['draft_id']+'@'+str(new_revision)
    return payload

@dataclass(frozen=True)
class Snapshot:
    draft_id:str
    revision:int
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def decision(self):return 'PENDING'
    def slot(self,kind,id):
        if kind not in ['input','criterion']:raise ValidationError('unknown slot kind')
        family='input_claims' if kind=='input' else 'criterion_claims';payload=self.payload
        if id not in payload[family]:raise ValidationError('unknown slot')
        claims=payload[family][id]
        present=[c for c in claims if c['literal'] is not None and c['literal'].strip()!='']
        signatures={(c['literal'],c['unit_literal'],c['currency_literal'],c['period_literal']) for c in present}
        state='missing' if not present else 'conflicting_claims' if len(signatures)>1 else 'unverified_claims'
        return {'state':state,'claims':claims,'has_blank_claims':len(present)!=len(claims),'financially_normalized':False,'decision':'PENDING'}
