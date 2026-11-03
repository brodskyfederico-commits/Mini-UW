# Mini-UW — revisión interna sintética

Decisión: **PENDING**. Evaluación UTC: 2027\-07\-01T12:00:00Z.
Retorno mostrado: equity agregado del proyecto. Retorno personal: pendiente de términos de reparto; ninguna cifra es una promesa al inversor.
Importes de presentación con cuatro decimales (mitad par); evidencia JSON conserva fracciones exactas. Redondear no define tolerancias financieras.
Sin aprobación profesional, publicación financiera, despliegue o decisiones reales.

## Caso: Disponibilidad por tramos, obra, operación y venta: ejemplo sintético

Decisión: **PENDING**. Estado técnico: current\_synthetic\_phased\_rental\_lifecycle\_at\_declared\_time.

### Caja del proyecto (USD)

| Concepto | Importe |
|---|---:|
| Aportes brutos totales | 1400.0000 |
| Cobros brutos totales | 778.0000 |
| Resultado neto de caja | -622.0000 |
| Equity Multiple (x) | 0.5557 |

| Desglose bruto | Importe (USD) |
|---|---:|
| Aporte inicial | 1000.0000 |
| Aporte adicional | 400.0000 |
| Cash-in de refi | 0.0000 |
| Cobro neto de refi | 0.0000 |
| Distribución operativa | 200.0000 |
| Cobro neto de venta | 578.0000 |
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
| 2027\-07\-01 | Cobro neto de venta | 4.1286 |
| 2027\-07\-01 | Aporte adicional | 0.0000 |

Total aportado escalado: 10.0000; cobrado: 5.5571; resultado: -4.4429.

### Movimientos brutos y fechas

| Fecha | Movimiento | Importe (USD) |
|---|---|---:|
| 2026\-10\-01 | Aporte inicial | 1000.0000 |
| 2026\-11\-01 | Aporte adicional | 400.0000 |
| 2027\-03\-01 | Distribución operativa | 100.0000 |
| 2027\-03\-01 | Aporte adicional | 0.0000 |
| 2027\-06\-01 | Distribución operativa | 100.0000 |
| 2027\-06\-01 | Aporte adicional | 0.0000 |
| 2027\-07\-01 | Cobro neto de venta | 578.0000 |
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

- Intervalo exacto: \{"lower":\{"denominator":"5850617355225199657604996833758752474027602254899856384259257635881584895228540568164741661813222900390625","numerator":"\-3394025427703327415048115884892440447098760637929610760113048037159279487864034411138808751516033381456609"\},"lower\_closed":true,"upper":\{"denominator":"23963954564469633747418188176842481781816536676122043460447456970259670618101115218419977449926407436151806961","numerator":"\-13901754029340045041905203810286067719516001413011917383944582453893107669536097999241756249349119166598077425"\},"upper\_closed":false\}.

### Riesgos y pendientes

- Aportes no recuperados al corte: 622.0000.
- Pico de financiación neta de equity al cierre de fecha: 1400.0000.
- Cota superior intradía sin orden verificado: 1400.0000.
- Proporción de cobros que depende de venta (fracción): 0.7429.
- Recuperación de caja al corte no equivale a pérdida económica definitiva o fondos disponibles.
- Retorno personal, revisión financiera y criterios de inversión siguen pendientes.
- 2026:positive\_declared\_annual\_capital\_base\_missing
- 2027:positive\_declared\_annual\_capital\_base\_missing
- capital\_and\_retained\_equity\_snapshots\_missing

No se selecciona un caso como aprobado ni se promedian retornos. Una evidencia vencida requiere nueva evaluación y revisión explícita; no hay monitor automático.

## Disponibilidad y fracción suministradas

| Inicio / fin excluido | Disponibles | Fracción de mes | Potencial | Pérdida | Concesión | Efectiva |
|---|---:|---:|---:|---:|---:|---:|
| 2027\-01\-01 / 2027\-01\-16 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 2027\-01\-16 / 2027\-02\-01 | 5.0000 | 0.5000 | 5.0000 | 0.0000 | 0.0000 | 5.0000 |
| 2027\-02\-01 / 2027\-03\-01 | 5.0000 | 1.0000 | 10.0000 | 2.0000 | 0.0000 | 8.0000 |
| 2027\-03\-01 / 2027\-04\-01 | 10.0000 | 1.0000 | 20.0000 | 0.0000 | 5.0000 | 15.0000 |
| 2027\-04\-01 / 2027\-05\-01 | 10.0000 | 1.0000 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |
| 2027\-05\-01 / 2027\-06\-01 | 10.0000 | 1.0000 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |
| 2027\-06\-01 / 2027\-07\-01 | 10.0000 | 1.0000 | 20.0000 | 0.0000 | 0.0000 | 20.0000 |

Disponibilidad y fracción son datos de prueba, no entrega, ocupación, contrato, convención por días o cobro acreditado. No se certifica liquidez intraperíodo.

## Gastos y pagos ya incluidos en la caja

| Período | Gasto devengado | Pago operativo |
|---|---:|---:|
| SYNTHETIC\-hold\-1 | 15.0000 | 10.0000 |
| SYNTHETIC\-hold\-2 | 15.0000 | 20.0000 |

Rentas y gastos se vinculan a la misma caja; no se cuentan nuevamente como cobros o pagos del inversor. CoC, capital/equity y retorno personal conservan sus pendientes.
