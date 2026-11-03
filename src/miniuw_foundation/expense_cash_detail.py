"""T76 exact per-item synthetic expense/cash reconciliation; no tax rule adoption."""
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import re

from .drafts import ContextSeed, ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant
from .debt_service import _date, _fraction, rational
from .operating_noi import OperatingNoiRun, produce_operating_noi, parse_operating_noi, _bounded, ArithmeticBudgetError
from .operating_cash import OperatingCashRun, reconcile_operating_cash, parse_operating_cash

SCHEMA = 'miniuw.synthetic-expense-cash-detail.v1'
BUNDLE_SCHEMA = 'miniuw.synthetic-expense-cash-bundle.v1'
ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T76.md'
BALANCES = ('opening_payables', 'closing_payables', 'opening_prepaid', 'closing_prepaid')
ASSUMPTIONS = {'noncash_expenses': False, 'refunds_or_offsets': False, 'interitem_transfers': False,
               'payment_dates_are': 'supplied_plan_not_verified_bank_history', 'rounding': 'none_exact'}


def _json(raw, limit=1_048_576):
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValidationError('bounded nonempty UTF-8 expense source required')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationError('invalid expense JSON') from error


def _exact(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValidationError('exact expense profile fields required')


def parse_expense_cash_detail(raw):
    p = _json(raw)
    _exact(p, {'schema', 'context', 'currency', 'period_ref', 'start_date', 'end_date',
               'noi_source_sha256', 'noi_run_sha256', 'cash_source_sha256', 'cash_run_sha256',
               'inventory_declared_complete', 'classification_basis_ref', 'assumptions', 'items'})
    if p['schema'] != SCHEMA:
        raise ValidationError('supported synthetic expense profile required')
    if type(p['context']) is not dict:
        raise ValidationError('explicit context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact context required') from error
    for key in ('currency', 'period_ref'):
        nonempty(p[key], key)
    for key in ('noi_source_sha256', 'noi_run_sha256', 'cash_source_sha256', 'cash_run_sha256'):
        if type(p[key]) is not str or not re.fullmatch('[a-f0-9]{64}', p[key]):
            raise ValidationError('exact source/run hash required')
    if _date(p['start_date']) >= _date(p['end_date']):
        raise ValidationError('increasing explicit period required')
    _exact(p['assumptions'], ASSUMPTIONS)
    if any(type(p['assumptions'][k]) is not type(v) or p['assumptions'][k] != v for k, v in ASSUMPTIONS.items()):
        raise ValidationError('unsupported expense assumptions')
    def declaration(value):
        if value is not None and type(value) is not bool:
            raise ValidationError('explicit boolean declaration or null required')
    def ref(value):
        if value is not None:
            nonempty(value, 'basis/source reference')
    declaration(p['inventory_declared_complete'])
    ref(p['classification_basis_ref'])
    if type(p['items']) is not list or len(p['items']) > 65:
        raise ValidationError('bounded item inventory required')
    identities, payment_ids = set(), set()
    for row in p['items']:
        _exact(row, {'item_id', 'kind', 'noi_pointer', 'expense_amount', 'currency', 'period_ref',
                     'source_ref', 'settlement_basis_ref', 'payments_inventory_declared_complete', 'payments', *BALANCES})
        for key in ('item_id', 'kind', 'noi_pointer'):
            nonempty(row[key], key)
        if row['item_id'] in identities:
            raise ValidationError('duplicate expense item ID')
        identities.add(row['item_id'])
        for key in ('currency', 'period_ref', 'source_ref', 'settlement_basis_ref'):
            ref(row[key])
        for key in ('expense_amount', *BALANCES):
            _fraction(row[key])
        declaration(row['payments_inventory_declared_complete'])
        if type(row['payments']) is not list or len(row['payments']) > 128:
            raise ValidationError('bounded payment inventory required')
        for payment in row['payments']:
            _exact(payment, {'payment_id', 'date', 'amount', 'source_ref'})
            nonempty(payment['payment_id'], 'payment_id')
            if payment['payment_id'] in payment_ids:
                raise ValidationError('duplicate payment identity across expense items')
            payment_ids.add(payment['payment_id'])
            _date(payment['date'])
            _fraction(payment['amount'])
            ref(payment['source_ref'])
    return p


@dataclass(frozen=True)
class ExpenseCashDetailRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def reconcile_expense_cash_detail(noi_raw, noi_run, cash_raw, cash_run, detail_raw):
    if type(noi_run) is not OperatingNoiRun or produce_operating_noi(noi_raw) != noi_run:
        raise ValidationError('exact NOI must reproduce')
    if type(cash_run) is not OperatingCashRun or reconcile_operating_cash(noi_raw, noi_run, cash_raw) != cash_run:
        raise ValidationError('exact cash plan must reproduce')
    p = parse_expense_cash_detail(detail_raw)
    n, c = noi_run.payload, cash_run.payload
    ns, cs = parse_operating_noi(noi_raw), parse_operating_cash(cash_raw)
    blockers, rows, pointers, payment_refs = [], [], set(), set()
    for key, actual in [('noi_source_sha256', hashlib.sha256(noi_raw).hexdigest()), ('noi_run_sha256', noi_run.sha256),
                        ('cash_source_sha256', hashlib.sha256(cash_raw).hexdigest()), ('cash_run_sha256', cash_run.sha256)]:
        if p[key] != actual:
            blockers.append(key + '_mismatch')
    for key in ('context', 'currency', 'period_ref'):
        if p[key] != n[key] or p[key] != c[key]:
            blockers.append(key + '_mismatch')
    for key in ('start_date', 'end_date'):
        if p[key] != c[key]:
            blockers.append(key + '_mismatch')
    if n['calculation_status'] != 'computed_synthetic_profile' or c['state'] != 'reconciled_synthetic_plan':
        blockers.append('upstream_NOI_or_cash_blocked')
    if p['inventory_declared_complete'] is not True:
        blockers.append('expense_inventory_not_declared_complete')
    if p['classification_basis_ref'] is None:
        blockers.append('classification_and_no_overlap_basis_missing')
    if _fraction(cs['amounts']['noncash_expense']['value']) != 0:
        blockers.append('noncash_expense_outside_reduced_profile')
    expected = {'/expense_rows/' + str(i): row['value'] for i, row in enumerate(ns['expense_rows'])}
    expected['/property_tax'] = n['property_tax']
    totals = {key: Fraction(0) for key in ('expense_amount', 'cash_payments', *BALANCES)}
    try:
        for row in p['items']:
            issues, vals, paid = [], {}, Fraction(0)
            pointer = row['noi_pointer']
            if pointer in pointers:
                issues.append('duplicate_NOI_target')
            pointers.add(pointer)
            if pointer not in expected:
                issues.append('unknown_NOI_target')
            if row['kind'] not in ('insurance', 'property_tax', 'other_operating_expense'):
                issues.append('expense_kind_outside_profile')
            if (row['kind'] == 'property_tax') != (pointer == '/property_tax'):
                issues.append('tax_must_bind_only_computed_property_tax')
            if row['currency'] != p['currency'] or row['period_ref'] != p['period_ref']:
                issues.append('item_currency_or_period_mismatch')
            if row['source_ref'] is None or row['settlement_basis_ref'] is None:
                issues.append('item_source_or_settlement_basis_missing')
            if row['payments_inventory_declared_complete'] is not True:
                issues.append('payment_inventory_not_declared_complete')
            for key in ('expense_amount', *BALANCES):
                vals[key] = _fraction(row[key])
                if vals[key] is None or vals[key] < 0:
                    issues.append(key + '_missing_or_negative')
            if pointer in expected and (expected[pointer] is None or vals['expense_amount'] != _fraction(expected[pointer], 1300)):
                issues.append('expense_differs_from_exact_NOI_item')
            payment_complete = True
            for payment in row['payments']:
                value = _fraction(payment['amount'])
                if value is None or value < 0:
                    issues.append('payment_amount_missing_or_negative')
                    payment_complete = False
                else:
                    paid = _bounded(paid + value)
                if not p['start_date'] <= payment['date'] < p['end_date']:
                    issues.append('payment_outside_declared_half_open_period')
                if payment['source_ref'] is None:
                    issues.append('payment_source_missing')
                elif payment['source_ref'] in payment_refs:
                    issues.append('payment_source_reused_no_split_profile')
                else:
                    payment_refs.add(payment['source_ref'])
            predicted = residual = None
            if all(v is not None and v >= 0 for v in vals.values()) and payment_complete:
                predicted = _bounded(vals['expense_amount'] + vals['opening_payables'] - vals['closing_payables']
                                     + vals['closing_prepaid'] - vals['opening_prepaid'])
                residual = _bounded(paid - predicted)
                if predicted < 0:
                    issues.append('negative_expected_payment_requires_other_profile')
                if residual != 0:
                    issues.append('item_expense_cash_identity_mismatch')
            if not issues:
                for key in vals:
                    totals[key] = _bounded(totals[key] + vals[key])
                totals['cash_payments'] = _bounded(totals['cash_payments'] + paid)
            blockers.extend(row['item_id'] + ':' + reason for reason in issues)
            rows.append({'item_id': row['item_id'], 'kind': row['kind'], 'noi_pointer': pointer,
                         'source_ref': row['source_ref'], 'declared_expense': row['expense_amount'],
                         'payments': row['payments'], 'cash_payments': rational(paid) if payment_complete else None,
                         'expected_cash_payments': None if predicted is None else rational(predicted),
                         'cash_identity_residual': None if residual is None else rational(residual),
                         'balances': {key: row[key] for key in BALANCES}, 'blockers': sorted(set(issues))})
        if pointers != set(expected):
            blockers.append('exact_all_NOI_expenses_and_tax_inventory_required')
        if not blockers:
            for key, family, cutoff in [('opening_payables', 'payables', 'opening'), ('closing_payables', 'payables', 'closing'),
                                        ('opening_prepaid', 'prepaid_expenses', 'opening'), ('closing_prepaid', 'prepaid_expenses', 'closing')]:
                if totals[key] != _fraction(cs['working_balances'][family][cutoff]['value']):
                    blockers.append(key + '_differs_from_aggregate_cash_plan')
            if totals['cash_payments'] != _fraction(c['expected_operating_payments'], 1300):
                blockers.append('item_payment_sum_differs_from_operating_cash')
    except ArithmeticBudgetError:
        blockers.append('exact_arithmetic_budget_exceeded')
    payload = {'component': 'T76', 'purpose': 'synthetic_per_item_expense_cash_reconciliation',
               'engine_sha256': ENGINE_SHA256, 'definition_sha256': hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
               'noi_source_sha256': hashlib.sha256(noi_raw).hexdigest(), 'noi_run_sha256': noi_run.sha256,
               'cash_source_sha256': hashlib.sha256(cash_raw).hexdigest(), 'cash_run_sha256': cash_run.sha256,
               'detail_source_sha256': hashlib.sha256(detail_raw).hexdigest(), 'context': p['context'],
               'currency': p['currency'], 'period_ref': p['period_ref'], 'start_date': p['start_date'], 'end_date': p['end_date'],
               'items': rows, 'totals': None if blockers else {key: rational(v) for key, v in totals.items()},
               'blockers': sorted(set(blockers)), 'upstream_cash_blockers': c['blockers'], 'upstream_NOI_blockers': n['blockers'],
               'state': 'matched_synthetic_expense_cash_detail' if not blockers else 'blocked',
               'new_expense_or_payment_generated': False, 'bank_payment_history_verified': False,
               'tax_or_insurance_policy_adopted': False, 'intraperiod_liquidity_verified': False,
               'current_source_authority_verified': False, 'decision': 'PENDING', 'real_decisions_enabled': False,
               'production_authorized': False}
    encoded = canonical(payload)
    return ExpenseCashDetailRun(encoded, digest(encoded))


def export_expense_cash_bundle(noi_raw, noi_run, cash_raw, cash_run, detail_raw, detail_run):
    if type(detail_run) is not ExpenseCashDetailRun or reconcile_expense_cash_detail(noi_raw, noi_run, cash_raw, cash_run, detail_raw) != detail_run:
        raise ValidationError('expense detail must replay before export')
    sources = {name: {'utf8': raw.decode('utf-8'), 'sha256': hashlib.sha256(raw).hexdigest()}
               for name, raw in [('noi', noi_raw), ('cash', cash_raw), ('detail', detail_raw)]}
    body = {'schema': BUNDLE_SCHEMA, 'engine_sha256': ENGINE_SHA256,
            'definition_sha256': hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), 'sources': sources, 'result': asdict(detail_run)}
    encoded = (canonical(body) + '\n').encode('utf-8')
    if len(encoded) > 4_194_304:
        raise ValidationError('expense recovery transport budget exceeded')
    return encoded


def recover_expense_cash_bundle(raw):
    p = _json(raw, 4_194_304)
    _exact(p, {'schema', 'engine_sha256', 'definition_sha256', 'sources', 'result'})
    if p['schema'] != BUNDLE_SCHEMA or p['engine_sha256'] != ENGINE_SHA256 or p['definition_sha256'] != hashlib.sha256(DEFINITION.read_bytes()).hexdigest():
        raise ValidationError('incompatible expense recovery version')
    _exact(p['sources'], {'noi', 'cash', 'detail'})
    sources = {}
    for name, entry in p['sources'].items():
        _exact(entry, {'utf8', 'sha256'})
        if type(entry['utf8']) is not str:
            raise ValidationError('exact UTF-8 source required')
        sources[name] = entry['utf8'].encode('utf-8')
        if hashlib.sha256(sources[name]).hexdigest() != entry['sha256']:
            raise ValidationError('expense recovery source hash mismatch')
    noi = produce_operating_noi(sources['noi'])
    cash = reconcile_operating_cash(sources['noi'], noi, sources['cash'])
    run = reconcile_expense_cash_detail(sources['noi'], noi, sources['cash'], cash, sources['detail'])
    if asdict(run) != p['result']:
        raise ValidationError('expense recovery full result mismatch')
    return run
