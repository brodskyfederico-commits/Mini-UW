"""T37 bounded cash-risk observations on replayed synthetic project equity.

No LP waterfall, final economic-loss assertion, financing approval or decision.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError, canonical, digest
from .debt_service import _fraction, rational
from .investor_returns import InvestorReturnsRun, produce_investor_returns
from .operating_noi import ArithmeticBudgetError, _bounded

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T37.md'


@dataclass(frozen=True)
class CashRiskRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def summarize_cash_risk(raw: bytes, investor_run: InvestorReturnsRun) -> CashRiskRun:
    """Require exact T23 replay; observe dated equity flows without modifying them."""
    if type(investor_run) is not InvestorReturnsRun:
        raise ValidationError('typed investor return run required')
    if digest(investor_run.payload_json) != investor_run.sha256:
        raise ValidationError('investor run digest mismatch')
    replay = produce_investor_returns(raw)
    if replay != investor_run:
        raise ValidationError('investor source/run replay mismatch')
    source = replay.payload
    blockers = list(source['cash_blockers'])
    metrics = None
    rows = []
    if source['cash_metrics_state'] == 'computed_synthetic':
        try:
            # T23 already checked amounts, dates, categories, currency and inventory.
            dates = [row['date'] for row in source['dated_net_flows']]
            gross = {d: [Fraction(0), Fraction(0)] for d in dates}
            for event in source['events']:
                index = 0 if event['kind'] == 'contribution' else 1
                gross[event['date']][index] = _bounded(
                    gross[event['date']][index] + _fraction(event['amount']))
            balance = close_peak = upper_peak = Fraction(0)
            for day in dates:
                contributions, distributions = gross[day]
                before = balance
                # Worst unspecified order within this date: all contributions first.
                possible_peak = max(Fraction(0), _bounded(before + contributions))
                balance = _bounded(_bounded(before + contributions) - distributions)
                close_peak = max(close_peak, balance)
                upper_peak = max(upper_peak, possible_peak)
                rows.append({
                    'date': day, 'gross_contributions': rational(contributions),
                    'gross_distributions': rational(distributions),
                    'cumulative_contributions_less_distributions': rational(balance),
                    'within_date_peak_upper_bound': rational(possible_peak)})
            a = _fraction(source['gross_contributions'], max_digits=1300)
            d = _fraction(source['gross_distributions'], max_digits=1300)
            sale = _fraction(source['cash_by_category']['net_sale_distribution'], max_digits=1300)
            q = rational
            metrics = {
                'gross_contributions': q(a), 'gross_distributions': q(d),
                'net_cash_profit': q(_bounded(d - a)),
                'cash_shortfall_at_horizon': q(max(Fraction(0), balance)),
                'cash_surplus_at_horizon': q(max(Fraction(0), -balance)),
                'peak_cumulative_net_equity_funding_at_date_close': q(close_peak),
                'possible_intraday_peak_upper_bound': q(upper_peak),
                'net_sale_distribution': q(sale),
                'sale_share_of_distributions': q(_bounded(sale / d)) if d > 0 else None,
                'sale_share_state': 'computed_synthetic' if d > 0 else 'undefined_zero_distributions',
                'receipts_excluding_sale_distributions': q(_bounded(d - sale)),
                'cash_shortfall_excluding_sale_receipts': q(max(Fraction(0), _bounded(a - _bounded(d - sale)))),
                'additional_capital_contributions': source['cash_by_category']['additional_capital'],
                'refinance_cash_in_contributions': source['cash_by_category']['refinance_cash_in']}
        except ArithmeticBudgetError:
            blockers.append('cash_risk_exact_arithmetic_budget_exceeded')
            metrics = None
            rows = []
    payload = {
        'component': 'T37', 'purpose': 'synthetic_project_equity_cash_risk_observations',
        'engine_sha256': ENGINE_SHA256,
        'definition_sha256': hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'investor_source_sha256': source['source_sha256'],
        'investor_run_sha256': investor_run.sha256,
        'context': source['context'], 'currency': source['currency'],
        'equity_level': 'aggregate_project_equity', 'cash_horizon': source['cash_horizon'],
        'state': 'computed_synthetic' if metrics is not None else 'blocked',
        'metrics': metrics, 'dated_funding_observations': rows,
        'cash_blockers': sorted(set(blockers)), 'upstream_story_blockers': source['story_blockers'],
        'personal_investor_return': None, 'personal_investor_return_state': 'PENDING',
        'final_economic_capital_loss': None, 'final_economic_capital_loss_state': 'PENDING',
        'unresolved': ['personal_allocation_terms_and_investor_ledger_not_verified',
                       'terminal_assets_liabilities_and_economic_close_not_verified',
                       'intra_date_order_and_actual_funding_availability_not_verified',
                       'independent_downside_inputs_and_financing_compatibility_not_verified'],
        'sale_exclusion_is_a_recomputed_scenario': False,
        'capital_still_invested_derived_from_net_cash': False,
        'retained_equity_included_in_receipts': False,
        'financing_compatibility_checked': False, 'LP_allocation_applied': False,
        'risk_analysis_completed': False, 'decision': 'PENDING',
        'production_authorized': False, 'real_decisions_enabled': False}
    encoded = canonical(payload)
    return CashRiskRun(encoded, digest(encoded))


def verify_cash_risk(raw: bytes, investor_run: InvestorReturnsRun, summary: CashRiskRun):
    """Replay supplied evidence; a self-consistent hash alone does not validate it."""
    if type(summary) is not CashRiskRun or digest(summary.payload_json) != summary.sha256:
        raise ValidationError('typed cash risk run with matching digest required')
    if summarize_cash_risk(raw, investor_run) != summary:
        raise ValidationError('cash risk replay mismatch')
    return summary
