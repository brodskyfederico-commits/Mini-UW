from pathlib import Path
import json
from fractions import Fraction
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from project_test_support import load_case
from sale_revision_test_support import make_evidence,raw,sha

ROOT=Path(__file__).resolve().parents[1]


def valuation():
    nr=(ROOT/'templates/synthetic-exit-forward-noi.json').read_bytes();n=produce_operating_noi(nr)
    vr=(ROOT/'templates/synthetic-exit-value-spec.json').read_bytes();v=produce_exit_value(nr,n,vr)
    return nr,n,vr,v


def evidence(compatible=True):
    p=load_case();p['closings'][1]['valuation_claim']=None
    return make_evidence(compatible=compatible,project=p)


def cost_source(value_run):
    p=value_run.payload
    source=dict(schema='miniuw.synthetic-fixed-and-gross-percent-sale-costs.v1',context=p['context'],currency=p['currency'],sale_date=p['valuation_date'],
        gross_price=dict(value=p['candidate_value'],currency=p['currency'],as_of_date=p['valuation_date'],basis='projected_gross_sale_price',source_ref='miniuw:synthetic-exit-value:'+value_run.sha256+'#/candidate_value'),
        inventory_declared_complete=True,inventory_basis_ref='SYNTHETIC-selected-cost-inventory-not-real-completeness',nonoverlap_basis_ref='SYNTHETIC-no-overlap-with-each-other-or-bank-payoffs',costs=[])
    for identity,kind,amount,unit in [('fixed','fixed',10,'currency'),('fee','percent_of_gross',Fraction(1,20),'fraction_of_gross_price')]:
        source['costs'].append(dict(cost_id=identity,classification='transaction_cost',kind=kind,applicability='included',applicability_basis_ref='SYNTHETIC-explicit-charge-not-adopted',value=rational(Fraction(amount)),unit=unit,currency=p['currency'],as_of_date=p['valuation_date'],source_ref='SYNTHETIC-explicit-cost:'+identity))
    return source


def bridge_spec(e,vr,v,cr,c):
    return dict(schema='miniuw.synthetic-costed-exit-sale.v1',revision_id='SYNTHETIC-costed-sale',base_evidence_sha256=evidence_fingerprint(e),exit_spec_sha256=sha(vr),exit_run_sha256=v.sha256,
        sale_node_id='SYNTHETIC-project-sale',sale_at_value_hypothesis_ref='SYNTHETIC-explicit-sale-hypothesis-not-actual-receipt',unchanged_other_sources_basis_ref='SYNTHETIC-other-sources-frozen',equity_funding_assumption_ref=None,cost_source_sha256=sha(cr),cost_run_sha256=c.sha256)
