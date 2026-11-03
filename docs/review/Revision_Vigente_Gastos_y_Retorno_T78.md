# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Obra, gastos detallados, operación y venta: ejemplo sintético

Decisión: **PENDING**. Estado técnico: current\_synthetic\_expense\_checked\_lifecycle\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 840.0000 |
| Resultado neto de caja | -560.0000 |
| Equity Multiple (x) | 0.6000 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 0.0000 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 640.0000 |
| Otra distribución | 0.0000 |

### Por el aporte base declarado

Referencia: 10.0000 USD por una base de 1400.0000 USD. Base: SYNTHETIC\-all\-declared\-gross\-equity.
La escala pertenece al proyecto; no aplica porcentajes LP/JV ni términos personales.

| Fecha | Movimiento | Importe escalado |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 7.1429 |
| 2026\-11\-01 | Aporte adicional | 2.8571 |
| 2027\-03\-01 | Distribución operativa | 0.7143 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 0.7143 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 4.5714 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 6.0000; resultado: -4.0000.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 640.0000 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

### Capital, equity retenido y caja anual

Capital aún invertido y equity retenido son stocks declarados, no cobros ni una resta automática de aportes menos distribuciones.

| Corte | Capital aún invertido | Equity retenido (no caja) |
|---|---:|---:|
| Pendiente | Pendiente | Pendiente |

| Año de cobro | Distribución operativa | CoC condicional (fracción) |
|---|---:|---:|
| 2026 | 0.0000 | Pendiente |
| 2027 | 200.0000 | Pendiente |

### IRR anual

No se selecciona automáticamente una raíz. Tasas como fracciones anuales; no son porcentajes enteros.

- Intervalo exacto: \{"lower":\{"denominator":"17681966599145027406332053115053234999758922722984614415646244506385043796178504631023558086641","numerator":"\-9338267240078972396976499575328422052092108182528939533040613225829497992347877482496362434545"\},"lower\_closed":true,"upper":\{"denominator":"1053920080129891690078862828910922536351508101669554977638282998314369341846623163231121","numerator":"\-556596843720105047923480580764101696251051950872207260197819021421209844834089787698065"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 560.0000.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.7619.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- capital\_and\_retained\_equity\_snapshots\_missing

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.

## Puente de gastos y pagos

| Período | Gasto devengado | Pago operativo | Por pagar inicial/final | Prepago inicial/final |
|---|---:|---:|---:|---:|
| SYNTHETIC\-hold\-1 | 15.0000 | 10.0000 | 0.0000 / 5.0000 | 0.0000 / 0.0000 |
| SYNTHETIC\-hold\-2 | 15.0000 | 20.0000 | 5.0000 / 0.0000 | 0.0000 / 0.0000 |

Cada concepto conserva sus saldos entre períodos. Estos pagos ya pertenecen a la caja operativa: no se restan otra vez del retorno. Vigencia y pagos son declaraciones sintéticas; capital, CoC y retorno personal conservan sus pendientes.
