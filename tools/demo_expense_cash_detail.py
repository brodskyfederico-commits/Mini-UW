"""Reproduce per-item planned expenses/payments without adding new cash flows."""
import copy
import hashlib
import json
from pathlib import Path
from fractions import Fraction

from miniuw_foundation.drafts import canonical
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.expense_cash_detail import (
    reconcile_expense_cash_detail, export_expense_cash_bundle, recover_expense_cash_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def build_case():
    nr = (ROOT/'templates/synthetic-expense-detail-noi.json').read_bytes()
    cr = (ROOT/'templates/synthetic-expense-detail-cash.json').read_bytes()
    dr = (ROOT/'templates/synthetic-expense-cash-detail.json').read_bytes()
    n = produce_operating_noi(nr)
    c = reconcile_operating_cash(nr, n, cr)
    return nr, n, cr, c, dr


def main():
    args = build_case()
    nr, n, cr, c, dr = args
    run = reconcile_expense_cash_detail(*args)
    assert run.payload['state'] == 'matched_synthetic_expense_cash_detail'
    bundle = export_expense_cash_bundle(*args, run)
    assert recover_expense_cash_bundle(bundle) == run
    saved = (ROOT/'templates/synthetic-expense-cash-bundle.json').read_bytes()
    assert saved == bundle and recover_expense_cash_bundle(saved) == run
    q = lambda x: rational(Fraction(x))
    altered = copy.deepcopy(json.loads(dr))
    altered['items'][0]['payments'][0]['amount'] = q(141)
    altered['items'][2]['payments'][0]['amount'] = q(179)
    bad = reconcile_expense_cash_detail(nr, n, cr, c, canonical(altered).encode())
    assert bad.payload['state'] == 'blocked' and bad.payload['totals'] is None
    return {'purpose': 'synthetic_expense_accrual_payment_balance_demo', 'component': 'T76',
            'NOI': n.payload['noi'], 'baseline': run.payload, 'result_sha256': run.sha256,
            'net_operating_cash': c.payload['net_operating_cash'],
            'planned_distribution': c.payload['exportable_operating_distribution'],
            'closing_free_cash': c.payload['expected_closing_free_cash'],
            'offsetting_errors_blocked': bad.payload['blockers'],
            'offsetting_errors_totals_withheld': bad.payload['totals'] is None,
            'bundle_sha256': hashlib.sha256(bundle).hexdigest(),
            'exact_source_recovery_passed': True, 'additional_expense_or_payment_generated': False,
            'decision': 'PENDING', 'real_decisions_enabled': False, 'production_authorized': False}


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
