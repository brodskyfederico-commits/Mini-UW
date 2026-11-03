# Compra, tenencia y venta sin refinanciación

Este caso sintético independiente conserva el préstamo inicial durante la operación y lo liquida en la venta. No genera un refi ni una extensión automática del vencimiento. La decisión sigue **PENDING**, sin despliegue ni decisiones reales.

| Retorno del equity agregado del proyecto | USD |
|---|---:|
| Aportes brutos | 1400.0000 |
| Cobros brutos | 1360.0000 |
| Resultado neto de caja | -40.0000 |
| EM (x) | 0.9714 |

El ejemplo aporta 1.000 en octubre de 2026 y 400 en noviembre. Un draw de deuda de 120 en diciembre, junto con esos aportes, financia pagos previos de 520 y deja caja de apertura de 1.000. Esa caja se arrastra al período operativo y no cuenta como otro aporte.

## Cuánto se cobra por cada 10 aportados

La base expresa es el total de equity aportado, 1.400, escalado a 10. El aporte inicial representa 7,1429 y el adicional 2,8571. La escala pertenece al proyecto; el retorno personal depende de términos de reparto.

| Fecha | Movimiento bruto | USD del proyecto | Escala por 10 |
|---|---|---:|---:|
| 2026-10-01 | Aporte inicial | 1000.0000 | 7.1429 |
| 2026-11-01 | Aporte adicional | 400.0000 | 2.8571 |
| 2027-03-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-03-01 | Aporte adicional | 0.0000 | 0.0000 |
| 2027-06-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-06-01 | Aporte adicional | 0.0000 | 0.0000 |
| 2027-07-01 | Cobro neto de venta | 1160.0000 | 8.2857 |
| 2027-07-01 | Aporte adicional | 0.0000 | 0.0000 |

Los cobros suman 9.7143 por cada 10 aportados; el resultado neto de caja es -0.2857. Los aportes de cero son explícitos, no datos faltantes.

## Deuda y caja hasta la venta

El préstamo del caso nuevo declara origen en diciembre de 2026 y vencimiento en julio de 2027. En operación se pagan seis cuotas de principal de 10; la venta liquida los 60 restantes, más fee suministrado de 10. La tasa cero es un dato de esta prueba, no una condición bancaria adoptada. No se cuenta un balloon adicional al principal ya liquidado.

En este ejemplo, la caja operativa parte de 1.000; los cobros operativos suman 150, los pagos de capex 40, los depósitos a reserva 100 y las distribuciones operativas 200. Antes de vender quedan 750 libres y 100 restringidos. La venta cobra 400, libera la reserva y paga principal 60, fee 10 y costo de cierre 20: el cobro neto de equity en venta es 1.160.

El préstamo anterior con vencimiento en abril se conserva sin cambios. Si se intenta llevar ese contrato hasta julio sin otra solución, el resultado permanece pendiente: no se fabrica financiación ni una prórroga. Los ejemplos con/sin deuda y con refi tienen entradas propias y no constituyen un ranking de estrategias.

## IRR y riesgos

Se usa la grilla mensual expresa desde octubre hasta julio para la IRR periódica anualizada; se conservan todas las raíces/intervalos sin elegir una tasa preferida.

- Intervalo anual contenido entre -4.09% y -4.08% (extremos ampliados sólo para presentación).

- Caja aportada no recuperada al corte: 40.0000 USD; no equivale automáticamente a pérdida económica definitiva.
- Pico neto de financiación de equity al cierre de fecha: 1400.0000 USD.
- Proporción de cobros procedente de venta: 0.8529 como fracción.

CoC, capital remanente y equity retenido siguen pendientes de bases expresas. Los valores retenidos no se suman a cobros. Tampoco se verifican documentos, pagos, disponibilidad bancaria o activos/TDC reales. El caso se recupera desde sus fuentes y su vista actual exige vigencia de 16 bindings al instante UTC declarado; una fuente vencida retira las cifras actuales y conserva la historia.

[Evidencia del ejemplo](synthetic-hold-sale-demo.json) · [Vista interna actual](Revision_Vigente_Sin_Refi_T67.md) · [Vista pendiente](Revision_Pendiente_Sin_Refi_T67.md) · [Contrato del recorrido](../technical-implementation-T63-T65.md).
