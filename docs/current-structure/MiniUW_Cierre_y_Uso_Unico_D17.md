# Caja reservas y obligaciones en el cobro final de venta

El cobro final hacia el equity debe incluir una sola vez la caja disponible y descontar una sola vez cada pago del cierre. Esta conciliación clasifica todos los importes del cierre suministrado en las dos versiones sintéticas existentes, conserva los saldos y obligaciones por separado y enlaza el residual con el cobro de venta del [calendario de retorno](MiniUW_Calendario_y_Retorno_D16.md).

La referencia conserva un cobro neto de 578 y la versión comparada uno de 576, en USD ficticios del proyecto. Las fuentes y los resultados no se modifican. Las comprobaciones siguientes documentan su consistencia dentro de ese perfil; no representan correcciones de fallos reales ni nuevas reglas financieras.

## De la caja de operación al cobro de venta

| Concepto del cierre | Referencia | Comparada | Tratamiento en el residual |
| --- | ---: | ---: | --- |
| Caja libre que llega de operación | 213 | 211 | Se incorpora una vez como saldo disponible. |
| Cobro bruto de venta | 400 | 400 | Se incorpora una vez como proceeds declarados. |
| Reserva que se libera | 100 | 100 | Pasa de restringida a libre una vez. |
| Otros orígenes de caja | 0 | 0 | Se conserva el cero declarado. |
| Principal pagado al cierre | 100 | 100 | Se descuenta una vez. |
| Fees de deuda pagados al cierre | 10 | 10 | Se descuentan una vez, separados del principal. |
| Costos de cierre pagados | 20 | 20 | Se descuentan una vez. |
| Otros usos del cierre | 5 | 5 | Incluyen el pago de seguro al corte. |
| Intereses y otros pagos de deuda | 0 | 0 | Se conservan sus partidas separadas. |
| Nueva reserva y caja libre retenida | 0 | 0 | Se conservan sus bases distintas y ceros. |
| Cobro neto hacia el equity | 578 | 576 | Se exporta como distribución de venta. |

La [matriz de 24 términos](MiniUW_Terminos_24_D17.csv) desglosa doce términos por versión, incluidos todos los ceros, con signo, fuente y referencia al inventario. Su orden es algebraico y de presentación: no acredita prioridad de pagos, liquidez intradía o disponibilidad efectiva de fondos.

Los 578 o 576 ya incluyen la caja libre y la reserva liberada. Esos saldos no se suman otra vez al retorno. El aporte de cierre es cero dentro de este ejemplo con residual positivo; esa observación no completa un faltante ni asegura financiación para otro perfil.

## Qué es movimiento qué es saldo y qué es obligación

La [matriz de 38 declaraciones](MiniUW_Inventario_38_D17.csv) conserva 19 declaraciones monetarias de cada cierre: diez campos de caja/saldo, cuatro obligaciones de deuda, cuatro pagos de deuda y una declaración de valoración vacía. Cada una mantiene su moneda, fecha, base, referencia literal y ubicación exacta mediante archivo, hash y punteros.

Doce declaraciones intervienen en el residual libre. Las siete restantes conservan funciones diferentes: dos saldos restringidos, cuatro obligaciones que respaldan los pagos y la valoración vacía. Quedar fuera de ese residual no vuelve irrelevante una declaración: los saldos restringidos intervienen en su propia conservación y las obligaciones se cotejan con los pagos.

La valoración permanece vacía y separada de caja. No se interpreta como cero ni se reemplaza por el precio bruto de venta. La clasificación procede del contrato y del perfil declarado; una palabra dentro de una referencia literal de fuente no cambia un cierre de venta en refinanciación.

El inventario es exhaustivo respecto de los campos suministrados en estos cierres. No certifica que un cierre real carezca de otros costos, impuestos, acreedores o condiciones. Las declaraciones de inventario completo y los hashes conservan su alcance sintético.

## Reserva y seguro sin un segundo cómputo

La reserva empieza en 100, libera 100, no recibe una nueva reserva y termina en cero. En la cuenta libre se incluye la liberación; en la conservación total se incluyen los saldos restringidos inicial y final. Sumar además el saldo restringido inicial dentro del residual libre contaría el mismo dinero dos veces.

El seguro tiene payable de 5 antes del corte y cero después, con prepaid cero a ambos lados. El pago suministrado al corte es 5. Se cotejan su ID, cuota, fecha e importe con el plan y con el binding de cierre; el binding vincula los bytes exactos de las fuentes de plan y venta.

La hipótesis expresa de este perfil dice que esos 5 son la totalidad de `other_cash_uses`. Por eso se descuentan dentro de esa partida, una vez. El saldo por pagar, el vencimiento nominal y el pago no son tres egresos distintos. La conciliación conserva los saldos contables como declaraciones independientes; no los deriva del remanente nominal ni autentica pago bancario o extinción legal.

## Principal antes del corte y alcance del agregado

El préstamo suministrado tiene principal inicial operativo de 200, tasa efectiva cero y diez cuotas de amortización para este ejemplo. Hay cinco pagos regulares de principal de 20 estrictamente anteriores al cierre: quedan 100 antes de todos los eventos de la fecha de venta. La sexta fecha regular coincide con el cierre y no se resta de nuevo después de descontar el payoff de 100.

El agregado de tenencia y venta muestra principal pagado de 200: 100 durante operación y 100 en venta. No representa otros 200 por pagar en el cierre. La [matriz de 28 conciliaciones](MiniUW_Puentes_28_D17.csv) conserva ese puente de alcance y el listado de fechas anteriores y coincidentes queda en el [registro completo](MiniUW_Cierre_y_Uso_Unico_D17.json).

Esta reconstrucción utiliza las condiciones suministradas de tasa cero, amortización, corte y ausencia de nuevos draws. No convierte tasas anuales, renueva un préstamo ni elige una estructura financiera para otro deal.

## Conservación del cierre y pendientes

En la referencia, las fuentes totales del cierre son 213 de caja libre, 100 de caja restringida y 400 de venta: 713. Los usos son 110 de principal/fees, 20 de costos, 5 de seguro y 578 de distribución: también 713. En la versión comparada ambos lados son 711, con distribución de 576. La liberación de reserva desaparece como transferencia interna en esta conservación total, manteniendo su identidad entre las dos cuentas.

Las 28 conciliaciones revisan continuidad de caja, reserva final, las cuatro obligaciones frente a sus pagos, seguro contable/nominal/caja, residual libre, conservación total, corte del principal y agregado de deuda. La [verificación del cierre](D17-design-validation.json) conserva fuentes, fórmulas y límites. Son lecturas y cálculos independientes sobre los archivos guardados; no se llama a productores ni se recalcula TIR.

Ambas versiones mantienen PENDING, diez criterios vacíos y pendientes de capital, CoC y retorno personal. Los 54 mapeos semánticos y la aceptación financiera siguen abiertos. Se conserva T111 con datos sintéticos, sin despliegue ni decisiones reales; la salida externa mantiene una página y estas matrices son evidencia interna.
