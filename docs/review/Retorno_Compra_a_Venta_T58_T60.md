# Retorno sintético desde la compra hasta la venta

El recorrido conecta compra y obra, deuda de apertura, operación, refinanciación y venta. La decisión continúa **PENDING**; son cifras de prueba del equity agregado del proyecto, sin reparto personal ni uso para decisiones reales.

| Resultado del ejemplo en USD | Importe |
|---|---:|
| Aportes brutos de equity | 1400.0000 |
| Cobros brutos de equity | 1298.9197 |
| Resultado neto de caja | -101.0803 |
| Equity Multiple (x) | 0.9278 |
| Cash-in de refi del caso base | 0.0000 |

Los aportes son 1.000 en octubre de 2026 y 400 en noviembre. La caja de 1.000 al iniciar la operación ya procede de esa historia y de la deuda: no se cuenta como otro aporte. El préstamo inicial recibe 120 en diciembre; su principal de apertura se concilia con el calendario de deuda utilizado en la operación y el refi.

## Aportes y cobros por cada 10 de equity total

La base es el total de aportes declarados de 1.400, escalado a 10. El aporte inicial representa 7,1429 y el adicional 2,8571. Es una escala del proyecto; el retorno personal requiere términos de reparto.

| Fecha | Movimiento | USD del proyecto | Escala por 10 |
|---|---|---:|---:|
| 2026-10-01 | Aporte inicial | 1000.0000 | 7.1429 |
| 2026-11-01 | Aporte adicional | 400.0000 | 2.8571 |
| 2027-03-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-04-01 | Cobro neto de refi | 353.0100 | 2.5215 |
| 2027-06-01 | Cobro operativo | 100.0000 | 0.7143 |
| 2027-07-01 | Cobro neto de venta | 745.9097 | 5.3279 |

Por cada 10 aportados, los cobros suman 9.2780 y el resultado de caja es -0.7220.

## Recorrido del principal de deuda

| Punto | Principal USD |
|---|---:|
| Préstamo previo al refi en la apertura operativa | 120.0000 |
| Principal regular pagado antes del refi | 30.0000 |
| Principal liquidado en el refi | 90.0000 |
| Nuevo principal después del refi | 303.0100 |
| Principal regular pagado después del refi | 201.0000 |
| Principal liquidado en la venta | 102.0100 |

Estas cifras provienen de los cierres y calendarios reproducidos. Interés, fees, reservas y otros usos se conservan aparte; principal de deuda no equivale a un cobro del inversor.

## IRR anual y caja anual

El calendario empieza en octubre de 2026 y termina en julio de 2027. Se usa la grilla mensual expresa para la IRR periódica anualizada. Se conservan todas las raíces/intervalos; no se elige una raíz automáticamente. Los racionales exactos están en el paquete recuperable.

- Intervalo anual contenido entre -11.27% y -11.26% (extremos ampliados sólo para presentación).

| Año de cobro | Distribución operativa USD | CoC |
|---|---:|---|
| 2026 | 0.0000 | Pendiente |
| 2027 | 200.0000 | Pendiente |

CoC, capital aún invertido y equity retenido permanecen pendientes de bases expresas. El equity retenido no se suma a los cobros.

## Riesgos y controles

- Caja aportada no recuperada al corte: 101.0803 USD; no certifica pérdida económica definitiva.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000 USD.
- Proporción de cobros procedente de venta: 0.5743 como fracción.
- Un caso separado que requiere cash-in lo registra como aporte bruto y mantiene en cero el cobro de refi. Sin una hipótesis expresa de financiación, queda bloqueado.
- Se conserva el bloqueo del ejemplo previo de deuda no conciliada y el fallo bancario con NOI 50. El caso completo usa una rama de prueba independiente con NOI bancario 2.000; no corrige ni reemplaza los originales.
- El paquete sintético se recupera desde sus fuentes exactas y reproduce deuda, capacidad, caja y retorno; un hash actualizado no valida cifras manipuladas.

La base de activos/TDC, documentación y pagos reales, disponibilidad de financiación, términos personales y revisión financiera siguen abiertos. Este recorrido no habilita despliegue, publicación financiera ni decisiones reales.

[Evidencia del recorrido](synthetic-lifecycle-returns-demo.json) · [Paquete recuperable sintético](../../templates/synthetic-lifecycle-bundle-example.json) · [Contrato del retorno](../technical-implementation-T59.md).
