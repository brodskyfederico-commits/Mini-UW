# Seguro y caja del cierre T107

Vínculo local entre tres fuentes sintéticas: plan nominal, caja bruta de venta y pagos del seguro incluidos en `other_cash_uses`. Comprueba su identidad por pago/cuota/importe/fecha y conserva el residual calculado por el cierre, sin descontar el seguro otra vez. La integración de operación/tenencia, contabilidad y retorno de toda la vida sigue pendiente.

Desde la raíz del repositorio con Python y `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/insurance_terminal_miniuw_v1.py run \
  templates/insurance-terminal-on-cut-plan-T107.json \
  templates/insurance-terminal-on-cut-closing-T107.json \
  templates/insurance-terminal-on-cut-binding-T107.json \
  --output /tmp/miniuw-T107-seguro-cierre
PYTHONDONTWRITEBYTECODE=1 python tools/insurance_terminal_miniuw_v1.py audit /tmp/miniuw-T107-seguro-cierre
PYTHONDONTWRITEBYTECODE=1 python tools/check_insurance_terminal_T107.py
```

Ejemplo explícito: seguro20, pagos previstos15 antes del corte y5 en el corte de julio. La fuente de venta declara100 brutos y5 en otros usos, sin otros movimientos. El residual sigue siendo95. No se transforma en90 al vincular el seguro. Otro control declara seguro prepagado, otros usos0 y residual100; son hipótesis diferentes, no valorización o consejo de inversión.

Si faltan la hipótesis de aporte necesaria, datos/fuentes/vínculos o inventarios completos, se retiran todos los importes derivados del vínculo. Un pago de agosto no se adelanta al cierre de julio. Cero conocido conserva su fila y no equivale a importe faltante. El perfil declara que todos los otros usos del cierre corresponden exclusivamente a los pagos de este seguro en el corte; otras clasificaciones o fechas necesitan otro perfil.

El paquete contiene cinco JSON, recuperables desde las tres fuentes con reproducción completa; [ejemplo interno](review/miniuw-v1-insurance-terminal-example/). Reintento idéntico verificado, rechazo de otra salida y límites de archivos/versiones. No hay pago bancario, aprobación de payable, inferencia de comprador/pagador, nuevo PDF externo, publicación productiva o despliegue. [Definición y pendientes T107](technical-implementation-T107.md).
