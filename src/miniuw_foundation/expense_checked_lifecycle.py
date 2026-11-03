"""T77 full synthetic staged lifecycle gated by per-item operating expense continuity."""
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError, canonical, digest, nonempty, ContextSeed
from .debt_service import _fraction
from .expense_cash_detail import (
    ExpenseCashDetailRun, reconcile_expense_cash_detail, parse_expense_cash_detail,
    _json, _exact, ENGINE_SHA256 as EXPENSE_ENGINE_SHA256, DEFINITION as EXPENSE_DEFINITION,
)
from .staged_lifecycle_bundle import recover_staged_lifecycle_bundle, versions as lifecycle_versions
from .holding_cash import parse_holding_cash
from .operating_noi import parse_operating_noi
from .investor_returns import InvestorReturnsRun

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T77-T78.md'
MAX_BUNDLE_BYTES = 24 * 1024 * 1024


def _utf8(value, limit):
    if type(value) is not str:
        raise ValidationError('exact nested UTF-8 source required')
    try:
        raw = value.encode('utf-8')
    except UnicodeError as error:
        raise ValidationError('invalid nested UTF-8 source') from error
    if not raw or len(raw) > limit:
        raise ValidationError('nested source outside transport budget')
    return raw


def parse_expense_lifecycle_manifest(raw):
    p = _json(raw, 8 * 1024 * 1024)
    _exact(p, {'schema', 'lifecycle_bundle_sha256', 'context', 'currency', 'inventory_declared_complete',
               'continuity_basis_ref', 'item_inventory_basis_ref', 'periods'})
    if p['schema'] != 'miniuw.synthetic-expense-lifecycle-manifest.v1':
        raise ValidationError('exact expense lifecycle manifest required')
    from .evidence_currency import _sha
    _sha(p['lifecycle_bundle_sha256'])
    if type(p['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact synthetic context required') from error
    nonempty(p['currency'], 'currency')
    if p['inventory_declared_complete'] is not None and type(p['inventory_declared_complete']) is not bool:
        raise ValidationError('explicit boolean completeness declaration required')
    for k in ('continuity_basis_ref', 'item_inventory_basis_ref'):
        if p[k] is not None:
            nonempty(p[k], k)
    if type(p['periods']) is not list or len(p['periods']) > 64:
        raise ValidationError('bounded period inventory required')
    ids = set()
    for row in p['periods']:
        _exact(row, {'period_ref', 'detail_source_utf8', 'detail_run'})
        nonempty(row['period_ref'], 'period_ref')
        if row['period_ref'] in ids:
            raise ValidationError('duplicate expense period identity')
        ids.add(row['period_ref'])
        parse_expense_cash_detail(_utf8(row['detail_source_utf8'], 1_048_576))
        _exact(row['detail_run'], {'payload_json', 'sha256'})
        if type(row['detail_run']['payload_json']) is not str:
            raise ValidationError('exact expense run JSON text required')
        _sha(row['detail_run']['sha256'])
    return p


@dataclass(frozen=True)
class ExpenseCheckedLifecycleRun:
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


def assemble_expense_checked_lifecycle(lifecycle_raw, manifest_raw):
    recovered = recover_staged_lifecycle_bundle(lifecycle_raw)
    base, p = recovered.run, parse_expense_lifecycle_manifest(manifest_raw)
    b = base.payload
    periods = recovered.window_args[3][0]
    ordered = [row['period_ref'] for row in parse_holding_cash(recovered.window_args[3][2])['periods']]
    supplied = {e.cash_run.payload['period_ref']: e for e in periods}
    blockers, rows, checks, previous = [], [], [], None
    payment_ids, payment_refs = set(), set()
    if p['lifecycle_bundle_sha256'] != recovered.bundle_sha256:
        blockers.append('lifecycle_bundle_identity_mismatch')
    if p['context'] != b['context'] or p['currency'] != b['currency']:
        blockers.append('expense_lifecycle_context_or_currency_mismatch')
    if p['inventory_declared_complete'] is not True:
        blockers.append('expense_period_inventory_not_declared_complete')
    for k in ('continuity_basis_ref', 'item_inventory_basis_ref'):
        if p[k] is None:
            blockers.append(k + '_missing')
    if [row['period_ref'] for row in p['periods']] != ordered:
        blockers.append('exact_ordered_operating_period_inventory_required')
    if b['state'] != 'compiled_synthetic_staged_purchase_to_sale':
        blockers.append('underlying_staged_lifecycle_blocked')
    for row in p['periods']:
        period = row['period_ref']
        evidence = supplied.get(period)
        if evidence is None:
            blockers.append(period + ':unknown_operating_period')
            continue
        dr = _utf8(row['detail_source_utf8'], 1_048_576)
        run = reconcile_expense_cash_detail(evidence.noi_raw, evidence.noi_run, evidence.spec_raw, evidence.cash_run, dr)
        if asdict(run) != row['detail_run']:
            raise ValidationError('expense detail proof does not replay from exact lifecycle period')
        d, source = run.payload, parse_expense_cash_detail(dr)
        if d['period_ref'] != period:
            blockers.append(period + ':detail_period_identity_mismatch')
        if d['state'] != 'matched_synthetic_expense_cash_detail':
            blockers.append(period + ':expense_detail_blocked')
        current = {}
        if d['state'] == 'matched_synthetic_expense_cash_detail':
            noi = parse_operating_noi(evidence.noi_raw)
            for item in source['items']:
                pointer = item['noi_pointer']
                identity = '/property_tax' if pointer == '/property_tax' else noi['expense_rows'][int(pointer.rsplit('/', 1)[1])]['item_id']
                current[item['item_id']] = (item['kind'], identity, item)
                for pay in item['payments']:
                    if pay['payment_id'] in payment_ids or pay['source_ref'] in payment_refs:
                        blockers.append(period + ':payment_identity_or_source_reused_across_periods')
                    payment_ids.add(pay['payment_id'])
                    payment_refs.add(pay['source_ref'])
            if previous is not None:
                prev_period, prior = previous
                if set(current) != set(prior):
                    blockers.append(period + ':expense_item_inventory_changed_no_implicit_zero')
                for key in sorted(set(current) & set(prior)):
                    old, new = prior[key], current[key]
                    same = old[:2] == new[:2]
                    payables = _fraction(old[2]['closing_payables']) == _fraction(new[2]['opening_payables'])
                    prepaid = _fraction(old[2]['closing_prepaid']) == _fraction(new[2]['opening_prepaid'])
                    checks.append(dict(item_id=key, prior_period_ref=prev_period, next_period_ref=period,
                                       same_economic_item=same, payables_match=payables, prepaid_match=prepaid))
                    if not same:
                        blockers.append(period + ':' + key + ':expense_identity_or_classification_changed')
                    if not payables or not prepaid:
                        blockers.append(period + ':' + key + ':item_working_balance_discontinuity')
            previous = period, current
        rows.append(dict(period_ref=period, detail_source_sha256=hashlib.sha256(dr).hexdigest(),
                         detail_run=asdict(run), blockers=d['blockers']))
    compatible = not blockers
    payload = dict(component='T77', purpose='synthetic_expense_checked_staged_lifecycle_returns', engine_sha256=ENGINE_SHA256,
                   definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), lifecycle_bundle_sha256=recovered.bundle_sha256,
                   manifest_source_sha256=hashlib.sha256(manifest_raw).hexdigest(), historical_lifecycle_run_sha256=base.sha256,
                   context=b['context'], currency=b['currency'], periods=rows, item_continuity_checks=checks,
                   compiled_investor_json=b['compiled_investor_json'] if compatible else None,
                   investor_run=b['investor_run'] if compatible else None, cash_risk_run=b['cash_risk_run'] if compatible else None,
                   blockers=sorted(set(blockers)), lifecycle_blockers=b['blockers'], historical_lifecycle_state=b['state'],
                   state='compiled_synthetic_expense_checked_lifecycle' if compatible else 'blocked',
                   additional_expense_payment_or_equity_generated=False, personal_investor_return=None,
                   authentic_payments_contracts_or_financial_scope_verified=False, financial_model_complete=False,
                   decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return ExpenseCheckedLifecycleRun(encoded, digest(encoded))


def versions():
    return dict(T77=ENGINE_SHA256, T76=EXPENSE_ENGINE_SHA256,
                T76_definition=hashlib.sha256(EXPENSE_DEFINITION.read_bytes()).hexdigest(),
                definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(), lifecycle=lifecycle_versions())


def export_expense_checked_bundle(lifecycle_raw, manifest_raw, run):
    if type(run) is not ExpenseCheckedLifecycleRun or assemble_expense_checked_lifecycle(lifecycle_raw, manifest_raw) != run:
        raise ValidationError('complete expense checked lifecycle must replay before export')
    body = dict(schema='miniuw.synthetic-expense-checked-lifecycle-bundle.v1', versions=versions(),
                lifecycle_source_utf8=lifecycle_raw.decode('utf-8'), manifest_source_utf8=manifest_raw.decode('utf-8'), expected_run=asdict(run))
    raw = canonical(body).encode('utf-8')
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValidationError('expense checked bundle transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredExpenseCheckedLifecycle:
    lifecycle_raw: bytes
    manifest_raw: bytes
    run: ExpenseCheckedLifecycleRun
    bundle_sha256: str


def recover_expense_checked_bundle(raw):
    p = _json(raw, MAX_BUNDLE_BYTES)
    _exact(p, {'schema', 'versions', 'lifecycle_source_utf8', 'manifest_source_utf8', 'expected_run'})
    if p['schema'] != 'miniuw.synthetic-expense-checked-lifecycle-bundle.v1' or p['versions'] != versions():
        raise ValidationError('incompatible expense checked bundle version')
    lr = _utf8(p['lifecycle_source_utf8'], 16 * 1024 * 1024)
    mr = _utf8(p['manifest_source_utf8'], 8 * 1024 * 1024)
    run = assemble_expense_checked_lifecycle(lr, mr)
    if asdict(run) != p['expected_run']:
        raise ValidationError('expense checked result does not fully reproduce')
    return RecoveredExpenseCheckedLifecycle(lr, mr, run, hashlib.sha256(raw).hexdigest())
