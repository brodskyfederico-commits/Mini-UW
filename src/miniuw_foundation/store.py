"""Local SQLite versioned synthetic draft storage with atomic CAS and exact retry identity."""
from dataclasses import dataclass
from contextlib import contextmanager
import json,sqlite3
from .drafts import ContextSeed,RawClaim,Snapshot,ValidationError,canonical,digest,fresh_payload,append_claims

class AlreadyExists(ValueError):pass
class NotFound(KeyError):pass
class RevisionConflict(ValueError):pass
class IdempotencyConflict(ValueError):pass
class CorruptSnapshot(ValueError):pass
class UnsupportedDatabase(ValueError):pass

@dataclass(frozen=True)
class MutationResult:
    snapshot:Snapshot
    current_revision_observed:int
    replayed:bool

class DraftStore:
    APPLICATION_ID=0x4D555731
    def __init__(self,path):
        self._connection=sqlite3.connect(path,isolation_level=None,timeout=5)
        self._connection.execute('PRAGMA foreign_keys=ON')
        app=self._connection.execute('PRAGMA application_id').fetchone()[0];version=self._connection.execute('PRAGMA user_version').fetchone()[0]
        existing=self._connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        if (version==0 and (existing or app!=0)) or (version!=0 and (version!=1 or app!=self.APPLICATION_ID)):
            self.close();raise UnsupportedDatabase('not an empty database or a supported T01 store')
        if version==0:
            self._connection.executescript('''BEGIN IMMEDIATE;
CREATE TABLE drafts(draft_id TEXT PRIMARY KEY, current_revision INTEGER NOT NULL);
CREATE TABLE revisions(draft_id TEXT NOT NULL REFERENCES drafts(draft_id), revision INTEGER NOT NULL, payload TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(draft_id,revision));
CREATE TABLE operations(draft_id TEXT NOT NULL, operation_id TEXT NOT NULL, payload_digest TEXT NOT NULL, applied_revision INTEGER NOT NULL, PRIMARY KEY(draft_id,operation_id), FOREIGN KEY(draft_id,applied_revision) REFERENCES revisions(draft_id,revision));
PRAGMA application_id=1297438513;
PRAGMA user_version=1;
COMMIT;''')
    def close(self):self._connection.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _commit(self):self._connection.execute('COMMIT')
    @contextmanager
    def _transaction(self):
        self._connection.execute('BEGIN IMMEDIATE')
        try:
            yield
            self._commit()
        except BaseException:
            if self._connection.in_transaction:self._connection.execute('ROLLBACK')
            raise
    def _head(self,id):
        row=self._connection.execute('SELECT current_revision FROM drafts WHERE draft_id=?',(id,)).fetchone()
        if row is None:raise NotFound(id)
        return row[0]
    def _read(self,id,revision):
        row=self._connection.execute('SELECT payload,sha256 FROM revisions WHERE draft_id=? AND revision=?',(id,revision)).fetchone()
        if row is None:raise NotFound((id,revision))
        if digest(row[0])!=row[1]:raise CorruptSnapshot('snapshot content hash mismatch')
        payload=json.loads(row[0])
        if payload.get('draft_id')!=id or payload.get('revision')!=revision or payload.get('context',{}).get('input_revision')!=id+'@'+str(revision) or payload.get('decision')!='PENDING' or payload.get('run_ready') is not False or payload.get('authorization')!='not_granted':raise CorruptSnapshot('snapshot identity/development guards changed')
        return Snapshot(id,revision,row[0],row[1])
    def _insert(self,id,revision,payload):
        encoded=canonical(payload);self._connection.execute('INSERT INTO revisions VALUES(?,?,?,?)',(id,revision,encoded,digest(encoded)))
    def create(self,id,seed):
        payload=fresh_payload(id,seed)
        with self._transaction():
            if self._connection.execute('SELECT 1 FROM drafts WHERE draft_id=?',(id,)).fetchone():raise AlreadyExists(id)
            self._connection.execute('INSERT INTO drafts VALUES(?,0)',(id,));self._insert(id,0,payload);snapshot=self._read(id,0)
        return snapshot
    def get(self,id,revision=None):
        # The returned snapshot is immutable; latest is only an observation, not publication authority.
        if revision is None:revision=self._head(id)
        return self._read(id,revision)
    def append(self,id,*,expected_revision,operation_id,claims):
        if type(expected_revision) is not int or expected_revision<0:raise ValidationError('explicit nonnegative expected revision required')
        if type(operation_id) is not str or not operation_id.strip():raise ValidationError('explicit operation identity required')
        if type(claims) not in (list,tuple) or not claims or any(type(c) is not RawClaim for c in claims):raise ValidationError('explicit nonempty RawClaim batch required')
        request_digest=digest(canonical({'expected_revision':expected_revision,'claims':[c.record() for c in claims]}))
        with self._transaction():
            head=self._head(id);op=self._connection.execute('SELECT payload_digest,applied_revision FROM operations WHERE draft_id=? AND operation_id=?',(id,operation_id)).fetchone()
            if op is not None:
                if op[0]!=request_digest:raise IdempotencyConflict('operation ID reused with a different request')
                result=MutationResult(self._read(id,op[1]),head,True)
            else:
                if head!=expected_revision:raise RevisionConflict('draft changed since the supplied revision')
                revision=head+1;payload=append_claims(self._read(id,head).payload,claims,revision);self._insert(id,revision,payload)
                changed=self._connection.execute('UPDATE drafts SET current_revision=? WHERE draft_id=? AND current_revision=?',(revision,id,head)).rowcount
                if changed!=1:raise RevisionConflict('concurrent draft update')
                self._connection.execute('INSERT INTO operations VALUES(?,?,?,?)',(id,operation_id,request_digest,revision));result=MutationResult(self._read(id,revision),revision,False)
        return result
