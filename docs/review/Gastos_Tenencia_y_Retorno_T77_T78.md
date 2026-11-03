# Gastos de tenencia conectados al retorno hasta venta

El nuevo control sigue cada concepto de gasto a través de los períodos operativos y comprueba que el retorno use exactamente esa caja. Reproduce compra/obra, deuda operativa y venta; los datos son sintéticos y la decisión permanece **PENDING**.

| Concepto del nuevo ejemplo independiente (USD) | Primer período | Segundo período |
|---|---:|---:|
| Gasto devengado de seguro | 10 | 10 |
| Otros gastos devengados | 5 | 5 |
| Impuesto calculado de prueba | 0 | 0 |
| Total devengado | 15 | 15 |
| Seguro por pagar al inicio | 0 | 5 |
| Seguro por pagar al final | 5 | 0 |
| Pagos operativos | 10 | 20 |
| NOI condicional | 45 | 75 |
| Reparto operativo propuesto | 100 | 100 |

El saldo de seguro pendiente de 5 cruza de un período al siguiente y se paga en el segundo. Los prepagos y las otras cuentas por pagar son cero expreso. El impuesto cero pertenece exclusivamente al fixture con sus fuentes de prueba; no acredita una exención o regla aplicable. El reparto de 100 en cada período usa también caja de apertura, y no equivale al NOI.

En la frontera de obra se mantienen principal 200 y caja libre 590, sin segundo desembolso o aporte. La operación termina con caja libre 270 y restringida 100. La venta del 1 de julio de 2027 liquida principal 100, fee 10 y costo de venta 20; con proceeds de 400, distribuye 640. Los pagos operativos acumulados de 30 ya están incluidos en la caja; no se descuentan nuevamente del inversor.

| Movimiento del equity agregado | Fecha | USD | Por cada 10 del total aportado |
|---|---|---:|---:|
| Aporte inicial | 2026-10-01 | 1.000 | 7,1429 |
| Aporte adicional | 2026-11-01 | 400 | 2,8571 |
| Cobro operativo | 2027-03-01 | 100 | 0,7143 |
| Cobro operativo | 2027-06-01 | 100 | 0,7143 |
| Cobro neto de venta | 2027-07-01 | 640 | 4,5714 |
| Total de cobros | Hasta venta | 840 | 6 |
| Resultado neto de caja | Hasta venta | −560 | −4 |

El EM es **0,6x**. La IRR anual del ejemplo queda contenida entre **−52,82% y −52,81%**, con extremos ampliados sólo para presentación. Se recalcula en la grilla mensual expresa desde octubre de 2026 a julio de 2027; [la vista interna](Revision_Vigente_Gastos_y_Retorno_T78.md) conserva sus raíces/intervalos exactos, sin elegir una tasa preferida. La escala por 10 usa los 1.400 aportados como base de equity agregado, sin prometer un resultado personal. Los movimientos brutos de aporte cero también se conservan en el ledger técnico.

No se modificó el ejemplo anterior de cobros 870: éste tiene fuentes nuevas con 30 de pagos operativos, por eso cobra 840. Ambos se conservan; no se elige el más favorable ni se ajustan variables para obtener PASS.

El control exige todos los períodos y conceptos, mismos IDs económicos y continuidad de saldos por concepto. Reutilizar un pago, omitir un período o trasladar una cuenta por pagar a otro gasto retira el retorno exportable, aunque los totales agregados sigan cuadrando. Las fuentes y resultados exactos se recuperan y vuelven a comprobarse.

La vista actual necesita **26 vínculos de fuentes** vigentes al instante UTC declarado, incluidos obra, contrato de fase, operación, venta, inversor y detalles nuevos. Una fuente vencida retira tanto el retorno como la tabla de gastos actuales, conservando la historia: [ejemplo pendiente](Revision_Pendiente_Gastos_y_Retorno_T78.md).

Capital todavía invertido, equity retenido, CoC y reparto personal conservan los pendientes de sus bases/términos. Cobertura del seguro, obligaciones fiscales, contratos, pagos/saldos reales, financiación disponible y validación financiera siguen sin acreditar. No hay despliegue, decisiones reales ni ampliación a condominios.

[Contrato técnico](../technical-implementation-T77-T78.md) · [Evidencia reproducible](synthetic-expense-checked-lifecycle-demo.json) · [Cobertura incremental](../technical-coverage-T77-T78.json).
