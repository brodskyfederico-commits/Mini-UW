# T108: operación, saldos y venta hasta el retorno del proyecto

Una entrada local reproduce compra/obra, continuidad de la deuda, NOI/caja y gastos por período, liquidación del seguro y venta. Compila todos los aportes y cobros fechados, EM, TIR por intervalos, detalle anual y normalización explícita del recorrido sintético. El retorno personal, capital/CoC y la validación financiera conservan sus pendientes.

Desde la raíz del repositorio, con Python y `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/settled_miniuw_v1.py run \
  templates/settled-lifecycle-retained-T108.json \
  --output /tmp/miniuw-T108-operacion-venta
PYTHONDONTWRITEBYTECODE=1 python tools/settled_miniuw_v1.py audit /tmp/miniuw-T108-operacion-venta
PYTHONDONTWRITEBYTECODE=1 python tools/check_settled_lifecycle_T108.py
```

El ejemplo directo T77 declara seguro20, pagos operativos5+10 y payable contable5 antes de venta, además del plan nominal independiente. Los5 permanecen expresamente en caja: cierre operativo275, apertura de venta275 y pago5 ya incluido en otros usos de venta. Cobro de venta640, cobros operativos200, aportes1400, cobros totales840 y neto−560. Una normalización de todos los aportes a10 da cobros6 y neto−4; es equity agregado del proyecto, sin reparto personal supuesto. Este control tiene ingresos60/90; no sustituye el caso posterior de renta faseada T83/T95.

La hipótesis `distributed` suministra reparto operativo adicional5 y caja terminal270; venta635 y operación205 conservan cobros totales840, pero cambian las fechas y se recalcula la TIR completa sin escoger un punto. No se genera ese reparto desde el cálculo ni se adopta una hipótesis automáticamente.

Cada saldo contable y cada vínculo de pago se suministran expresamente. El saldo nominal no rellena un payable faltante. Inventarios, identidad económica y continuidad por concepto, pagos/cuotas/fechas, caja libre/restringida y deuda deben conciliar. Un fallo retira todos los importes del resumen/retorno combinado y conserva las fuentes y motivos. Pagos posteriores al corte necesitan otro perfil. Las rutas anteriores conservan su guarda de saldo cero.

El paquete interno contiene tres JSON: fuente completa, resultados y manifiesto. [Ejemplo reproducible](review/miniuw-v1-settled-lifecycle-example/). Recuperación desde fuentes, versiones y repetición completa; rehashear una alteración no la valida. Reintento idéntico verificado y otra salida en otro directorio. No crea otro PDF externo, pago real, servicio o despliegue.

Esta conexión es técnica para el perfil suministrado. Vigencia T46 y salida de una página para esta nueva ruta, integración de todos los perfiles/métricas,54 mapeos, datos/contratos/banco auténticos, aceptación financiera y retorno personal siguen pendientes. Decisión PENDING. [Definición y cobertura T108](technical-implementation-T108.md).
