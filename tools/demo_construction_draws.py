"""Reproduce proposed staged debt cash, blocked funding and explicit-time review."""
from pathlib import Path
import copy,json,hashlib
from construction_demo_support import sources,build,raw,money
from miniuw_foundation.construction_bundle import export_construction_bundle,recover_construction_bundle
from miniuw_foundation.current_construction_cash import required_construction_sources,assemble_current_construction_cash
from miniuw_foundation.evidence_currency import evaluate_evidence_currency

ROOT=Path(__file__).resolve().parents[1]
AT='2027-01-01T12:00:00Z'


def registry(recovered,bundle):
    requirements=required_construction_sources(recovered,bundle)
    return dict(schema='miniuw.synthetic-evidence-currency.v1',context=recovered.run.payload['context'],inventory_declared_complete=True,
        inventory_basis_ref='SYNTHETIC-complete-staged-construction-transport-not-original-documents',requirements=requirements,
        evidence=[dict(evidence_id='SYNTHETIC-staged-evidence-'+str(i),**r,issued_at='2026-10-01T00:00:00Z',valid_from='2026-10-01T00:00:00Z',valid_until='2027-01-02T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-express-software-validity-not-professional-review')for i,r in enumerate(requirements)])


def main():
    case=build(sources());assert case[-1].payload['state']=='reconciled_synthetic_staged_preopening_cash'
    bundle=export_construction_bundle(*case);recovered=recover_construction_bundle(bundle);assert recovered.run==case[-1]
    (ROOT/'templates/synthetic-construction-cash-bundle-example.json').write_bytes(bundle)
    declared=registry(recovered,bundle);path=ROOT/'templates/synthetic-construction-evidence-example.json';path.write_text(json.dumps(declared,ensure_ascii=False,indent=2)+'\n');source=path.read_bytes()
    current=assemble_current_construction_cash(bundle,source,evaluate_evidence_currency(source,AT),AT)
    expired=copy.deepcopy(declared);next(e for e in expired['evidence']if e['requirement_id']=='/construction/loans/0')['valid_until']=AT;expired_raw=raw(expired)
    pending=assemble_current_construction_cash(bundle,expired_raw,evaluate_evidence_currency(expired_raw,AT),AT);assert pending.payload['current_construction_summary']is None
    deficit=sources();deficit['draft']['events'][0]['amount']=money(200);deficit['draft']['events'][2]['amount']=money(1200);blocked=build(deficit)
    assert blocked[-1].payload['state']=='blocked'and blocked[-1].preopening_run.payload['exportable_equity_movements']is None
    assert recover_construction_bundle(export_construction_bundle(*blocked)).run==blocked[-1]
    limit=sources();limit['loans'][0]['principal_commitment']=money(200);over=build(limit);assert over[-1].compiled_raw is None
    assert recover_construction_bundle(export_construction_bundle(*over)).run==over[-1]
    for path,result in [('docs/review/Revision_Vigente_Deuda_Obra_T71.md',current),('docs/review/Revision_Pendiente_Deuda_Obra_T71.md',pending)]:(ROOT/path).write_text(result.payload['markdown'])
    guide='''# Intereses de obra por desembolsos y su efecto en caja

El ejemplo sintético calcula deuda e intereses antes de la operación a partir de movimientos expresos. Se separan compromiso, disponible declarado, draws acumulados y saldo; no se generan préstamos ni aportes para cerrar un déficit. La decisión continúa PENDING.

| Intervalo | Draw al inicio | Principal expuesto | Factor del intervalo | Interés al final | Fee al inicio | Repago al final | Principal final |
|---|---:|---:|---:|---:|---:|---:|---:|
| Octubre a noviembre de 2026 | 100 | 100 | 1% | 1 | 2 | 0 | 100 |
| Noviembre a diciembre de 2026 | 100 | 200 | 1% | 2 | 2 | 50 | 150 |
| Diciembre de 2026 a enero de 2027 | 50 | 200 | 1% | 2 | 1 | 0 | 200 |

Todos los importes son USD de prueba. El 1% es el factor suministrado para cada intervalo; no es una tasa anual dividida por doce. El fee suministrado es 2% de cada draw bruto. El interés se calcula sobre el saldo previo más el draw inicial, antes del repago final, y se propone pagar al final. Los intereses y fees no se capitalizan en este perfil.

El compromiso no revolvente declarado es 300, los draws brutos suman 250, los repagos 50 y el saldo final es 200. Repagar 50 no restituye capacidad para nuevos draws. Además, cada draw debe caber en el disponible expresamente declarado para ese momento; el cálculo no acredita disponibilidad bancaria real.

La conexión rellena sólo los eventos de deuda vacíos de la caja previa. El aporte inicial de equity es 1.000 y el adicional 400; compra/obra/costos blandos suman 1.000. La identidad del ejemplo es: 1.400 de equity + 250 de draws = 1.000 de usos + 50 de repago + 5 de interés + 5 de fees + 590 de caja libre final. La caja restringida termina en cero.

Un caso separado mantiene el mismo total de equity pero aporta demasiado tarde: queda bloqueado por el déficit inicial, aunque cierre después con fondos. Otro excede el compromiso no revolvente y no se compila. Ambos se recuperan conservando sus bloqueos. Una fuente vencida retira las cifras de la vista actual y conserva la historia.

Todavía no se conectan estos préstamos multidesembolso con un contrato operativo/refi/venta: los perfiles anteriores exigían draw único y permanecen intactos. No se calcula el retorno final ni se presenta EM/IRR desde un alcance intermedio. CoC/capital/equity retenido, base de activos/TDC, convenciones bancarias reales, capitalización, pagos y revisión profesional siguen pendientes. Sin despliegue ni decisiones reales.

[Vista interna actual](Revision_Vigente_Deuda_Obra_T71.md) · [Vista pendiente](Revision_Pendiente_Deuda_Obra_T71.md) · [Evidencia reproducible](synthetic-construction-cash-demo.json) · [Contrato de cálculo y vínculo](../technical-implementation-T68-T69.md).
'''
    (ROOT/'docs/review/Intereses_Obra_y_Caja_T68_T71.md').write_text(guide)
    return dict(purpose='synthetic_staged_construction_interest_cash_recovery_and_evidence',components=['T68','T69','T70','T71'],
        loan_run_sha256s=[e.run.sha256 for e in case[0]],cash_run_sha256=case[-1].sha256,bundle_sha256=hashlib.sha256(bundle).hexdigest(),full_recovery=True,
        registry_source_sha256=hashlib.sha256(source).hexdigest(),required_source_bindings=len(current.payload['required_source_bindings']),evaluated_as_of_UTC=AT,
        current_run_sha256=current.sha256,current_report_sha256=current.payload['markdown_sha256'],pending_report_sha256=pending.payload['markdown_sha256'],guide_sha256=hashlib.sha256(guide.encode()).hexdigest(),expired_registry_json=expired_raw.decode(),
        staged_loan_totals=[e.run.payload['totals']for e in case[0]],preopening_totals=case[-1].preopening_run.payload['totals'],terminal_balances=case[-1].preopening_run.payload['date_close_balances'][-1],
        late_equity_case=dict(state=blocked[-1].payload['state'],cash_blockers=blocked[-1].payload['cash_blockers'],automatic_funding_generated=False,recovered_still_blocked=True),
        exceeded_commitment_case=dict(state=over[-1].payload['state'],loan_blockers=over[-1].payload['loan_blockers'],cash_compiled=False,recovered_still_blocked=True),
        expired_current_summary=pending.payload['current_construction_summary'],expired_evidence_blockers=pending.payload['evidence_blockers'],whole_project_return_connected=False,decision='PENDING',production_authorized=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
