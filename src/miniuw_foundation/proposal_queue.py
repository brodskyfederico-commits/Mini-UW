"""T17 local synthetic proposal lifecycle ledger, never approval or publication."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib,json,re,sqlite3
from .drafts import ValidationError,canonical,digest,nonempty


class QueueRevisionConflict(ValidationError):pass
class QueueOperationConflict(ValidationError):pass
class QueueIntegrityError(ValueError):pass


@dataclass(frozen=True)
class QueueReceipt:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


class ProposalQueue:
    APPLICATION_ID=0x4D555751
    def __init__(self,path):
        self._connection=sqlite3.connect(path,isolation_level=None,timeout=5)
        try:
            app=self._connection.execute('PRAGMA application_id').fetchone()[0]
            version=self._connection.execute('PRAGMA user_version').fetchone()[0]
            tables={r[0]for r in self._connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if version==0:
                if tables or app!=0:raise QueueIntegrityError('queue requires its own empty database')
                self._connection.executescript('''BEGIN IMMEDIATE;
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL);
INSERT INTO meta VALUES(1,0);
CREATE TABLE entries(proposal_id TEXT PRIMARY KEY,bundle_sha TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('recorded','withdrawn','superseded')),parent_proposal_id TEXT,candidate_case_sha TEXT NOT NULL,candidate_run_sha TEXT NOT NULL,base_case_sha TEXT NOT NULL,document_sha TEXT NOT NULL,deal_id TEXT NOT NULL);
CREATE TABLE events(revision INTEGER PRIMARY KEY,operation_id TEXT UNIQUE NOT NULL,request_sha TEXT NOT NULL,payload_json TEXT NOT NULL,receipt_sha TEXT NOT NULL);
PRAGMA application_id='''+str(self.APPLICATION_ID)+''';
PRAGMA user_version=1;
COMMIT;''')
            elif version!=1 or app!=self.APPLICATION_ID or tables!={'meta','entries','events'}:
                raise QueueIntegrityError('unsupported proposal queue')
        except BaseException:self._connection.close();raise
    def close(self):self._connection.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _commit(self):self._connection.execute('COMMIT')
    @contextmanager
    def _transaction(self):
        self._connection.execute('BEGIN IMMEDIATE')
        try:yield;self._commit()
        except BaseException:
            if self._connection.in_transaction:self._connection.execute('ROLLBACK')
            raise
    def _entry(self,proposal_id):
        nonempty(proposal_id,'proposal_id')
        row=self._connection.execute('SELECT proposal_id,bundle_sha,state,parent_proposal_id,candidate_case_sha,candidate_run_sha,base_case_sha,document_sha,deal_id FROM entries WHERE proposal_id=?',(proposal_id,)).fetchone()
        if row is None:raise QueueRevisionConflict('proposal is absent')
        return dict(zip(['proposal_id','bundle_sha','state','parent_proposal_id','candidate_case_sha','candidate_run_sha','base_case_sha','document_sha','deal_id'],row))
    def _evidence(self,archive,bundle_sha):
        if type(bundle_sha)is not str or not re.fullmatch('[a-f0-9]{64}',bundle_sha):raise ValidationError('exact review bundle hash required')
        bundle=archive.load_scenario_review(bundle_sha);p=bundle.run.payload;c=bundle.run.candidate_run
        return {'proposal_id':p['proposal_id'],'bundle_sha':bundle_sha,'candidate_case_sha':p['candidate_case_sha256'],
            'candidate_run_sha':c.sha256,'base_case_sha':p['base_case_sha256'],'document_sha':p['document_sha256'],
            'deal_id':c.payload['context']['deal_id'],'base_run_sha':p['base_run_sha256']}
    def _insert(self,info,parent):
        if self._connection.execute('SELECT 1 FROM entries WHERE proposal_id=?',(info['proposal_id'],)).fetchone():
            raise QueueRevisionConflict('proposal identity already recorded; no replacement by name')
        self._connection.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?,?,?)',(info['proposal_id'],info['bundle_sha'],'recorded',parent,
            info['candidate_case_sha'],info['candidate_run_sha'],info['base_case_sha'],info['document_sha'],info['deal_id']))
    def _change(self,request,action):
        nonempty(request['operation_id'],'operation_id');nonempty(request['actor_label'],'actor_label');nonempty(request['reason'],'reason')
        expected=request['expected_revision']
        if type(expected)is not int or expected<0:raise ValidationError('nonnegative exact expected queue revision required')
        request_sha=digest(canonical(request))
        with self._transaction():
            prior=self._connection.execute('SELECT request_sha,payload_json,receipt_sha FROM events WHERE operation_id=?',(request['operation_id'],)).fetchone()
            if prior:
                if prior[0]!=request_sha:raise QueueOperationConflict('operation identity reused with different request')
                if digest(prior[1])!=prior[2]:raise QueueIntegrityError('receipt content changed')
                return QueueReceipt(prior[1],prior[2])
            revision=self._connection.execute('SELECT revision FROM meta WHERE id=1').fetchone()[0]
            if revision!=expected:raise QueueRevisionConflict('queue revision changed; refresh before a new operation')
            outcome=action();new=revision+1
            payload={'component':'T17','purpose':'synthetic_lifecycle_only','revision':new,'operation_id':request['operation_id'],
                'request':request,'outcome':outcome,'actor_identity_verified':False,'proposal_accepted':False,
                'professional_review_authenticated':False,'decision':'PENDING','production_authorized':False}
            encoded=canonical(payload);sha=digest(encoded)
            self._connection.execute('INSERT INTO events VALUES(?,?,?,?,?)',(new,request['operation_id'],request_sha,encoded,sha))
            self._connection.execute('UPDATE meta SET revision=? WHERE id=1',(new,))
            return QueueReceipt(encoded,sha)
    def record(self,archive,bundle_sha,*,operation_id,expected_revision,actor_label,reason):
        request=dict(kind='record',bundle_sha=bundle_sha,operation_id=operation_id,expected_revision=expected_revision,actor_label=actor_label,reason=reason)
        def action():
            info=self._evidence(archive,bundle_sha);self._insert(info,None)
            return {'proposal_id':info['proposal_id'],'state':'recorded','bundle_sha':bundle_sha}
        return self._change(request,action)
    def withdraw(self,proposal_id,*,operation_id,expected_revision,actor_label,reason):
        request=dict(kind='withdraw',proposal_id=proposal_id,operation_id=operation_id,expected_revision=expected_revision,actor_label=actor_label,reason=reason)
        def action():
            entry=self._entry(proposal_id)
            if entry['state']!='recorded':raise QueueRevisionConflict('only a recorded proposal may be withdrawn')
            self._connection.execute("UPDATE entries SET state='withdrawn' WHERE proposal_id=?",(proposal_id,))
            return {'proposal_id':proposal_id,'state':'withdrawn','bundle_sha':entry['bundle_sha']}
        return self._change(request,action)
    def supersede(self,archive,proposal_id,new_bundle_sha,*,operation_id,expected_revision,actor_label,reason):
        request=dict(kind='supersede',proposal_id=proposal_id,new_bundle_sha=new_bundle_sha,operation_id=operation_id,expected_revision=expected_revision,actor_label=actor_label,reason=reason)
        def action():
            old=self._entry(proposal_id)
            if old['state']!='recorded':raise QueueRevisionConflict('only a recorded proposal may be superseded')
            prior=self._evidence(archive,old['bundle_sha'])
            for key in ['proposal_id','candidate_case_sha','candidate_run_sha','base_case_sha','document_sha','deal_id']:
                if prior[key]!=old[key]:raise QueueIntegrityError('prior evidence reference changed')
            info=self._evidence(archive,new_bundle_sha)
            if (info['base_case_sha']!=old['candidate_case_sha']or info['base_run_sha']!=old['candidate_run_sha']or info['document_sha']!=old['document_sha']or info['deal_id']!=old['deal_id']):
                raise QueueRevisionConflict('replacement must descend from the exact prior candidate and run')
            self._insert(info,proposal_id)
            self._connection.execute("UPDATE entries SET state='superseded' WHERE proposal_id=?",(proposal_id,))
            return {'proposal_id':proposal_id,'state':'superseded','replacement_proposal_id':info['proposal_id'],'replacement_bundle_sha':new_bundle_sha}
        return self._change(request,action)
    def snapshot(self):
        with self._transaction():
            revision=self._connection.execute('SELECT revision FROM meta WHERE id=1').fetchone()[0]
            ids=[r[0]for r in self._connection.execute('SELECT proposal_id FROM entries ORDER BY proposal_id')]
            return {'revision':revision,'entries':[self._entry(i)for i in ids],'purpose':'synthetic_queue_projection_only',
                'evidence_replayed':False,'decision':'PENDING','professional_review_authenticated':False,'production_authorized':False}
    def history(self):
        with self._transaction():
            result=[]
            for payload,sha in self._connection.execute('SELECT payload_json,receipt_sha FROM events ORDER BY revision'):
                if digest(payload)!=sha:raise QueueIntegrityError('receipt content changed')
                result.append(QueueReceipt(payload,sha))
            return tuple(result)
    def verify_entry(self,archive,proposal_id):
        with self._transaction():
            entry=self._entry(proposal_id);info=self._evidence(archive,entry['bundle_sha'])
            for key in ['proposal_id','candidate_case_sha','candidate_run_sha','base_case_sha','document_sha','deal_id']:
                if info[key]!=entry[key]:raise QueueIntegrityError('queue evidence reference changed')
            return dict(entry,evidence_replayed=True,professional_review_authenticated=False,decision='PENDING')
