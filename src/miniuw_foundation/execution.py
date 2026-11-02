"""T02 synthetic-only DAG execution and dependency freshness observation.

Operations inspect literal text; none normalize or evaluate financial values.
Freshness reports are observations, never authority to publish or decide.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .drafts import ContextSeed, Snapshot, ValidationError, canonical, digest, nonempty

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
OPERATIONS = frozenset({'literal_echo', 'text_length', 'integer_sum'})


@dataclass(frozen=True, kw_only=True)
class SlotRef:
    kind: str
    slot_id: str

    def __post_init__(self):
        if self.kind not in ('input', 'criterion'):
            raise ValidationError('unknown slot kind')
        nonempty(self.slot_id, 'slot_id')


@dataclass(frozen=True, kw_only=True)
class Node:
    node_id: str
    operation: str
    definition_revision: str
    dependencies: tuple[str, ...]
    slots: tuple[SlotRef, ...]

    def __post_init__(self):
        nonempty(self.node_id, 'node_id')
        nonempty(self.definition_revision, 'definition_revision')
        if self.operation not in OPERATIONS:
            raise ValidationError('unknown synthetic operation')
        if type(self.dependencies) is not tuple or type(self.slots) is not tuple:
            raise ValidationError('immutable explicit dependency/slot tuples required')
        for dependency in self.dependencies:
            nonempty(dependency, 'dependency')
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValidationError('duplicate dependency')
        if any(type(ref) is not SlotRef for ref in self.slots):
            raise ValidationError('explicit SlotRef required')
        if len(set(self.slots)) != len(self.slots):
            raise ValidationError('duplicate slot reference')
        arity = len(self.slots) + len(self.dependencies)
        if arity == 0 or (self.operation != 'integer_sum' and arity != 1):
            raise ValidationError('wrong synthetic operation arity')


@dataclass(frozen=True)
class Graph:
    nodes: tuple[Node, ...]

    def __post_init__(self):
        if type(self.nodes) is not tuple or not self.nodes or any(type(n) is not Node for n in self.nodes):
            raise ValidationError('nonempty immutable Node tuple required')
        names = {n.node_id for n in self.nodes}
        if len(names) != len(self.nodes):
            raise ValidationError('duplicate node identity')
        if any(d not in names for n in self.nodes for d in n.dependencies):
            raise ValidationError('unknown upstream node')
        self.ordered()  # Reject cycles; no implicit financial fixed-point solver.

    def ordered(self):
        remaining = {n.node_id: n for n in self.nodes}
        completed = set()
        ordered = []
        while remaining:
            ready = sorted(k for k, n in remaining.items() if set(n.dependencies) <= completed)
            if not ready:
                raise ValidationError('cycle requires an explicitly designed separate pass')
            for key in ready:
                ordered.append(remaining.pop(key))
                completed.add(key)
        return tuple(ordered)

    @property
    def sha256(self):
        return digest(canonical({'engine_sha256': ENGINE_SHA256,
            'nodes': [asdict(n) for n in self.ordered()]}))


@dataclass(frozen=True)
class Execution:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def _snapshot_payload(snapshot):
    if type(snapshot) is not Snapshot or digest(snapshot.payload_json) != snapshot.sha256:
        raise ValidationError('intact explicit source snapshot required')
    payload = snapshot.payload
    context = payload.get('context', {})
    try:
        ContextSeed(**{key: context[key] for key in
            ('deal_id', 'scenario_id', 'run_id', 'definition_set_revision')})
    except (KeyError, TypeError) as error:
        raise ValidationError('incomplete synthetic snapshot context') from error
    if (payload.get('purpose') != 'synthetic_development_only'
        or payload.get('draft_id') != snapshot.draft_id
        or payload.get('revision') != snapshot.revision
        or context.get('input_revision') != snapshot.draft_id + '@' + str(snapshot.revision)
        or payload.get('run_ready') is not False
        or payload.get('decision') != 'PENDING'
        or payload.get('authorization') != 'not_granted'):
        raise ValidationError('synthetic snapshot identity/guards changed')
    return payload


def _plan(snapshot, graph):
    payload = _snapshot_payload(snapshot)
    if type(graph) is not Graph:
        raise ValidationError('explicit Graph required')
    # A node key excludes the aggregate input revision only. Exact source identity
    # is retained separately, so an unchanged branch never makes an old run current.
    context = {k: v for k, v in payload['context'].items() if k != 'input_revision'}
    keys, sources = {}, {}
    for node in graph.ordered():
        records = [snapshot.slot(ref.kind, ref.slot_id) for ref in node.slots]
        keys[node.node_id] = digest(canonical({
            'engine_sha256': ENGINE_SHA256, 'draft_id': snapshot.draft_id,
            'context': context, 'template_sha256': payload['source_template_sha256'],
            'definition': asdict(node), 'sources': records,
            'upstream': [(d, keys[d]) for d in node.dependencies]}))
        sources[node.node_id] = records
    return keys, sources


def execute_synthetic(snapshot, graph):
    """Reexecute every declared node; matching fingerprints do not reuse a cache."""
    keys, sources = _plan(snapshot, graph)
    results = {}
    for node in graph.ordered():
        blockers, values = [], []
        for ref, source in zip(node.slots, sources[node.node_id]):
            if source['state'] != 'unverified_claims':
                blockers.append(ref.kind + ':' + ref.slot_id + ':' + source['state'])
            else:
                # This is literal fixture inspection, not verified financial input.
                values.append(next(c['literal'] for c in source['claims']
                    if c['literal'] is not None and c['literal'].strip() != ''))
        for dependency in node.dependencies:
            upstream = results[dependency]
            if upstream['state'] != 'computed_synthetic':
                blockers.append('upstream_blocked:' + dependency)
            else:
                values.append(upstream['value'])
        value = None
        if not blockers:
            if node.operation == 'literal_echo':
                value = values[0]
            elif node.operation == 'text_length' and type(values[0]) is str:
                value = len(values[0])
            elif node.operation == 'integer_sum' and all(type(v) is int for v in values):
                value = sum(values)
            else:
                blockers.append('synthetic_operation_type_mismatch')
        results[node.node_id] = {'fingerprint': keys[node.node_id],
            'state': 'blocked' if blockers else 'computed_synthetic',
            'value': value, 'blockers': blockers, 'definition': asdict(node),
            'source_slots': sources[node.node_id],
            'upstream_fingerprints': {d: keys[d] for d in node.dependencies}}
    payload = {'component': 'T02', 'purpose': 'synthetic_development_only',
        'engine_sha256': ENGINE_SHA256, 'graph_sha256': graph.sha256,
        'source': {'draft_id': snapshot.draft_id, 'revision': snapshot.revision,
            'sha256': snapshot.sha256, 'context': snapshot.payload['context']},
        'results': results, 'decision': 'PENDING', 'run_ready': False,
        'financially_normalized': False, 'production_authorized': False}
    encoded = canonical(payload)
    return Execution(encoded, digest(encoded))


def observe_freshness(execution, snapshot, graph):
    """Compare with an observed snapshot, without an atomic publication guarantee."""
    if type(execution) is not Execution or digest(execution.payload_json) != execution.sha256:
        raise ValidationError('intact execution snapshot required')
    prior = execution.payload
    if (prior.get('component') != 'T02' or prior.get('decision') != 'PENDING'
        or prior.get('run_ready') is not False or prior.get('production_authorized') is not False):
        raise ValidationError('synthetic execution guards changed')
    keys, _ = _plan(snapshot, graph)
    old = prior['results']
    added = sorted(set(keys) - set(old))
    removed = sorted(set(old) - set(keys))
    affected = sorted(k for k in set(old) & set(keys) if old[k]['fingerprint'] != keys[k])
    source_current = prior['source'] == {'draft_id': snapshot.draft_id,
        'revision': snapshot.revision, 'sha256': snapshot.sha256,
        'context': snapshot.payload['context']}
    graph_current = prior['graph_sha256'] == graph.sha256
    return {'affected_nodes': affected, 'added_nodes': added, 'removed_nodes': removed,
        'unchanged_nodes': sorted(k for k in set(old) & set(keys) if k not in affected),
        'source_snapshot_current': source_current, 'graph_current': graph_current,
        'entire_run_current': source_current and graph_current and not (added or removed or affected),
        'observation_only': True, 'publication_authorized': False, 'decision': 'PENDING'}
