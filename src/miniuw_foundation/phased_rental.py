"""T82 supplied availability and month-fraction segments; no delivery/day-count rule."""
from dataclasses import dataclass, asdict
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
from .rental_calendar import next_month
from .operating_noi import _bounded, ArithmeticBudgetError

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T82-T84.md'
SCHEMA = 'miniuw.synthetic-phased-rental.v1'


def parse_phased_rental(raw):
    p = _json(raw, 8 * 1024 * 1024)
    _exact(p, {'schema', 'context', 'currency', 'period_ref', 'start_date', 'end_date',
               'inventory_declared_complete', 'capacity_basis_ref', 'calendar_basis_ref', 'capacity', 'segments'})
    if p['schema'] != SCHEMA:
        raise ValidationError('exact supplied phased rental profile required')
    if type(p['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact context required') from error
    for key in ('currency', 'period_ref'):
        nonempty(p[key], key)
    for key in ('capacity_basis_ref', 'calendar_basis_ref'):
        if p[key] is not None:
            nonempty(p[key], key)
    if p['inventory_declared_complete'] is not None and type(p['inventory_declared_complete']) is not bool:
        raise ValidationError('explicit completeness declaration required')
    if _date(p['start_date']) >= _date(p['end_date']):
        raise ValidationError('increasing phased rental period required')
    if type(p['capacity']) is not list or len(p['capacity']) > 64:
        raise ValidationError('bounded physical capacity inventory required')
    seen = set()
    for row in p['capacity']:
        _exact(row, {'group_id', 'total_units', 'unit_rentable_sf', 'rent_basis', 'source_ref'})
        nonempty(row['group_id'], 'group_id')
        if row['group_id'] in seen:
            raise ValidationError('duplicate capacity group')
        seen.add(row['group_id'])
        for key in ('total_units', 'unit_rentable_sf'):
            _fraction(row[key])
        for key in ('rent_basis', 'source_ref'):
            if row[key] is not None:
                nonempty(row[key], key)
    if type(p['segments']) is not list or len(p['segments']) > 240:
        raise ValidationError('bounded explicit segment inventory required')
    seen = set()
    for row in p['segments']:
        _exact(row, {'segment_id', 'start_date', 'end_date', 'month_anchor', 'proration_fraction',
                     'proration_basis_ref', 'availability_source_ref', 'rental_source_utf8'})
        nonempty(row['segment_id'], 'segment_id')
        if row['segment_id'] in seen:
            raise ValidationError('duplicate phased rental segment')
        seen.add(row['segment_id'])
        for key in ('start_date', 'end_date', 'month_anchor'):
            _date(row[key])
        _fraction(row['proration_fraction'])
        for key in ('proration_basis_ref', 'availability_source_ref'):
            if row[key] is not None:
                nonempty(row[key], key)
        parse_rental_operations(_utf8(row['rental_source_utf8'], 1_048_576))
    return p


def capacity_equal(a, b):
    if {r['group_id'] for r in a} != {r['group_id'] for r in b}:
        return False
    aa, bb = ({r['group_id']:r for r in rows} for rows in (a, b))
    return all(aa[k]['rent_basis'] == bb[k]['rent_basis'] and
               _fraction(aa[k]['total_units']) == _fraction(bb[k]['total_units']) and
               _fraction(aa[k]['unit_rentable_sf']) == _fraction(bb[k]['unit_rentable_sf']) for k in aa)


@dataclass(frozen=True)
class PhasedRentalRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def produce_phased_rental(raw):
    p = parse_phased_rental(raw)
    blockers, rows, month_rows, previous = [], [], {}, p['start_date']
    capacity = {r['group_id']:r for r in p['capacity']}
    if not p['capacity']:
        blockers.append('physical_capacity_empty_not_assumed_zero')
    if not p['segments'] or p['inventory_declared_complete'] is not True:
        blockers.append('segments_missing_or_not_declared_complete')
    for key in ('capacity_basis_ref', 'calendar_basis_ref'):
        if p[key] is None:
            blockers.append(key + '_missing')
    for key, cap in capacity.items():
        units, area = _fraction(cap['total_units']), _fraction(cap['unit_rentable_sf'])
        if units is None or units < 0 or units.denominator != 1:
            blockers.append(key + ':capacity_units_missing_or_invalid')
        if cap['rent_basis'] not in ('per_unit_per_month', 'per_rentable_sf_per_month') or cap['source_ref'] is None:
            blockers.append(key + ':capacity_basis_or_source_missing')
        if (area is not None and area < 0) or (cap['rent_basis'] == 'per_rentable_sf_per_month' and area is None):
            blockers.append(key + ':capacity_area_missing_or_invalid')
    totals = {k:Fraction(0) for k in ('gross_potential_rent', 'vacancy_loss', 'concession_loss', 'effective_rent', 'available_unit_months')}
    try:
        for row in p['segments']:
            rr = _utf8(row['rental_source_utf8'], 1_048_576)
            source, run = parse_rental_operations(rr), produce_rental_operations(rr)
            r, local, weight = run.payload, [], _fraction(row['proration_fraction'])
            start, end, anchor = (_date(row[k]) for k in ('start_date', 'end_date', 'month_anchor'))
            if anchor.day != 1 or not anchor <= start < end <= next_month(anchor):
                local.append('segment_must_stay_inside_explicit_reference_month')
            if row['start_date'] != previous:
                local.append('segment_gap_overlap_or_order_mismatch')
            previous = row['end_date']
            if weight is None or not 0 <= weight <= 1:
                local.append('month_fraction_missing_or_outside_unit_interval')
            for key in ('proration_basis_ref', 'availability_source_ref'):
                if row[key] is None:
                    local.append(key + '_missing')
            if source['context'] != p['context'] or source['currency'] != p['currency'] or source['period_ref'] != row['segment_id']:
                local.append('reference_source_context_currency_or_segment_mismatch')
            if source['months_in_period'] != 1 or source['months_per_year'] != 12:
                local.append('exact_one_regular_reference_month_required')
            if r['state'] != 'computed_synthetic':
                local.append('reference_rental_producer_blocked')
            if not r['expenses'] or any(e['amount'] is None or _fraction(e['amount'],1300) != 0 for e in r['expenses']):
                local.append('income_only_reference_requires_explicit_zero_expenses')
            groups = {g['group_id']:g for g in source['residential_groups']}
            if set(groups) != set(capacity):
                local.append('exact_physical_group_inventory_required_in_every_segment')
            for key, g in groups.items():
                cap = capacity.get(key)
                if cap is None:
                    continue
                available, limit = _fraction(g['units']), _fraction(cap['total_units'])
                if available is None or limit is None or available < 0 or available.denominator != 1 or available > limit:
                    local.append(key + ':available_units_missing_invalid_or_above_capacity')
                if g['rent_basis'] != cap['rent_basis'] or _fraction(g['unit_rentable_sf']) != _fraction(cap['unit_rentable_sf']):
                    local.append(key + ':reference_area_or_rent_basis_differs_from_capacity')
            month = month_rows.setdefault(row['month_anchor'], dict(start=row['start_date'], end=row['end_date'], fraction=Fraction(0), complete=True))
            month['end'] = row['end_date']
            if weight is None or not 0 <= weight <= 1:
                month['complete'] = False
            else:
                month['fraction'] = _bounded(month['fraction'] + weight)
            values = None
            if not local:
                values = {k:Fraction(0) for k in totals}
                values['gross_potential_rent'] = _bounded(_fraction(r['gross_potential_total'],1300) * weight)
                values['effective_rent'] = _bounded(_fraction(r['residential_effective_rent'],1300) * weight)
                values['available_unit_months'] = _bounded(_fraction(r['unit_total'],1300) * weight)
                for g in r['groups']:
                    for key in ('vacancy_loss', 'concession_loss'):
                        values[key] = _bounded(values[key] + _bounded(_fraction(g['results'][key],1300) * weight))
                for key in totals:
                    totals[key] = _bounded(totals[key] + values[key])
            blockers.extend(row['segment_id'] + ':' + b for b in local)
            rows.append(dict(segment_id=row['segment_id'], start_date=row['start_date'], end_date=row['end_date'], month_anchor=row['month_anchor'],
                             proration_fraction=row['proration_fraction'], availability_source_ref=row['availability_source_ref'],
                             reference_source_sha256=hashlib.sha256(rr).hexdigest(), reference_rental_run=asdict(run),
                             amounts=None if values is None else {k:rational(v) for k,v in values.items()},
                             blockers=local, reference_blockers=r['blockers']))
        for anchor, month in month_rows.items():
            full = month['start'] == anchor and month['end'] == next_month(_date(anchor)).isoformat()
            if not month['complete'] or month['fraction'] > 1 or (full and month['fraction'] != 1):
                blockers.append(anchor + ':month_fraction_inventory_incompatible_with_declared_profile')
    except ArithmeticBudgetError:
        blockers.append('exact_phased_rental_arithmetic_budget_exceeded')
    if previous != p['end_date']:
        blockers.append('segments_do_not_reach_declared_end')
    payload = dict(component='T82', purpose='synthetic_supplied_availability_and_month_fractions', engine_sha256=ENGINE_SHA256,
                   definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), source_sha256=hashlib.sha256(raw).hexdigest(),
                   context=p['context'], currency=p['currency'], period_ref=p['period_ref'], start_date=p['start_date'], end_date=p['end_date'],
                   capacity=p['capacity'], segments=rows, month_fraction_checks=[dict(month_anchor=k, fraction=rational(v['fraction']), all_fractions_known=v['complete']) for k,v in month_rows.items()],
                   totals=None if blockers else {k:rational(v) for k,v in totals.items()}, blockers=sorted(set(blockers)),
                   state='computed_synthetic_phased_rental' if not blockers else 'blocked',
                   day_count_or_delivery_rule_generated=False, actual_capacity_availability_or_occupancy_verified=False,
                   proration_contract_authenticated=False, actual_collection_or_intraperiod_liquidity_verified=False,
                   decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return PhasedRentalRun(encoded, digest(encoded))
