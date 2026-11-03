# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Compra, tenencia y venta sin refinanciación: caso sintético independiente

Decisión: **PENDING**. Estado técnico: current\_synthetic\_hold\_sale\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 1360.0000 |
| Resultado neto de caja | -40.0000 |
| Equity Multiple (x) | 0.9714 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 0.0000 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 1160.0000 |
| Otra distribución | 0.0000 |

### Por el aporte base declarado

Referencia: 10.0000 USD por una base de 1400.0000 USD. Base: SYNTHETIC\-all\-declared\-gross\-contributions.
La escala pertenece al proyecto; no aplica porcentajes LP/JV ni términos personales.

| Fecha | Movimiento | Importe escalado |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 7.1429 |
| 2026\-11\-01 | Aporte adicional | 2.8571 |
| 2027\-03\-01 | Distribución operativa | 0.7143 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 0.7143 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 8.2857 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 9.7143; resultado: -0.2857.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 1160.0000 |
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

- Intervalo exacto: \{"lower":\{"denominator":"159115348980521956632352432997343401670052345841394904756924324698975769027062571928481","numerator":"\-6494106016219376882402630414651477705323943644798728635718633944955218952307651578785"\},"lower\_closed":true,"upper":\{"denominator":"651729549379222092895132320204825497214547481067529893427229954481256537049659004150390625","numerator":"\-26592938197438726239337928826119376655019945670271956034771445152788363943462850398035809"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 40.0000.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.8529.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- capital\_and\_retained\_equity\_snapshots\_missing

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.
