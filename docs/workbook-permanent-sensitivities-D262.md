# Si invierto USD 10, ¿cuánto cobro y cuándo?

D262 conecta los cambios C69–C72 por separado y en conjunto con la deuda permanente, la capacidad de refinanciación y los movimientos brutos por USD 10 en Base y Downside. Usa exclusivamente el perfil sintético documentado D200. Se conserva el equity inicial verificado de USD 2.400.000 y el factor `10 / 2.400.000`. Los aportes posteriores se muestran separados. El dictamen real y el retorno personal sin términos de reparto permanecen PENDING.

## Valores del ensayo y alcance

| Celda original y variable | Base original → variante | Downside original → variante | Unidad |
|---|---:|---:|---|
| `Inputs!C69` · Tasa permanente | 5,00 % → 6,00 % | 6,50 % → 6,40 % | Nominal anual convertible trimestralmente |
| `Inputs!C70` · Amortización | 20 → 21 | 11 → 12 | Años enteros |
| `Inputs!C71` · LTV máximo | 65,00 % → 64,99 % | 65,00 % → 64,99 % | Fracción de valor |
| `Inputs!C72` · DSCR mínimo | 1,250 → 1,251 | 1,300 → 1,301 | Múltiplo |

Son sustituciones explícitas para comprobar las conexiones; no son parámetros recomendados ni nuevos criterios de Lorena. La solicitud permanece en USD 1.400.000, el vencimiento en ocho pagos trimestrales y la primera cuota en la fecha de venta del perfil. Una amortización mayor no prorroga el vencimiento ni cambia las fechas de pago.

| Corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C69 | 10,000000 | 4,867042 | 18,044771 | 0,000000 |
| Base sólo C70 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C71 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C72 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base conjunto | 10,000000 | 4,867042 | 18,044771 | 0,000000 |
| Downside original | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C69 | 10,000000 | 8,189342 | 6,078162 | 12,111179 |
| Downside sólo C70 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C71 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C72 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside conjunto | 10,000000 | 8,189342 | 6,078162 | 12,111179 |

USD por USD 10 iniciales, sin redondeo intermedio y presentados a seis decimales. La caja sin recuperar compara todos los aportes con los cobros hasta el cierre; no certifica pérdida económica final.

### Fechas de aportes y cobros conjuntos

| Movimiento | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,000000 | 10,000000 |
| Aporte · 30/06/2027 | — | 0,762275 |
| Aporte · 30/09/2027 | 4,655375 | 0,035729 |
| Aporte · 30/12/2027 | 0,052917 | 7,034046 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,052917 cada fecha | 0,071458 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,071458 cada fecha |
| Cobro neto de refi | 2,846667 · 30/09/2028 | 2,445833 · 30/03/2029 |
| Cobro de operación | 1,424226 · 30/12/2028 | 0,561259 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,773879 · 30/12/2028 | 3,071070 · 30/06/2029 |

El aporte operativo explícito es cero y se conserva en los eventos. La cuota del proyecto en el conjunto es USD 29.424,973172 en Base y USD 42.008,061432 en Downside; el servicio anual equivalente para sizing es USD 117.699,892689 y USD 168.032,245727, respectivamente. Los vencimientos siguen en 30/09/2030 y 30/03/2031.

| Límite de capacidad del conjunto · USD del proyecto | Base | Downside |
|---|---:|---:|
| LTV | 3.012.838,432461 | 1.425.478,494390 |
| DSCR | 3.975.662,952835 | 1.501.954,254685 |
| Debt yield | 4.181.334,383929 | 1.563.534,033611 |
| Límite activo | LTV | LTV |

Los tres límites admiten la solicitud fija del ensayo principal. Los controles de solicitud excedida se guardan aparte y mantienen PENDING sin ajustar el préstamo para obtener un resultado calculado.

## Fórmulas y conexiones

Para el préstamo fijo de este perfil, con pagos vencidos:

```text
P = principal solicitado
i = C69 / 4
n = C70 × 4
cuota unitaria = i / (1 − (1 + i)^−n), si i > 0
cuota unitaria = 1 / n, si i = 0 explícito
cuota = P × cuota unitaria
interés del período = saldo inicial × i
principal amortizado = cuota − interés
saldo final = saldo inicial − principal amortizado
servicio anual para sizing = 4 × cuota
límite DSCR = NOI bancario / (C72 × 4 × cuota unitaria)
límite LTV = valor de refinanciación × C71
capacidad = mínimo de los límites aplicables, incluido debt yield documentado
```

La caja operativa resta la cuota efectivamente ubicada en la ventana. La venta cancela el principal pendiente después de la cuota correspondiente. El servicio anual equivalente de sizing no se resta otra vez de la caja. Las fuentes/usos de operación, obra, refi y venta se concilian por separado antes de normalizar por USD 10.

En esta prueba, operación y venta coinciden con la primera cuota trimestral: la suma cuota + saldo a cancelar equivale a principal + interés de ese trimestre. Por eso cambiar C70 redistribuye cobros entre operación y venta, manteniendo el total nominal si la tasa y las demás condiciones no cambian. Esa identidad pertenece a este calendario; no se generaliza a una tenencia con más cuotas ni implica que la amortización sea irrelevante para capacidad o liquidez.

Los cambios C71 y C72 no aumentan ni reducen automáticamente el préstamo solicitado. Si sigue dentro del menor límite, conservan los flujos. Si lo excede, el cobro de refi se retira, la ruta queda PENDING y no se publica una caja completa de esa variante.

## Respaldo documental de cada cambio

La variante lleva un PDF bancario sintético de una página, con escenario, caso, revisión nueva y huellas que lo enlazan al respaldo padre verificado. Sólo pueden cambiar tasa, amortización, LTV y DSCR. Principal solicitado, frecuencia, vencimiento y convenciones se conservan. El lector coteja los renglones y las unidades del PDF con las celdas modificadas mediante el control B08 existente; no se omite ese control.

El anexo de debt yield también debe estar declarado expresamente: cita la revisión PDF nueva y la huella del anexo padre, conserva aplicabilidad, base y mínimo, y tiene una fuente sintética nueva. El código no rebaja el mínimo ni adopta otra política para acomodar la variante. Una huella antigua, un cambio de mínimo o la ausencia del respaldo produce PENDING. Los originales permanecen intactos.

Las celdas modificadas citan `sha256:<binding>#/resulting_value`; las demás conservan la cita del Excel. El resultado retiene el PDF leído, los localizadores, la relación con el padre y la evidencia del anexo para la reproducción B16.

## Cobertura y bloqueos

| Requisito o variable y ubicación | Módulo o cálculo afectado | Evidencia de validación | Estado y pendiente |
|---|---|---|---|
| `Inputs!A69:F69` · Tasa | D152, cronograma, sizing DSCR, interés y caja | Cotejo PDF/celda; cuota independiente; tasa cero explícita | Conectado en sintético; términos reales pendientes |
| `Inputs!A70:F70` · Amortización | Cantidad de cuotas de amortización y saldo, conservando vencimiento separado | Cronograma completo y cancelación a la venta; años enteros obligatorios | Cero o plazo inválido queda PENDING |
| `Inputs!A71:F71` · LTV | Límite sobre valor de refi | Límite independiente y control de préstamo excedido | Cero numérico conserva capacidad LTV cero; préstamo positivo queda PENDING |
| `Inputs!A72:F72` · DSCR | Límite sobre NOI bancario y cuota anual equivalente | Fórmula independiente y control de límite activo | Cero o dato ausente queda PENDING |
| PDF y anexo | `worksheet_permanent_support_D262`, B08, D178 | Huellas, escenario, revisión y términos inmutables; discrepancias y fuentes faltantes | Las revisiones sintéticas no aprueban un préstamo real |
| Flujos por USD 10 | Sensibilidades D253/v10, deuda y cierre de venta | Conciliación D200 y movimientos brutos; amortización distinta de vencimiento | Retorno personal y dictamen real PENDING |

El contrato optativo `miniuw.synthetic-worksheet-sensitivities.v10` exige Base y Downside. Cada escenario declara de uno a cuatro cambios sin duplicados y `permanent_support` con un respaldo por cambio y otro para el conjunto. Cada cambio contiene `target_cell`, `operation`, `unit`, `value` racional explícito y `source_ref` sintético. C69 usa `annual_nominal_fraction`, C70 `years`, C71 `fraction` y C72 `multiple`. El ensayo usa reemplazos absolutos; C70 exige años enteros explícitos y C72 no acepta puntos porcentuales como múltiplos.

El JSON de los perfiles técnicos sintéticos v10 puede ocupar hasta 96 KiB por los PDF embebidos; cada PDF se limita a 32 KiB. Los contratos anteriores conservan sus límites, incluida la excepción v5 ya existente de 96 KiB. El lector por consola y el ensamblador comparten esta validación.

Ningún blanco se convierte en cero. Se prueban `null`, cadenas vacías, espacios, ausencia de fuente, unidades incompatibles y respaldos contradictorios. La tasa cero se calcula con amortización de principal; los ceros no válidos en otros campos quedan PENDING con su motivo. El ranking de deltas se retira cuando falta un cambio individual.

### Pendiente técnico de precisión

El ensayo inicial con C69 Base = 5,01 % encontró un límite anterior del transporte exacto de importes: el cronograma produce un principal de cuota con 370 dígitos de numerador y 366 de denominador, mientras los puentes de caja admiten 256 por entero. La fórmula de cuota no falló; el puente rechazó el importe exacto. Esa variante conserva la tasa declarada, caja PENDING, ranking retirado y motivo `permanent_exact_cash_transport_precision_unsupported`. No se redondea ni se sustituye el dato. El conjunto con 21 años también conserva el bloqueo, y Downside mantiene sus resultados disponibles.

Las tasas 6,00 % y 6,40 % del ensayo principal están identificadas como casos sintéticos separados. No corrigen ni reemplazan el caso bloqueado de 5,01 %. Sigue pendiente ampliar y versionar de punta a punta la precisión de los puentes de caja y sus productores/revisores, preservando la reproducción de expedientes anteriores. D262 no certifica cobertura de cualquier tasa válida ni cierre completo de ese pendiente.

## Reproducción

Con el runtime de OCR configurado en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_permanent_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_permanent_loan_D152.py --output /tmp/miniuw-d152
```

Este registro es documentación técnica interna. La entrega externa del motor conserva un PDF de una página. No se modifica el 1101, One Hollywood, los criterios de inversión ni las políticas pendientes. Sin despliegue ni decisiones reales. El respaldo excluye credenciales, expedientes reales, paquetes generados y registros de ejecución.

Validación en el VPS: cuatro pruebas nuevas en 240,051 segundos —ocho cambios individuales y dos conjuntos del ensayo principal, más faltantes, contradicciones, capacidad, ceros y el límite de precisión—; nueve controles unitarios anteriores; diecisiete casos completos D152 con diez PENDING esperados. B16 reprodujo el paquete D262 como VIGENTE y el D261 anterior sin diferencias. Los diez archivos generados por consola coincidieron byte a byte con D198. La prueba integrada está en `tests/test_worksheet_permanent_sensitivities.py`, método `PermanentSensitivityIntegrationTests.test_individual_joint_bank_binding_capacity_missing_and_zero`; los otros tres métodos comprueban el contrato, los límites de tamaño y las revisiones PDF/anexo. Son verificaciones dirigidas: la batería general completa no se repitió. El pendiente de precisión queda abierto aun cuando estas pruebas pasan, porque comprobar un bloqueo seguro no implementa la ampliación que falta.
