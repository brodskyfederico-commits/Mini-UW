# Mini-UW: TIR periódica comprobada y salida integrada

T100 resuelve el bloqueo numérico observado en el expediente sintético largo de T99, conservando exactamente sus entradas y presupuestos. Genera una página con intervalo anual de TIR, grupos de caja y todos los años de la ventana. El resultado es del equity agregado del proyecto; no es retorno personal o aprobación. T99 y los hitos anteriores conservan sus resultados y programas originales.

Con las dependencias de referencias instaladas, desde la raíz del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/irr_miniuw_v1.py run \
  templates/miniuw-v1-long-window-case.json --output /tmp/miniuw-tir-comprobada
PYTHONDONTWRITEBYTECODE=1 python tools/irr_miniuw_v1.py audit /tmp/miniuw-tir-comprobada
```

La fuente del caso es la misma que T99:65 puntos mensuales, aporte inicial en marzo2022, compra/obra y otros aportes desde2026, operación/venta en2027. No son seis años de renta. Aportes1.400, cobros778 y neto−622 siguen iguales. El programa anterior excede su límite de tamaño de fracción; el nuevo reduce contenidos positivos entre operaciones polinómicas exactas. No aumenta4.096 bits ni el presupuesto declarado de200.000 operaciones. El método completo, su validación y sus límites están en [T100](technical-implementation-T100.md).

La TIR se presenta como intervalo con extremos exactos en la evidencia y límites porcentuales exteriores en el PDF. No se elige un punto medio. La comparación puntual IRR permanece pendiente, igual que sus criterios vacíos y la decisión. Si hay varias raíces completas se conservan todas; si queda alguna sin resolver, los intervalos anuales actuales se retiran, aunque otra raíz ya esté aislada. La evidencia mantiene el intento parcial.

La anualización requiere frecuencia expresa compatible con la grilla suministrada; no se deduce de las fechas o de la etiqueta «mensual». Sin frecuencia, el caso `templates/miniuw-v1-IRR-frequency-pending-case.json` conserva el cálculo periódico y deja el anual pendiente. Con presupuesto insuficiente, `templates/miniuw-v1-IRR-budget-case.json` mantiene la TIR pendiente y la caja conciliada. No se modifica el dato para lograr una tasa o PASS.

El paquete contiene ocho archivos, incluido exactamente un PDF. `results.json` liga el resultado T100 a su padre T98 y conserva la evidencia numérica anterior en `irr_recalculation`. Esa evidencia incluye ledger compilado, grilla, controles, flujos netos fechados, solver previo/nuevo, anualización y bloqueos. El hash de proyección anterior queda en `parent_current_projection_run_sha256`; el resultado nuevo tiene su propia huella y `current_IRR_solver_result_sha256`.

```python
from pathlib import Path
from miniuw_foundation.irr_checked_artifacts import recover_irr_checked_bundle

proof = recover_irr_checked_bundle(
    Path('/tmp/miniuw-tir-comprobada/execution-evidence.json').read_bytes())
assert proof.run.payload['component'] == 'T100'
assert proof.run.payload['current_project_return_story']['selected_IRR'] is None
```

La API necesita el paquete instalado o `src` en `PYTHONPATH`. La recuperación reproduce primero fuentes y puertas financieras, luego capital/TIR y finalmente la página; no acepta un resultado o PDF sólo porque se hayan recalculado sus hashes. Una fuente vencida retira toda la proyección actual, incluso la TIR nueva. Auditoría de inventario regular exacto, bytes y reproducción completa; reintento idéntico y rechazo de salida distinta/incompleta. Límites de bytes y uso local de un escritor, sin publicación concurrente productiva.

No se han completado las54 correspondencias semánticas originales, las reglas y fuentes financieras reales, capital remanente/CoC sin base o la asignación personal. Los 16 originales, I01/matriz398, criterios vacíos y todos los hitos anteriores permanecen intactos. Sin despliegue, decisiones reales, aprobación profesional o certificación financiera general.

[PDF sintético](review/miniuw-v1-IRR-checked-example/MiniUW_v1_Resumen.pdf) · [Validación reproducida](review/IRR-output-validation-T100.json).
