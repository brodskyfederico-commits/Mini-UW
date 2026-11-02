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
from .scoped_profiles import DscrBinding, ScopedProfileRun, dispatch_scoped_profile, definition_sources
from .scoped_profiles import ENGINE_SHA256 as PROFILE_ENGINE_SHA256
from .debt_service import DebtServiceRun,DateWindow,parse_loan_terms,produce_debt_service
from .debt_service import ENGINE_SHA256 as DEBT_ENGINE_SHA256
from .debt_service import definition_sources as debt_definition_sources
from .debt_dscr import DebtDscrBinding,DebtDscrRun,calculate_debt_dscr
from .debt_dscr import ENGINE_SHA256 as DEBT_DSCR_ENGINE_SHA256
from .screening import ScreeningRun,parse_screening_case,simulate_screening,user_policy_reference
from .screening import ENGINE_SHA256 as SCREEN_ENGINE_SHA256
from .screening import definition_sources as screening_definition_sources
from .review_proposals import ReviewProposalRun,parse_review_proposal,evaluate_review_proposal
from .review_proposals import ENGINE_SHA256 as REVIEW_PROPOSAL_ENGINE_SHA256
from .scenario_threshold_rehearsal import ScenarioThresholdRun,simulate_scenario_thresholds
from .scenario_threshold_rehearsal import ENGINE_SHA256 as SCENARIO_THRESHOLD_ENGINE_SHA256
from .threshold_rehearsal import read_documented_thresholds,parse_rehearsal
from .threshold_rehearsal import ENGINE_SHA256 as THRESHOLD_SOURCE_ENGINE_SHA256
from .scenario_review import ScenarioReviewRun,parse_scenario_proposal,evaluate_scenario_proposal
from .scenario_review import ENGINE_SHA256 as SCENARIO_REVIEW_ENGINE_SHA256
from .operating_noi import OperatingNoiRun,parse_operating_noi,produce_operating_noi
from .operating_noi import ENGINE_SHA256 as OPERATING_NOI_ENGINE_SHA256
from .operating_noi import definition_sources as operating_noi_definition_sources
from .operating_dscr import OperatingDscrBinding,OperatingDscrRun,calculate_operating_dscr
from .operating_dscr import ENGINE_SHA256 as OPERATING_DSCR_ENGINE_SHA256
from .rental_operations import RentalOperationsRun,parse_rental_operations,produce_rental_operations
from .rental_operations import ENGINE_SHA256 as RENTAL_ENGINE_SHA256
from .rental_operations import definition_sources as rental_definition_sources
from .rental_noi import RentalNoiRun,parse_rental_noi_spec,assemble_rental_noi
from .rental_noi import ENGINE_SHA256 as RENTAL_NOI_ENGINE_SHA256


class MissingEvidence(KeyError):
    pass


class CorruptArchive(ValueError):
    pass


class UnsupportedArchive(ValueError):
    pass


@dataclass(frozen=True)
class ScenarioThresholdBundle:
    payload_json: str
    sha256: str

    @property
    def payload(self):return json.loads(self.payload_json)

    @property
    def run(self):return ScenarioThresholdRun(**self.payload['run'])


@dataclass(frozen=True)
class ScenarioReviewBundle:
    payload_json: str
    sha256: str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def base_run(self):return ScenarioThresholdRun(**self.payload['base_run'])
    @property
    def run(self):return ScenarioReviewRun(**self.payload['run'])


@dataclass(frozen=True)
class OperatingNoiBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def run(self):return OperatingNoiRun(**self.payload['run'])


@dataclass(frozen=True)
class OperatingDscrBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def run(self):return OperatingDscrRun(**self.payload['run'])


@dataclass(frozen=True)
class RentalOperationsBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def run(self):return RentalOperationsRun(**self.payload['run'])


@dataclass(frozen=True)
class RentalNoiBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def run(self):return RentalNoiRun(**self.payload['run'])


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


@dataclass(frozen=True)
class ScopedProfileBundle:
    payload_json: str
    sha256: str

    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def snapshot(self):return Snapshot(**self.payload['snapshot'])
    @property
    def profiles(self):return tuple(NumericProfile(**p) for p in self.payload['profiles'])
    @property
    def normalization(self):return NormalizationRun(**self.payload['normalization'])
    @property
    def graph(self):return graph_from_record(self.payload['graph'])
    @property
    def upstream(self):return CalculationRun(**self.payload['upstream'])
    @property
    def binding(self):return DscrBinding(**self.payload['binding'])
    @property
    def run(self):return ScopedProfileRun(**self.payload['run'])


@dataclass(frozen=True)
class DebtServiceBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def windows(self):return tuple(DateWindow(**w) for w in self.payload['windows'])
    @property
    def run(self):return DebtServiceRun(**self.payload['run'])


@dataclass(frozen=True)
class DebtDscrBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def snapshot(self):return Snapshot(**self.payload['snapshot'])
    @property
    def profiles(self):return tuple(NumericProfile(**p) for p in self.payload['profiles'])
    @property
    def normalization(self):return NormalizationRun(**self.payload['normalization'])
    @property
    def graph(self):return graph_from_record(self.payload['graph'])
    @property
    def upstream(self):return CalculationRun(**self.payload['upstream'])
    @property
    def windows(self):return tuple(DateWindow(**w) for w in self.payload['windows'])
    @property
    def debt_run(self):return DebtServiceRun(**self.payload['debt_run'])
    @property
    def binding(self):return DebtDscrBinding(**self.payload['binding'])
    @property
    def run(self):return DebtDscrRun(**self.payload['run'])


@dataclass(frozen=True)
class ScreeningBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def run(self):return ScreeningRun(**self.payload['run'])


@dataclass(frozen=True)
class ReviewProposalBundle:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def base_run(self):return ScreeningRun(**self.payload['base_run'])
    @property
    def run(self):return ReviewProposalRun(**self.payload['run'])


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


    def save_scoped_profile(self, snapshot, profiles, normalization, graph, upstream, binding, run):
        if type(run) is not ScopedProfileRun or dispatch_scoped_profile(snapshot,profiles,normalization,graph,upstream,binding) != run:
            raise ValidationError('scoped profile does not reproduce from full upstream evidence')
        with self._transaction():
            hashes=self._verify_sources(snapshot)
            payload={'schema':'miniuw.synthetic-scoped-profile-bundle.v1','purpose':'synthetic_development_only',
                'snapshot':asdict(snapshot),'profiles':[asdict(p) for p in sorted(profiles,key=lambda p:p.slot_id)],
                'normalization':asdict(normalization),'graph':graph.record(),'upstream':asdict(upstream),
                'binding':asdict(binding),'run':asdict(run),'source_hashes':hashes,
                'profile_engine_sha256':PROFILE_ENGINE_SHA256,'calculator_sha256':CALCULATOR_SHA256,
                'normalizer_sha256':NORMALIZER_SHA256,'definition_sources':definition_sources()}
            return self._put('bundle',canonical(payload).encode('utf-8'))

    def load_scoped_profile(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                payload=json.loads(raw)
                if set(payload) != {'schema','purpose','snapshot','profiles','normalization','graph','upstream','binding','run','source_hashes','profile_engine_sha256','calculator_sha256','normalizer_sha256','definition_sources'}:
                    raise CorruptArchive('scoped profile bundle fields changed')
                if payload['schema'] != 'miniuw.synthetic-scoped-profile-bundle.v1':
                    raise UnsupportedArchive('unsupported scoped profile schema')
                if payload['purpose'] != 'synthetic_development_only':
                    raise CorruptArchive('scoped profile purpose changed')
                if (payload['profile_engine_sha256'] != PROFILE_ENGINE_SHA256 or payload['calculator_sha256'] != CALCULATOR_SHA256
                    or payload['normalizer_sha256'] != NORMALIZER_SHA256 or payload['definition_sources'] != definition_sources()):
                    raise UnsupportedArchive('scoped replay requires compatible code and definition documents')
                bundle=ScopedProfileBundle(raw.decode('utf-8'),sha)
                if self._verify_sources(bundle.snapshot) != payload['source_hashes']:
                    raise CorruptArchive('scoped profile source inventory changed')
                if dispatch_scoped_profile(bundle.snapshot,bundle.profiles,bundle.normalization,bundle.graph,bundle.upstream,bundle.binding) != bundle.run:
                    raise CorruptArchive('scoped profile result does not reproduce')
            except MissingEvidence:
                raise
            except (KeyError, TypeError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
                raise CorruptArchive('invalid scoped profile evidence structure/content') from error
        return bundle


    def put_loan_source(self, raw):
        parse_loan_terms(raw)
        with self._transaction():return self._put('source',raw)

    def get_loan_source(self, sha):
        raw=self._read('source',sha);parse_loan_terms(raw);return raw

    def save_debt_service(self, raw, windows, run):
        if type(run) is not DebtServiceRun or produce_debt_service(raw,windows)!=run:
            raise ValidationError('debt service does not reproduce from loan terms/windows')
        with self._transaction():
            source=self._put('source',raw)
            payload={'schema':'miniuw.synthetic-debt-service-bundle.v1','purpose':'synthetic_development_only',
                'loan_source_sha256':source,'windows':[asdict(w) for w in sorted(windows,key=lambda w:w.window_id)],
                'run':asdict(run),'engine_sha256':DEBT_ENGINE_SHA256,'definition_sources':debt_definition_sources()}
            return self._put('bundle',canonical(payload).encode())

    def load_debt_service(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','loan_source_sha256','windows','run','engine_sha256','definition_sources'}:
                    raise CorruptArchive('debt service bundle fields changed')
                if p['schema']!='miniuw.synthetic-debt-service-bundle.v1':raise UnsupportedArchive('unsupported debt service schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('debt purpose changed')
                if p['engine_sha256']!=DEBT_ENGINE_SHA256 or p['definition_sources']!=debt_definition_sources():
                    raise UnsupportedArchive('debt replay requires compatible code/documents')
                bundle=DebtServiceBundle(raw.decode(),sha)
                loan=self.get_loan_source(p['loan_source_sha256'])
                if produce_debt_service(loan,bundle.windows)!=bundle.run:raise CorruptArchive('debt result does not reproduce')
            except MissingEvidence:raise
            except (KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError) as error:
                raise CorruptArchive('invalid debt evidence') from error
        return bundle

    def save_debt_dscr(self, snapshot, profiles, normalization, graph, upstream, loan_raw, windows, debt_run, binding, run):
        if type(run) is not DebtDscrRun or calculate_debt_dscr(snapshot,profiles,normalization,graph,upstream,loan_raw,windows,debt_run,binding)!=run:
            raise ValidationError('debt DSCR does not reproduce')
        with self._transaction():
            sources=self._verify_sources(snapshot);loan_source=self._put('source',loan_raw)
            p={'schema':'miniuw.synthetic-debt-dscr-bundle.v1','purpose':'synthetic_development_only',
                'snapshot':asdict(snapshot),'profiles':[asdict(p) for p in sorted(profiles,key=lambda p:p.slot_id)],
                'normalization':asdict(normalization),'graph':graph.record(),'upstream':asdict(upstream),
                'loan_source_sha256':loan_source,'windows':[asdict(w) for w in sorted(windows,key=lambda w:w.window_id)],
                'debt_run':asdict(debt_run),'binding':asdict(binding),'run':asdict(run),'source_hashes':sources,
                'versions':[DEBT_ENGINE_SHA256,DEBT_DSCR_ENGINE_SHA256,NORMALIZER_SHA256,CALCULATOR_SHA256],
                'definition_sources':debt_definition_sources()+definition_sources()}
            return self._put('bundle',canonical(p).encode())

    def load_debt_dscr(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','snapshot','profiles','normalization','graph','upstream','loan_source_sha256','windows','debt_run','binding','run','source_hashes','versions','definition_sources'}:
                    raise CorruptArchive('debt DSCR bundle fields changed')
                if p['schema']!='miniuw.synthetic-debt-dscr-bundle.v1':raise UnsupportedArchive('unsupported debt DSCR schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('debt DSCR purpose changed')
                if p['versions']!=[DEBT_ENGINE_SHA256,DEBT_DSCR_ENGINE_SHA256,NORMALIZER_SHA256,CALCULATOR_SHA256] or p['definition_sources']!=debt_definition_sources()+definition_sources():
                    raise UnsupportedArchive('debt DSCR replay requires compatible code/documents')
                bundle=DebtDscrBundle(raw.decode(),sha)
                if self._verify_sources(bundle.snapshot)!=p['source_hashes']:raise CorruptArchive('NOI source inventory changed')
                loan=self.get_loan_source(p['loan_source_sha256'])
                if calculate_debt_dscr(bundle.snapshot,bundle.profiles,bundle.normalization,bundle.graph,bundle.upstream,loan,bundle.windows,bundle.debt_run,bundle.binding)!=bundle.run:
                    raise CorruptArchive('debt DSCR result does not reproduce')
            except MissingEvidence:raise
            except (KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError) as error:
                raise CorruptArchive('invalid debt DSCR evidence') from error
        return bundle


    def get_screening_source(self, sha):
        raw=self._read('source',sha);parse_screening_case(raw);return raw

    def save_screening(self, raw, run):
        if type(run) is not ScreeningRun or simulate_screening(raw)!=run:
            raise ValidationError('screening simulation does not reproduce from explicit case/criteria')
        with self._transaction():
            source=self._put('source',raw)
            p={'schema':'miniuw.synthetic-screening-bundle.v2','purpose':'synthetic_development_only',
                'source_sha256':source,'run':asdict(run),'engine_sha256':SCREEN_ENGINE_SHA256,
                'definition_sources':screening_definition_sources(),'user_policy_reference':user_policy_reference()}
            return self._put('bundle',canonical(p).encode())

    def load_screening(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','source_sha256','run','engine_sha256','definition_sources','user_policy_reference'}:
                    raise CorruptArchive('screening bundle fields changed')
                if p['schema']!='miniuw.synthetic-screening-bundle.v2':raise UnsupportedArchive('unsupported screening schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('screening purpose changed')
                if p['engine_sha256']!=SCREEN_ENGINE_SHA256 or p['definition_sources']!=screening_definition_sources() or p['user_policy_reference']!=user_policy_reference():
                    raise UnsupportedArchive('screening replay requires compatible code/documents')
                bundle=ScreeningBundle(raw.decode(),sha)
                source=self.get_screening_source(p['source_sha256'])
                if simulate_screening(source)!=bundle.run:raise CorruptArchive('screening simulation does not reproduce')
            except MissingEvidence:raise
            except (KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError) as error:
                raise CorruptArchive('invalid screening evidence') from error
        return bundle


    def get_rental_source(self, sha):
        raw=self._read('source',sha);parse_rental_operations(raw);return raw

    def get_rental_noi_spec(self, sha):
        raw=self._read('source',sha);parse_rental_noi_spec(raw);return raw

    def save_rental_operations(self, source_raw, run):
        if type(run) is not RentalOperationsRun or produce_rental_operations(source_raw)!=run:
            raise ValidationError('residential result does not reproduce')
        with self._transaction():
            source=self._put('source',source_raw)
            p={'schema':'miniuw.synthetic-rental-bundle.v1','source_sha256':source,'run':asdict(run),
                'versions':[RENTAL_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256],
                'definition_sources':rental_definition_sources(),'purpose':'synthetic_development_only'}
            return self._put('bundle',canonical(p).encode())

    def load_rental_operations(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','source_sha256','run','versions','definition_sources','purpose'}:raise CorruptArchive('residential bundle fields changed')
                if p['schema']!='miniuw.synthetic-rental-bundle.v1':raise UnsupportedArchive('unsupported residential schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('residential purpose changed')
                if p['versions']!=[RENTAL_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256] or p['definition_sources']!=rental_definition_sources():raise UnsupportedArchive('residential replay requires compatible code/documents')
                bundle=RentalOperationsBundle(raw.decode(),sha)
                if produce_rental_operations(self.get_rental_source(p['source_sha256']))!=bundle.run:raise CorruptArchive('residential result does not reproduce')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:raise CorruptArchive('invalid residential evidence')from error
        return bundle

    def save_rental_noi(self, rental_raw, rental_run, spec_raw, run):
        if type(run) is not RentalNoiRun or assemble_rental_noi(rental_raw,rental_run,spec_raw)!=run:raise ValidationError('residential NOI assembly does not reproduce')
        with self._transaction():
            source=self._put('source',rental_raw);spec=self._put('source',spec_raw)
            compiled=None if run.compiled_raw is None else self._put('source',run.compiled_raw)
            p={'schema':'miniuw.synthetic-rental-noi-bundle.v1','purpose':'synthetic_development_only',
                'rental_source_sha256':source,'rental_run':asdict(rental_run),'spec_source_sha256':spec,
                'compiled_noi_source_sha256':compiled,'run':asdict(run),
                'versions':[RENTAL_NOI_ENGINE_SHA256,RENTAL_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256],
                'rental_definition_sources':rental_definition_sources(),'noi_definition_sources':operating_noi_definition_sources()}
            return self._put('bundle',canonical(p).encode())

    def load_rental_noi(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','rental_source_sha256','rental_run','spec_source_sha256','compiled_noi_source_sha256','run','versions','rental_definition_sources','noi_definition_sources'}:raise CorruptArchive('residential NOI fields changed')
                if p['schema']!='miniuw.synthetic-rental-noi-bundle.v1':raise UnsupportedArchive('unsupported residential NOI schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('residential NOI purpose changed')
                if p['versions']!=[RENTAL_NOI_ENGINE_SHA256,RENTAL_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256] or p['rental_definition_sources']!=rental_definition_sources() or p['noi_definition_sources']!=operating_noi_definition_sources():raise UnsupportedArchive('assembly replay requires compatible code/documents')
                bundle=RentalNoiBundle(raw.decode(),sha);source=self.get_rental_source(p['rental_source_sha256']);spec=self.get_rental_noi_spec(p['spec_source_sha256'])
                if assemble_rental_noi(source,RentalOperationsRun(**p['rental_run']),spec)!=bundle.run:raise CorruptArchive('assembly evidence does not reproduce')
                compiled=None if p['compiled_noi_source_sha256'] is None else self._read('source',p['compiled_noi_source_sha256'])
                if compiled!=bundle.run.compiled_raw:raise CorruptArchive('compiled source changed')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:raise CorruptArchive('invalid assembly evidence')from error
        return bundle

    def save_operating_dscr(self, noi_raw, noi_run, loan_raw, windows, debt_run, binding, run):
        if type(run) is not OperatingDscrRun or calculate_operating_dscr(noi_raw,noi_run,loan_raw,windows,debt_run,binding)!=run:
            raise ValidationError('computed NOI/DSCR result does not reproduce')
        with self._transaction():
            noi=self._put('source',noi_raw);loan=self._put('source',loan_raw)
            p={'schema':'miniuw.synthetic-operating-dscr-bundle.v1','purpose':'synthetic_development_only',
                'noi_source_sha256':noi,'loan_source_sha256':loan,'windows':[asdict(w)for w in windows],
                'noi_run':asdict(noi_run),'debt_run':asdict(debt_run),'binding':asdict(binding),'run':asdict(run),
                'versions':[OPERATING_DSCR_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256],
                'definition_sources':definition_sources(),'noi_definition_sources':operating_noi_definition_sources(),
                'debt_definition_sources':debt_definition_sources()}
            return self._put('bundle',canonical(p).encode())

    def load_operating_dscr(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','noi_source_sha256','loan_source_sha256','windows','noi_run','debt_run','binding','run','versions','definition_sources','noi_definition_sources','debt_definition_sources'}:
                    raise CorruptArchive('operating DSCR fields changed')
                if p['schema']!='miniuw.synthetic-operating-dscr-bundle.v1':raise UnsupportedArchive('unsupported operating DSCR schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('operating DSCR purpose changed')
                if p['versions']!=[OPERATING_DSCR_ENGINE_SHA256,OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256] or p['definition_sources']!=definition_sources() or p['noi_definition_sources']!=operating_noi_definition_sources() or p['debt_definition_sources']!=debt_definition_sources():
                    raise UnsupportedArchive('operating DSCR replay requires compatible code/documents')
                bundle=OperatingDscrBundle(raw.decode(),sha)
                noi=self.get_operating_noi_source(p['noi_source_sha256']);loan=self.get_loan_source(p['loan_source_sha256'])
                windows=tuple(DateWindow(**w)for w in p['windows'])
                binding=OperatingDscrBinding(**p['binding']);noi_run=OperatingNoiRun(**p['noi_run']);debt_run=DebtServiceRun(**p['debt_run'])
                if calculate_operating_dscr(noi,noi_run,loan,windows,debt_run,binding)!=bundle.run:
                    raise CorruptArchive('operating DSCR evidence does not reproduce')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:
                raise CorruptArchive('invalid operating DSCR evidence')from error
        return bundle

    def get_operating_noi_source(self, sha):
        raw=self._read('source',sha);parse_operating_noi(raw);return raw

    def save_operating_noi(self, source_raw, run):
        if type(run) is not OperatingNoiRun or produce_operating_noi(source_raw)!=run:
            raise ValidationError('operating NOI result does not reproduce')
        with self._transaction():
            source=self._put('source',source_raw)
            p={'schema':'miniuw.synthetic-operating-noi-bundle.v1','purpose':'synthetic_development_only',
                'source_sha256':source,'run':asdict(run),'versions':[OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256],
                'definition_sources':operating_noi_definition_sources()}
            return self._put('bundle',canonical(p).encode())

    def load_operating_noi(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','source_sha256','run','versions','definition_sources'}:
                    raise CorruptArchive('operating NOI fields changed')
                if p['schema']!='miniuw.synthetic-operating-noi-bundle.v1':raise UnsupportedArchive('unsupported operating NOI schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('operating NOI purpose changed')
                if p['versions']!=[OPERATING_NOI_ENGINE_SHA256,DEBT_ENGINE_SHA256] or p['definition_sources']!=operating_noi_definition_sources():
                    raise UnsupportedArchive('NOI replay requires compatible code/documents')
                bundle=OperatingNoiBundle(raw.decode(),sha)
                if produce_operating_noi(self.get_operating_noi_source(p['source_sha256']))!=bundle.run:
                    raise CorruptArchive('operating NOI evidence does not reproduce')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:
                raise CorruptArchive('invalid operating NOI evidence')from error
        return bundle

    def get_scenario_proposal_source(self, sha):
        raw=self._read('source',sha);parse_scenario_proposal(raw);return raw

    def save_scenario_review(self, document_raw, base_raw, base_run, proposal_raw, run):
        if type(run) is not ScenarioReviewRun or evaluate_scenario_proposal(document_raw,base_raw,base_run,proposal_raw)!=run:
            raise ValidationError('scenario review result does not reproduce')
        with self._transaction():
            document=self._put('source',document_raw);base=self._put('source',base_raw)
            proposal=self._put('source',proposal_raw);candidate=self._put('source',run.candidate_raw)
            p={'schema':'miniuw.synthetic-scenario-review-bundle.v1','purpose':'synthetic_development_only',
                'document_source_sha256':document,'base_case_sha256':base,'base_run':asdict(base_run),
                'proposal_source_sha256':proposal,'candidate_case_sha256':candidate,'run':asdict(run),
                'versions':[SCENARIO_REVIEW_ENGINE_SHA256,SCENARIO_THRESHOLD_ENGINE_SHA256,THRESHOLD_SOURCE_ENGINE_SHA256,SCREEN_ENGINE_SHA256],
                'definition_sources':screening_definition_sources(),'user_policy_reference':user_policy_reference()}
            return self._put('bundle',canonical(p).encode())

    def load_scenario_review(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','document_source_sha256','base_case_sha256','base_run','proposal_source_sha256','candidate_case_sha256','run','versions','definition_sources','user_policy_reference'}:
                    raise CorruptArchive('scenario review fields changed')
                if p['schema']!='miniuw.synthetic-scenario-review-bundle.v1':raise UnsupportedArchive('unsupported scenario review schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('scenario review purpose changed')
                if p['versions']!=[SCENARIO_REVIEW_ENGINE_SHA256,SCENARIO_THRESHOLD_ENGINE_SHA256,THRESHOLD_SOURCE_ENGINE_SHA256,SCREEN_ENGINE_SHA256] or p['definition_sources']!=screening_definition_sources() or p['user_policy_reference']!=user_policy_reference():
                    raise UnsupportedArchive('review replay requires compatible code/documents/policy')
                bundle=ScenarioReviewBundle(raw.decode(),sha)
                document=self.get_documented_threshold_source(p['document_source_sha256'])
                base=self.get_scenario_threshold_case(p['base_case_sha256'])
                proposal=self.get_scenario_proposal_source(p['proposal_source_sha256'])
                candidate=self.get_scenario_threshold_case(p['candidate_case_sha256'])
                if evaluate_scenario_proposal(document,base,bundle.base_run,proposal)!=bundle.run or candidate!=bundle.run.candidate_raw:
                    raise CorruptArchive('scenario review does not reproduce')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:
                raise CorruptArchive('invalid scenario review evidence')from error
        return bundle

    def get_documented_threshold_source(self, sha):
        raw=self._read('source',sha);read_documented_thresholds(raw);return raw

    def get_scenario_threshold_case(self, sha):
        raw=self._read('source',sha);parse_rehearsal(raw);return raw

    def save_scenario_thresholds(self, source_raw, case_raw, run):
        if type(run) is not ScenarioThresholdRun or simulate_scenario_thresholds(source_raw,case_raw)!=run:
            raise ValidationError('scenario threshold result does not reproduce from exact source and fixture')
        with self._transaction():
            source=self._put('source',source_raw);case=self._put('source',case_raw)
            p={'schema':'miniuw.synthetic-scenario-threshold-bundle.v1','purpose':'synthetic_development_only',
                'document_source_sha256':source,'case_source_sha256':case,'run':asdict(run),
                'versions':[SCENARIO_THRESHOLD_ENGINE_SHA256,THRESHOLD_SOURCE_ENGINE_SHA256,SCREEN_ENGINE_SHA256],
                'definition_sources':screening_definition_sources(),'user_policy_reference':user_policy_reference()}
            return self._put('bundle',canonical(p).encode('utf-8'))

    def load_scenario_thresholds(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','document_source_sha256','case_source_sha256','run','versions','definition_sources','user_policy_reference'}:
                    raise CorruptArchive('scenario threshold bundle fields changed')
                if p['schema']!='miniuw.synthetic-scenario-threshold-bundle.v1':raise UnsupportedArchive('unsupported scenario threshold schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('scenario threshold purpose changed')
                if p['versions']!=[SCENARIO_THRESHOLD_ENGINE_SHA256,THRESHOLD_SOURCE_ENGINE_SHA256,SCREEN_ENGINE_SHA256] or p['definition_sources']!=screening_definition_sources() or p['user_policy_reference']!=user_policy_reference():
                    raise UnsupportedArchive('scenario threshold replay requires compatible code/documents/policy')
                bundle=ScenarioThresholdBundle(raw.decode('utf-8'),sha)
                source=self.get_documented_threshold_source(p['document_source_sha256'])
                case=self.get_scenario_threshold_case(p['case_source_sha256'])
                if simulate_scenario_thresholds(source,case)!=bundle.run:
                    raise CorruptArchive('scenario threshold evidence does not reproduce')
            except MissingEvidence:raise
            except(KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError)as error:
                raise CorruptArchive('invalid scenario threshold evidence')from error
        return bundle

    def get_review_proposal_source(self, sha):
        raw=self._read('source',sha);parse_review_proposal(raw);return raw

    def save_review_proposal(self, base_raw, base_run, proposal_raw, run):
        if type(run) is not ReviewProposalRun or evaluate_review_proposal(base_raw,base_run,proposal_raw)!=run:
            raise ValidationError('review proposal result does not reproduce from exact base/patches')
        with self._transaction():
            base=self._put('source',base_raw);proposal=self._put('source',proposal_raw)
            candidate=self._put('source',run.candidate_raw)
            p={'schema':'miniuw.synthetic-review-proposal-bundle.v1','purpose':'synthetic_development_only',
                'base_source_sha256':base,'base_run':asdict(base_run),'proposal_source_sha256':proposal,
                'candidate_source_sha256':candidate,'run':asdict(run),
                'versions':[REVIEW_PROPOSAL_ENGINE_SHA256,SCREEN_ENGINE_SHA256],
                'definition_sources':screening_definition_sources(),'user_policy_reference':user_policy_reference()}
            return self._put('bundle',canonical(p).encode('utf-8'))

    def load_review_proposal(self, sha):
        with self._transaction():
            raw=self.read_bundle_bytes(sha)
            try:
                p=json.loads(raw)
                if set(p)!={'schema','purpose','base_source_sha256','base_run','proposal_source_sha256','candidate_source_sha256','run','versions','definition_sources','user_policy_reference'}:
                    raise CorruptArchive('review proposal bundle fields changed')
                if p['schema']!='miniuw.synthetic-review-proposal-bundle.v1':raise UnsupportedArchive('unsupported review proposal schema')
                if p['purpose']!='synthetic_development_only':raise CorruptArchive('review proposal purpose changed')
                if p['versions']!=[REVIEW_PROPOSAL_ENGINE_SHA256,SCREEN_ENGINE_SHA256] or p['definition_sources']!=screening_definition_sources() or p['user_policy_reference']!=user_policy_reference():
                    raise UnsupportedArchive('review replay requires compatible code/documents/policy')
                bundle=ReviewProposalBundle(raw.decode('utf-8'),sha)
                base=self.get_screening_source(p['base_source_sha256'])
                proposal=self.get_review_proposal_source(p['proposal_source_sha256'])
                candidate=self.get_screening_source(p['candidate_source_sha256'])
                if evaluate_review_proposal(base,bundle.base_run,proposal)!=bundle.run or candidate!=bundle.run.candidate_raw:
                    raise CorruptArchive('review proposal/candidate evidence does not reproduce')
            except MissingEvidence:raise
            except (KeyError,TypeError,UnicodeError,json.JSONDecodeError,ValidationError) as error:
                raise CorruptArchive('invalid review proposal evidence') from error
        return bundle


def archive_and_import(archive, store, draft_id, *, expected_revision, operation_id, raw):
    """Source-first ordering; draft failure may leave an unreferenced source.

    This deliberately does not claim atomicity across the two databases.
    """
    archive.put_source(raw)
    return import_synthetic_source(store, draft_id, expected_revision=expected_revision,
        operation_id=operation_id, raw=raw)
