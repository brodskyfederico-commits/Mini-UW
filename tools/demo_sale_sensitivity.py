"""Explicit isolated receipt cases; never an adopted Downside or project approval."""
from dataclasses import asdict
from pathlib import Path
import json

from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.sale_sensitivity import (compare_sale_receipts, verify_sale_sensitivity,
                                              SaleSensitivityRun)


def main():
    root = Path(__file__).resolve().parents[1]
    base_raw = (root/'templates/synthetic-investor-returns.json').read_bytes()
    spec_raw = (root/'templates/synthetic-sale-receipt-sensitivity.json').read_bytes()
    base = produce_investor_returns(base_raw)
    report = compare_sale_receipts(base_raw, base, spec_raw)
    saved = json.loads(json.dumps(asdict(report)))
    verify_sale_sensitivity(base_raw, base, spec_raw, SaleSensitivityRun(**saved))
    p = report.payload
    return {
        'purpose': 'internal_synthetic_isolated_net_sale_receipt_demo',
        'base_source_path': 'templates/synthetic-investor-returns.json',
        'spec_path': 'templates/synthetic-sale-receipt-sensitivity.json',
        'saved_report_replayed': True,
        'conditional_cash_recovery_net_sale_receipt_floor': p['conditional_cash_recovery_net_sale_receipt_floor'],
        'case_summary': [{'case_id': row['case_claim']['case_id'], 'state': row['state'],
            'replacement_net_sale_receipt': row['case_claim']['net_sale_distribution'],
            'net_cash_profit': row['outputs']['cash_metrics']['net_cash_profit'],
            'cash_shortfall_at_horizon': row['outputs']['cash_metrics']['cash_shortfall_at_horizon'],
            'equity_multiple': row['outputs']['equity_multiple'], 'decision': row['decision']}
            for row in p['cases']],
        'report': saved, 'project_scenario_recomputed': False,
        'full_risk_analysis_completed': False, 'production_authorized': False}


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
