"""Synthetic cash-risk observations; no new screening or downside policy."""
from dataclasses import asdict
from pathlib import Path
import json

from miniuw_foundation.cash_risk import CashRiskRun, summarize_cash_risk, verify_cash_risk
from miniuw_foundation.drafts import canonical
from miniuw_foundation.investor_returns import produce_investor_returns


def main():
    root = Path(__file__).resolve().parents[1]
    original = (root / 'templates/synthetic-investor-returns.json').read_bytes()
    source = json.loads(original)
    upstream = produce_investor_returns(original)
    summary = summarize_cash_risk(original, upstream)
    # Rehydrate saved report JSON and reproduce from unchanged input bytes.
    saved = json.loads(json.dumps(asdict(summary)))
    verify_cash_risk(original, upstream, CashRiskRun(**saved))
    cut = json.loads(original)
    cut['context']['run_id'] += '-explicit-zero-sale-cash-test'
    cut['events'][-1]['amount'] = {'numerator': '0', 'denominator': '1'}
    cut_raw = canonical(cut).encode()
    cut_run = produce_investor_returns(cut_raw)
    cut_risk = summarize_cash_risk(cut_raw, cut_run)
    return {
        'purpose': 'internal_synthetic_cash_risk_demonstration',
        'original_source_preserved': json.loads(original) == source,
        'saved_report_replayed': True,
        'base_report': asdict(summary),
        'explicit_zero_sale_cash_test': {
            'label': 'isolated arithmetic test; not an adopted Downside or a no-sale scenario',
            'source_json': cut_raw.decode(), 'report': asdict(cut_risk)},
        'full_risk_analysis_completed': False, 'professional_approval_inferred': False,
        'condominium_expansion': 'deferred_to_Full_UW',
        'decision': 'PENDING', 'production_authorized': False}


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
