"""Explicit software-only purchase/construction cash and cash-only operating link."""
from fractions import Fraction
from pathlib import Path
import hashlib,json
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.holding_cash import OperatingPeriodEvidence
from miniuw_foundation.preopening_cash import reconcile_preopening_cash,link_preopening_to_operation

ROOT=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def claim(value):return {'value':None if value is None else rational(Fraction(value)),'currency':'USD','source_ref':'SYNTHETIC-supplied-cash-only-not-invoice-or-bank-proof'}


def make_operation():
    nr=(ROOT/'templates/synthetic-project-pre-refi-noi.json').read_bytes();noi=produce_operating_noi(nr)
    spec=json.loads((ROOT/'templates/synthetic-project-pre-refi-operation.json').read_bytes())
    spec.update(noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256);sr=raw(spec)
    return OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=reconcile_operating_cash(nr,noi,sr))


def make_source(context):
    rows=[('2026-10-01','initial_equity_contribution',1500,None),('2026-10-01','acquisition_payment',400,None),
        ('2026-11-01','loan_draw',600,'SYNTHETIC-preopening-loan'),('2026-11-01','construction_payment',800,None),
        ('2026-11-01','soft_cost_payment',100,None),('2026-11-01','reserve_deposit',200,None),
        ('2026-12-01','additional_equity_contribution',300,None),('2026-12-01','loan_principal_repayment',100,'SYNTHETIC-preopening-loan'),
        ('2026-12-01','debt_interest_payment',20,'SYNTHETIC-preopening-loan'),('2026-12-01','debt_fee_payment',5,'SYNTHETIC-preopening-loan'),
        ('2026-12-01','equity_distribution',25,None),('2026-12-01','other_cash_receipt',100,None),
        ('2026-12-01','other_cash_payment',50,None),('2026-12-01','reserve_release',200,None),
        ('2027-01-01','additional_equity_contribution',0,None)]
    return {'schema':'miniuw.synthetic-preopening-cash.v1','profile':'SYNTHETIC-ZERO-OPENING-PREOPERATING-CASH-v1',
        'context':context,'currency':'USD','start_date':'2026-10-01','opening_operation_date':'2027-01-01',
        'inventory_declared_complete':True,'zero_opening_basis_ref':'SYNTHETIC-no-inherited-cash-principal-or-assets-in-this-cash-profile',
        'classification_basis_ref':'SYNTHETIC-explicit-disjoint-gross-cash-no-accrual-capitalization-or-direct-bank-payments',
        'boundary_basis_ref':'SYNTHETIC-all-cutoff-day-events-before-operating-opening-not-intraday-order',
        'loan_ids':['SYNTHETIC-preopening-loan'],
        'events':[dict(event_id='SYNTHETIC-preopening-event-'+str(i),date=date,category=category,loan_id=loan,amount=claim(value))for i,(date,category,value,loan)in enumerate(rows)],
        'terminal_claims':{'free_cash':claim(1000),'restricted_cash':claim(0),'loan_principal':{'SYNTHETIC-preopening-loan':claim(500)}}}


def make_binding(source,run,period):
    return {'schema':'miniuw.synthetic-preopening-operation-link.v1','preopening_source_sha256':sha(source),
        'preopening_run_sha256':run.sha256,'operating_source_sha256':sha(period.spec_raw),'operating_run_sha256':period.cash_run.sha256,
        'boundary_basis_ref':'SYNTHETIC-cash-only-no-debt-asset-or-return-integration'}


def main():
    period=make_operation();source=make_source(period.cash_run.payload['context']);sr=raw(source);run=reconcile_preopening_cash(sr)
    binding=make_binding(sr,run,period);br=raw(binding);link=link_preopening_to_operation(sr,run,period,br)
    assert run.payload['state']=='reconciled_synthetic_preopening_cash'and link.payload['state']=='matched_synthetic_cash_only'
    for path,value in [('templates/synthetic-preopening-cash-example.json',source),('templates/synthetic-preopening-operation-link-example.json',binding)]:
        (ROOT/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    # Bind examples to their actual saved bytes, including their intentional indentation.
    sr=(ROOT/'templates/synthetic-preopening-cash-example.json').read_bytes();run=reconcile_preopening_cash(sr)
    binding=make_binding(sr,run,period);(ROOT/'templates/synthetic-preopening-operation-link-example.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2)+'\n')
    br=(ROOT/'templates/synthetic-preopening-operation-link-example.json').read_bytes();link=link_preopening_to_operation(sr,run,period,br)
    missing=json.loads(sr);missing['events'][0]['amount']['value']=None;blocked=reconcile_preopening_cash(raw(missing))
    return {'purpose':'synthetic_preopening_cash_only_demo','source_sha256':sha(sr),'run_sha256':run.sha256,'link_binding_source_sha256':sha(br),'link_run_sha256':link.sha256,
        'state':run.payload['state'],'cash_only_link_state':link.payload['state'],'totals':run.payload['totals'],
        'date_close_balances':run.payload['date_close_balances'],'cash_conservation_residual':run.payload['cash_conservation_residual'],
        'equity_movements':run.payload['exportable_equity_movements'],'cash_boundary_checks':link.payload['cash_boundary_checks'],
        'missing_amount_case':{'state':blocked.payload['state'],'blockers':blocked.payload['blockers'],'exportable_equity_movements':blocked.payload['exportable_equity_movements']},
        'debt_carry_reconciliation_pending':True,'fixture_note':'Preopening closing principal 500 is not matched to any operating loan. Cash-only link leaves original T34 and all past investor-return examples unchanged; no whole-project return inferred.',
        'whole_project_investor_returns_connected':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
