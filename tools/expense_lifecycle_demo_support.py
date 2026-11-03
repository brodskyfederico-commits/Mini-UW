"""Explicit independent software fixture, not a tax or payment convention."""
from dataclasses import asdict
from pathlib import Path
import copy
import hashlib
import json
from fractions import Fraction

from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.expense_cash_detail import ASSUMPTIONS, reconcile_expense_cash_detail
from miniuw_foundation.staged_lifecycle_bundle import export_staged_lifecycle_bundle, recover_staged_lifecycle_bundle
from miniuw_foundation.expense_checked_lifecycle import recover_expense_checked_bundle
from miniuw_foundation.current_expense_lifecycle import required_expense_lifecycle_sources
from staged_phase_demo_support import make_case

ROOT = Path(__file__).resolve().parents[1]
AT = '2027-07-01T12:00:00Z'
raw = lambda p: canonical(p).encode('utf-8')
q = lambda n: rational(Fraction(n))
sha = lambda b: hashlib.sha256(b).hexdigest()


def make_lifecycle(terms_change=None):
    def change(d):
        for i, n in enumerate(d['nois']):
            row = n['expense_rows'][0]
            n['expense_rows'] = [dict(row, item_id='SYNTHETIC-insurance', value=q(10), source_ref='SYNTHETIC-insurance-accrual-'+str(i)),
                                 dict(row, item_id='SYNTHETIC-other-opex', value=q(5), source_ref='SYNTHETIC-other-accrual-'+str(i))]
            c = d['ops'][i]
            c['working_balances']['payables']['opening']['value'] = q(0 if i == 0 else 5)
            c['working_balances']['payables']['closing']['value'] = q(5 if i == 0 else 0)
            c['amounts']['operating_payments_claim']['value'] = q(10 if i == 0 else 20)
            c['amounts']['opening_free_cash']['value'] = q(590 if i == 0 else 430)
            c['amounts']['closing_free_cash_claim']['value'] = q(430 if i == 0 else 270)
        d['sale']['amounts']['opening_free_cash']['value'] = q(270)
    case = make_case(holding_change=change, terms_change=terms_change)
    if terms_change is None:
        assert case[-1].investor_run is not None, case[-1].payload['blockers']
    return export_staged_lifecycle_bundle(*case)


def make_manifest(lifecycle_raw):
    recovered = recover_staged_lifecycle_bundle(lifecycle_raw)
    p = dict(schema='miniuw.synthetic-expense-lifecycle-manifest.v1', lifecycle_bundle_sha256=sha(lifecycle_raw),
             context=recovered.run.payload['context'], currency='USD', inventory_declared_complete=True,
             continuity_basis_ref='SYNTHETIC-explicit-fixed-concept-payable-prepaid-continuity',
             item_inventory_basis_ref='SYNTHETIC-complete-fixed-insurance-other-tax-inventory', periods=[])
    for i, e in enumerate(recovered.window_args[3][0]):
        c = json.loads(e.spec_raw)
        detail = dict(schema='miniuw.synthetic-expense-cash-detail.v1', context=p['context'], currency='USD',
                      period_ref=c['period_ref'], start_date=c['start_date'], end_date=c['end_date'],
                      noi_source_sha256=sha(e.noi_raw), noi_run_sha256=e.noi_run.sha256,
                      cash_source_sha256=sha(e.spec_raw), cash_run_sha256=e.cash_run.sha256,
                      inventory_declared_complete=True, classification_basis_ref='SYNTHETIC-no-overlap-supplied-expense-items',
                      assumptions=copy.deepcopy(ASSUMPTIONS), items=[])
        for name, kind, pointer, expense, op, cp, pay in [
            ('insurance', 'insurance', '/expense_rows/0', 10, 0 if i == 0 else 5, 5 if i == 0 else 0, 5 if i == 0 else 15),
            ('other', 'other_operating_expense', '/expense_rows/1', 5, 0, 0, 5),
            ('tax', 'property_tax', '/property_tax', 0, 0, 0, 0),
        ]:
            identity = str(i)+'-'+name
            detail['items'].append(dict(item_id='SYNTHETIC-'+name, kind=kind, noi_pointer=pointer,
                expense_amount=q(expense), currency='USD', period_ref=c['period_ref'],
                opening_payables=q(op), closing_payables=q(cp), opening_prepaid=q(0), closing_prepaid=q(0),
                source_ref='SYNTHETIC-expense-detail-'+identity, settlement_basis_ref='SYNTHETIC-supplied-accrual-payment-and-balances-'+identity,
                payments_inventory_declared_complete=True,
                payments=[] if name == 'tax' else [dict(payment_id='SYNTHETIC-payment-'+identity,
                    date=c['cash_date'], amount=q(pay), source_ref='SYNTHETIC-payment-line-'+identity)]))
        dr = raw(detail)
        run = reconcile_expense_cash_detail(e.noi_raw, e.noi_run, e.spec_raw, e.cash_run, dr)
        assert run.payload['state'] == 'matched_synthetic_expense_cash_detail', run.payload['blockers']
        p['periods'].append(dict(period_ref=c['period_ref'], detail_source_utf8=dr.decode(), detail_run=asdict(run)))
    return p


def refresh_detail(lifecycle_raw, manifest, index, mutate):
    """Create a new explicitly changed source/result, never edit a saved source."""
    p = copy.deepcopy(manifest)
    e = recover_staged_lifecycle_bundle(lifecycle_raw).window_args[3][0][index]
    detail = json.loads(p['periods'][index]['detail_source_utf8'])
    mutate(detail)
    dr = raw(detail)
    run = reconcile_expense_cash_detail(e.noi_raw, e.noi_run, e.spec_raw, e.cash_run, dr)
    p['periods'][index].update(detail_source_utf8=dr.decode(), detail_run=asdict(run))
    return p


def make_registry(bundle):
    recovered = recover_expense_checked_bundle(bundle)
    requirements = required_expense_lifecycle_sources(recovered, bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1', context=recovered.run.payload['context'],
                inventory_declared_complete=True, inventory_basis_ref='SYNTHETIC-all-underlying-and-expense-sources', requirements=requirements,
                evidence=[dict(evidence_id='SYNTHETIC-expense-evidence-'+str(i), **r, issued_at='2027-01-01T00:00:00Z',
                               valid_from='2027-01-01T00:00:00Z', valid_until='2027-07-02T00:00:00Z', review_status='accepted_synthetic',
                               value_status='declared_synthetic', superseded_by_sha256=None,
                               basis_ref='SYNTHETIC-supplied-test-validity-not-authentic-review') for i, r in enumerate(requirements)])
