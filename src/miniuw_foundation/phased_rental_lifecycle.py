"""T83 supplied availability/month fractions linked to full staged cash returns."""
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
from .phased_rental import produce_phased_rental, capacity_equal, ENGINE_SHA256 as PHASED_ENGINE_SHA256, DEFINITION
from .rental_calendar import ENGINE_SHA256 as MONTH_UTILITIES_ENGINE_SHA256
from .rental_checked_lifecycle import parse_rental_lifecycle_manifest, ENGINE_SHA256 as TRANSPORT_ENGINE_SHA256
from .rental_operations import ENGINE_SHA256 as RESIDENTIAL_ENGINE_SHA256
from .investor_returns import InvestorReturnsRun
from .evidence_currency import _sha

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MAX_BYTES = 32 * 1024 * 1024


def parse_phased_lifecycle_manifest(raw):
    p = _json(raw, 8 * 1024 * 1024)
    if type(p) is not dict or p.get('schema') != 'miniuw.synthetic-phased-rental-lifecycle-manifest.v1':
        raise ValidationError('exact phased rental lifecycle manifest required')
    # Reuse only the pinned common transport shape, not T79/T80 rental semantics.
    try:
        shape_raw = canonical(dict(p, schema='miniuw.synthetic-rental-lifecycle-manifest.v1')).encode('utf-8')
    except UnicodeError as error:
        raise ValidationError('invalid nested phased rental UTF-8') from error
    parse_rental_lifecycle_manifest(shape_raw)
    return p


@dataclass(frozen=True)
class PhasedRentalLifecycleRun:
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


def assemble_phased_rental_lifecycle(expense_bundle_raw, manifest_raw):
    recovered = recover_expense_checked_bundle(expense_bundle_raw)
    lifecycle = recover_staged_lifecycle_bundle(recovered.lifecycle_raw)
    p, base = parse_phased_lifecycle_manifest(manifest_raw), recovered.run.payload
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
        run = produce_phased_rental(cr)
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
        if r['state'] != 'computed_synthetic_phased_rental':
            local.append('phased_rental_calendar_blocked')
        else:
            if target is not None and _fraction(target['value']) != _fraction(r['totals']['effective_rent'], 1300):
                local.append('rental_income_does_not_equal_exact_NOI_row')
            if inventory is None:
                inventory = r['capacity']
                income_identity = row['rental_income_item_id']
            elif not capacity_equal(inventory, r['capacity']) or income_identity != row['rental_income_item_id']:
                local.append('physical_capacity_or_rental_income_identity_changed_between_periods')
        blockers.extend(period + ':' + reason for reason in local)
        rows.append(dict(period_ref=period, calendar_source_sha256=hashlib.sha256(cr).hexdigest(), calendar_run=asdict(run),
                         rental_income_item_id=row['rental_income_item_id'], blockers=local))
    compatible = not blockers
    payload = dict(component='T83', purpose='synthetic_phased_rental_checked_full_cash_return', engine_sha256=ENGINE_SHA256,
                   definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), expense_bundle_sha256=recovered.bundle_sha256,
                   manifest_source_sha256=hashlib.sha256(manifest_raw).hexdigest(), historical_expense_run_sha256=recovered.run.sha256,
                   context=base['context'], currency=base['currency'], periods=rows, blockers=sorted(set(blockers)),
                   expense_lifecycle_blockers=base['blockers'],
                   compiled_investor_json=base['compiled_investor_json'] if compatible else None,
                   investor_run=base['investor_run'] if compatible else None, cash_risk_run=base['cash_risk_run'] if compatible else None,
                   state='compiled_synthetic_phased_rental_lifecycle' if compatible else 'blocked',
                   rental_income_counted_as_additional_equity_receipt=False, new_funding_or_distribution_generated=False,
                   day_count_delivery_or_collection_authenticated=False, intramonth_collection_or_liquidity_verified=False, personal_investor_return=None,
                   actual_market_lease_payments_or_financial_scope_verified=False, financial_model_complete=False,
                   decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return PhasedRentalLifecycleRun(encoded, digest(encoded))


def versions():
    return dict(T82=PHASED_ENGINE_SHA256, T83=ENGINE_SHA256, T21=RESIDENTIAL_ENGINE_SHA256,
                month_utilities=MONTH_UTILITIES_ENGINE_SHA256, transport_utilities=TRANSPORT_ENGINE_SHA256,
                definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), expense=expense_versions())


def export_phased_rental_bundle(expense_raw, manifest_raw, run):
    if type(run) is not PhasedRentalLifecycleRun or assemble_phased_rental_lifecycle(expense_raw, manifest_raw) != run:
        raise ValidationError('full rental checked lifecycle must reproduce before export')
    body = dict(schema='miniuw.synthetic-phased-rental-lifecycle-bundle.v1', versions=versions(),
                expense_bundle_utf8=expense_raw.decode('utf-8'), rental_manifest_utf8=manifest_raw.decode('utf-8'), expected_run=asdict(run))
    raw = canonical(body).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValidationError('rental checked transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredPhasedRentalLifecycle:
    expense_raw: bytes
    manifest_raw: bytes
    run: PhasedRentalLifecycleRun
    bundle_sha256: str


def recover_phased_rental_bundle(raw):
    p = _json(raw, MAX_BYTES)
    _exact(p, {'schema', 'versions', 'expense_bundle_utf8', 'rental_manifest_utf8', 'expected_run'})
    if p['schema'] != 'miniuw.synthetic-phased-rental-lifecycle-bundle.v1' or p['versions'] != versions():
        raise ValidationError('incompatible rental lifecycle bundle version')
    er = _utf8(p['expense_bundle_utf8'], 24 * 1024 * 1024)
    mr = _utf8(p['rental_manifest_utf8'], 8 * 1024 * 1024)
    run = assemble_phased_rental_lifecycle(er, mr)
    if asdict(run) != p['expected_run']:
        raise ValidationError('stored rental lifecycle result does not fully reproduce')
    return RecoveredPhasedRentalLifecycle(er, mr, run, hashlib.sha256(raw).hexdigest())
