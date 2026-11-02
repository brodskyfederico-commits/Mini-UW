"""Explicit synthetic fixture revisions for holding integration tests only."""
from pathlib import Path
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(p):return hashlib.sha256(p).hexdigest()
def load_case():
    return ([json.loads((R/f'templates/synthetic-holding-noi-{i}.json').read_bytes())for i in [1,2,3]],
        [json.loads((R/f'templates/synthetic-holding-period-{i}.json').read_bytes())for i in [1,2,3]],
        json.loads((R/'templates/synthetic-holding-manifest.json').read_bytes()),
        json.loads((R/'templates/synthetic-holding-investor-slots.json').read_bytes()))
def build(nois,specs,manifest):
    """Bind newly supplied test revisions; never repair values, balances or order."""
    m=copy.deepcopy(manifest);periods=[]
    for n,s in zip(nois,specs):
        s=copy.deepcopy(s);nr=raw(n);noi=produce_operating_noi(nr);s.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256)
        sr=raw(s);cash=reconcile_operating_cash(nr,noi,sr);periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash))
        for row in m['periods']:
            if row['period_ref']==s['period_ref']:row.update({k:s[k]for k in ['start_date','end_date','cash_date']},noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256,spec_source_sha256=sha(sr),cash_run_sha256=cash.sha256)
    return tuple(periods),raw(m)
