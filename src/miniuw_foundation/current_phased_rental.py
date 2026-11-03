"""T84 full-source current supplied availability and month-fraction return review."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .drafts import ValidationError, canonical, digest
from .phased_rental_lifecycle import recover_phased_rental_bundle, parse_phased_lifecycle_manifest
from .phased_rental import parse_phased_rental, DEFINITION
from .expense_checked_lifecycle import recover_expense_checked_bundle
from .current_expense_lifecycle import required_expense_lifecycle_sources
from .evidence_currency import EvidenceCurrencyRun, evaluate_evidence_currency
from .investor_review import _render, literal, amount, ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def required_phased_rental_sources(recovered, bundle_raw):
    if recover_phased_rental_bundle(bundle_raw) != recovered:
        raise ValidationError('recovered rental lifecycle must match exact transport')
    expense = recover_expense_checked_bundle(recovered.expense_raw)
    rows = required_expense_lifecycle_sources(expense, recovered.expense_raw)
    def add(path, raw):
        rows.append(dict(requirement_id=path, source_sha256=hashlib.sha256(raw).hexdigest(), source_locator=path))
    add('/phased/manifest', recovered.manifest_raw)
    add('/transport/phased_rental_bundle', bundle_raw)
    for i, row in enumerate(parse_phased_lifecycle_manifest(recovered.manifest_raw)['periods']):
        cr = row['calendar_source_utf8'].encode('utf-8')
        add('/phased/periods/'+str(i)+'/calendar', cr)
        for j, segment in enumerate(parse_phased_rental(cr)['segments']):
            add('/phased/periods/'+str(i)+'/segments/'+str(j), segment['rental_source_utf8'].encode('utf-8'))
    if len(rows) > 256:
        raise ValidationError('complete rental source inventory exceeds evidence profile budget')
    return rows


@dataclass(frozen=True)
class CurrentPhasedRentalRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def assemble_current_phased_rental(bundle_raw, registry_raw, registry_run, as_of):
    recovered = recover_phased_rental_bundle(bundle_raw)
    p = recovered.run.payload
    if type(registry_run) is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw, as_of) != registry_run:
        raise ValidationError('rental source registry must replay at exact supplied UTC instant')
    r, required = registry_run.payload, required_phased_rental_sources(recovered, bundle_raw)
    blockers, story = [], None
    if sorted(required, key=lambda e:e['requirement_id']) != sorted([e['requirement'] for e in r['requirements']], key=lambda e:e['requirement_id']):
        blockers.append('complete_rental_lifecycle_source_inventory_mismatch')
    if r['context'] != p['context']:
        blockers.append('rental_lifecycle_evidence_context_mismatch')
    if r['state'] != 'current_synthetic_evidence':
        blockers.append('rental_lifecycle_sources_not_current')
    if p['state'] != 'compiled_synthetic_phased_rental_lifecycle':
        blockers.append('rental_lifecycle_calculation_blocked')
    if not blockers:
        inv = recovered.run.investor_run.payload
        story = {k:inv[k] for k in ['currency', 'gross_contributions', 'gross_distributions', 'net_cash_profit',
                                  'equity_multiple', 'cash_by_category', 'cash_horizon', 'normalized_story',
                                  'capital_snapshots', 'annual_cash_receipts', 'periodic_irr', 'annual_irr_roots']}
        story.update(equity_level='aggregate_project_equity', dated_events=inv['events'], upstream_story_blockers=inv['story_blockers'],
                     selected_IRR=None, risk_observations=json.loads(p['cash_risk_run']['payload_json'])['metrics'],
                     personal_investor_return=None, decision='PENDING')
    row = dict(case_id='Disponibilidad por tramos, obra, operación y venta: ejemplo sintético',
               state='current_synthetic_phased_rental_lifecycle_at_declared_time' if story is not None else 'PENDING',
               current_matched_case=None if story is None else dict(candidate_project_return_story=story),
               blockers=blockers, comparison_blockers=[], reference_evidence_blockers=[], candidate_evidence_blockers=r['blockers'],
               reference_calculation_blockers=[], candidate_calculation_blockers=p['blockers'] + p['expense_lifecycle_blockers'],
               reference_original_cost_blockers=[], candidate_original_cost_blockers=[])
    markdown = _render(dict(evaluated_as_of_UTC=as_of, blockers=[], case_rows=[row]))
    segments = capacities = expense_totals = None
    if story is not None:
        segments, capacities, expense_totals = [], [], []
        markdown += '\n## Disponibilidad y fracción suministradas\n\n| Inicio / fin excluido | Disponibles | Fracción de mes | Potencial | Pérdida | Concesión | Efectiva |\n|---|---:|---:|---:|---:|---:|---:|\n'
        for period in p['periods']:
            calendar = json.loads(period['calendar_run']['payload_json'])
            capacities.append(dict(period_ref=period['period_ref'], capacity=calendar['capacity']))
            for segment in calendar['segments']:
                a = segment['amounts']
                available = json.loads(segment['reference_rental_run']['payload_json'])['unit_total']
                segments.append(dict(period_ref=period['period_ref'], segment_id=segment['segment_id'],
                                     start_date=segment['start_date'], end_date=segment['end_date'], available_units=available,
                                     proration_fraction=segment['proration_fraction'], amounts=a))
                markdown += '| ' + literal(segment['start_date']) + ' / ' + literal(segment['end_date']) + ' | ' + amount(available) + ' | ' + amount(segment['proration_fraction']) + ' | ' + ' | '.join(amount(a[k]) for k in ['gross_potential_rent', 'vacancy_loss', 'concession_loss', 'effective_rent']) + ' |\n'
        markdown += '\nDisponibilidad y fracción son datos de prueba, no entrega, ocupación, contrato, convención por días o cobro acreditado. No se certifica liquidez intraperíodo.\n'
        markdown += '\n## Gastos y pagos ya incluidos en la caja\n\n| Período | Gasto devengado | Pago operativo |\n|---|---:|---:|\n'
        for period in recover_expense_checked_bundle(recovered.expense_raw).run.payload['periods']:
            t = json.loads(period['detail_run']['payload_json'])['totals']
            expense_totals.append(dict(period_ref=period['period_ref'], totals=t))
            markdown += '| ' + literal(period['period_ref']) + ' | ' + amount(t['expense_amount']) + ' | ' + amount(t['cash_payments']) + ' |\n'
        markdown += '\nRentas y gastos se vinculan a la misma caja; no se cuentan nuevamente como cobros o pagos del inversor. CoC, capital/equity y retorno personal conservan sus pendientes.\n'
    payload = dict(component='T84', purpose='synthetic_current_phased_rental_and_full_cash_return', engine_sha256=ENGINE_SHA256,
                   presentation_engine_sha256=PRESENTATION_ENGINE_SHA256, definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
                   bundle_sha256=recovered.bundle_sha256, historical_run_sha256=recovered.run.sha256,
                   registry_source_sha256=hashlib.sha256(registry_raw).hexdigest(), registry_run_sha256=registry_run.sha256,
                   context=p['context'], currency=p['currency'], evaluated_as_of_UTC=as_of, required_source_bindings=required,
                   current_project_return_story=story, current_phased_segments=segments, current_capacity_inventories=capacities, current_expense_period_totals=expense_totals,
                   markdown=markdown, markdown_sha256=digest(markdown), state=row['state'], blockers=sorted(set(blockers)),
                   evidence_blockers=r['blockers'], calculation_blockers=row['candidate_calculation_blockers'],
                   historical_calculation_preserved=True, live_expiry_monitor_enabled=False,
                   actual_delivery_proration_contract_collection_or_review_authenticated=False, financial_publication_authorized=False,
                   external_decision_pdf_produced=False, decision='PENDING', real_decisions_enabled=False, production_authorized=False)
    encoded = canonical(payload)
    return CurrentPhasedRentalRun(encoded, digest(encoded))
