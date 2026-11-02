"""Explicit synthetic sizing source revisions; never auto-select a principal."""
from pathlib import Path
import json,copy,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.debt_closing import DatedLoanEvidence
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.refinance_capacity import RefinanceInputs
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def load_capacity(case='tie'):
    def read(name):return json.loads((R/'templates'/name).read_bytes())
    return dict(valuation=read(f'synthetic-capacity-{case}-valuation-noi.json'),bank=read(f'synthetic-capacity-{case}-bank-noi.json'),loan=read('synthetic-capacity-tie-loan.json'if case=='tie'else'synthetic-project-sale-loan.json'),closing=read('synthetic-capacity-tie-closing.json'if case=='tie'else'synthetic-project-refinance-closing.json'),spec=read(f'synthetic-capacity-{case}-spec.json'))
def build_capacity(data):
    vr=raw(data['valuation']);br=raw(data['bank']);lr=raw(data['loan']);cr=raw(data['closing']);v=produce_operating_noi(vr);b=produce_operating_noi(br);loan=produce_debt_service(lr,());closing=produce_closing_cash(cr);s=copy.deepcopy(data['spec'])
    s.update(valuation_noi_source_sha256=sha(vr),valuation_noi_run_sha256=v.sha256,bank_noi_source_sha256=sha(br),bank_noi_run_sha256=b.sha256,new_loan_source_sha256=sha(lr),new_loan_run_sha256=loan.sha256,closing_source_sha256=sha(cr),closing_run_sha256=closing.sha256)
    return RefinanceInputs(valuation_noi_raw=vr,valuation_noi_run=v,bank_noi_raw=br,bank_noi_run=b,new_loan=DatedLoanEvidence(loan_raw=lr,windows=(),run=loan),closing_raw=cr,closing_run=closing),raw(s)
