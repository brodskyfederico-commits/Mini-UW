# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Obra por etapas, misma deuda operativa y venta: ejemplo sintético

Decisión: **PENDING**. Estado técnico: current\_synthetic\_staged\_lifecycle\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 870.0000 |
| Resultado neto de caja | -530.0000 |
| Equity Multiple (x) | 0.6214 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 0.0000 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 670.0000 |
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
| 2027\-07\-01 | Cobro neto de venta | 4.7857 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 6.2143; resultado: -3.7857.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 670.0000 |
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

- Intervalo exacto: \{"lower":\{"denominator":"487496436775735415149957239055040714499048023417556202538105849699869736904902626357838732321264576721","numerator":"\-244937942667800176628282227486571584946753436824133689258874433826921656816574766696369315097382824145"\},"lower\_closed":true,"upper":\{"denominator":"29056856441690361243977384672840860490563404794511533376549835979576790326479803574975520475121","numerator":"\-14599243563133201431427137267760713131651497920723742048165471382199723708971400532333081036785"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 530.0000.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.7701.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- capital\_and\_retained\_equity\_snapshots\_missing

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.

## Continuidad del principal sin nuevos fondos

| Préstamo | Principal de obra trasladado | Ancla operativa | Vencimiento conservado |
|---|---:|---|---|
| SYNTHETIC\-staged\-loan | 200.0000 | 2027\-01\-01 | 2027\-07\-01 |

El ancla del calendario no es un draw: principal y caja se trasladan sin crear otros aportes o cobros. Contrato/liquidaciones reales, activos/TDC y retorno personal siguen pendientes.
