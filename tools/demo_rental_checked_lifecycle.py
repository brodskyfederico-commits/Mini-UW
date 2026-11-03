"""Reproduce supplied monthly rental inputs through complete declared cash returns."""
from pathlib import Path
import copy
import hashlib
import json

from rental_lifecycle_demo_support import raw, q, refresh_calendar, change_month, AT
from miniuw_foundation.rental_checked_lifecycle import assemble_rental_checked_lifecycle, export_rental_checked_bundle, recover_rental_checked_bundle
from miniuw_foundation.current_rental_lifecycle import assemble_current_rental_lifecycle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency

ROOT = Path(__file__).resolve().parents[1]


def main():
    er = (ROOT/'templates/synthetic-rental-expense-base.json').read_bytes()
    mr = (ROOT/'templates/synthetic-rental-lifecycle-manifest.json').read_bytes()
    bundle = (ROOT/'templates/synthetic-rental-checked-lifecycle-bundle.json').read_bytes()
    rr = (ROOT/'templates/synthetic-rental-lifecycle-evidence.json').read_bytes()
    run = assemble_rental_checked_lifecycle(er, mr)
    assert export_rental_checked_bundle(er, mr, run) == bundle and recover_rental_checked_bundle(bundle).run == run
    current = assemble_current_rental_lifecycle(bundle, rr, evaluate_evidence_currency(rr, AT), AT)
    expired = copy.deepcopy(json.loads(rr))
    next(e for e in expired['evidence'] if e['requirement_id'] == '/rental/periods/0/months/0')['valid_until'] = AT
    expired_raw = raw(expired)
    pending = assemble_current_rental_lifecycle(bundle, expired_raw, evaluate_evidence_currency(expired_raw, AT), AT)
    assert current.payload['current_project_return_story'] is not None
    assert pending.payload['current_project_return_story'] is None and pending.payload['current_rental_months'] is None
    changed = refresh_calendar(json.loads(mr), 0, lambda c:change_month(c, 2, lambda s:s['residential_groups'][0].update(rent=q(3))))
    changed_raw = raw(changed)
    blocked = assemble_rental_checked_lifecycle(er, changed_raw)
    assert blocked.investor_run is None
    blocked_bundle = export_rental_checked_bundle(er, changed_raw, blocked)
    assert recover_rental_checked_bundle(blocked_bundle).run == blocked
    for path, view in [('docs/review/Revision_Vigente_Renta_Mensual_T81.md', current), ('docs/review/Revision_Pendiente_Renta_Mensual_T81.md', pending)]:
        (ROOT/path).write_text(view.payload['markdown'])
    p = run.investor_run.payload
    return dict(components=['T79','T80','T81'], purpose='synthetic_monthly_rental_to_NOI_cash_and_full_investor_return',
                expense_base_sha256=hashlib.sha256(er).hexdigest(), rental_manifest_sha256=hashlib.sha256(mr).hexdigest(),
                return_run_sha256=run.sha256, bundle_sha256=hashlib.sha256(bundle).hexdigest(), full_recovery_passed=True,
                evaluated_as_of_UTC=AT, required_source_bindings=len(current.payload['required_source_bindings']),
                current_run_sha256=current.sha256, current_markdown_sha256=current.payload['markdown_sha256'],
                pending_run_sha256=pending.sha256, pending_markdown_sha256=pending.payload['markdown_sha256'], expired_registry_source_utf8=expired_raw.decode(),
                monthly_amounts=current.payload['current_rental_months'], expense_period_totals=current.payload['current_expense_period_totals'],
                base_case={k:p[k] for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','annual_cash_receipts','annual_irr_roots','story_blockers']},
                changed_rent_but_unchanged_NOI=dict(manifest_source_utf8=changed_raw.decode(), blockers=blocked.payload['blockers'],
                    full_return_withheld=True, recovered_still_blocked=True, bundle_sha256=hashlib.sha256(blocked_bundle).hexdigest()),
                rental_income_double_counted=False, market_absorption_or_funding_generated=False,
                financial_model_complete=False, personal_investor_return=None, decision='PENDING', production_authorized=False)


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
