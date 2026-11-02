"""T38 isolated net sale receipt sensitivity; not a rebuilt project scenario."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import re

from .drafts import ContextSeed, ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant
from .debt_service import _fraction, rational
from .operating_noi import _bounded, ArithmeticBudgetError
from .investor_returns import InvestorReturnsRun, produce_investor_returns, parse_investor_returns
from .cash_risk import summarize_cash_risk, ENGINE_SHA256 as RISK_ENGINE_SHA256

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T38.md'
SCHEMA = 'miniuw.synthetic-net-sale-receipt-sensitivity.v1'


@dataclass(frozen=True)
class SaleSensitivityRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def parse_sale_sensitivity(raw):
    if type(raw) is not bytes or not raw or len(raw) > 131072:
        raise ValidationError('bounded sale sensitivity JSON required')
    try:
        p = json.loads(raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationError('invalid sensitivity JSON') from error
    keys = {'schema', 'context', 'base_source_sha256', 'base_run_sha256', 'target_event_id',
            'frozen_cash_assumption_ref', 'case_inventory_declared_complete', 'cases'}
    if type(p) is not dict or set(p) != keys or p['schema'] != SCHEMA:
        raise ValidationError('exact net sale receipt sensitivity profile required')
    if type(p['context']) is not dict:
        raise ValidationError('explicit synthetic context required')
    try:
        ContextSeed(**p['context'])
    except TypeError as error:
        raise ValidationError('exact synthetic context required') from error
    for key in ['base_source_sha256', 'base_run_sha256']:
        if type(p[key]) is not str or not re.fullmatch('[a-f0-9]{64}', p[key]):
            raise ValidationError('explicit source/run hash required')
    nonempty(p['target_event_id'], 'target_event_id')
    if p['frozen_cash_assumption_ref'] is not None:
        nonempty(p['frozen_cash_assumption_ref'], 'frozen_cash_assumption_ref')
    if p['case_inventory_declared_complete'] is not None and type(p['case_inventory_declared_complete']) is not bool:
        raise ValidationError('explicit inventory declaration required')
    if type(p['cases']) is not list or not 1 <= len(p['cases']) <= 12:
        raise ValidationError('one to twelve explicit sensitivity cases required')
    seen = set(); runs = set(); scenarios = set()
    for row in p['cases']:
        if type(row) is not dict or set(row) != {'case_id', 'scenario_id', 'run_id',
                'net_sale_distribution', 'currency', 'date', 'source_ref'}:
            raise ValidationError('exact sensitivity case fields required')
        for key in ['case_id', 'scenario_id', 'run_id']:
            nonempty(row[key], key)
        if not row['scenario_id'].startswith('SYNTHETIC-'):
            raise ValidationError('explicit synthetic sensitivity label required')
        for key in ['currency', 'date', 'source_ref']:
            if row[key] is not None:
                nonempty(row[key], key)
        _fraction(row['net_sale_distribution'])
        if row['case_id'] in seen or row['run_id'] in runs or row['scenario_id'] in scenarios:
            raise ValidationError('unique case, run and scenario identities required')
        seen.add(row['case_id']); runs.add(row['run_id']); scenarios.add(row['scenario_id'])
    return p


def compare_sale_receipts(base_raw, base_run, spec_raw):
    """Replace only a selected net sale distribution; keep all other cash fixed."""
    spec = parse_sale_sensitivity(spec_raw)
    if type(base_run) is not InvestorReturnsRun or digest(base_run.payload_json) != base_run.sha256:
        raise ValidationError('typed base run with matching digest required')
    if produce_investor_returns(base_raw) != base_run:
        raise ValidationError('base investor source/run replay mismatch')
    base = base_run.payload
    source = parse_investor_returns(base_raw)
    blockers = []
    for key, actual in [('base_source_sha256', hashlib.sha256(base_raw).hexdigest()),
                        ('base_run_sha256', base_run.sha256), ('context', base['context'])]:
        if spec[key] != actual:
            blockers.append(key + '_mismatch')
    if spec['frozen_cash_assumption_ref'] is None:
        blockers.append('explicit_frozen_other_cash_assumption_missing')
    if spec['case_inventory_declared_complete'] is not True:
        blockers.append('case_inventory_not_declared_complete')
    if base['cash_metrics_state'] != 'computed_synthetic':
        blockers.append('base_cash_metrics_blocked')
    targets = [e for e in source['events'] if e['event_id'] == spec['target_event_id']]
    target = targets[0] if len(targets) == 1 else None
    if target is None or target['kind'] != 'distribution' or target['category'] != 'net_sale_distribution':
        blockers.append('target_not_an_explicit_net_sale_distribution')
    required = None
    equity_multiple_one_defined = False
    if not blockers:
        try:
            a = _fraction(base['gross_contributions'], max_digits=1300)
            d = _fraction(base['gross_distributions'], max_digits=1300)
            old = _fraction(target['amount'])
            required = rational(max(Fraction(0), _bounded(a - _bounded(d - old))))
            # With A > 0, EM >= 1 iff the replacement receipt meets this floor.
            # A floor of zero need not yield exact EM == 1 if other receipts exceed A.
            equity_multiple_one_defined = a > 0
        except ArithmeticBudgetError:
            blockers.append('sensitivity_exact_arithmetic_budget_exceeded')
    results = []
    for row in spec['cases']:
        issues = list(blockers)
        amount = _fraction(row['net_sale_distribution'])
        if amount is None or amount < 0:
            issues.append('net_sale_receipt_missing_or_negative')
        if row['currency'] != source['currency']:
            issues.append('case_currency_missing_or_mismatch')
        if target is not None and row['date'] != target['date']:
            issues.append('case_date_missing_or_changed')
        if row['source_ref'] is None:
            issues.append('case_source_ref_missing')
        if row['run_id'] == source['context']['run_id'] or row['scenario_id'] == source['context']['scenario_id']:
            issues.append('case_requires_distinct_run_and_scenario_identity')
        result = {'case_claim': row, 'state': 'blocked', 'blockers': [],
                  'compiled_investor_json': None, 'compiled_source_sha256': None,
                  'investor_run_sha256': None, 'risk_run_sha256': None, 'outputs': None,
                  'decision': 'PENDING'}
        if not issues:
            # JSON clone; never edit the original or silently retune a bank/cash input.
            compiled = json.loads(canonical(source))
            compiled['context']['scenario_id'] = row['scenario_id']
            compiled['context']['run_id'] = row['run_id']
            event = next(e for e in compiled['events'] if e['event_id'] == target['event_id'])
            event['amount'] = row['net_sale_distribution']
            event['source_ref'] = row['source_ref']
            raw = canonical(compiled).encode()
            try:
                run = produce_investor_returns(raw)
                risk = summarize_cash_risk(raw, run)
                p = run.payload; rp = risk.payload
                if p['cash_metrics_state'] != 'computed_synthetic' or rp['state'] != 'computed_synthetic':
                    issues.extend(p['cash_blockers'] + rp['cash_blockers'])
                    issues.append('compiled_cash_observations_blocked')
                else:
                    profit = _fraction(p['net_cash_profit'], max_digits=1300)
                    base_profit = _fraction(base['net_cash_profit'], max_digits=1300)
                    result.update(state='computed_synthetic', compiled_investor_json=raw.decode(),
                        compiled_source_sha256=hashlib.sha256(raw).hexdigest(), investor_run_sha256=run.sha256,
                        risk_run_sha256=risk.sha256, outputs={
                            'cash_metrics': rp['metrics'], 'equity_multiple': p['equity_multiple'],
                            'net_cash_profit_change_from_base': rational(_bounded(profit - base_profit)),
                            'periodic_irr': p['periodic_irr'], 'annual_irr_roots': p['annual_irr_roots'],
                            'selected_IRR': None, 'upstream_story_blockers': p['story_blockers']})
            except (ValidationError, ArithmeticBudgetError):
                # Failed compilation never publishes a partial result or substitutes a float.
                issues.append('compiled_source_or_exact_arithmetic_unsupported')
                result.update(state='blocked', compiled_investor_json=None, compiled_source_sha256=None,
                              investor_run_sha256=None, risk_run_sha256=None, outputs=None)
        result['blockers'] = sorted(set(issues))
        results.append(result)
    payload = {
        'component': 'T38', 'purpose': 'isolated_synthetic_net_sale_receipt_sensitivity',
        'engine_sha256': ENGINE_SHA256, 'risk_engine_sha256': RISK_ENGINE_SHA256,
        'definition_sha256': hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'spec_sha256': hashlib.sha256(spec_raw).hexdigest(),
        'base_source_sha256': hashlib.sha256(base_raw).hexdigest(), 'base_run_sha256': base_run.sha256,
        'context': base['context'], 'currency': source['currency'],
        'equity_level': 'aggregate_project_equity', 'target_event_id': spec['target_event_id'],
        'frozen_cash_assumption_ref': spec['frozen_cash_assumption_ref'],
        'conditional_cash_recovery_net_sale_receipt_floor': required,
        'EM_ge_one_equivalence_defined': equity_multiple_one_defined,
        'blockers': sorted(set(blockers)), 'cases': results,
        'all_declared_cases_computable': all(r['state'] == 'computed_synthetic' for r in results),
        'gross_sale_price_break_even': None, 'exit_cap_break_even': None,
        'project_scenario_recomputed': False, 'bank_capacity_checked': False,
        'cash_and_closing_producer_link_preserved': False,
        'original_source_modified': False, 'downside_policy_adopted': False,
        'personal_investor_return': None, 'final_economic_capital_loss': None,
        'risk_analysis_completed': False, 'decision': 'PENDING',
        'real_decisions_enabled': False, 'production_authorized': False}
    encoded = canonical(payload)
    return SaleSensitivityRun(encoded, digest(encoded))


def verify_sale_sensitivity(base_raw, base_run, spec_raw, report):
    if type(report) is not SaleSensitivityRun or digest(report.payload_json) != report.sha256:
        raise ValidationError('typed sensitivity report with matching hash required')
    if compare_sale_receipts(base_raw, base_run, spec_raw) != report:
        raise ValidationError('sensitivity report replay mismatch')
    return report
