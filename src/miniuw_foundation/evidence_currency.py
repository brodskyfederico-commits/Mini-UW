"""T46 explicit as-of synthetic evidence validity; no inferred TTL or authentication."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T46-T47.md'


def timestamp(value):
    if type(value)is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',value):
        raise ValidationError('explicit UTC timestamp with seconds and Z required')
    try:return datetime.fromisoformat(value[:-1]+'+00:00')
    except ValueError as error:raise ValidationError('invalid UTC timestamp')from error


def _sha(value):
    if type(value)is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValidationError('exact source SHA-256 required')


def parse_evidence_currency(raw):
    if type(raw)is not bytes or not raw or len(raw)>1048576:raise ValidationError('bounded synthetic evidence registry required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid evidence JSON')from error
    if type(p)is not dict or set(p)!={'schema','context','inventory_declared_complete','inventory_basis_ref','requirements','evidence'}or p['schema']!='miniuw.synthetic-evidence-currency.v1':
        raise ValidationError('exact synthetic evidence currency profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit inventory declaration required')
    if p['inventory_basis_ref']is not None:nonempty(p['inventory_basis_ref'],'inventory_basis_ref')
    if type(p['requirements'])is not list or not 1<=len(p['requirements'])<=256:raise ValidationError('one to 256 explicit requirements required')
    ids=set()
    for row in p['requirements']:
        if type(row)is not dict or set(row)!={'requirement_id','source_sha256','source_locator'}:raise ValidationError('exact source/locator requirement required')
        nonempty(row['requirement_id'],'requirement_id');nonempty(row['source_locator'],'source_locator');_sha(row['source_sha256'])
        if row['requirement_id']in ids:raise ValidationError('duplicate evidence requirement')
        ids.add(row['requirement_id'])
    if type(p['evidence'])is not list or len(p['evidence'])>512:raise ValidationError('bounded explicit evidence records required')
    seen=set()
    for row in p['evidence']:
        keys={'evidence_id','requirement_id','source_sha256','source_locator','issued_at','valid_from','valid_until','review_status','value_status','superseded_by_sha256','basis_ref'}
        if type(row)is not dict or set(row)!=keys:raise ValidationError('exact evidence validity/review record required')
        for key in ['evidence_id','requirement_id','source_locator']:nonempty(row[key],key)
        if row['evidence_id']in seen:raise ValidationError('duplicate evidence identity')
        seen.add(row['evidence_id']);_sha(row['source_sha256'])
        if row['superseded_by_sha256']is not None:_sha(row['superseded_by_sha256'])
        if row['basis_ref']is not None:nonempty(row['basis_ref'],'basis_ref')
        for key in ['issued_at','valid_from','valid_until']:
            if row[key]is not None:timestamp(row[key])
        if row['review_status']not in ['accepted_synthetic','pending','rejected']or row['value_status']not in ['declared_synthetic','estimate','unresolved']:
            raise ValidationError('explicit synthetic review/value status required')
    return p


@dataclass(frozen=True)
class EvidenceCurrencyRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def evaluate_evidence_currency(raw,as_of):
    p=parse_evidence_currency(raw);at=timestamp(as_of);blockers=[];rows=[]
    if p['inventory_declared_complete']is not True or p['inventory_basis_ref']is None:blockers.append('evidence_inventory_not_explicitly_complete_with_basis')
    required={r['requirement_id']:r for r in p['requirements']}
    if any(e['requirement_id']not in required for e in p['evidence']):blockers.append('evidence_for_unknown_requirement')
    for requirement in p['requirements']:
        matches=[e for e in p['evidence']if e['requirement_id']==requirement['requirement_id']];issues=[]
        if not matches:issues.append('required_evidence_missing')
        elif len(matches)>1:issues.append('multiple_evidence_records_require_explicit_resolution')
        for e in matches:
            if e['source_sha256']!=requirement['source_sha256']or e['source_locator']!=requirement['source_locator']:issues.append('source_hash_or_locator_mismatch')
            if e['review_status']!='accepted_synthetic':issues.append('synthetic_review_'+e['review_status'])
            if e['value_status']!='declared_synthetic':issues.append('value_'+e['value_status'])
            if e['superseded_by_sha256']is not None:issues.append('evidence_superseded')
            if e['basis_ref']is None:issues.append('validity_and_review_basis_missing')
            if any(e[key]is None for key in ['issued_at','valid_from','valid_until']):issues.append('explicit_validity_dates_missing_no_inferred_TTL')
            else:
                issued,start,end=[timestamp(e[key])for key in ['issued_at','valid_from','valid_until']]
                if not issued<=start<end:issues.append('validity_date_order_invalid')
                if at<issued or at<start:issues.append('evidence_not_yet_current')
                if at>=end:issues.append('evidence_expired')
        rows.append({'requirement':requirement,'evidence_records':matches,'state':'current_synthetic'if not issues else'PENDING','blockers':sorted(set(issues))})
        blockers.extend(requirement['requirement_id']+':'+i for i in issues)
    payload={'component':'T46','purpose':'synthetic_evidence_currency_at_explicit_time',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(raw).hexdigest(),'context':p['context'],'evaluated_as_of_UTC':as_of,
        'validity_interval_convention':'valid_from_inclusive_valid_until_exclusive','requirements':rows,
        'state':'current_synthetic_evidence'if not blockers else'PENDING','blockers':sorted(set(blockers)),
        'review_authenticated':False,'source_authority_verified':False,'financial_policy_adopted':False,
        'automatic_clock_or_monitor_enabled':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(payload);return EvidenceCurrencyRun(encoded,digest(encoded))
