"""Explicit staged-loan software inputs and empty preopening debt slots."""
import json,copy,hashlib
from fractions import Fraction
from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.construction_draws import produce_construction_draws
from miniuw_foundation.construction_cash import ConstructionLoanEvidence,assemble_construction_cash

def raw(p):return canonical(p).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def q(n):return rational(Fraction(n))
def money(n):return dict(value=None if n is None else q(n),currency='USD',source_ref='SYNTHETIC-explicit-cash-input-not-bank-proof')


def sources():
    context=dict(deal_id='SYNTHETIC-construction-draw-demo',scenario_id='SYNTHETIC-draw-plan',run_id='SYNTHETIC-construction-draw-run',definition_set_revision='SYNTHETIC-simple-interval-factors')
    loan_id='SYNTHETIC-staged-loan';periods=[]
    dates=['2026-10-01','2026-11-01','2026-12-01','2027-01-01']
    for i,(draw,repayment)in enumerate([(100,0),(100,50),(50,0)]):
        pid='SYNTHETIC-construction-period-'+str(i+1)
        periods.append(dict(period_id=pid,start_date=dates[i],end_date=dates[i+1],interval_basis_ref='SYNTHETIC-provided-factor-for-entire-interval-not-annual-rate',draw_at_start=money(draw),available_new_draw=money(draw),principal_repayment_at_end=money(repayment),interest_fraction=dict(value=q(Fraction(1,100)),unit='simple_interval_fraction',interval_ref=pid,source_ref='SYNTHETIC-explicit-interval-factor-not-day-count-rule')))
    loan=dict(schema='miniuw.synthetic-construction-draws.v1',profile='SYNTHETIC-START-DRAW-END-REPAY-SIMPLE-INTERVAL-NONREVOLVING-v1',context=copy.deepcopy(context),currency='USD',loan_id=loan_id,start_date=dates[0],end_date=dates[-1],maturity_date='2027-07-01',inventory_declared_complete=True,
        zero_opening_principal_basis_ref='SYNTHETIC-no-prior-principal',nonrevolving_commitment_basis_ref='SYNTHETIC-no-credit-recycling',principal_commitment=money(300),draw_fee_fraction=dict(value=q(Fraction(2,100)),unit='gross_draw_fraction',source_ref='SYNTHETIC-explicit-fee-per-gross-draw-not-commitment'),periods=periods)
    pre=dict(schema='miniuw.synthetic-preopening-cash.v1',profile='SYNTHETIC-ZERO-OPENING-PREOPERATING-CASH-v1',context=context,currency='USD',start_date=dates[0],opening_operation_date=dates[-1],inventory_declared_complete=True,
        zero_opening_basis_ref='SYNTHETIC-zero-cash-and-principal-not-asset-verification',classification_basis_ref='SYNTHETIC-disjoint-cash-only-no-capitalization',boundary_basis_ref='SYNTHETIC-all-cutoff-events-before-operating-opening',loan_ids=[loan_id],
        events=[dict(event_id='SYNTHETIC-equity-initial',date=dates[0],category='initial_equity_contribution',loan_id=None,amount=money(1000)),
            dict(event_id='SYNTHETIC-acquisition',date=dates[0],category='acquisition_payment',loan_id=None,amount=money(300)),
            dict(event_id='SYNTHETIC-equity-additional',date=dates[1],category='additional_equity_contribution',loan_id=None,amount=money(400)),
            dict(event_id='SYNTHETIC-construction',date=dates[1],category='construction_payment',loan_id=None,amount=money(600)),
            dict(event_id='SYNTHETIC-soft-cost',date=dates[2],category='soft_cost_payment',loan_id=None,amount=money(100))],
        terminal_claims=dict(free_cash=money(590),restricted_cash=money(0),loan_principal={loan_id:money(200)}))
    return dict(loans=[loan],draft=pre)


def build(data,binding_change=None,draft_change=None):
    loans=tuple(ConstructionLoanEvidence(raw=raw(p),run=produce_construction_draws(raw(p)))for p in data['loans']);draft=copy.deepcopy(data['draft']);slots=[]
    for i,source in enumerate(data['loans']):
        for j,row in enumerate(source['periods']):
            for category,key in [('loan_draw','start_date'),('debt_fee_payment','start_date'),('debt_interest_payment','end_date'),('loan_principal_repayment','end_date')]:
                eid='SYNTHETIC-debt-'+str(i)+'-'+str(j)+'-'+category
                draft['events'].append(dict(event_id=eid,date=row[key],category=category,loan_id=source['loan_id'],amount=dict(value=None,currency=source['currency'],source_ref=None)))
                slots.append(dict(loan_id=source['loan_id'],period_id=row['period_id'],category=category,target_event_id=eid))
    draft['events'].sort(key=lambda e:e['date'])
    if draft_change:draft_change(draft)
    dr=raw(draft);b=dict(schema='miniuw.synthetic-construction-cash-link.v1',preopening_source_sha256=sha(dr),scope_basis_ref='SYNTHETIC-exact-all-staged-debt-cash-events-no-auto-funding',loans=[dict(loan_id=e.run.payload['loan_id'],source_sha256=sha(e.raw),run_sha256=e.run.sha256)for e in loans],event_slots=slots)
    if binding_change:binding_change(b)
    br=raw(b);return loans,dr,br,assemble_construction_cash(loans,dr,br)
