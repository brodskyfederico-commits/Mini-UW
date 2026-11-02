"""T08 exact typed synthetic arithmetic, without underwriting rules or decisions."""
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from .drafts import ValidationError, canonical, digest, nonempty
from .normalization import NormalizationRun, normalize_synthetic

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MAX_BITS = 4096  # Computational bound, never financial precision/tolerance.


@dataclass(frozen=True, kw_only=True)
class Operand:
    kind: str
    ref: str

    def __post_init__(self):
        if self.kind not in ('input','node'):
            raise ValidationError('explicit input/node operand required')
        nonempty(self.ref,'operand ref')


@dataclass(frozen=True, kw_only=True)
class CalculationNode:
    node_id: str
    definition_revision: str
    operation: str
    operands: tuple[Operand, ...]

    def __post_init__(self):
        nonempty(self.node_id,'node_id');nonempty(self.definition_revision,'definition_revision')
        if self.operation not in ('identity','sum','difference','scale','ratio'):
            raise ValidationError('unsupported synthetic arithmetic operation')
        if type(self.operands) is not tuple or not 1 <= len(self.operands) <= 256 or any(type(o) is not Operand for o in self.operands):
            raise ValidationError('bounded immutable explicit operand tuple required')
        if ((self.operation == 'identity' and len(self.operands) != 1)
            or (self.operation in ('difference','scale','ratio') and len(self.operands) != 2)):
            raise ValidationError('wrong arithmetic operand count')


@dataclass(frozen=True, kw_only=True)
class CalculationGraph:
    graph_id: str
    definition_revision: str
    nodes: tuple[CalculationNode, ...]

    def __post_init__(self):
        nonempty(self.graph_id,'graph_id');nonempty(self.definition_revision,'graph revision')
        if not self.graph_id.startswith('SYNTHETIC-'):
            raise ValidationError('explicit synthetic calculation graph required')
        if type(self.nodes) is not tuple or not 1 <= len(self.nodes) <= 256 or any(type(n) is not CalculationNode for n in self.nodes):
            raise ValidationError('bounded immutable calculation-node tuple required')
        ids={n.node_id for n in self.nodes}
        if len(ids) != len(self.nodes) or any(o.ref not in ids for n in self.nodes for o in n.operands if o.kind == 'node'):
            raise ValidationError('duplicate or unknown node identity')
        self.ordered()

    def ordered(self):
        remaining={n.node_id:n for n in self.nodes};done=set();result=[]
        while remaining:
            ready=sorted(k for k,n in remaining.items() if all(o.ref in done for o in n.operands if o.kind == 'node'))
            if not ready:
                raise ValidationError('cycle requires an explicit separate solver/pass')
            for key in ready:
                result.append(remaining.pop(key));done.add(key)
        return tuple(result)

    def record(self):
        return {'graph_id':self.graph_id,'definition_revision':self.definition_revision,
            'nodes':[asdict(n) for n in self.ordered()]}

    @property
    def sha256(self):
        return digest(canonical(self.record()))


def graph_from_record(record):
    if type(record) is not dict or set(record) != {'graph_id','definition_revision','nodes'}:
        raise ValidationError('exact explicit calculation graph fields required')
    return CalculationGraph(graph_id=record['graph_id'],definition_revision=record['definition_revision'],
        nodes=tuple(CalculationNode(**dict(n,operands=tuple(Operand(**o) for o in n['operands']))) for n in record['nodes']))


@dataclass(frozen=True)
class CalculationRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def _limited(value):
    return max(abs(value.numerator).bit_length(),value.denominator.bit_length()) <= MAX_BITS


def _apply(operation, values, quantities):
    first=quantities[0]
    if operation in ('sum','difference','ratio') and any(q != first for q in quantities):
        return None,None,'incompatible_quantity_unit_currency_or_period'
    if operation == 'scale':
        if quantities[1] != {'kind':'scalar','unit':'fraction','currency':None,'period':None}:
            return None,None,'scale_requires_explicit_dimensionless_fraction'
        value=values[0]*values[1];quantity=first
    elif operation == 'ratio':
        if values[1] == 0:
            return None,None,'division_by_zero_unresolved'
        value=values[0]/values[1]
        quantity={'kind':'scalar','unit':'fraction','currency':None,'period':None}
    elif operation == 'difference':
        value=values[0]-values[1];quantity=first
    elif operation == 'sum':
        value=values[0]
        for item in values[1:]:
            value += item
            if not _limited(value):
                return None,None,'technical_rational_size_bound'
        quantity=first
    else:
        value=values[0];quantity=first
    if not _limited(value):
        return None,None,'technical_rational_size_bound'
    return value,quantity,None


def calculate_synthetic(snapshot, profiles, normalization, graph):
    if type(normalization) is not NormalizationRun or normalize_synthetic(snapshot,profiles) != normalization:
        raise ValidationError('exact reproducible normalization for the supplied snapshot/profiles required')
    if type(graph) is not CalculationGraph:
        raise ValidationError('explicit calculation graph required')
    decoded=normalization.payload
    context={k:v for k,v in decoded['source']['context'].items() if k != 'input_revision'}
    results={}
    for node in graph.ordered():
        values=[];quantities=[];lineage=[];blockers=[]
        for operand in node.operands:
            if operand.kind == 'input':
                if operand.ref not in decoded['results']:
                    raise ValidationError('graph input requires its own explicit numeric profile')
                record=decoded['results'][operand.ref]
                key=digest(canonical({'decoded_input':record,'decoder_sha256':decoded['engine_sha256']}))
                ready=record['state'] == 'decoded_synthetic'
                quantity={'kind':record['profile']['quantity_kind'],'unit':record['target_unit'],
                    'currency':record['currency_literal'],'period':record['period_literal']}
            else:
                record=results[operand.ref];key=record['fingerprint']
                ready=record['state'] == 'computed_synthetic';quantity=record['quantity']
            lineage.append({'kind':operand.kind,'ref':operand.ref,'fingerprint':key})
            if not ready:
                blockers.append(operand.kind+'_blocked:'+operand.ref)
            else:
                number=record['rational']
                value=Fraction(int(number['numerator']),int(number['denominator']))
                if not _limited(value):
                    blockers.append('technical_rational_size_bound')
                values.append(value);quantities.append(quantity)
        value=quantity=None
        if not blockers:
            value,quantity,failure=_apply(node.operation,values,quantities)
            if failure:blockers.append(failure)
        fingerprint=digest(canonical({'engine_sha256':ENGINE_SHA256,
            'draft_id':decoded['source']['draft_id'],'context':context,
            'graph_id':graph.graph_id,'graph_revision':graph.definition_revision,
            'node':asdict(node),'operands':lineage}))
        results[node.node_id]={'fingerprint':fingerprint,'definition':asdict(node),
            'state':'blocked' if blockers else 'computed_synthetic',
            'rational':None if value is None else {'numerator':str(value.numerator),'denominator':str(value.denominator)},
            'quantity':quantity,'lineage':lineage,'blockers':sorted(set(blockers)),
            'financially_validated':False}
    payload={'component':'T08','purpose':'synthetic_development_only','engine_sha256':ENGINE_SHA256,
        'normalizer_sha256':decoded['engine_sha256'],'normalization_sha256':normalization.sha256,
        'source':decoded['source'],'graph':graph.record(),'graph_sha256':graph.sha256,
        'results':results,'decision':'PENDING','run_ready':False,
        'financially_validated':False,'production_authorized':False}
    encoded=canonical(payload)
    return CalculationRun(encoded,digest(encoded))


def observe_calculation_freshness(run,snapshot,profiles,normalization,graph):
    if type(run) is not CalculationRun or digest(run.payload_json) != run.sha256:
        raise ValidationError('intact calculation run required')
    old=run.payload
    if old.get('component') != 'T08' or old.get('decision') != 'PENDING' or old.get('run_ready') is not False or old.get('production_authorized') is not False:
        raise ValidationError('synthetic calculation guards changed')
    current=calculate_synthetic(snapshot,profiles,normalization,graph).payload
    prior=old['results'];now=current['results']
    added=sorted(set(now)-set(prior));removed=sorted(set(prior)-set(now))
    affected=sorted(k for k in set(prior)&set(now) if prior[k]['fingerprint'] != now[k]['fingerprint'])
    source_current=old['source'] == current['source']
    normalization_current=old['normalization_sha256'] == current['normalization_sha256']
    graph_current=old['graph_sha256'] == current['graph_sha256']
    engine_current=old['engine_sha256'] == current['engine_sha256']
    return {'source_snapshot_current':source_current,'normalization_current':normalization_current,
        'graph_current':graph_current,'engine_current':engine_current,
        'affected_nodes':affected,'added_nodes':added,'removed_nodes':removed,
        'unchanged_nodes':sorted(k for k in set(prior)&set(now) if k not in affected),
        'entire_run_current':source_current and normalization_current and graph_current and engine_current and not (added or removed or affected),
        'observation_only':True,'publication_authorized':False,'decision':'PENDING'}
