"""Explicit synthetic capacity/availability/proration declarations, never delivery rules."""
from dataclasses import asdict
from pathlib import Path
from fractions import Fraction
import copy
import hashlib
import json

from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.phased_rental import produce_phased_rental, SCHEMA
from miniuw_foundation.phased_rental_lifecycle import recover_phased_rental_bundle
from miniuw_foundation.current_phased_rental import required_phased_rental_sources
from miniuw_foundation.expense_checked_lifecycle import assemble_expense_checked_lifecycle, export_expense_checked_bundle, recover_expense_checked_bundle
from miniuw_foundation.staged_lifecycle_bundle import export_staged_lifecycle_bundle, recover_staged_lifecycle_bundle
from expense_lifecycle_demo_support import make_manifest as expense_manifest
from staged_phase_demo_support import make_case

ROOT = Path(__file__).resolve().parents[1]
AT = '2027-07-01T12:00:00Z'
raw = lambda p: canonical(p).encode('utf-8')
q = lambda n: rational(Fraction(n))
sha = lambda b: hashlib.sha256(b).hexdigest()


def make_expense_base():
    def change(d):
        for i, n in enumerate(d['nois']):
            row = n['expense_rows'][0]
            n['expense_rows'] = [dict(row, item_id='SYNTHETIC-insurance', value=q(10), source_ref='SYNTHETIC-insurance-accrual-'+str(i)),
                                 dict(row, item_id='SYNTHETIC-other-opex', value=q(5), source_ref='SYNTHETIC-other-accrual-'+str(i))]
            n['income_rows'][0]['value'] = q(28 if i == 0 else 60)
            c = d['ops'][i]
            c['working_balances']['payables']['opening']['value'] = q(0 if i == 0 else 5)
            c['working_balances']['payables']['closing']['value'] = q(5 if i == 0 else 0)
            for key, value in dict(operating_receipts_claim=28 if i == 0 else 60, operating_payments_claim=10 if i == 0 else 20,
                                   opening_free_cash=590 if i == 0 else 398, closing_free_cash_claim=398 if i == 0 else 208).items():
                c['amounts'][key]['value'] = q(value)
        d['sale']['amounts']['opening_free_cash']['value'] = q(208)
    case = make_case(holding_change=change)
    assert case[-1].investor_run is not None, case[-1].payload['blockers']
    lr = export_staged_lifecycle_bundle(*case)
    mr = raw(expense_manifest(lr))
    run = assemble_expense_checked_lifecycle(lr, mr)
    assert run.investor_run is not None, run.payload['blockers']
    return export_expense_checked_bundle(lr, mr, run)


def make_manifest(expense_raw):
    expense = recover_expense_checked_bundle(expense_raw)
    lifecycle = recover_staged_lifecycle_bundle(expense.lifecycle_raw)
    template = json.loads((ROOT/'templates/synthetic-residential-operations.json').read_bytes())
    manifest = dict(schema='miniuw.synthetic-phased-rental-lifecycle-manifest.v1', expense_bundle_sha256=sha(expense_raw),
                    context=expense.run.payload['context'], currency='USD', inventory_declared_complete=True,
                    rental_scope_and_no_overlap_basis_ref='SYNTHETIC-residential-only-other-income-zero-explicit',
                    period_recognition_basis_ref='SYNTHETIC-declared-segment-rent-in-operating-period-not-verified-cash-timing', periods=[])
    for i, e in enumerate(lifecycle.window_args[3][0]):
        c, n = json.loads(e.spec_raw), json.loads(e.noi_raw)
        calendar = dict(schema=SCHEMA, context=manifest['context'], currency='USD', period_ref=c['period_ref'],
                        start_date=c['start_date'], end_date=c['end_date'], inventory_declared_complete=True,
                        capacity_basis_ref='SYNTHETIC-supplied-fixed-capacity-not-delivery-approval',
                        calendar_basis_ref='SYNTHETIC-contiguous-segments-with-supplied-month-fractions',
                        capacity=[dict(group_id=template['residential_groups'][0]['group_id'], total_units=q(10),
                                       unit_rentable_sf=None, rent_basis='per_unit_per_month', source_ref='SYNTHETIC-capacity-claim')], segments=[])
        frames = [('2027-01-01','2027-01-16',0,Fraction(1,2),0,0), ('2027-01-16','2027-02-01',5,Fraction(1,2),0,0),
                  ('2027-02-01','2027-03-01',5,1,Fraction(1,5),0), ('2027-03-01','2027-04-01',10,1,0,Fraction(1,4))] if i == 0 else [
                  ('2027-04-01','2027-05-01',10,1,0,0), ('2027-05-01','2027-06-01',10,1,0,0), ('2027-06-01','2027-07-01',10,1,0,0)]
        for j, (start,end,available,weight,loss,concession) in enumerate(frames):
            sid = 'SYNTHETIC-phased-'+str(i)+'-'+str(j)
            source = copy.deepcopy(template)
            source.update(context=manifest['context'], period_ref=sid, months_in_period=1, months_per_year=12)
            source['residential_groups'][0].update(units=q(available), rent=q(2), loss_fraction=q(loss), concession_fraction=q(concession),
                concession_basis='after_vacancy_rent', source_ref='SYNTHETIC-reference-rent-'+sid, policy_ref='SYNTHETIC-explicit-loss-and-concession-'+sid)
            source['expense_items'] = [dict(item_id='SYNTHETIC-income-only-zero', kind='fixed_per_declared_period', rate=q(0), currency='USD',
                                           source_ref='SYNTHETIC-explicit-zero-placeholder-not-period-opex', policy_ref='SYNTHETIC-income-only-reference')]
            calendar['segments'].append(dict(segment_id=sid, start_date=start, end_date=end, month_anchor=start[:7]+'-01',
                proration_fraction=q(weight), proration_basis_ref='SYNTHETIC-supplied-half-or-full-month-not-inferred-from-days',
                availability_source_ref='SYNTHETIC-availability-proposal-'+sid, rental_source_utf8=raw(source).decode()))
        cr = raw(calendar)
        run = produce_phased_rental(cr)
        assert run.payload['state'] == 'computed_synthetic_phased_rental', run.payload['blockers']
        manifest['periods'].append(dict(period_ref=c['period_ref'], calendar_source_utf8=cr.decode(), calendar_run=asdict(run),
            noi_source_sha256=sha(e.noi_raw), cash_source_sha256=sha(e.spec_raw), rental_income_item_id=n['income_rows'][0]['item_id'],
            other_zero_income_item_ids=[row['item_id'] for row in n['income_rows'][1:]]))
    return manifest


def change_segment(calendar, index, mutate):
    row = calendar['segments'][index]
    source = json.loads(row['rental_source_utf8'])
    mutate(source)
    row['rental_source_utf8'] = raw(source).decode()


def refresh_calendar(manifest, index, mutate):
    p = copy.deepcopy(manifest)
    c = json.loads(p['periods'][index]['calendar_source_utf8'])
    mutate(c)
    cr = raw(c)
    p['periods'][index].update(calendar_source_utf8=cr.decode(), calendar_run=asdict(produce_phased_rental(cr)))
    return p


def make_registry(bundle):
    recovered = recover_phased_rental_bundle(bundle)
    requirements = required_phased_rental_sources(recovered, bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1', context=recovered.run.payload['context'], inventory_declared_complete=True,
                inventory_basis_ref='SYNTHETIC-all-phased-and-underlying-exact-sources', requirements=requirements,
                evidence=[dict(evidence_id='SYNTHETIC-phased-evidence-'+str(i), **r, issued_at='2027-01-01T00:00:00Z',
                               valid_from='2027-01-01T00:00:00Z', valid_until='2027-07-02T00:00:00Z', review_status='accepted_synthetic',
                               value_status='declared_synthetic', superseded_by_sha256=None,
                               basis_ref='SYNTHETIC-supplied-test-validity-not-authority') for i,r in enumerate(requirements)])
