"""T78 explicit-time full-source gate for expense-checked staged cash returns."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError, canonical, digest
from .expense_checked_lifecycle import recover_expense_checked_bundle, parse_expense_lifecycle_manifest, DEFINITION
from .staged_lifecycle_bundle import recover_staged_lifecycle_bundle, required_staged_lifecycle_sources
from .evidence_currency import EvidenceCurrencyRun, evaluate_evidence_currency
from .investor_review import _render, literal, amount, ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def required_expense_lifecycle_sources(recovered, bundle_raw):
    if recover_expense_checked_bundle(bundle_raw) != recovered:
        raise ValidationError('recovered expense lifecycle must match exact bundle')
    base = recover_staged_lifecycle_bundle(recovered.lifecycle_raw)
    required = required_staged_lifecycle_sources(base, recovered.lifecycle_raw)
    def add(path, raw):
        required.append(dict(requirement_id=path, source_sha256=hashlib.sha256(raw).hexdigest(), source_locator=path))
    add('/expense/manifest', recovered.manifest_raw)
    add('/transport/expense_checked_bundle', bundle_raw)
    for i, row in enumerate(parse_expense_lifecycle_manifest(recovered.manifest_raw)['periods']):
        add('/expense/periods/' + str(i) + '/detail', row['detail_source_utf8'].encode('utf-8'))
    if len(required) > 256:
        raise ValidationError('expense source inventory exceeds evidence profile budget')
    return required


@dataclass(frozen=True)
class CurrentExpenseLifecycleRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def assemble_current_expense_lifecycle(bundle_raw, registry_raw, registry_run, as_of):
    recovered = recover_expense_checked_bundle(bundle_raw)
    p = recovered.run.payload
    if type(registry_run) is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw, as_of) != registry_run:
        raise ValidationError('expense lifecycle registry must replay at identical explicit UTC instant')
    r = registry_run.payload
    required = required_expense_lifecycle_sources(recovered, bundle_raw)
    blockers, story = [], None
    if sorted(required, key=lambda e:e['requirement_id']) != sorted([e['requirement'] for e in r['requirements']], key=lambda e:e['requirement_id']):
        blockers.append('complete_expense_lifecycle_source_inventory_mismatch')
    if r['context'] != p['context']:
        blockers.append('expense_lifecycle_evidence_context_mismatch')
    if r['state'] != 'current_synthetic_evidence':
        blockers.append('expense_lifecycle_sources_not_current')
    if p['state'] != 'compiled_synthetic_expense_checked_lifecycle':
        blockers.append('expense_lifecycle_calculation_blocked')
    if not blockers:
        inv = recovered.run.investor_run.payload
        story = {k:inv[k] for k in ['currency', 'gross_contributions', 'gross_distributions', 'net_cash_profit',
                                  'equity_multiple', 'cash_by_category', 'cash_horizon', 'normalized_story',
                                  'capital_snapshots', 'annual_cash_receipts', 'periodic_irr', 'annual_irr_roots']}
        story.update(equity_level='aggregate_project_equity', dated_events=inv['events'], upstream_story_blockers=inv['story_blockers'],
                     selected_IRR=None, risk_observations=json.loads(p['cash_risk_run']['payload_json'])['metrics'],
                     personal_investor_return=None, decision='PENDING')
    row = dict(case_id='Obra, gastos detallados, operación y venta: ejemplo sintético',
               state='current_synthetic_expense_checked_lifecycle_at_declared_time' if story is not None else 'PENDING',
               current_matched_case=None if story is None else dict(candidate_project_return_story=story),
               blockers=blockers, comparison_blockers=[], reference_evidence_blockers=[], candidate_evidence_blockers=r['blockers'],
               reference_calculation_blockers=[], candidate_calculation_blockers=p['blockers'] + p['lifecycle_blockers'],
               reference_original_cost_blockers=[], candidate_original_cost_blockers=[])
    markdown = _render(dict(evaluated_as_of_UTC=as_of, blockers=[], case_rows=[row]))
    totals = None
    if story is not None:
        totals = []
        markdown += '\n## Puente de gastos y pagos\n\n| Período | Gasto devengado | Pago operativo | Por pagar inicial/final | Prepago inicial/final |\n|---|---:|---:|---:|---:|\n'
        for period in p['periods']:
            d = json.loads(period['detail_run']['payload_json'])
            t = d['totals']
            totals.append(dict(period_ref=period['period_ref'], totals=t))
            markdown += '| ' + literal(period['period_ref']) + ' | ' + amount(t['expense_amount']) + ' | ' + amount(t['cash_payments']) + ' | ' + amount(t['opening_payables']) + ' / ' + amount(t['closing_payables']) + ' | ' + amount(t['opening_prepaid']) + ' / ' + amount(t['closing_prepaid']) + ' |\n'
        markdown += '\nCada concepto conserva sus saldos entre períodos. Estos pagos ya pertenecen a la caja operativa: no se restan otra vez del retorno. Vigencia y pagos son declaraciones sintéticas; capital, CoC y retorno personal conservan sus pendientes.\n'
    payload = dict(component='T78', purpose='synthetic_current_expense_checked_lifecycle_review', engine_sha256=ENGINE_SHA256,
                   presentation_engine_sha256=PRESENTATION_ENGINE_SHA256, definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
                   bundle_sha256=recovered.bundle_sha256, historical_run_sha256=recovered.run.sha256,
                   registry_source_sha256=hashlib.sha256(registry_raw).hexdigest(), registry_run_sha256=registry_run.sha256,
                   context=p['context'], currency=p['currency'], evaluated_as_of_UTC=as_of, required_source_bindings=required,
                   current_project_return_story=story, current_expense_period_totals=totals,
                   markdown=markdown, markdown_sha256=digest(markdown), state=row['state'], blockers=sorted(set(blockers)),
                   evidence_blockers=r['blockers'], calculation_blockers=row['candidate_calculation_blockers'],
                   historical_calculation_preserved=True, live_expiry_monitor_enabled=False,
                   real_sources_payments_or_professional_approval_authenticated=False, financial_publication_authorized=False,
                   external_decision_pdf_produced=False, decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return CurrentExpenseLifecycleRun(encoded, digest(encoded))
