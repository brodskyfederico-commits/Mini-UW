# Hipótesis de reparto de caja T104

Con fracciones explícitamente suministradas, calcula cuánto aporta y cobra cada participante ficticio y cuándo. Es una hipótesis sobre cada movimiento bruto del proyecto, no un retorno personal verificado o una asignación LP/JV aprobada. El estado del deal y del retorno personal real permanece PENDING.

Desde la raíz del repositorio, Python y dependencias de `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/cash_participation_miniuw_v1.py run \
  templates/miniuw-v1-policy-renewal-case.json \
  templates/worksheet-case-matched-T103.xlsx \
  --binding templates/worksheet-case-matched-T103.json \
  --terms templates/cash-participation-quarter-T104.json \
  --output /tmp/miniuw-T104-reparto
PYTHONDONTWRITEBYTECODE=1 python tools/cash_participation_miniuw_v1.py audit /tmp/miniuw-T104-reparto
PYTHONDONTWRITEBYTECODE=1 python tools/check_cash_participation_T104.py
```

El paquete interno contiene términos, resultados completos, evidencia recuperable y manifiesto: cuatro JSON. El ejemplo está en `docs/review/miniuw-v1-cash-participation-example/`. No genera otro PDF externo ni modifica la página T103. La orden opera localmente; no publica, selecciona alternativas o despliega servicios. Otra salida distinta exige otro directorio; el reintento idéntico se verifica.

Cada fracción se aplica a todos los aportes iniciales/adicionales/cash-in y a todos los cobros de operación/refi/venta/otros. Se conserva fecha, clasificación y cero; la suma de participantes debe ser exactamente1. No se elige un porcentaje a partir del monto inicial, no se completa un residual, no se compensan brutos ni se redondea a centavos. El perfil exige declarar inventario completo y ausencia de fees/promote/impuestos/ajustes prioritarios adicionales a nivel participante; los costos e impuestos del proyecto ya forman parte de su caja original; otros esquemas requieren otro contrato y permanecen pendientes.

En el ensayo1/4+3/4, la primera hipótesis aporta250 inicialmente y100 después, y cobra50 de operación más144,50 de venta. Sus totales son350 aportados,194,50 cobrados y−155,50 netos, con las fechas del proyecto conservadas. No significa invertir350 hoy ni acredita derecho a esos pagos. Los tercios conservan racionales exactos; fracción0 conserva caja0 pero múltiplo/TIR indefinidos. Una fracción faltante retira todo el reparto.

La TIR se recalcula desde cada calendario neto con los controles T100 originales: todas las raíces/intervalos, anualización sólo compatible, sin punto elegido ni criterio aplicado. Un límite numérico deja su TIR pendiente y conserva la caja conciliada; una fuente padre bloqueada retira el reparto entero incluso tras recuperar la evidencia.

Capital/equity retenido, CoC, contratos auténticos, pagos reales, retorno personal verificado y las54 correspondencias semánticas originales mantienen sus pendientes. Los términos de ejemplo son controles de software, no una política o propuesta de inversión. [Definición T104](technical-implementation-T104.md).
