"""Reproduce availability/proration declarations and guarded full cash return."""
from pathlib import Path
import copy
import hashlib
import json

from phased_rental_demo_support import raw,q,refresh_calendar,change_segment,AT
from miniuw_foundation.phased_rental import produce_phased_rental
from miniuw_foundation.phased_rental_lifecycle import assemble_phased_rental_lifecycle,export_phased_rental_bundle,recover_phased_rental_bundle
from miniuw_foundation.current_phased_rental import assemble_current_phased_rental
from miniuw_foundation.evidence_currency import evaluate_evidence_currency

ROOT=Path(__file__).resolve().parents[1]


def main():
    er=(ROOT/'templates/synthetic-phased-expense-base.json').read_bytes();mr=(ROOT/'templates/synthetic-phased-lifecycle-manifest.json').read_bytes()
    bundle=(ROOT/'templates/synthetic-phased-rental-bundle.json').read_bytes();rr=(ROOT/'templates/synthetic-phased-rental-evidence.json').read_bytes()
    run=assemble_phased_rental_lifecycle(er,mr);assert export_phased_rental_bundle(er,mr,run)==bundle and recover_phased_rental_bundle(bundle).run==run
    current=assemble_current_phased_rental(bundle,rr,evaluate_evidence_currency(rr,AT),AT)
    expired=copy.deepcopy(json.loads(rr));next(e for e in expired['evidence']if e['requirement_id']=='/phased/periods/0/calendar')['valid_until']=AT;expired_raw=raw(expired)
    pending=assemble_current_phased_rental(bundle,expired_raw,evaluate_evidence_currency(expired_raw,AT),AT)
    assert current.payload['current_project_return_story']is not None and pending.payload['current_project_return_story']is None
    assert pending.payload['current_phased_segments']is None and pending.payload['current_capacity_inventories']is None
    changed=refresh_calendar(json.loads(mr),0,lambda c:change_segment(c,1,lambda s:s['residential_groups'][0].update(units=q(6))));changed_raw=raw(changed)
    blocked=assemble_phased_rental_lifecycle(er,changed_raw);assert blocked.investor_run is None
    blocked_bundle=export_phased_rental_bundle(er,changed_raw,blocked);assert recover_phased_rental_bundle(blocked_bundle).run==blocked
    partial_raw=(ROOT/'templates/synthetic-partial-rental-period.json').read_bytes();partial=produce_phased_rental(partial_raw);assert partial.payload['totals']['effective_rent']==q(5)
    for path,view in [('docs/review/Revision_Vigente_Disponibilidad_y_Retorno_T84.md',current),('docs/review/Revision_Pendiente_Disponibilidad_y_Retorno_T84.md',pending)]:(ROOT/path).write_text(view.payload['markdown'])
    p=run.investor_run.payload
    return dict(components=['T82','T83','T84'],purpose='synthetic_supplied_availability_proration_and_full_cash_return',
                expense_base_sha256=hashlib.sha256(er).hexdigest(),manifest_sha256=hashlib.sha256(mr).hexdigest(),return_run_sha256=run.sha256,
                bundle_sha256=hashlib.sha256(bundle).hexdigest(),full_recovery_passed=True,evaluated_as_of_UTC=AT,required_source_bindings=len(current.payload['required_source_bindings']),
                current_run_sha256=current.sha256,current_markdown_sha256=current.payload['markdown_sha256'],pending_run_sha256=pending.sha256,pending_markdown_sha256=pending.payload['markdown_sha256'],expired_registry_source_utf8=expired_raw.decode(),
                segment_amounts=current.payload['current_phased_segments'],capacity_inventories=current.payload['current_capacity_inventories'],expense_period_totals=current.payload['current_expense_period_totals'],
                base_case={k:p[k]for k in ['gross_contributions','gross_distributions','net_cash_profit','equity_multiple','normalized_story','annual_cash_receipts','annual_irr_roots','story_blockers']},
                changed_availability_but_unchanged_NOI=dict(manifest_source_utf8=changed_raw.decode(),blockers=blocked.payload['blockers'],full_return_withheld=True,recovered_still_blocked=True),
                standalone_partial_period=dict(source_sha256=hashlib.sha256(partial_raw).hexdigest(),run_sha256=partial.sha256,start_date=partial.payload['start_date'],end_date=partial.payload['end_date'],totals=partial.payload['totals'],not_automatically_extended_to_operating_window=True),
                delivery_or_day_count_rule_generated=False,rental_income_double_counted=False,financial_model_complete=False,personal_investor_return=None,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
