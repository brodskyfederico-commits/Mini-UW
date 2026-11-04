# Mini-UW sintético: resumen completo en una página

T99 permite resumir hasta256 movimientos y doce años de caja en una sola página. Conserva el resultado T98, la vista de capital controlada y la cadena financiera actual; no añade decisiones, fórmulas financieras o datos reales. Los CLI anteriores y sus ejemplos siguen disponibles como versiones históricas.

Desde la raíz del repositorio, con las dependencias de referencias instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/long_miniuw_v1.py run \
  templates/miniuw-v1-long-window-case.json --output /tmp/miniuw-resumen-largo
PYTHONDONTWRITEBYTECODE=1 python tools/long_miniuw_v1.py audit /tmp/miniuw-resumen-largo
```

La página conserva las siete categorías de caja: aporte inicial, adicional, cash-in de refi, cobro neto de refi, operativo, venta y otros cobros. Cada fila muestra el total y la primera/última fecha, con la cantidad de movimientos declarados. Los ceros siguen en el inventario. Un concepto sin movimientos se identifica expresamente; un rango no significa periodicidad o un único cobro. Las fechas e importes de cada movimiento se consultan en `results.json`, `current_project_return_story.dated_events`; los índices que componen cada resumen están en `report-manifest.json`, `event_groups`.

La caja anual incluye todos los años, aunque no tengan movimientos: A son aportes brutos, C cobros brutos, N cobros menos aportes y O sólo cobros operativos. CoC se expresa como fracción y queda pendiente sin base compatible. La ventana anual no acredita un año operativo completo. No se recortan años ni se agrega una segunda página cuando se excede el presupuesto: la generación queda bloqueada con una explicación.

La referencia normalizada conserva su base explícita y los aportes/cobros escalados del proyecto. No atribuye esos valores a una persona. Capital y valor retenido se presentan separados de caja; el último corte pendiente no se sustituye por otro anterior ni se deriva del déficit. La TIR mantiene raíces/intervalos y fechas del resultado, sin elegir un punto para el comparador.

El ejemplo de seis años representa aporte inicial en marzo2022, otros aportes y compra/obra desde2026, operación y venta en2027. No representa seis años de renta. Los ocho aportes adicionales nuevos son ceros hipotéticos expresos: los totales siguen1.400 aportados,778 cobrados y−622 de caja. Las nuevas fechas afectan la TIR, que se recalcula. Los diez criterios siguen vacíos y la decisión PENDING.

En este expediente largo, el solver existente termina con `status: incomplete_synthetic` y `root_classification: arithmetic_budget_exhausted`: no completa las raíces dentro de su límite aritmético. La TIR permanece pendiente, sin sustituirla por la tasa del caso corto ni estimarla a partir del EM. El formato de seis años funciona; resolver ese polinomio queda como trabajo numérico posterior. El presupuesto numérico y el programa financiero no se modifican para obtener una tasa.

La carpeta contiene ocho archivos: caso, resultado T98, evidencia portable, PDF, manifiesto, auditoría técnica, revisión interna e inventario. `audit` reproduce fuentes/resultado/resumen/PDF y compara todos los bytes. Un reintento idéntico verifica la carpeta existente; una salida distinta o incompleta requiere otra carpeta. La prueba portable usa primero la evidencia financiera T95 y reconstruye T98/T99, incluso cuando las fuentes están bloqueadas. No necesita renderizar la página anterior.

```python
from pathlib import Path
from miniuw_foundation.long_horizon_artifacts import recover_long_horizon_bundle

proof = recover_long_horizon_bundle(
    Path('/tmp/miniuw-resumen-largo/execution-evidence.json').read_bytes())
assert proof.report.manifest['component'] == 'T99'
assert proof.run.payload['component'] == 'T98'
```

La API requiere el paquete instalado o `src` en `PYTHONPATH`. El inventario, los límites de bytes y las versiones se verifican antes de aceptar la recuperación. No se renuevan fuentes ni se autentican políticas, pagos o revisiones. La operación es local para un escritor; no es publicación productiva ni respaldo de runtime/infraestructura. Las54 correspondencias semánticas de la hoja original, el retorno personal y la aceptación financiera mantienen sus pendientes.

[Ejemplo de una página](review/miniuw-v1-long-output-example/MiniUW_v1_Resumen.pdf) · [Validación](review/long-output-validation-T99.json) · [Alcance](technical-implementation-T99.md).
