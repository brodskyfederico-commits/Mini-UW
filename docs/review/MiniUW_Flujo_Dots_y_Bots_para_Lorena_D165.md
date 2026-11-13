# Si invierto USD 10, ¿cuánto cobro y cuándo?

Guía para Lorena · Flujo del Mini-UW y estado a D164

Ejemplo sintético del equity agregado del proyecto. El aporte inicial es USD 10 el 30/03/2027 en ambos escenarios.

| Por USD 10 iniciales | Base | Downside |
|---|---|---|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| Total cobrado | USD 19,10 | USD 6,80 |
| Ganancia o déficit de caja | +USD 4,23 | −USD 11,39 |
| Múltiplo sobre todos los aportes | 1,28x | 0,37x |
| Sin recuperar al cierre | USD 0,00 | USD 11,39 |

Los totales se calculan antes de redondear. La página 4 detalla cada aporte adicional. La TIR y el retorno personal quedan PENDING para este expediente.

## Flujo por proyecto

1. **D01 · Recepción (B01–B03).** Registrar el proyecto, los archivos y su revisión. Distribuir las fuentes a las tres ramas de evidencia.
2. **D02 · Planilla (B04).** Validar los 55 campos y sus fuentes, unidades, escenarios y aplicabilidad. Registrar los criterios por separado.
3. **D03 · Planos y evidencia financiera (B05–B09).** B05 y B06 entregan sus lecturas a B07. En paralelo, **B08** lee cotización y préstamos. **B09** espera el área conciliada de B07 y la cotización de B08. Los términos bancarios de B08 siguen a D05.
4. **D04 · Datos oficiales (B10–B11).** Cotejar vigencia y cita en la copia disponible. D02, D03 y D04 entregan sus resultados y bloqueos a D05.
5. **D05 · Cálculo y evaluación (B12–B14).** Habilitar sólo los cálculos respaldados, calcular los flujos y cotejar criterios vigentes.
6. **D06 y D07 · Informe y auditoría (B15–B16).** Preparar una página por proyecto y reproducir el expediente. El carril humano revisa la versión antes de una decisión real.

**Calidad de versión.** B17 ejecuta las pruebas de regresión fuera de la corrida de cada proyecto.

<!-- page -->
# Carril humano

Los responsables se indican por función. La autoridad para aprobar un proyecto real debe quedar acreditada en su expediente.

| Quién interviene | Qué entrega o revisa | Qué permite reanudar |
|---|---|---|
| Lorena · Planilla y supuestos | Planilla Base y Downside con valores de métricas, fuentes, unidades y fechas. Aclara datos o diferencias frente al cálculo. | Planilla y respaldo corregidos. B04 valida otra vez y B12/B13 revisan dependientes. |
| Contratista general (GC) | Cotización vigente, área, alcance, inclusiones y exclusiones. Responde discrepancias con el plano. | B08 y B09 cotejan la nueva evidencia antes de usar el costo en B13. |
| Banco | Términos vigentes del préstamo de obra o permanente. Aclara importe, tasa, plazo, comisiones o condiciones en conflicto. | B08 coteja el documento y B13 recalcula deuda, capacidad y caja afectadas. |
| Responsable de evidencia oficial, por designar | Copia y cita verificables para la jurisdicción y fecha del caso. | B10 y B11 cotejan vigencia. B12 y B13 revisan los dependientes. |
| Responsable de criterios, por confirmar | Confirma definición, unidad, período, escenario, umbral, operador, igualdad y agregación aplicables. | B14 coteja los criterios de la revisión vigente. |
| Revisor financiero, por designar | Revisa evidencia, supuestos, cálculo, escenarios y excepciones de la versión que se va a entregar. | Deja constancia de alcance, hallazgos y revisión. Si cambia un dato o regla, se vuelve a revisar. |
| Persona autorizada para el paso a Full UW | Emite una aprobación final auténtica, con autoridad acreditada, alcance y versión identificados. | Un PASS vigente más esa aprobación permite evaluar el paso a Full UW. |

## Qué pasa ante un pendiente

- Registrar el dato o regla afectada, la fuente, el responsable, la evidencia esperada y los cálculos que dependen de ella.
- Conservar la revisión anterior. Ingresar la corrección por D01, recalcular lo afectado y repetir las revisiones que correspondan.
- **PENDING** por faltante, discrepancia, regla indefinida o banda intermedia. Un informe parcial puede mostrar las cifras conciliadas.
- **FAIL** si la evaluación completa incumple un criterio aplicable. **PASS** si la evaluación completa cumple los criterios vigentes. La aprobación final es un acto separado.
- B16 comprueba que el expediente sea reproducible. La revisión financiera y la aprobación están en el carril humano.

<!-- page -->
# Estados del flujo y de los bots

**VS** · Verificado con datos sintéticos en el alcance indicado. **PA** · Programado con alcance acotado y pruebas de partes del flujo. **P** · Pendiente. **VR** · Validado con datos reales. Ningún bot tiene estado VR.

El estado de cada Dot refleja el de sus bots menos avanzados. Se muestra aparte el estado del carril humano y de la operación real.

| Etapa | Estado | Controles y entregas |
|---|---|---|
| D01 · Recepción | PA | B01 VS orquesta. B02 VS coteja inventario y revisión. B03 PA clasifica los documentos de los perfiles probados. |
| D02 · Planilla | PA | B04 PA coteja 55 campos, unidades, revisión y fuentes. Los perfiles sintéticos prueban sólo mapeos y cálculos declarados. |
| D03 · Planos y evidencia financiera | PA | B05 PA lee A101. B06 PA lee A601. B07 PA concilia sus lecturas. B08 PA extrae y coteja cotización y préstamos. B09 PA compara área y alcance con la cotización de B08. |
| D04 · Datos oficiales | PA | B10 PA revisa la copia local. B11 PA cita el dato vigente en esa copia. La consulta externa autorizada está pendiente. |
| D05 · Cálculo y evaluación | PA | B12 VS conserva bloqueos sintéticos. B13 PA calcula NOI, caja, deuda, capacidad y retorno. B14 PA compara métricas según el perfil y criterios disponibles. |
| D06 · Informe | VS | B15 VS arma una página y conserva las fechas, cifras y bloqueos del expediente sintético. |
| D07 · Comprobación | VS | B16 VS reproduce fuentes, cálculo y salida. |
| Fuera del flujo · Calidad | VS | B17 VS corre regresiones por versión. |
| Carril humano y operación real | P | Quedan pendientes responsables con autoridad, revisión financiera independiente y validación con proyectos reales. |

## Estado por módulo

| Módulo | Estado | Alcance verificado y pendiente |
|---|---|---|
| M1 · Programa | PA | Áreas y alcance en planos sintéticos. Faltan formatos reales y tolerancias aprobadas. |
| M2 · Operación e impuestos | PA | Renta, gastos, seguro e impuesto sintéticos. Falta validar supuestos de mercado y reglas fiscales vigentes. |
| M3 · Presupuesto / M4 · Calendario / M5 · Deuda de obra | PA cada uno | Costos, plazos y desembolsos conciliados en el piloto. Faltan fuentes y condiciones de un caso real. |
| M6 · Refinanciación | PA | Cuota, capacidad LTV/DSCR y liquidación sintéticas. Falta validación bancaria real. |
| M7 · Tenencia, venta y retorno | PA | Caja agregada por USD 10. El reparto LP/GP y el retorno personal requieren términos documentados. |
| M8 · Escenarios | PA | Alternativas explícitas. Precio pedido frente a RLV sigue pendiente de definición. |
| M9 · Dictamen y auditoría | PA | Cotejo y reproducción sintéticos. Pendientes la revisión y la aprobación auténticas de un caso real. |

<!-- page -->
# Ejemplo · Movimientos por USD 10 iniciales

D164 · Equity agregado del proyecto. El 30/03/2027 se aportan USD 10,00 en Base y en Downside.

| Fecha | Movimiento | Base | Downside |
|---|---|---|---|
| 30/06/2027 | Aporte adicional | — | 0,76 |
| 30/09/2027 | Aporte adicional | 4,66 | 0,04 |
| 30/12/2027 | Aporte adicional | 0,05 | 7,03 |
| 30/03/2028 | Aporte adicional | 0,05 | 0,07 |
| 30/06/2028 | Aporte adicional | 0,05 | 0,07 |
| 30/09/2028 | Aporte adicional | 0,05 | 0,07 |
| 30/09/2028 | Cobro de refinanciación | 2,85 | — |
| 30/12/2028 | Aporte adicional | — | 0,07 |
| 30/12/2028 | Cobro de venta | 14,82 | — |
| 30/12/2028 | Cobro de operación | 1,43 | — |
| 30/03/2029 | Aporte adicional | — | 0,07 |
| 30/03/2029 | Cobro de refinanciación | — | 2,45 |
| 30/06/2029 | Cobro de venta | — | 3,81 |
| 30/06/2029 | Cobro de operación | — | 0,55 |

## Cómo leer el resultado

- El múltiplo divide los cobros por todos los aportes. La ganancia o déficit de caja es lo cobrado menos lo aportado. El saldo sin recuperar se mide al cierre de la venta.
- En D164, la TIR anual, el CoC y el valor del equity retenido quedan **PENDING** para esta guía. El retorno LP/GP y los impuestos personales requieren términos y tratamiento documentados. Las cifras del ejemplo son antes de impuestos personales.
- El ejemplo reproduce una corrida sintética con refinanciación. La decisión real queda **PENDING**.

## Evidencia técnica

D139 verificó el mapeo sintético de 55 campos. D138 probó el cotejo de planos en PDF. D147 unió los controles documentales y el motor. D164 verificó la cotización y cuatro préstamos de Base y Downside, con páginas giradas, recortadas y fuera de orden. Sus variantes probaron datos faltantes, discrepancias y duplicados. La matriz de cobertura enlaza cada afirmación con su evidencia y el pendiente correspondiente.
