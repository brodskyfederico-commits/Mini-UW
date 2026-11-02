"""T03 local content-addressed synthetic evidence archive, separate from drafts.

Hashes detect content alteration; they do not authenticate people or approve deals.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import sqlite3

from .drafts import Snapshot, ValidationError, canonical
from .execution import (ENGINE_SHA256, Execution, Graph, Node, SlotRef,
    _snapshot_payload, execute_synthetic)
from .sources import parse_source_claims, import_synthetic_source
from .normalization import NumericProfile, NormalizationRun, normalize_synthetic
from .normalization import ENGINE_SHA256 as NORMALIZER_SHA256
from .calculations import CalculationRun, calculate_synthetic, graph_from_record
from .calculations import ENGINE_SHA256 as CALCULATOR_SHA256


class MissingEvidence(KeyError):
    pass


class CorruptArchive(ValueError):
    pass


class UnsupportedArchive(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _key(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValidationError('explicit lowercase SHA-256 required')


def _graph(records):
    return Graph(tuple(Node(**dict(record, slots=tuple(SlotRef(**ref) for ref in record['slots']),
        dependencies=tuple(record['dependencies']))) for record in records))


@dataclass(frozen=True)
class EvidenceBundle:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def snapshot(self):
        return Snapshot(**self.payload['snapshot'])

    @property
    def execution(self):
        return Execution(**self.payload['execution'])

    @property
    def graph(self):
        return _graph(self.payload['graph']['nodes'])


@dataclass(frozen=True)
class NormalizationBundle:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def snapshot(self):
        return Snapshot(**self.payload['snapshot'])

    @property
    def run(self):
        return NormalizationRun(**self.payload['run'])

    @property
    def profiles(self):
        return tuple(NumericProfile(**p) for p in self.payload['profiles'])


@dataclass(frozen=True)
class CalculationBundle:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def snapshot(self):
        return Snapshot(**self.payload['snapshot'])

    @property
    def profiles(self):
        return tuple(NumericProfile(**p) for p in self.payload['profiles'])

    @property
    def normalization(self):
        return NormalizationRun(**self.payload['normalization'])

    @property
    def graph(self):
        return graph_from_record(self.payload['graph'])

    @property
    def run(self):
        return CalculationRun(**self.payload['run'])


class EvidenceArchive:
    APPLICATION_ID = 0x4D555733

    def __init__(self, path):
        self._connection = sqlite3.connect(path, isolation_level=None, timeout=5)
        try:
            app = self._connection.execute('PRAGMA application_id').fetchone()[0]
            version = self._connection.execute('PRAGMA user_version').fetchone()[0]
            tables = self._connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if (version == 0 and (tables or app != 0)) or (version != 0 and (version != 1 or app != self.APPLICATION_ID)):
                raise UnsupportedArchive('not an empty database or supported T03 archive')
            if version == 0:
                self._connection.executescript('''BEGIN IMMEDIATE;
CREATE TABLE objects(kind TEXT NOT NULL CHECK(kind IN ('source','bundle')), sha256 TEXT NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(kind,sha256));
PRAGMA application_id=''' + str(self.APPLICATION_ID) + ''';
PRAGMA user_version=1;
COMMIT;''')
        except BaseException:
            self._connection.close()
            raise

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _commit(self):
        self._connection.execute('COMMIT')

    @contextmanager
    def _transaction(self):
        self._connection.execute('BEGIN IMMEDIATE')
        try:
            yield
            self._commit()
        except BaseException:
            if self._connection.in_transaction:
                self._connection.execute('ROLLBACK')
            raise

    def _read(self, kind, sha):
        _key(sha)
        row = self._connection.execute('SELECT payload FROM objects WHERE kind=? AND sha256=?', (kind, sha)).fetchone()
        if row is None:
            raise MissingEvidence((kind, sha))
        if type(row[0]) is not bytes or _sha(row[0]) != sha:
            raise CorruptArchive('content hash mismatch')
        return row[0]

    def _put(self, kind, raw):
        sha = _sha(raw)
        row = self._connection.execute('SELECT payload FROM objects WHERE kind=? AND sha256=?', (kind, sha)).fetchone()
        if row is None:
            self._connection.execute('INSERT INTO objects VALUES(?,?,?)', (kind, sha, raw))
        elif self._read(kind, sha) != raw:
            raise CorruptArchive('existing object differs; never overwrite')
        return sha

    def put_source(self, raw):
        parse_source_claims(raw)  # Archive only explicitly marked synthetic envelopes.
        with self._transaction():
            return self._put('source', raw)

    def get_source(self, sha):
        raw = self._read('source', sha)
        parse_source_claims(raw)
        return raw

    def _verify_sources(self, snapshot):
        payload = _snapshot_payload(snapshot)
        claims = [c for family in ('input_claims', 'criterion_claims')
            for records in payload[family].values() for c in records]
        hashes = sorted({c['source_sha256'] for c in claims})
        available = {sha: {canonical(c.record()) for c in parse_source_claims(self.get_source(sha))}
            for sha in hashes}
        for record in claims:
            if canonical(record) not in available[record['source_sha256']]:
                raise CorruptArchive('snapshot claim or locator does not match archived source bytes')
        return hashes

    def save_execution(self, snapshot, graph, execution):
        if type(execution) is not Execution:
            raise ValidationError('explicit execution required')
        expected = execute_synthetic(snapshot, graph)
        if execution != expected:
            raise ValidationError('execution does not reproduce from exact snapshot/graph/current engine')
        # Immutable arguments allow calculation before the transaction; evidence
        # lookup and archive insertion are one transaction, without a draft-head claim.
        with self._transaction():
            hashes = self._verify_sources(snapshot)
            payload = {'schema': 'miniuw.synthetic-evidence-bundle.v1',
                'purpose': 'synthetic_development_only',
                'snapshot': asdict(snapshot), 'execution': asdict(execution),
                'graph': {'nodes': [asdict(n) for n in graph.ordered()],
                    'sha256': graph.sha256, 'engine_sha256': ENGINE_SHA256},
                'source_hashes': hashes}
            raw = canonical(payload).encode('utf-8')
            sha = self._put('bundle', raw)
        return sha

    def read_bundle_bytes(self, sha):
        """Hash-checked bytes only; no replay/currentness/financial certification."""
        return self._read('bundle', sha)

    def load_execution(self, sha):
        """Validate all evidence and replay with the same supported engine bytes."""
        with self._transaction():
            raw = self.read_bundle_bytes(sha)
            try:
                payload = json.loads(raw)
                if set(payload) != {'schema','purpose','snapshot','execution','graph','source_hashes'}:
                    raise CorruptArchive('bundle fields changed')
                if payload['schema'] != 'miniuw.synthetic-evidence-bundle.v1':
                    raise UnsupportedArchive('unsupported evidence bundle schema')
                if payload['purpose'] != 'synthetic_development_only':
                    raise CorruptArchive('development purpose changed')
                if payload['graph']['engine_sha256'] != ENGINE_SHA256:
                    raise UnsupportedArchive('replay requires the archived engine version')
                bundle = EvidenceBundle(raw.decode('utf-8'), sha)
                snapshot, graph, execution = bundle.snapshot, bundle.graph, bundle.execution
                if graph.sha256 != payload['graph']['sha256']:
                    raise CorruptArchive('graph identity changed')
                if self._verify_sources(snapshot) != payload['source_hashes']:
                    raise CorruptArchive('source inventory changed')
                if execute_synthetic(snapshot, graph) != execution:
                    raise CorruptArchive('execution does not reproduce from archived evidence')
            except MissingEvidence:
                raise
            except (KeyError, TypeError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
                raise CorruptArchive('invalid archived evidence structure or content') from error
        return bundle


    def save_normalization(self, snapshot, profiles, run):
        if type(run) is not NormalizationRun or normalize_synthetic(snapshot,profiles) != run:
            raise ValidationError('numeric run does not reproduce from exact source/profiles')
        with self._transaction():
            hashes = self._verify_sources(snapshot)
            payload = {'schema':'miniuw.synthetic-normalization-bundle.v1',
                'purpose':'synthetic_development_only','snapshot':asdict(snapshot),
                'profiles':[asdict(p) for p in sorted(profiles,key=lambda p:p.slot_id)],
                'run':asdict(run),'normalizer_sha256':NORMALIZER_SHA256,
                'source_hashes':hashes}
            return self._put('bundle',canonical(payload).encode('utf-8'))

    def load_normalization(self, sha):
        with self._transaction():
            raw = self.read_bundle_bytes(sha)
            try:
                payload = json.loads(raw)
                if set(payload) != {'schema','purpose','snapshot','profiles','run','normalizer_sha256','source_hashes'}:
                    raise CorruptArchive('normalization bundle fields changed')
                if payload['schema'] != 'miniuw.synthetic-normalization-bundle.v1':
                    raise UnsupportedArchive('unsupported normalization evidence schema')
                if payload['purpose'] != 'synthetic_development_only':
                    raise CorruptArchive('normalization development purpose changed')
                if payload['normalizer_sha256'] != NORMALIZER_SHA256:
                    raise UnsupportedArchive('replay requires the archived numeric decoder version')
                bundle = NormalizationBundle(raw.decode('utf-8'),sha)
                if self._verify_sources(bundle.snapshot) != payload['source_hashes']:
                    raise CorruptArchive('normalization source inventory changed')
                if normalize_synthetic(bundle.snapshot,bundle.profiles) != bundle.run:
                    raise CorruptArchive('numeric result does not reproduce from archived evidence')
            except MissingEvidence:
                raise
            except (KeyError, TypeError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
                raise CorruptArchive('invalid normalization evidence structure/content') from error
        return bundle


    def save_calculation(self, snapshot, profiles, normalization, graph, run):
        if type(run) is not CalculationRun or calculate_synthetic(snapshot,profiles,normalization,graph) != run:
            raise ValidationError('calculation does not reproduce from exact numeric evidence/graph')
        with self._transaction():
            hashes = self._verify_sources(snapshot)
            payload = {'schema':'miniuw.synthetic-calculation-bundle.v1',
                'purpose':'synthetic_development_only','snapshot':asdict(snapshot),
                'profiles':[asdict(p) for p in sorted(profiles,key=lambda p:p.slot_id)],
                'normalization':asdict(normalization),'graph':graph.record(),'run':asdict(run),
                'calculator_sha256':CALCULATOR_SHA256,'normalizer_sha256':NORMALIZER_SHA256,
                'source_hashes':hashes}
            return self._put('bundle',canonical(payload).encode('utf-8'))

    def load_calculation(self, sha):
        with self._transaction():
            raw = self.read_bundle_bytes(sha)
            try:
                payload = json.loads(raw)
                if set(payload) != {'schema','purpose','snapshot','profiles','normalization','graph','run','calculator_sha256','normalizer_sha256','source_hashes'}:
                    raise CorruptArchive('calculation bundle fields changed')
                if payload['schema'] != 'miniuw.synthetic-calculation-bundle.v1':
                    raise UnsupportedArchive('unsupported calculation evidence schema')
                if payload['purpose'] != 'synthetic_development_only':
                    raise CorruptArchive('calculation purpose changed')
                if payload['calculator_sha256'] != CALCULATOR_SHA256 or payload['normalizer_sha256'] != NORMALIZER_SHA256:
                    raise UnsupportedArchive('replay requires compatible calculator and decoder code')
                bundle = CalculationBundle(raw.decode('utf-8'),sha)
                if self._verify_sources(bundle.snapshot) != payload['source_hashes']:
                    raise CorruptArchive('calculation source inventory changed')
                if calculate_synthetic(bundle.snapshot,bundle.profiles,bundle.normalization,bundle.graph) != bundle.run:
                    raise CorruptArchive('calculation result does not reproduce from archived evidence')
            except MissingEvidence:
                raise
            except (KeyError, TypeError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
                raise CorruptArchive('invalid calculation evidence structure/content') from error
        return bundle


def archive_and_import(archive, store, draft_id, *, expected_revision, operation_id, raw):
    """Source-first ordering; draft failure may leave an unreferenced source.

    This deliberately does not claim atomicity across the two databases.
    """
    archive.put_source(raw)
    return import_synthetic_source(store, draft_id, expected_revision=expected_revision,
        operation_id=operation_id, raw=raw)
