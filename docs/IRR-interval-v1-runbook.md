# Ensayo de un criterio IRR con todo el intervalo anual

T101 comprueba una condición sintética de TIR sin elegir una tasa intermedia. El deal sigue PENDIENTE: este ensayo de una fila no sustituye los diez criterios, sus escenarios o las otras validaciones requeridas. La plantilla y los casos anteriores conservan sus criterios vacíos; los seis casos nuevos declaran reglas hipotéticas sólo para probar el programa.

Desde la raíz del repositorio, con las dependencias de referencias instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/irr_interval_miniuw_v1.py run \
  templates/miniuw-v1-IRR-condition-band-case.json --output /tmp/miniuw-criterio-irr
PYTHONDONTWRITEBYTECODE=1 python tools/irr_interval_miniuw_v1.py audit /tmp/miniuw-criterio-irr
```

La condición se toma de la fila IRR de la entrada única. Se exige definición `SYNTHETIC-ANNUAL-PERIODIC-IRR-ENCLOSURE-v1`, unidad `fraction`, período `SYNTHETIC-lifecycle:inicio:fin` igual a la ventana actual y fuente explícita, además de ambos operadores y umbrales. Son metadatos de un perfil experimental; no equivalen a aprobación de Lorena. No se convierten porcentajes o períodos automáticamente.

| Estado de la fila | Qué demuestra el ensayo | Deal |
| --- | --- | --- |
| PASS_CONDITION | Todo el intervalo cumple PASS y ninguno de sus valores cumple FAIL | PENDIENTE |
| FAIL_CONDITION | Todo el intervalo cumple FAIL y ninguno de sus valores cumple PASS | PENDIENTE |
| BAND | El intervalo no cumple ninguna de las dos condiciones; revisión profesional pendiente | PENDIENTE |
| CONFLICT | Las regiones PASS/FAIL se solapan, según la regla T11 | PENDIENTE |
| PENDING | Falta fuente/metadato/regla/raíz/anualización, o el intervalo cruza un umbral | PENDIENTE |

La TIR del PDF se muestra como porcentaje; los umbrales mantienen su unidad de entrada, identificada como [fraccion anual] en este perfil. Por ejemplo,−0,2 es−20%, no−0,2%. La comparación usa la fracción exacta.

No se elige una raíz entre varias. Una raíz incompleta o frecuencia ausente impiden la comprobación actual. El cero explícito es un umbral válido. La igualdad se trata con el operador suministrado y con los extremos abiertos/cerrados: no se redondea para decidir. Un cruce de umbral queda pendiente; no se aumenta la precisión o cambia una variable automáticamente.

Los seis archivos `templates/miniuw-v1-IRR-condition-*-case.json` cubren PASS, FAIL, banda, conflicto, presupuesto insuficiente y frecuencia ausente. Los umbrales negativos que aparecen son controles hipotéticos de prueba, no recomendaciones de inversión. Los cuatro primeros conservan los flujos y retornos del caso largo; los otros dos conservan sus bloqueos numéricos T100. No son seis años de renta: el horizonte largo contiene aporte inicial en2022 y operación/venta en2027 bajo datos expresamente ficticios.

`results.json` guarda `IRR_interval_comparison`: criterio, intervalo, relaciones every/none/mixed, bloqueos, punteros y política de bandas. `current_project_return_story`, los criterios/estados puntuales, la caja, las raíces y el screening del padre T100 permanecen iguales. La página única agrega una línea identificada como ensayo, mantiene el encabezado PENDIENTE y liga el resultado al SHA de T101.

```python
from pathlib import Path
from miniuw_foundation.irr_interval_artifacts import recover_irr_interval_bundle

proof = recover_irr_interval_bundle(
    Path('/tmp/miniuw-criterio-irr/execution-evidence.json').read_bytes())
assert proof.run.payload['IRR_interval_comparison']['row_state'] == 'BAND'
assert proof.run.payload['decision'] == 'PENDING'
```

La API requiere el paquete instalado o `src` en `PYTHONPATH`. El paquete local contiene ocho archivos, incluido un único PDF. La recuperación reproduce primero la evidencia portable T100 y después el criterio/política/resultado/página T101; no basta recalcular un hash. Si vence una fuente, se retiran tanto la proyección como la comprobación actuales. Inventario regular exacto y límites de bytes, reintento idéntico verificado, no sobrescritura distinta/incompleta y limpieza del temporal propio ante fallo.

Sin publicación concurrente productiva, despliegue, contacto con Lorena, aprobación o decisiones reales. Las54 correspondencias semánticas originales y las demás puertas financieras conservan sus pendientes. [Alcance T101](technical-implementation-T101.md) · [PDF sintético](review/miniuw-v1-IRR-interval-example/MiniUW_v1_Resumen.pdf) · [Validación reproducida](review/IRR-interval-validation-T101.json).
