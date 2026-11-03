# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Renta mensual, obra, operación y venta: ejemplo sintético

Decisión: **PENDING**. Estado técnico: current\_synthetic\_rental\_checked\_lifecycle\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 775.0000 |
| Resultado neto de caja | -625.0000 |
| Equity Multiple (x) | 0.5536 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 0.0000 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 575.0000 |
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
| 2027\-07\-01 | Cobro neto de venta | 4.1071 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 5.5357; resultado: -4.4643.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 575.0000 |
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

- Intervalo exacto: \{"lower":\{"denominator":"92762715193394245921694303303765029683542522216898885264513874646033539831638336181640625","numerator":"\-54042925339958473927918869966898267237091768066181747279471329107255595347605901623172529"\},"lower\_closed":true,"upper":\{"denominator":"1556288769732500964319645168911379470661150415965141331959096900752723054814833127386839279272881","numerator":"\-906678491886800675453324068325165033876357680215663353082233345058809104170212421793555403572145"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 625.0000.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.7419.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- capital\_and\_retained\_equity\_snapshots\_missing

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.

## Renta mensual declarada

| Inicio de mes | Potencial | Pérdida | Concesión | Efectiva |
|---|---:|---:|---:|---:|
| 2027\-01\-01 | 20.0000 | 20.0000 | 0.0000 | 0.0000 |
| 2027\-02\-01 | 20.0000 | 10.0000 | 0.0000 | 10.0000 |
| 2027\-03\-01 | 20.0000 | 0.0000 | 5.0000 | 15.0000 |
| 2027\-04\-01 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |
| 2027\-05\-01 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |
| 2027\-06\-01 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |

Pérdidas y concesiones tienen bases expresas por mes; no acreditan ocupación física, contratos o cobros. No hay estabilización ni liquidez intramensual certificadas.

## Gastos y pagos ya incluidos en la caja

| Período | Gasto devengado | Pago operativo |
|---|---:|---:|
| SYNTHETIC\-hold\-1 | 15.0000 | 10.0000 |
| SYNTHETIC\-hold\-2 | 15.0000 | 20.0000 |

Rentas y gastos se vinculan a la misma caja; no se cuentan nuevamente como cobros o pagos del inversor. CoC, capital/equity y retorno personal conservan sus pendientes.
