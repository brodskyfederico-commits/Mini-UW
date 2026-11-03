# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Compra a venta: alcance sintético declarado

Decisión: **PENDING**. Estado técnico: current\_synthetic\_lifecycle\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 1298.9197 |
| Resultado neto de caja | -101.0803 |
| Equity Multiple (x) | 0.9278 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 353.0100 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 745.9097 |
| Otra distribución | 0.0000 |

### Por el aporte base declarado

Referencia: 10.0000 USD por una base de 1400.0000 USD. Base: SYNTHETIC\-all\-declared\-gross\-contributions\-not\-LP\-allocation.
La escala pertenece al proyecto; no aplica porcentajes LP/JV ni términos personales.

| Fecha | Movimiento | Importe escalado |
|---|---|---:|
| 2027\-03\-01 | Distribución operativa | 0.7143 |
| 2027\-04\-01 | Cobro neto de refi | 2.5215 |
| 2027\-06\-01 | Distribución operativa | 0.7143 |
| 2027\-07\-01 | Cobro neto de venta | 5.3279 |
| 2026\-10\-01 | Aporte inicial | 7.1429 |
| 2026\-11\-01 | Aporte adicional | 2.8571 |

Total aportado escalado: 10.0000; cobrado: 9.2780; resultado: -0.7220.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-04\-01 | Cobro neto de refi | 353.0100 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-07\-01 | Cobro neto de venta | 745.9097 |
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |

### Capital, equity retenido y caja anual

Capital aún invertido y equity retenido son stocks declarados, no cobros ni una resta automática de aportes menos distribuciones.

| Corte | Capital aún invertido | Equity retenido (no caja) |
|---|---:|---:|
| 2027\-04\-01 | Pendiente | Pendiente |

| Año de cobro | Distribución operativa | CoC condicional (fracción) |
|---|---:|---:|
| 2026 | 0.0000 | Pendiente |
| 2027 | 200.0000 | Pendiente |

### IRR anual

No se selecciona automáticamente una raíz. Tasas como fracciones anuales; no son porcentajes enteros.

- Intervalo exacto: \{"lower":\{"denominator":"14420451601106911393560611786376313721878131422932456029962906183626165865623216024026281356042127869982692012746452938053683758820199754316914306640625","numerator":"\-1624456363821306888806904996674342458553349719827387369764442693733524097604159129181032070848535851775258277840722101180876631934381398546554240690929"\},"lower\_closed":true,"upper":\{"denominator":"990959317969650775275905069363075887758859719876196231387951581415116138522912234205003487606585561200710573863140247787521008527466397700558808087874790345044481","numerator":"\-111625220947035876723785914218386029155471853617389006629760580478493371407944745115024981032603885249229542895024286389962328180421403072875778177501230326772225"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 101.0803.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.5743.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- snapshot:2027\-04\-01:capital\_still\_invested\_missing\_or\_negative
- snapshot:2027\-04\-01:retained\_equity\_value\_missing
- snapshot:2027\-04\-01:snapshot\_metadata\_missing\_or\_mismatch

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.

## Deuda de apertura conciliada bajo calendario sintético

| Préstamo | Principal al abrir operación |
|---|---:|
| SYNTHETIC\-project\-old\-loan | 120.0000 |

La caja de apertura procede del historial y no se agrega como otro aporte. Los pagos/activos/fondos reales y el retorno personal siguen pendientes.
