"""T70 bounded exact-source portable construction cash replay."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical
from .intake import _unique_object,_invalid_constant
from . import construction_draws,construction_cash,lifecycle_bundle
from .construction_draws import produce_construction_draws
from .construction_cash import ConstructionLoanEvidence,ConstructionCashRun,assemble_construction_cash
from .lifecycle_bundle import _shape,_list,_bytes,MAX_BYTES

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T70-T71.md'
def versions():return dict(T68=construction_draws.ENGINE_SHA256,T69=construction_cash.ENGINE_SHA256,T70=ENGINE_SHA256,transport_utilities=lifecycle_bundle.ENGINE_SHA256,definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest())


def export_construction_bundle(loans,preopening_raw,binding_raw,run):
    if type(run)is not ConstructionCashRun or assemble_construction_cash(loans,preopening_raw,binding_raw)!=run:raise ValidationError('complete staged debt/cash proof must reproduce before export')
    p=dict(schema='miniuw.synthetic-construction-cash-bundle.v1',versions=versions(),loans=[dict(source=e.raw.decode())for e in loans],preopening_source=preopening_raw.decode(),binding_source=binding_raw.decode(),expected_run=asdict(run))
    raw=canonical(p).encode()
    if len(raw)>MAX_BYTES:raise ValidationError('construction bundle transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredConstructionCash:
    loans:tuple
    preopening_raw:bytes
    binding_raw:bytes
    run:ConstructionCashRun
    bundle_sha256:str


def recover_construction_bundle(raw):
    if type(raw)is not bytes or not raw or len(raw)>MAX_BYTES:raise ValidationError('bounded immutable construction bundle required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid construction bundle JSON')from error
    _shape(p,['schema','versions','loans','preopening_source','binding_source','expected_run'])
    if p['schema']!='miniuw.synthetic-construction-cash-bundle.v1'or p['versions']!=versions():raise ValidationError('unsupported construction bundle schema or component version')
    loans=[]
    for row in _list(p['loans'],32):
        _shape(row,['source']);source=_bytes(row['source']);loans.append(ConstructionLoanEvidence(raw=source,run=produce_construction_draws(source)))
    pre=_bytes(p['preopening_source']);binding=_bytes(p['binding_source']);loans=tuple(loans);run=assemble_construction_cash(loans,pre,binding)
    _shape(p['expected_run'],['payload_json','sha256'])
    if p['expected_run']!=asdict(run):raise ValidationError('construction cash result does not reproduce from exact source bytes')
    return RecoveredConstructionCash(loans,pre,binding,run,hashlib.sha256(raw).hexdigest())
