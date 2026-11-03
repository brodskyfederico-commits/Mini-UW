"""T79 sum fully supplied one-month residential sources; no lease-up assumptions."""
from dataclasses import asdict, dataclass
from datetime import date
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .drafts import ContextSeed, ValidationError, canonical, digest, nonempty
from .debt_service import _date, _fraction, rational
from .expense_cash_detail import _json, _exact
from .expense_checked_lifecycle import _utf8
from .rental_operations import parse_rental_operations, produce_rental_operations
from .operating_noi import _bounded, ArithmeticBudgetError

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T79-T81.md'
SCHEMA = 'miniuw.synthetic-monthly-rental-calendar.v1'


def next_month(day):
    if day.year == 9999 and day.month == 12:
        raise ValidationError('calendar endpoint outside supported date domain')
    return date(day.year + (day.month == 12), 1 if day.month == 12 else day.month + 1, 1)


def parse_rental_calendar(raw):
    p = _json(raw, 8 * 1024 * 1024)
    _exact(p, {'schema', 'context', 'currency', 'period_ref', 'start_date', 'end_date',
               'inventory_declared_complete', 'calendar_basis_ref', 'group_inventory_basis_ref', 'months'})
    if p['schema'] != SCHEMA:
        raise ValidationError('exact monthly rental calendar profile required')
    if type(p['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact synthetic context required') from error
    for k in ('currency', 'period_ref'):
        nonempty(p[k], k)
    for k in ('calendar_basis_ref', 'group_inventory_basis_ref'):
        if p[k] is not None:
            nonempty(p[k], k)
    if p['inventory_declared_complete'] is not None and type(p['inventory_declared_complete']) is not bool:
        raise ValidationError('explicit complete-inventory declaration required')
    if _date(p['start_date']) >= _date(p['end_date']):
        raise ValidationError('increasing calendar window required')
    if type(p['months']) is not list or len(p['months']) > 120:
        raise ValidationError('bounded supplied month inventory required')
    ids = set()
    for row in p['months']:
        _exact(row, {'period_ref', 'start_date', 'end_date', 'rental_source_utf8'})
        nonempty(row['period_ref'], 'period_ref')
        if row['period_ref'] in ids:
            raise ValidationError('duplicate month period identity')
        ids.add(row['period_ref'])
        _date(row['start_date'])
        _date(row['end_date'])
        parse_rental_operations(_utf8(row['rental_source_utf8'], 1_048_576))
    return p


@dataclass(frozen=True)
class RentalCalendarRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def rental_group_inventory(source):
    return {row['group_id']: dict(units=row['units'], unit_rentable_sf=row['unit_rentable_sf'], rent_basis=row['rent_basis'])
            for row in source['residential_groups']}


def group_inventory_equal(a, b):
    return set(a) == set(b) and all(
        a[k]['rent_basis'] == b[k]['rent_basis']
        and _fraction(a[k]['units']) == _fraction(b[k]['units'])
        and _fraction(a[k]['unit_rentable_sf']) == _fraction(b[k]['unit_rentable_sf']) for k in a)


def produce_rental_calendar(raw):
    p = parse_rental_calendar(raw)
    blockers, rows, previous, inventory = [], [], p['start_date'], None
    if p['inventory_declared_complete'] is not True or not p['months']:
        blockers.append('month_inventory_missing_or_not_declared_complete')
    for key in ('calendar_basis_ref', 'group_inventory_basis_ref'):
        if p[key] is None:
            blockers.append(key + '_missing')
    totals = {k: Fraction(0) for k in ('gross_potential_rent', 'vacancy_loss', 'concession_loss', 'effective_rent')}
    try:
        for row in p['months']:
            source_raw = _utf8(row['rental_source_utf8'], 1_048_576)
            source = parse_rental_operations(source_raw)
            run = produce_rental_operations(source_raw)
            r, local = run.payload, []
            start, end = _date(row['start_date']), _date(row['end_date'])
            if start.day != 1 or end != next_month(start):
                local.append('exact_first_day_complete_calendar_month_required')
            if row['start_date'] != previous:
                local.append('month_gap_overlap_or_order_mismatch')
            previous = row['end_date']
            if any(source[k] != p[k] for k in ('context', 'currency')) or source['period_ref'] != row['period_ref']:
                local.append('month_context_currency_or_period_mismatch')
            if source['months_in_period'] != 1 or source['months_per_year'] != 12:
                local.append('exact_one_regular_month_source_required')
            if r['state'] != 'computed_synthetic':
                local.append('monthly_residential_producer_blocked')
            if not r['expenses'] or any(e['amount'] is None or _fraction(e['amount'], 1300) != 0 for e in r['expenses']):
                local.append('monthly_expenses_must_be_explicit_zero_placeholders_in_income_only_profile')
            current = rental_group_inventory(source)
            if inventory is None:
                inventory = current
            elif not group_inventory_equal(inventory, current):
                local.append('physical_group_inventory_changed_no_implicit_availability_profile')
            values = None
            if not local:
                values = {k: Fraction(0) for k in totals}
                values['gross_potential_rent'] = _fraction(r['gross_potential_total'], 1300)
                values['effective_rent'] = _fraction(r['residential_effective_rent'], 1300)
                for g in r['groups']:
                    for k in ('vacancy_loss', 'concession_loss'):
                        values[k] = _bounded(values[k] + _fraction(g['results'][k], 1300))
                for k in totals:
                    totals[k] = _bounded(totals[k] + values[k])
            blockers.extend(row['period_ref'] + ':' + b for b in local)
            rows.append(dict(period_ref=row['period_ref'], start_date=row['start_date'], end_date=row['end_date'],
                             rental_source_sha256=hashlib.sha256(source_raw).hexdigest(), rental_run=asdict(run),
                             amounts=None if values is None else {k:rational(v) for k, v in values.items()},
                             blockers=local, monthly_blockers=r['blockers']))
    except ArithmeticBudgetError:
        blockers.append('exact_monthly_aggregation_budget_exceeded')
    if previous != p['end_date']:
        blockers.append('month_inventory_does_not_reach_declared_end')
    payload = dict(component='T79', purpose='synthetic_supplied_monthly_residential_rental_income', engine_sha256=ENGINE_SHA256,
                   definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), source_sha256=hashlib.sha256(raw).hexdigest(),
                   context=p['context'], currency=p['currency'], period_ref=p['period_ref'], start_date=p['start_date'], end_date=p['end_date'],
                   months=rows, group_inventory=inventory, totals=None if blockers else {k:rational(v) for k, v in totals.items()},
                   blockers=sorted(set(blockers)), state='computed_synthetic_monthly_rental_calendar' if not blockers else 'blocked',
                   loss_fraction_certifies_physical_occupancy=False, missing_month_or_market_assumption_generated=False,
                   monthly_expense_included_in_income=False, actual_rent_lease_or_collection_verified=False,
                   decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return RentalCalendarRun(encoded, digest(encoded))
