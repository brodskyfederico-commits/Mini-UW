# Deuda de obra, deuda operativa y retorno hasta la venta

El caso sintético conecta los desembolsos de obra con una fase amortizante de la misma obligación, la operación y la venta. El principal y la caja se arrastran sin generar otro préstamo o aporte. La decisión sigue **PENDING**; no hay despliegue ni decisiones reales.

## Cómo pasa la deuda a operación

| Concepto del ejemplo | USD o fecha |
|---|---:|
| Draws brutos de obra | 250 |
| Principal repagado durante obra | 50 |
| Interés de obra pagado según el plan | 5 |
| Fees de obra pagados según el plan | 5 |
| Principal trasladado a la fase operativa | 200 |
| Caja libre trasladada a operación | 590 |
| Nuevos fondos en la frontera de fases | 0 |
| Inicio de fase operativa | 2027-01-01 |
| Vencimiento original conservado | 2027-07-01 |

Los draws de obra empiezan en octubre de 2026. El ancla de enero de 2027 sirve para el cálculo del calendario operativo; no es una nueva fecha de financiación. La continuidad de la misma obligación y la liquidación previa de intereses/fees son hipótesis expresas del contrato sintético, todavía sin autenticación documental.

Los términos operativos suministran tasa cero por intervalo de pago, frecuencia 12, amortización de 10 pagos y vencimiento en el sexto. El pago regular calculado es 20: dos pagos antes de abril y tres entre abril y julio reducen el principal de 200 a 100. La venta liquida esos 100 antes de la cuota regular de julio, sin añadir otra vez el balloon. La tasa operativa cero es un dato de prueba nuevo; no se deduce del factor de obra de 1%.

Cambiar el principal a 201, mover el ancla o extender el vencimiento sin otro perfil deja el caso pendiente. Una caja operativa que reinicia con un saldo distinto de 590 también queda bloqueada, aunque sus cuentas locales cuadren.

## Retorno del equity agregado del proyecto

| Concepto | USD o múltiplo |
|---|---:|
| Aportes brutos históricos | 1400.0000 |
| Cobros brutos | 870.0000 |
| Resultado neto de caja | -530.0000 |
| EM (x) | 0.6214 |

Los aportes son 1.000 en octubre y 400 en noviembre de 2026. Los 200 de principal y los 590 de caja de enero no se cuentan como movimientos nuevos del inversor. La escala siguiente usa el total aportado de 1.400 como base equivalente a 10; es una escala del proyecto, no una participación LP/JV.

| Fecha | Movimiento | USD | Escala por 10 |
|---|---|---:|---:|
| 2026-10-01 | Aporte inicial | 1000.0000 | 7.1429 |
| 2026-11-01 | Aporte adicional | 400.0000 | 2.8571 |
| 2027-03-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-03-01 | Aporte adicional | 0.0000 | 0.0000 |
| 2027-06-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-06-01 | Aporte adicional | 0.0000 | 0.0000 |
| 2027-07-01 | Cobro neto de venta | 670.0000 | 4.7857 |
| 2027-07-01 | Aporte adicional | 0.0000 | 0.0000 |

Por cada 10 de equity total, los cobros suman 6.2143 y el resultado neto de caja es -3.7857. Se conserva el resultado negativo.

## IRR anual y riesgos

La grilla mensual expresa va de octubre de 2026 a julio de 2027. La IRR periódica se anualiza bajo esa frecuencia; se conservan todas las raíces/intervalos sin elegir una tasa preferida. Los racionales exactos permanecen en el paquete recuperable.

- Intervalo anual contenido entre -50.25% y -50.24% (extremos ampliados sólo para presentación).

- Caja aportada no recuperada al corte: 530.0000 USD, sin certificar pérdida económica final.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000 USD.
- Proporción de cobros que procede de venta: 0.7701 como fracción.

CoC, capital remanente, equity retenido y retorno personal conservan sus pendientes de bases/términos. Los valores retenidos no se suman a cobros. Contratos, pagos, disponibilidad real, activos/devengos/TDC y revisión financiera siguen sin verificarse. La fase no autoriza una novación, capitalización o prórroga real.

La recuperación reproduce todo el recorrido desde las fuentes exactas. La vista actual exige vigencia de 22 bindings al instante UTC declarado; una fuente vencida retira cifras actuales y conserva la historia.

[Vista actual](Revision_Vigente_Obra_Operacion_T75.md) · [Vista pendiente](Revision_Pendiente_Obra_Operacion_T75.md) · [Evidencia](synthetic-staged-operating-demo.json) · [Contrato técnico](../technical-implementation-T72-T75.md).
