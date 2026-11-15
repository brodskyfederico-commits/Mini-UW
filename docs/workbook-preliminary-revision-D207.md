# Si invierto USD 10, ¿cuánto cobro y cuándo?

Para un expediente nuevo la respuesta se mantiene **PENDING** hasta poder cotejar su evidencia. La referencia sintética D206 permite ensayar la revisión completa. Base aporta USD 6,22 adicionales y cobra USD 29,14 hasta el 30/12/2028. Downside aporta USD 8,01 adicionales y cobra USD 9,06 hasta esa fecha, con USD 8,95 sin recuperar. El informe muestra cada movimiento por fecha. [Ejemplo sintético por USD 10](review/MiniUW_Preliminar_Respaldo_PDF_D206.pdf)

## Cotejo por dato

Cada fila vincula el expediente, la revisión, el escenario y el campo con la planilla y la evidencia aplicable. Conserva la huella y versión de cada archivo, su ubicación exacta, los literales leídos, el valor normalizado, la unidad, la base del cálculo, el período, la fecha de corte y el responsable. La confirmación del respaldo se registra con el rol y la revisión correspondientes. Los datos comunes sólo se comparten si la misma evidencia declara que aplica a ambos escenarios.

| Evidencia | Qué se coteja | Cálculo o salida que depende del dato |
| --- | --- | --- |
| Plano A101 y cuadro A601 | Conteos por tipo, versión y unidades elegibles para renta, gastos y reservas. | Renta potencial, gastos por unidad, NOI, reservas, capacidad y venta. |
| Adquisición y cotización de obra | Precio y cierre, costo base y alcance, estacionamientos, contingencia y costos blandos. | Usos, costo elegible, desembolsos, intereses y aportes. Si cambia el aporte inicial verificado, cambia el factor de todos los flujos por USD 10. |
| Rentas y gastos | Importe por tipo, vacancia, otros ingresos, gastos, seguro, reposición y crecimiento con su período. | NOI operativo, NOI de valoración y banco, capacidad y NOI de salida. |
| Calendario | Compra, desembolsos, fin de obra, estabilización, refinanciación y fecha de venta. | Intereses, vigencia de deuda, padrones fiscales aplicables y fechas de los aportes y cobros. |
| Crédito de obra | Límites, disponibilidad por etapa, tasa, comisión y vencimiento. | Desembolsos y aportes, costo de intereses y saldo que se liquida al refinanciar. |
| Crédito permanente | Principal, LTV, DSCR, debt yield cuando aplica, tasa, amortización, vencimiento, comisiones y reservas. | Capacidad por el menor límite, caja al refinanciar, servicio, saldo al vender y cobros. |
| Respaldo fiscal | Clasificación, padrones, millage escolar y no escolar, tasaciones y fecha de retasación. | M2, NOI por ventana, capacidad y cobros. El NOI de salida usa el padrón del comprador cuando corresponde. |
| Supuesto de salida | Cap y su base de NOI, costos y disposición de reservas. | Precio de venta, costos, cobro neto, múltiplo y saldo sin recuperar. |

El cotejo conserva el blanco como faltante y el cero explícito como valor. Una unidad, base o período incompatible deja la fila sin confirmar. Si dos respaldos vigentes discrepan, se conservan ambas lecturas y se registra el motivo de la resolución, su fuente y quién la confirma. La huella acredita la identidad de los bytes. La publicación, fecha, vigencia y aplicabilidad de la fuente se verifican por separado. [Contrato de evidencias](evidence-locator-contract.md)

## Qué pasa cuando se corrige una fuente

1. **Abrir una revisión.** Guardar la anterior con sus documentos, resultados y huellas. Registrar el campo cambiado, el valor anterior y nuevo, la ubicación en cada respaldo y los escenarios alcanzados.
2. **Volver a cotejar los respaldos.** La planilla y la fuente deben seguir concordando. Registrar por separado las diferencias y los campos requeridos sin respaldo. Cuando el cambio afecta a ambos escenarios, volver a verificar ambos.
3. **Recalcular el expediente.** Repetir la corrida completa por disponibilidad de la implementación actual. Usar las dependencias de la tabla para verificar qué cifras debieron cambiar. Comparar también los importes y fechas independientes del cambio.
4. **Cotejar la caja.** Reconstruir los movimientos en USD del proyecto desde las fuentes. Escalar cada movimiento bruto por `10 ÷ aporte inicial verificado` del escenario. Cotejar fecha, signo y categoría, incluso si coinciden aportes y cobros en un mismo día. Conciliar refi, operación, venta, aportes adicionales, múltiplo y saldo sin recuperar. [Método de conciliación independiente](workbook-independent-reconciliation-D179.md)
5. **Actualizar el ranking.** Si hay un dato obligatorio faltante o discrepante, la caja afectada queda PENDING y el expediente sale del ranking. Los demás expedientes comparables y la caja verificable del escenario independiente siguen visibles. Al resolver la causa y repetir la corrida, el caso puede volver a PRELIMINAR. El dictamen formal permanece PENDING.

## Casos para verificar el diseño

| Cambio | Resultado esperado | Evidencia disponible |
| --- | --- | --- |
| Quitar A601 o el crédito de obra | Downside PENDING, fuera del ranking. Base y el comparador conservan sus flujos. | Verificado con PDF sintéticos en D206. |
| Declarar distinto DSCR en banco y planilla | PENDING con página y celda. Se retira la caja de Downside. | Verificado en D206. |
| Aumentar el millage no escolar Downside en un PDF registrado | Se recalculan el NOI bancario, los cobros y el múltiplo de Downside. | Verificado en D206 con la tasa de prueba. |
| Corregir un aporte inicial en una revisión completa | Volver a conciliar fuentes y usos. Recalcular el factor por USD 10 de todos los eventos del escenario y cotejar montos antes de redondear. | Verificado en D213. Se cambió C32 en Downside, de USD 100.000 a USD 140.000, y el aporte inicial del proyecto pasó de USD 105.000 a USD 147.000. La caja bruta posterior se conservó y los once movimientos se cotejaron por fecha, tipo e importe. |
| Reponer exactamente el respaldo original | El paquete vuelve a reproducirse byte a byte en las mismas condiciones. | Verificado en D205 y D206. |
| Restituir evidencia con valores nuevos | Guardar ambas revisiones, demostrar qué diferencias se explican por el cambio y recalcular el ranking vigente. | Procedimiento definido en D207. D206 prueba un cambio fiscal. D213 vuelve a calcular el ranking ante el nuevo aporte inicial, conserva la revisión anterior y verifica que las discrepancias o un aporte cero dejen el caso fuera del ranking. |

La tabla describe el flujo de revisión diseñado en D207. La corrida D206 acepta los PDF de tablas sintéticas y deja trazas por página y línea. La vinculación de documentos con formatos reales, la revisión de sus términos aplicables y la comparación financiera del primer proyecto se harán cuando exista un expediente autorizado. El PRELIMINAR mantiene el dictamen formal PENDING.

## Vigencia tras una corrección

La auditoría archivada reproduce el expediente con sus propios respaldos y devuelve el resultado de esa revisión. Para consultar el ranking vigente, indicá en `audit` el directorio externo que se designó como revisión vigente. La comparación verifica el inventario completo y las huellas de sus archivos. Un inventario distinto, una fuente ausente o alterada, o un directorio de fuentes dentro del propio expediente deja el cotejo PENDING, con ranking vacío y sin huella de PDF vigente.

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pdf-D206 --current-source templates/preliminary-pilot-D206
```

D214 aplica el cotejo a las dos revisiones sintéticas de C32. La revisión original conserva su ranking histórico. Frente al inventario corregido, el ranking original queda retirado de la consulta vigente. El paquete corregido muestra el orden recalculado y conserva sus flujos por USD 10. La designación es explícita y corresponde al piloto sintético. El dictamen formal sigue PENDING.

## Entrega del PDF vigente

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py deliver /tmp/miniuw-pdf-D206 /tmp/MiniUW_PRELIMINAR_Vigente.pdf --current-source templates/preliminary-pilot-D206
```

`deliver` reproduce el paquete, verifica el inventario designado inmediatamente antes de la entrega y escribe el PDF auditado de una página en un destino nuevo. El destino queda fuera del paquete y de sus fuentes. Si la revisión es anterior, el inventario cambió durante el cotejo o el caso de foco tiene un escenario PENDING, devuelve `delivery=PENDING` con código 2 y el destino no se crea. Un paquete alterado o un destino ocupado genera un error. Una entrega identifica el PDF, el inventario y el ranking de la revisión en ese momento. El archivo histórico sigue disponible mediante `audit`.

D215 coteja los aportes y cobros fechados de Base y Downside antes de redondear y verifica su presentación en el PDF entregado. Con la revisión sintética de C32, Downside aporta USD 5,72 adicionales, cobra USD 6,47 hasta el 30/12/2028 y queda con USD 9,25 sin recuperar por USD 10 iniciales. El dictamen formal sigue PENDING.
