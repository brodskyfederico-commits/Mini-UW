"""T80 exact monthly rental income tied to expense-checked staged cash returns."""
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError, canonical, digest, nonempty, ContextSeed
from .debt_service import _fraction
from .expense_cash_detail import _json, _exact
from .expense_checked_lifecycle import recover_expense_checked_bundle, _utf8, versions as expense_versions
from .staged_lifecycle_bundle import recover_staged_lifecycle_bundle
from .holding_cash import parse_holding_cash
from .operating_noi import parse_operating_noi
from .rental_calendar import produce_rental_calendar, group_inventory_equal, ENGINE_SHA256 as RENTAL_ENGINE_SHA256, DEFINITION
from .rental_operations import ENGINE_SHA256 as RESIDENTIAL_ENGINE_SHA256
from .investor_returns import InvestorReturnsRun
from .evidence_currency import _sha

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MAX_BYTES = 32 * 1024 * 1024


def parse_rental_lifecycle_manifest(raw):
    p = _json(raw, 8 * 1024 * 1024)
    _exact(p, {'schema', 'expense_bundle_sha256', 'context', 'currency', 'inventory_declared_complete',
               'rental_scope_and_no_overlap_basis_ref', 'period_recognition_basis_ref', 'periods'})
    if p['schema'] != 'miniuw.synthetic-rental-lifecycle-manifest.v1':
        raise ValidationError('exact rental lifecycle manifest required')
    _sha(p['expense_bundle_sha256'])
    if type(p['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact context required') from error
    nonempty(p['currency'], 'currency')
    if p['inventory_declared_complete'] is not None and type(p['inventory_declared_complete']) is not bool:
        raise ValidationError('explicit completeness declaration required')
    for k in ('rental_scope_and_no_overlap_basis_ref', 'period_recognition_basis_ref'):
        if p[k] is not None:
            nonempty(p[k], k)
    if type(p['periods']) is not list or len(p['periods']) > 64:
        raise ValidationError('bounded period inventory required')
    seen = set()
    for row in p['periods']:
        _exact(row, {'period_ref', 'calendar_source_utf8', 'calendar_run', 'noi_source_sha256', 'cash_source_sha256',
                     'rental_income_item_id', 'other_zero_income_item_ids'})
        for k in ('period_ref', 'rental_income_item_id'):
            nonempty(row[k], k)
        if row['period_ref'] in seen:
            raise ValidationError('duplicate rental period identity')
        seen.add(row['period_ref'])
        for k in ('noi_source_sha256', 'cash_source_sha256'):
            _sha(row[k])
        _utf8(row['calendar_source_utf8'], 8 * 1024 * 1024)
        _exact(row['calendar_run'], {'payload_json', 'sha256'})
        if type(row['calendar_run']['payload_json']) is not str:
            raise ValidationError('exact calendar result JSON text required')
        _sha(row['calendar_run']['sha256'])
        ids = row['other_zero_income_item_ids']
        if type(ids) is not list or len(ids) > 64:
            raise ValidationError('bounded nonresidential zero-income inventory required')
        for key in ids:
            nonempty(key, 'other income item ID')
        if len(ids) != len(set(ids)):
            raise ValidationError('duplicate other-income identity')
    return p


@dataclass(frozen=True)
class RentalCheckedLifecycleRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def compiled_raw(self):
        v = self.payload['compiled_investor_json']
        return None if v is None else v.encode('utf-8')

    @property
    def investor_run(self):
        v = self.payload['investor_run']
        return None if v is None else InvestorReturnsRun(**v)


def assemble_rental_checked_lifecycle(expense_bundle_raw, manifest_raw):
    recovered = recover_expense_checked_bundle(expense_bundle_raw)
    lifecycle = recover_staged_lifecycle_bundle(recovered.lifecycle_raw)
    p, base = parse_rental_lifecycle_manifest(manifest_raw), recovered.run.payload
    ordered = [e['period_ref'] for e in parse_holding_cash(lifecycle.window_args[3][2])['periods']]
    periods = {e.cash_run.payload['period_ref']:e for e in lifecycle.window_args[3][0]}
    blockers, rows, inventory, income_identity = [], [], None, None
    if p['expense_bundle_sha256'] != recovered.bundle_sha256:
        blockers.append('expense_bundle_identity_mismatch')
    if p['context'] != base['context'] or p['currency'] != base['currency']:
        blockers.append('rental_lifecycle_context_or_currency_mismatch')
    if p['inventory_declared_complete'] is not True:
        blockers.append('rental_period_inventory_not_declared_complete')
    for k in ('rental_scope_and_no_overlap_basis_ref', 'period_recognition_basis_ref'):
        if p[k] is None:
            blockers.append(k + '_missing')
    if [e['period_ref'] for e in p['periods']] != ordered:
        blockers.append('exact_ordered_rental_period_inventory_required')
    if base['state'] != 'compiled_synthetic_expense_checked_lifecycle':
        blockers.append('expense_checked_lifecycle_blocked')
    for row in p['periods']:
        period = row['period_ref']
        e = periods.get(period)
        if e is None:
            blockers.append(period + ':unknown_operating_period')
            continue
        cr = _utf8(row['calendar_source_utf8'], 8 * 1024 * 1024)
        run = produce_rental_calendar(cr)
        if asdict(run) != row['calendar_run']:
            raise ValidationError('rental calendar proof must reproduce exactly')
        r, n, local = run.payload, parse_operating_noi(e.noi_raw), []
        for key in ('context', 'currency', 'period_ref'):
            if r[key] != e.cash_run.payload[key]:
                local.append(key + '_mismatch')
        for key in ('start_date', 'end_date'):
            if r[key] != e.cash_run.payload[key]:
                local.append(key + '_mismatch')
        if row['noi_source_sha256'] != hashlib.sha256(e.noi_raw).hexdigest() or row['cash_source_sha256'] != hashlib.sha256(e.spec_raw).hexdigest():
            local.append('exact_NOI_or_cash_source_mismatch')
        incomes = {a['item_id']:a for a in n['income_rows']}
        target = incomes.get(row['rental_income_item_id'])
        others = set(incomes) - {row['rental_income_item_id']}
        if target is None or set(row['other_zero_income_item_ids']) != others:
            local.append('exact_residential_and_other_income_inventory_required')
        if any(_fraction(incomes[k]['value']) != 0 for k in others):
            local.append('nonresidential_income_requires_other_profile')
        if r['state'] != 'computed_synthetic_monthly_rental_calendar':
            local.append('monthly_rental_calendar_blocked')
        else:
            if target is not None and _fraction(target['value']) != _fraction(r['totals']['effective_rent'], 1300):
                local.append('rental_income_does_not_equal_exact_NOI_row')
            if inventory is None:
                inventory = r['group_inventory']
                income_identity = row['rental_income_item_id']
            elif not group_inventory_equal(inventory, r['group_inventory']) or income_identity != row['rental_income_item_id']:
                local.append('physical_group_or_rental_income_identity_changed_between_periods')
        blockers.extend(period + ':' + reason for reason in local)
        rows.append(dict(period_ref=period, calendar_source_sha256=hashlib.sha256(cr).hexdigest(), calendar_run=asdict(run),
                         rental_income_item_id=row['rental_income_item_id'], blockers=local))
    compatible = not blockers
    payload = dict(component='T80', purpose='synthetic_monthly_rental_checked_full_cash_return', engine_sha256=ENGINE_SHA256,
                   definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), expense_bundle_sha256=recovered.bundle_sha256,
                   manifest_source_sha256=hashlib.sha256(manifest_raw).hexdigest(), historical_expense_run_sha256=recovered.run.sha256,
                   context=base['context'], currency=base['currency'], periods=rows, blockers=sorted(set(blockers)),
                   expense_lifecycle_blockers=base['blockers'],
                   compiled_investor_json=base['compiled_investor_json'] if compatible else None,
                   investor_run=base['investor_run'] if compatible else None, cash_risk_run=base['cash_risk_run'] if compatible else None,
                   state='compiled_synthetic_rental_checked_lifecycle' if compatible else 'blocked',
                   rental_income_counted_as_additional_equity_receipt=False, new_funding_or_distribution_generated=False,
                   intramonth_collection_or_liquidity_verified=False, personal_investor_return=None,
                   actual_market_lease_payments_or_financial_scope_verified=False, financial_model_complete=False,
                   decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return RentalCheckedLifecycleRun(encoded, digest(encoded))


def versions():
    return dict(T79=RENTAL_ENGINE_SHA256, T80=ENGINE_SHA256, T21=RESIDENTIAL_ENGINE_SHA256,
                definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), expense=expense_versions())


def export_rental_checked_bundle(expense_raw, manifest_raw, run):
    if type(run) is not RentalCheckedLifecycleRun or assemble_rental_checked_lifecycle(expense_raw, manifest_raw) != run:
        raise ValidationError('full rental checked lifecycle must reproduce before export')
    body = dict(schema='miniuw.synthetic-rental-checked-lifecycle-bundle.v1', versions=versions(),
                expense_bundle_utf8=expense_raw.decode('utf-8'), rental_manifest_utf8=manifest_raw.decode('utf-8'), expected_run=asdict(run))
    raw = canonical(body).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValidationError('rental checked transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredRentalLifecycle:
    expense_raw: bytes
    manifest_raw: bytes
    run: RentalCheckedLifecycleRun
    bundle_sha256: str


def recover_rental_checked_bundle(raw):
    p = _json(raw, MAX_BYTES)
    _exact(p, {'schema', 'versions', 'expense_bundle_utf8', 'rental_manifest_utf8', 'expected_run'})
    if p['schema'] != 'miniuw.synthetic-rental-checked-lifecycle-bundle.v1' or p['versions'] != versions():
        raise ValidationError('incompatible rental lifecycle bundle version')
    er = _utf8(p['expense_bundle_utf8'], 24 * 1024 * 1024)
    mr = _utf8(p['rental_manifest_utf8'], 8 * 1024 * 1024)
    run = assemble_rental_checked_lifecycle(er, mr)
    if asdict(run) != p['expected_run']:
        raise ValidationError('stored rental lifecycle result does not fully reproduce')
    return RecoveredRentalLifecycle(er, mr, run, hashlib.sha256(raw).hexdigest())
