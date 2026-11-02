"""Explicit source revisions for integrated cash-window tests; no value repairs."""
from pathlib import Path
import json,copy,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence,reconcile_debt_closing
from miniuw_foundation.project_cash import CheckedClosingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def load_case():
    def read(tag):return json.loads((R/f'templates/synthetic-project-{tag}.json').read_bytes())
    return dict(nois=[read(tag+'-noi')for tag in ['pre-refi','post-refi']],ops=[read(tag+'-operation')for tag in ['pre-refi','post-refi']],closings=[read(k+'-closing')for k in ['refinance','sale']],loans=[[read(k+'-loan')]for k in ['refinance','sale']],debt_specs=[read(k+'-debt-binding')for k in ['refinance','sale']],closing_ids=['SYNTHETIC-project-refinance','SYNTHETIC-project-sale'],manifest=read('cash-manifest'),investor=read('investor-slots'))
def build(data):
    m=copy.deepcopy(data['manifest']);periods=[];closings=[];bindings={}
    for n,s in zip(data['nois'],data['ops']):
        nr=raw(n);noi=produce_operating_noi(nr);s=copy.deepcopy(s);s.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256);sr=raw(s);cash=reconcile_operating_cash(nr,noi,sr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash));bindings[s['period_ref']]=dict(source_sha256=sha(sr),run_sha256=cash.sha256,upstream_source_sha256=sha(nr),upstream_run_sha256=noi.sha256)
    for closing,loans,binding,cid in zip(data['closings'],data['loans'],data['debt_specs'],data['closing_ids']):
        cr=raw(closing);c=produce_closing_cash(cr);b=copy.deepcopy(binding);b.update(closing_source_sha256=sha(cr),closing_run_sha256=c.sha256);evidence=[]
        for terms in loans:
            lr=raw(terms);debt=produce_debt_service(lr,());evidence.append(DatedLoanEvidence(loan_raw=lr,windows=(),run=debt))
            for row in b['loans']:
                if row['loan_id']==terms['loan_id']:row.update(loan_source_sha256=sha(lr),loan_run_sha256=debt.sha256)
        br=raw(b);r=reconcile_debt_closing(tuple(evidence),cr,c,br);closings.append(CheckedClosingEvidence(closing_id=cid,closing_raw=cr,closing_run=c,loans=tuple(evidence),debt_spec_raw=br,debt_run=r))
        bindings[cid]=dict(source_sha256=sha(cr),run_sha256=c.sha256,upstream_source_sha256=sha(br),upstream_run_sha256=r.sha256)
    for row in m['nodes']:
        if row['node_id']in bindings:row.update(bindings[row['node_id']])
    return tuple(periods),tuple(closings),raw(m)
