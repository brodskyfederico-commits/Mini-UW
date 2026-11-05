# Seguro con liquidación posterior al corte T106

Conciliación matemática de costo/gasto nominal, vencimientos y pagos previstos independientes. Hace visible lo que no estaba liquidado antes del corte. Es un productor sintético separado: la conexión con caja de venta/retorno y la validación financiera siguen pendientes.

Desde la raíz del repositorio, Python y dependencias de `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/deferred_insurance_miniuw_v1.py run \
  templates/insurance-settlement-deferred-T106.json \
  --output /tmp/miniuw-T106-seguro
PYTHONDONTWRITEBYTECODE=1 python tools/deferred_insurance_miniuw_v1.py audit /tmp/miniuw-T106-seguro
PYTHONDONTWRITEBYTECODE=1 python tools/check_deferred_insurance_T106.py
```

El paquete interno contiene fuente, resultados y manifiesto: tres JSON. Ejemplo en `docs/review/miniuw-v1-deferred-insurance-example/`. Recupera desde la fuente y repite el cálculo completo; rehashear una alteración no la valida. Reintento idéntico verificado y otra salida en otro directorio, sin sustituir una corrida distinta. No genera otro PDF ni publica, mueve caja o despliega servicios.

Ejemplo: costo20, gasto10+10 por fracciones suministradas, cuotas/pagos5 en marzo,10 en junio y5 en agosto. Antes del corte de julio se prevén15 pagados; quedan5 nominales de la hipótesis por liquidar. La salida exige otra fuente de liquidación: no descuenta5 automáticamente en venta, crea financiación o traslada obligación al comprador. El caso completo previo conserva sus cifras y guardas.

Un vencimiento futuro puede estar prepagado, y un vencimiento anterior puede tener pago previsto posterior. Se contrastan por ID, importe y fecha separados, sin compensar diferencias entre cuotas. La fecha del corte se trata antes de todos los eventos de ese día: un pago en el corte no pertenece a la caja anterior. Un cero requiere dato/inventarios completos; un importe faltante deja todo lo derivado pendiente.

El perfil exige seguro, ventana completa, corte al final, ausencia declarada de apertura/créditos y ajustes adicionales bajo una hipótesis sintética. Fechas y fracciones no se infieren de días, términos legales o pagos bancarios. Apertura, pólizas superpuestas/complementarias, penalidades, reembolsos, saldos contables e integración con cierre/retorno necesitan otros contratos y evidencia. No es una aprobación de payable legal o pago real; decisión PENDING. [Definición T106](technical-implementation-T106.md).
