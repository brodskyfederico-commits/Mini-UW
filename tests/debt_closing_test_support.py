"""Explicit synthetic source revisions for debt/closing integration tests."""
from pathlib import Path
import json,copy,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import DatedLoanEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def fixture(kind='refinance'):
    return tuple(json.loads((R/f'templates/synthetic-debt-checked-{kind}-{part}.json').read_bytes())for part in ['loan','closing','binding'])
def build(loan,closing,spec,windows=()):
    nr=raw(loan);dr=produce_debt_service(nr,windows);cr=raw(closing);c=produce_closing_cash(cr);s=copy.deepcopy(spec)
    s.update(closing_source_sha256=sha(cr),closing_run_sha256=c.sha256)
    for row in s['loans']:
        if row['loan_id']==loan['loan_id']:row.update(loan_source_sha256=sha(nr),loan_run_sha256=dr.sha256)
    return (DatedLoanEvidence(loan_raw=nr,windows=windows,run=dr),),cr,c,raw(s)
def set_closing_date(closing,date):
    closing['closing_date']=date
    for row in closing['amounts'].values():row['as_of_date']=date
    for d in closing['old_debts']:
        for key,row in d.items():
            if key!='loan_id':row['as_of_date']=date
    if closing['new_loan']is not None:closing['new_loan']['principal_after_closing']['as_of_date']=date
