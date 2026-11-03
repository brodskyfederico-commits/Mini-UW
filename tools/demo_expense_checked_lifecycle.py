"""Reproduce declared purchase-to-sale returns and expense continuity/current gates."""
from pathlib import Path
import copy
import hashlib
import json

from expense_lifecycle_demo_support import raw, q, refresh_detail, AT
from miniuw_foundation.expense_checked_lifecycle import assemble_expense_checked_lifecycle, export_expense_checked_bundle, recover_expense_checked_bundle
from miniuw_foundation.current_expense_lifecycle import assemble_current_expense_lifecycle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency

ROOT = Path(__file__).resolve().parents[1]


def main():
    lifecycle = (ROOT/'templates/synthetic-expense-lifecycle-base.json').read_bytes()
    manifest_raw = (ROOT/'templates/synthetic-expense-lifecycle-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    run = assemble_expense_checked_lifecycle(lifecycle, manifest_raw)
    bundle = (ROOT/'templates/synthetic-expense-checked-lifecycle-bundle.json').read_bytes()
    assert export_expense_checked_bundle(lifecycle, manifest_raw, run) == bundle
    assert recover_expense_checked_bundle(bundle).run == run
    rr = (ROOT/'templates/synthetic-expense-lifecycle-evidence.json').read_bytes()
    current = assemble_current_expense_lifecycle(bundle, rr, evaluate_evidence_currency(rr, AT), AT)
    expired = copy.deepcopy(json.loads(rr))
    next(e for e in expired['evidence'] if e['requirement_id'] == '/expense/periods/0/detail')['valid_until'] = AT
    er = raw(expired)
    pending = assemble_current_expense_lifecycle(bundle, er, evaluate_evidence_currency(er, AT), AT)
    assert current.payload['current_project_return_story'] is not None
    assert pending.payload['current_project_return_story'] is None and pending.payload['current_expense_period_totals'] is None
    def move_payable(d):
        a, b = d['items'][:2]
        a['closing_payables'] = q(0)
        b['closing_payables'] = q(5)
        a['payments'][0]['amount'] = q(10)
        b['payments'][0]['amount'] = q(0)
    wrong_manifest = refresh_detail(lifecycle, manifest, 0, move_payable)
    wrong_raw = raw(wrong_manifest)
    wrong = assemble_expense_checked_lifecycle(lifecycle, wrong_raw)
    assert wrong.investor_run is None
    assert all(not p['blockers'] for p in wrong.payload['periods'])
    wrong_bundle = export_expense_checked_bundle(lifecycle, wrong_raw, wrong)
    assert recover_expense_checked_bundle(wrong_bundle).run == wrong
    for path, view in [('docs/review/Revision_Vigente_Gastos_y_Retorno_T78.md', current), ('docs/review/Revision_Pendiente_Gastos_y_Retorno_T78.md', pending)]:
        (ROOT/path).write_text(view.payload['markdown'])
    p = run.investor_run.payload
    return dict(components=['T77', 'T78'], purpose='synthetic_expense_detail_continuity_and_full_cash_return',
                lifecycle_source_sha256=hashlib.sha256(lifecycle).hexdigest(), manifest_source_sha256=hashlib.sha256(manifest_raw).hexdigest(),
                return_run_sha256=run.sha256, bundle_sha256=hashlib.sha256(bundle).hexdigest(), full_recovery_passed=True,
                evaluated_as_of_UTC=AT, required_source_bindings=len(current.payload['required_source_bindings']),
                current_run_sha256=current.sha256, current_markdown_sha256=current.payload['markdown_sha256'],
                expired_registry_source_utf8=er.decode(), pending_run_sha256=pending.sha256,
                pending_markdown_sha256=pending.payload['markdown_sha256'],
                current_story={k:p[k] for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','annual_cash_receipts','annual_irr_roots','story_blockers']},
                item_continuity_checks=run.payload['item_continuity_checks'], expense_period_totals=current.payload['current_expense_period_totals'],
                aggregate_balanced_but_wrong_item=dict(manifest_source_utf8=wrong_raw.decode(), blockers=wrong.payload['blockers'],
                    all_period_details_individually_compatible=True, full_return_withheld=True, blocked_recovery_passed=True,
                    bundle_sha256=hashlib.sha256(wrong_bundle).hexdigest()),
                historical_negative_result_preserved=True, additional_expense_payment_or_equity_generated=False,
                personal_investor_return=None, financial_model_complete=False, decision='PENDING', production_authorized=False)


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
