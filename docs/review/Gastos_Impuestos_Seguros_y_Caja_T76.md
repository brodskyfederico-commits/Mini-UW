# Gasto reconocido y dinero pagado

Este bloque detalla los gastos de operación para que un pago de seguro o impuesto no vuelva a restarse del NOI y de la caja. Es una comprobación sintética por concepto, sin cambios de política fiscal ni pagos reales.

| Concepto de prueba | Gasto del período | Por pagar inicial | Por pagar final | Prepago inicial | Prepago final | Pago planificado |
|---|---:|---:|---:|---:|---:|---:|
| Seguro | 120 | 0 | 0 | 40 | 60 | 140 |
| Otros gastos operativos | 130 | 20 | 30 | 0 | 0 | 120 |
| Impuesto condicional del ejemplo | 200 | 80 | 100 | 0 | 0 | 180 |
| Total USD | 450 | 100 | 130 | 40 | 60 | 440 |

Los pagos suministrados están fechados el 1 de enero, 1 de junio y 31 de diciembre de 2027 respectivamente, dentro del período declarado 2027-01-01 a 2028-01-01. Son fechas de un plan de prueba, sin acreditación bancaria o vencimientos legales.

La identidad es: **pago = gasto + deuda operativa inicial − deuda operativa final + prepago final − prepago inicial**. Aquí «deuda operativa» significa cuentas por pagar de gastos; el préstamo financiero permanece separado. Los 450 reconocidos generan 440 de pagos porque las cuentas por pagar aumentan 30 y los prepagos aumentan 20.

El NOI sigue siendo 1.000 en este ejemplo independiente. Después de los demás cobros, usos y reservas expresos T25, el plan propone distribuir 100 y conservar 405 de caja libre. No se reparte el NOI completo. Si se suministra un prepago de seguro adicional de 60 con su pago y saldos compatibles, el NOI permanece en 1.000 y la caja libre cae a 345; no se inventa una nueva distribución. No es un escenario adoptado ni un retorno personal o compra-a-venta nuevo: [el hito anterior conserva esa historia completa de caja](Deuda_Obra_a_Operacion_y_Retorno_T72_T75.md).

El modelo bloquea el detalle si falta un concepto, saldo, fuente o declaración; un importe desconocido no se convierte en cero. También bloquea seguro pagado de más por 1 e impuesto pagado de menos por 1, aunque el total global coincida. El impuesto se vincula al resultado fiscal condicional T19 existente, sin adoptar su fórmula como ley aplicable.

La recuperación conserva las fuentes y reproduce el cálculo exacto. Una diferencia por concepto, un fallo previo de caja o una prueba alterada mantiene **PENDING**. La cobertura del seguro, obligaciones/vencimientos fiscales, pagos reales, vigencia de fuentes, devengos intraperíodo, revisión contable y suficiencia de caja intradía quedan pendientes. No hay despliegue ni decisiones reales.

[Contrato técnico](../technical-implementation-T76.md) · [Evidencia reproducible](synthetic-expense-cash-demo.json) · [Cobertura incremental](../technical-coverage-T76.json).
