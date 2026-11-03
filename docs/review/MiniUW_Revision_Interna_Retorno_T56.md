# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Caso sintético: precio 200

Decisión: **PENDING**. Estado técnico: current\_synthetic\_matched\_case\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1000.0000 |
| Cobros brutos totales | 1083.9197 |
| Resultado neto de caja | 83.9197 |
| Equity Multiple (x) | 1.0839 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 0.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 353.0100 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 530.9097 |
| Otra distribución | 0.0000 |

### Por el aporte base declarado

Referencia: 10.0000 USD por una base de 1000.0000 USD. Base: SYNTHETIC\-initial\-contribution\-only.
La escala pertenece al proyecto; no aplica porcentajes LP/JV ni términos personales.

| Fecha | Movimiento | Importe escalado |
|---|---|---:|
| 2027\-01\-01 | Aporte inicial | 10.0000 |
| 2027\-03\-01 | Distribución operativa | 1.0000 |
| 2027\-04\-01 | Cobro neto de refi | 3.5301 |
| 2027\-06\-01 | Distribución operativa | 1.0000 |
| 2027\-07\-01 | Cobro neto de venta | 5.3091 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 10.8392; resultado: 0.8392.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2027\-01\-01 | Aporte inicial | 1000.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-04\-01 | Cobro neto de refi | 353.0100 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-07\-01 | Cobro neto de venta | 530.9097 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

### Capital, equity retenido y caja anual

Capital aún invertido y equity retenido son stocks declarados, no cobros ni una resta automática de aportes menos distribuciones.

| Corte | Capital aún invertido | Equity retenido (no caja) |
|---|---:|---:|
| 2027\-04\-01 | Pendiente | Pendiente |

| Año de cobro | Distribución operativa | CoC condicional (fracción) |
|---|---:|---:|
| 2027 | 200.0000 | 0.2000 |

### IRR anual

No se selecciona automáticamente una raíz. Tasas como fracciones anuales; no son porcentajes enteros.

- Intervalo exacto: \{"lower":\{"denominator":"174817576163967932376730528505919804813046911986490798119247902749261966062444424738682084992460607648849459486488258994890263149834409607644081926481","numerator":"41497572223215290542887789982416478519622884226970570099751248677336456268415786912108912413184567039351958446343845899956653465896844024403689623215"\},"lower\_closed":true,"upper":\{"denominator":"12013271474309677023683352391254806403356144247264410003094490502503487825256414852878130565236965862933483297654738267077359906236434070371180312917093280486401","numerator":"2851792332927748384310860644103857506467962362396409380265751437160383669723436356526437536978504074123030095662730775837984506419641665224442028132883659385855"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 0.0000.
- Pico de financiación neta de equity al cierre de fecha: 1000.0000.
- Cota superior intradía sin orden verificado: 1000.0000.
- Proporción de cobros que depende de venta (fracción): 0.4898.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- snapshot:2027\-04\-01:capital\_still\_invested\_missing\_or\_negative
- snapshot:2027\-04\-01:retained\_equity\_value\_missing
- snapshot:2027\-04\-01:snapshot\_metadata\_missing\_or\_mismatch

## Caso: Caso sintético: evidencia vencida

Decisión: **PENDING**. Estado técnico: PENDING.

Resultado actual pendiente; no se sustituye por cero ni se presenta una cifra histórica como vigente.

- blockers: candidate\_story\_not\_current
- candidate\_evidence\_blockers: /exit/cost\_bounds:evidence\_expired

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.
