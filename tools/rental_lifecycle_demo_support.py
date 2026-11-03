"""Supplied monthly rental toy inputs; never inferred market or absorption rules."""
from dataclasses import asdict
from pathlib import Path
import copy
import hashlib
import json
from fractions import Fraction

from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.rental_calendar import produce_rental_calendar, SCHEMA
from miniuw_foundation.rental_checked_lifecycle import recover_rental_checked_bundle
from miniuw_foundation.current_rental_lifecycle import required_rental_lifecycle_sources
from miniuw_foundation.expense_checked_lifecycle import assemble_expense_checked_lifecycle, export_expense_checked_bundle, recover_expense_checked_bundle
from miniuw_foundation.staged_lifecycle_bundle import export_staged_lifecycle_bundle, recover_staged_lifecycle_bundle
from staged_phase_demo_support import make_case
from expense_lifecycle_demo_support import make_manifest as expense_manifest

ROOT = Path(__file__).resolve().parents[1]
AT = '2027-07-01T12:00:00Z'
raw = lambda p: canonical(p).encode('utf-8')
q = lambda n: rational(Fraction(n))
sha = lambda b: hashlib.sha256(b).hexdigest()


def make_expense_bundle():
    def change(d):
        for i, n in enumerate(d['nois']):
            base = n['expense_rows'][0]
            n['expense_rows'] = [dict(base, item_id='SYNTHETIC-insurance', value=q(10), source_ref='SYNTHETIC-insurance-accrual-'+str(i)),
                                 dict(base, item_id='SYNTHETIC-other-opex', value=q(5), source_ref='SYNTHETIC-other-accrual-'+str(i))]
            n['income_rows'][0]['value'] = q(25 if i == 0 else 60)
            c = d['ops'][i]
            c['working_balances']['payables']['opening']['value'] = q(0 if i == 0 else 5)
            c['working_balances']['payables']['closing']['value'] = q(5 if i == 0 else 0)
            for key, value in dict(operating_receipts_claim=25 if i == 0 else 60, operating_payments_claim=10 if i == 0 else 20,
                                   opening_free_cash=590 if i == 0 else 395, closing_free_cash_claim=395 if i == 0 else 205).items():
                c['amounts'][key]['value'] = q(value)
        d['sale']['amounts']['opening_free_cash']['value'] = q(205)
    case = make_case(holding_change=change)
    assert case[-1].investor_run is not None, case[-1].payload['blockers']
    lr = export_staged_lifecycle_bundle(*case)
    mr = raw(expense_manifest(lr))
    run = assemble_expense_checked_lifecycle(lr, mr)
    assert run.investor_run is not None, run.payload['blockers']
    return export_expense_checked_bundle(lr, mr, run)


def make_rental_manifest(expense_raw):
    expense = recover_expense_checked_bundle(expense_raw)
    lifecycle = recover_staged_lifecycle_bundle(expense.lifecycle_raw)
    p = dict(schema='miniuw.synthetic-rental-lifecycle-manifest.v1', expense_bundle_sha256=sha(expense_raw),
             context=expense.run.payload['context'], currency='USD', inventory_declared_complete=True,
             rental_scope_and_no_overlap_basis_ref='SYNTHETIC-residential-only-other-income-explicit-zero',
             period_recognition_basis_ref='SYNTHETIC-full-month-accrual-in-quarter-not-proof-of-intramonth-cash', periods=[])
    template = json.loads((ROOT/'templates/synthetic-residential-operations.json').read_bytes())
    for i, e in enumerate(lifecycle.window_args[3][0]):
        c, n = json.loads(e.spec_raw), json.loads(e.noi_raw)
        calendar = dict(schema=SCHEMA, context=p['context'], currency='USD', period_ref=c['period_ref'],
                        start_date=c['start_date'], end_date=c['end_date'], inventory_declared_complete=True,
                        calendar_basis_ref='SYNTHETIC-explicit-full-month-rental-profile',
                        group_inventory_basis_ref='SYNTHETIC-fixed-ten-units-not-an-availability-ramp', months=[])
        for j in range(3):
            month = 1 + 3*i + j
            start, end = '2027-'+str(month).zfill(2)+'-01', '2027-'+str(month+1).zfill(2)+'-01'
            m = copy.deepcopy(template)
            m.update(context=p['context'], period_ref='SYNTHETIC-rental-'+start[:7], months_in_period=1, months_per_year=12)
            g = m['residential_groups'][0]
            g.update(units=q(10), rent=q(2), loss_fraction=q([1, Fraction(1,2), 0][j] if i == 0 else 0),
                     concession_fraction=q(Fraction(1,4) if i == 0 and j == 2 else 0), concession_basis='after_vacancy_rent',
                     source_ref='SYNTHETIC-supplied-monthly-rent-'+start, policy_ref='SYNTHETIC-vacancy-only-loss-and-explicit-concession-for-this-test')
            m['expense_items'] = [dict(item_id='SYNTHETIC-zero-income-only-placeholder', kind='fixed_per_declared_period', rate=q(0),
                                       currency='USD', source_ref='SYNTHETIC-explicit-zero-placeholder-not-period-opex', policy_ref='SYNTHETIC-income-only-calendar')]
            calendar['months'].append(dict(period_ref=m['period_ref'], start_date=start, end_date=end, rental_source_utf8=raw(m).decode()))
        cr = raw(calendar)
        run = produce_rental_calendar(cr)
        assert run.payload['state'] == 'computed_synthetic_monthly_rental_calendar', run.payload['blockers']
        p['periods'].append(dict(period_ref=c['period_ref'], calendar_source_utf8=cr.decode(), calendar_run=asdict(run),
                                noi_source_sha256=sha(e.noi_raw), cash_source_sha256=sha(e.spec_raw),
                                rental_income_item_id=n['income_rows'][0]['item_id'],
                                other_zero_income_item_ids=[a['item_id'] for a in n['income_rows'][1:]]))
    return p


def refresh_calendar(manifest, index, mutate):
    p = copy.deepcopy(manifest)
    c = json.loads(p['periods'][index]['calendar_source_utf8'])
    mutate(c)
    cr = raw(c)
    p['periods'][index].update(calendar_source_utf8=cr.decode(), calendar_run=asdict(produce_rental_calendar(cr)))
    return p


def change_month(calendar, index, mutate):
    r = calendar['months'][index]
    source = json.loads(r['rental_source_utf8'])
    mutate(source)
    r['rental_source_utf8'] = raw(source).decode()


def make_registry(bundle):
    recovered = recover_rental_checked_bundle(bundle)
    requirements = required_rental_lifecycle_sources(recovered, bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1', context=recovered.run.payload['context'], inventory_declared_complete=True,
                inventory_basis_ref='SYNTHETIC-complete-rental-and-underlying-source-inventory', requirements=requirements,
                evidence=[dict(evidence_id='SYNTHETIC-rental-evidence-'+str(i), **r, issued_at='2027-01-01T00:00:00Z',
                               valid_from='2027-01-01T00:00:00Z', valid_until='2027-07-02T00:00:00Z', review_status='accepted_synthetic',
                               value_status='declared_synthetic', superseded_by_sha256=None,
                               basis_ref='SYNTHETIC-provided-test-validity-not-authentic-review') for i, r in enumerate(requirements)])
