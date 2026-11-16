# Si invierto USD 10, ¿cuánto cobro y cuándo?

**Mini-UW v1 · Informe técnico integral · D250**

Procedimientos, siete Dots, diecisiete bots y conexiones entre fuentes, variables, fórmulas y entregables. Alcance residencial de renta, refinanciación, tenencia y venta. El dictamen y el retorno histórico del 1101 real siguen **PENDING**.

## 1. Cierre y alcance

**Estado al 16/11/2026 22:29 UTC.** La batería de cierre del commit D249 está en curso en el VPS. En la sesión actual figuran 716 de 1.676 pruebas aprobadas y 0 fallos o errores registrados a este corte. El primer intento se interrumpió por el límite de duración de la terminal y la corrida se reinició en una sesión independiente. La última regresión completa documentada, D228, aprobó 1.649 unitarias, 26 suites de referencia y el ensayo integral D102. El piloto real sigue PENDING.

El diseño sintético de v1 cerró los **16 hitos** de D197 con la aceptación D200. Los casos de D228 a D249 agregan el control de vigencia del PDF, la configuración de criterios, los calendarios anuales con y sin refinanciación y las sensibilidades trazables. Este informe documenta el perfil ejecutado y las condiciones de otros perfiles conservados para reproducir ensayos anteriores. Toda cifra de ejemplo corresponde a equity agregado del proyecto de prueba, antes de impuestos personales. El retorno personal requiere un reparto aplicable y acreditado.

### Ejemplo anual con las cuatro rutas

| Ruta | Aporte extra | Cobro neto de refi | Operación | Venta neta y fecha | Cobro total | Sin recuperar |
| --- | --- | --- | --- | --- | --- | --- |
| Base · con refi | 4,87 | 2,03 · 30/09/2028 | 1,20 | 13,68 · 30/09/2029 | 16,92 | 0,00 |
| Base · sin refi | 4,87 | N/A | 1,35 | 15,73 · 30/09/2029 | 17,08 | 0,00 |
| Downside · con refi | 8,32 | 1,64 · 30/03/2029 | 0,21 | 3,08 · 30/03/2030 | 4,94 | 13,38 |
| Downside · sin refi | 8,23 | N/A | 0,41 | 4,82 · 30/03/2030 | 5,22 | 13,01 |

La venta neta de cada ruta y el último cobro suceden en la fecha de salida de esa ruta. La caja operativa se registra por período entre la estabilización y la venta. El anexo de movimientos muestra aportes y cobros separados incluso cuando coinciden en fecha. El saldo sin recuperar es nominal al cierre. Los ejercicios D239–D249 descontaron esa caja sólo para sensibilidades con tasa declarada.

**Referencias.** [Aceptación D200](worksheet-technical-acceptance-D200.md) · [Comparación D238](worksheet-annual-comparison-D238.md) · [Alcance congelado D189](preliminary-pilot-readiness-D189.md).

## 2. Procedimientos de punta a punta

1. **Recepción y registro.** Fijar ID de proyecto, moneda, fecha de corte y revisión. Inventariar los originales Base y Downside, planos, cotización GC, términos de obra y permanente si aplica, comparables, seguro, fuentes fiscales y criterios. Cada archivo guarda nombre, revisión y SHA‑256. Dos entradas con nombre parecido requieren cotejo de contenido, identidad y fecha.
2. **Planilla.** B04 verifica geometría, IDs, unidad, origen, unidad temporal y aplicabilidad. Guarda celda y rango exactos. Un dato vacío queda pendiente. El cero explícito se respeta cuando la fórmula lo admite. N/A requiere justificación por perfil. Cada escenario conserva sus fuentes. Los umbrales se cargan en un contrato separado y versionado.
3. **Planos, cotización y crédito.** B05 y B06 leen las hojas requeridas. B07 cruza evidencias. En paralelo, B08 lee cotización, mercado, seguro y términos bancarios. B09 espera la salida de B07 y B08 para cotejar moneda, área, alcance, exclusiones y costo. Los cuadros de superficies conservan GSF, NRSF, estacionamiento, sitio y áreas por uso con sus bases propias.
4. **Evidencia oficial.** B10 revisa la copia local autorizada y su aplicabilidad temporal. B11 localiza el dato, unidad, jurisdicción y fuente dentro del documento. El custodio confirma vigencia y alcance real. M2 recibe por separado las bases imponibles y millages de escolar y no escolar, las fechas de padrón y la evidencia de cada retasación aplicable.
5. **Dependencias y cálculo.** B12 abre sólo los cálculos con entradas respaldadas. B13 pasa de programa a ingresos y presupuesto, de presupuesto a calendario y deuda de obra, y de NOI y deuda a capacidad, operación, venta y retorno. Las cajas libre y restringida se concilian por fecha. Una refi superior a la capacidad bloquea esa ruta. Una ruta sin refi puede seguir si su propio plazo y sus fuentes concilian.
6. **Comparación de criterios.** B14 coteja valor e intervalo con umbral, operador, definición, unidad, escenario y fecha compatibles. En el perfil D230, se ensayan PASS, HOLD económico, HOLD por diligencia, FAIL y PENDING. En perfiles históricos, la banda intermedia se conserva PENDING según su política. El resultado operativo exige un criterio vigente aprobado. No se trasladan umbrales de una simulación a otra revisión.
7. **PDF y auditoría.** B15 arma una página para el deal. B16 reconstruye desde las fuentes, coteja huellas, fechas, cifras y PDF. El control documental audita afirmaciones por dato crítico. La exportación vuelve a cotejar expediente y revisión vigente inmediatamente antes de publicar. Una alteración, una cita crítica falsa o una revisión anterior bloquean la entrega aplicable.
8. **Corrección y revisión.** Guardar la revisión anterior. Registrar el nuevo respaldo, fuente, motivo, responsable y celdas afectadas. Reingresar por B02/B04 o el lector pertinente. Recalcular dependientes, reproducir en B16 y validar el PDF vigente. Denegar uso de una copia anterior aunque sus números coincidan. La revisión financiera independiente y la autorización proceden por el carril humano.
9. **Calidad por versión.** B17 prueba regresiones, ensayos de referencia y aceptación integrada en el código exacto. Registra resultados por suite y en el VPS. Esta actividad se realiza por versión, fuera de la ejecución de un deal.

### Dos formas de ingreso

| Ruta | Datos mínimos y cálculo | Entrega y bloqueo |
| --- | --- | --- |
| PRELIMINAR | Entradas Base/Downside con fuente, responsable, fecha y supuestos explícitos. El perfil de obra por etapas verifica desembolsos, deuda, caja y evidencia fiscal. El ensayo prioriza por múltiplo de Downside entre casos comparables. | Caja estimada por USD 10 y faltantes. Si falta un mínimo, falla la evidencia fiscal o excede capacidad, queda fuera del ranking. Dictamen formal PENDING. |
| Evaluación integrada | Dos planillas e inventario de documentos. Cotejo de fuentes, cálculos, métricas con sus períodos, criterios aplicables y revisión vigente. | PDF de una página con caja, métricas y estado. Mantener sólo cifras que tengan respaldo bajo la ruta evaluada. Repetir B16 para entregar una revisión nueva. |

**Secuencia de traspasos.** D01 distribuye a D02, D03 y D04. Los tres devuelven objetos verificados y motivos de bloqueo a D05. Dentro de D03, B09 sólo recibe el resultado de B07 y B08. D05 entrega cálculo y comparaciones a D06. D07 coteja la salida antes de la entrega. Las correcciones regresan a D01. B17 corre por versión.

**Referencias.** [PRELIMINAR D189](preliminary-pilot-readiness-D189.md) · [M2 en PRELIMINAR D204](workbook-preliminary-tax-D204.md) · [Inventario y armado D200](worksheet-technical-acceptance-D200.md) · [Evidencia crítica D219](workbook-critical-evidence-audit-D219.md).

### Archivos y puntos de entrada

| Operación | Entrada | Evidencia o salida |
| --- | --- | --- |
| `worksheet_intake_D198.py register` | Directorio de fuentes, identificación y revisión | Registro de huellas de archivos y celdas |
| `worksheet_intake_D198.py run` | Fuentes, registro y configuración versionada | Expediente derivado desde XLSX y respaldos |
| `miniuw_worksheet_v1.py audit` | Expediente y constancia de revisión vigente | Reproducción desde fuentes y estado de revisión |
| `lorena_screening.py rehearse-workbook` | Expediente auditado, configuración y ruta de tenencia si aplica | Comparaciones, métricas, motivos de PENDING y caja reproducida |
| `miniuw_worksheet_v1.py deliver` | Expediente auditado y revisión vigente | PDF vigente en un destino nuevo y recibo con huella |
| `miniuw_worksheet_v1.py compare-annual` | Las rutas anuales con y sin refi y el expediente vigente | Comparación de las cuatro cajas y fuentes exactas |
| `worksheet_preliminary_pilot_D205.py` | Inventario, planillas y respaldos vinculados a la fecha de corte | Evaluación PRELIMINAR con mínimo, ranking y auditoría del paquete |

El paquete integrado conserva `case.json`, `results.json`, `package.json` y `MiniUW_Resumen.pdf`. Según el perfil también conserva `Inputs.xlsx`, `Downside_Inputs.xlsx`, `Criterios_Lorena.xlsx`, `Plan.pdf`, `Evidence.pdf` y `current_revision.json`. El manifiesto marca los archivos del expediente, su tamaño y huellas. La entrega toma la designación de revisión vigente desde fuera de ese directorio. [Ingreso y entrega](worksheet-technical-acceptance-D200.md) · [Cotejo D231](worksheet-lorena-screening-D231.md).

## 3. Dots, bots y decisiones

| Dot | Función | Camino de salida |
| --- | --- | --- |
| D01 | Recepción, registros, orquestación y clasificación | Inventario y revisión para D02, D03 y D04 |
| D02 | Validación de planillas y registro de aplicabilidad | Filas tipadas, fuentes y faltantes para D05 |
| D03 | Planos, evidencia financiera y comprobación cruzada | Programa conciliado, respaldo de costo, banco, mercado y seguro para D05 |
| D04 | Evidencia oficial y vigencia | Dato oficial citado y aplicabilidad para D05 |
| D05 | Control de dependencias, cálculo y evaluación | Cajas por escenario, métricas, bloqueos y cotejos para D06 |
| D06 | Informe y control de presentación | PDF de una página y referencia del cálculo para D07 |
| D07 | Auditoría de expediente, con B17 como control de versión | Reproducción técnica y señal de entrega o bloqueo |

| Bot y Dot | Entrada y acción | Resultado y condición de bloqueo | Evidencia |
| --- | --- | --- | --- |
| B01 · D01 | Orquesta la ejecución por esquema, escenario y revisión. | Etapas ordenadas y expediente. Un contexto incompatible impide combinar resultados. | D147, D198–D200 |
| B02 · D01 | Registra archivos, huellas, metadatos y revisión. | Inventario por fuente. Una huella o revisión distinta invalida la referencia. | D198, D216 |
| B03 · D01 | Identifica páginas y categorías por inventario, formato, texto u OCR del perfil. | Páginas localizadas. Ausencia, ambigüedad o duplicados quedan pendientes. | D135, D158–D164 |
| B04 · D02 | Valida los 55 campos por escenario, plantilla y confirmaciones. | Filas tipadas con celda y estado. Vacío, cambio de unidad o plantilla incompatible bloquean dependientes. | D139, D171, D176 |
| B05 · D03 | Lee superficie y datos explícitos de A101. | Valor y cita con unidad, página y huella. Campo ilegible, ausente o conflictivo queda PENDING. | D130–D138 |
| B06 · D03 | Lee la fuente de contraste, A601 en el caso ensayado, y coteja texto y OCR donde aplica. | Lectura citada de la segunda fuente. Un conflicto conserva ambos valores. | D130–D138 |
| B07 · D03 | Conciliación de B05 y B06 bajo la regla declarada. | Área compatible entregada a B09. Faltante de una lectura o discrepancia detiene la conciliación. | D147, D208–D209 |
| B08 · D03 | Lee cotización, préstamos, comparables, concesiones, absorción, cap y seguro respaldados. | Afirmaciones localizadas para B09 y B13. Discrepancia de condiciones o evidencia oculta queda PENDING. | D156–D166 |
| B09 · D03 | Coteja áreas y alcance de B07 con costo vertical y cotización de B08. | Comparación GC documentada. Sin fuente, compatibilidad de base o autoridad de resolución, mantiene el bloqueo. | D147, D156, D219 |
| B10 · D04 | Valida inventario, fuente, autorización y vigencia de copia oficial local. | Registro documental fechado. La consulta externa de producción requiere autorización y fuentes de la jurisdicción. | D147, D156, D203 |
| B11 · D04 | Verifica el dato en la ubicación de la copia oficial. | Valor, unidad y cita con huella. Copia, cita o fecha ausente queda PENDING. | D147, D156, D219 |
| B12 · D05 | Consolida dependencia, completitud, capacidad y aplicabilidad por cálculo. | Libera cálculo respaldado y retiene los dependientes del faltante. Dictamen y caja tienen controles propios. | D146, D200, D220–D225 |
| B13 · D05 | Calcula presupuesto, NOI, deuda, venta y retorno con calendario explícito. | Libro de caja, métricas y fuentes reconciliadas. Saldo que descuadra o evidencia incompatible detienen el cálculo afectado. | D179, D200, D234–D249 |
| B14 · D05 | Aplica el contrato vigente de criterios a métricas compatibles. | Comparación por métrica y dictamen de ensayo. Bandas y faltantes quedan identificados según el contrato. | D193–D196, D218, D230–D237 |
| B15 · D06 | Renderiza el informe a partir del resultado reproducido. | PDF con aportes, cobros, fechas, saldos y estado. Un resultado incompleto o desactualizado limita la entrega bajo su perfil. | D181, D216–D229, D236–D238 |
| B16 · D07 | Reconstruye fuentes, cálculo, PDF y vigencia. Audita citas críticas y verifica revisión antes de entregar. | Constancia y huellas. Error de fuente, falso verde o cambio de revisión bloquean la exportación. | D200, D219–D228 |
| B17 · D07 | Ejecuta pruebas y controles de la versión publicada por separado. | Resultados de regresión. La evidencia se registra sobre el corte exacto. | D228, D250 |

**Alcance de los bots.** Las funciones corren localmente en los formatos y perfiles ensayados. D219 observó 48 de 48 datos críticos sintéticos con respaldo y detectó la alteración inyectada en cada uno. La tasa de errores con documentos reales requiere una muestra y una referencia independiente. D208–D209 aportan evidencia puntual del plano histórico 1101, con discrepancias registradas por hojas y efecto en cálculos. La autorización del expediente, el dictamen y el retorno histórico del 1101 siguen PENDING.

**Referencias.** [Contratos y etapas](MiniUW_v1_Dots_y_Bots.md) · [Flujo revisado D165](review/MiniUW_Flujo_Dots_y_Bots_para_Lorena_D165.md) · [Ingreso del plano D208](workbook-documentary-intake-D208.md) · [Checklist D209](workbook-plan-checklist-D209.md) · [Falsos verdes D219](workbook-critical-evidence-audit-D219.md).

## 4. Cómo se conectan los módulos

| Módulo | Inputs y conexión | Salidas y consumidores |
| --- | --- | --- |
| M1 · Programa | Planos, cuadro de unidades, áreas, espacios de parking y cotización. Unidades y superficies por uso, con revisión y fuente. | Cantidades para renta y seguro M2, GSF y plazas para M3. Una discrepancia compartida puede afectar ambos escenarios. |
| M2 · Operación e impuesto | Programa, comparables, vacancia, concesiones, servicios, controlables, seguro, reservas, impuestos, crecimiento y meses aplicables. | EGI, NOI operativo, NOI_uw, NOI bancario, NOI de valoración y NOI forward. Según su base, alimentan M6, M7 y las métricas de M9. |
| M3 · Adquisición y presupuesto | Precio evaluado y C33, costo vertical y base, parking, sitio, contingencia, soft y TI/LC. | Costo de terreno, hard directo, usos por partida y TDC reconciliado. M4 fecha usos, M5 financia y M8 recalcula bajo cambios de precio/obra. |
| M4 · Calendario | Fecha de compra, inicio y término de obra, TCO, lease-up, hitos de aportes, deuda, estabilización, venta y NOI forward. | Grillas y ventanas compatibles para ingresos, obra, deuda, caja, TIR y auditoría. |
| M5 · Deuda de obra | C51–C53, costo elegible, compromiso, disponibilidad, fechas, tasa y vencimiento. | Desembolsos, intereses, capital pendiente y aportes adicionales. El saldo se cancela al refinanciar o vender si se permite tenencia de la deuda. |
| M6 · Capacidad y refi | NOI bancario y de valoración, cap de refi, tasa y amortización, LTV, DSCR, límites aplicables, gastos y reserva. | Capacidad, cuota, plazo y tabla de deuda. El cierre liquida M5 y agrega cobro o aporte de equity. Los pagos y el saldo entran a M7. |
| M7 · Tenencia, venta y retorno | Caja operativa después de pagos y reservas, deuda vigente según ruta, NOI forward del comprador, cap de salida y costos. | Cobros fechados, aportes, reintegro de reservas, neto al vender, saldo sin recuperar, múltiplo, TIR, CoC, VAN y reparto si hay términos. |
| M8 · Escenarios, sensibilidad y RLV | Base/Downside explícitos, alternativas C80–C82 confirmadas, grilla de precio y política de evaluación. | Diferencias de caja, fronteras de recuperación y precio soportado. Recalcula dependencias y conserva referencias de la variante. |
| M9 · Dictamen y auditoría | Métricas de M2, M3, M6, M7 y M8, criterios versionados, evidencia y revisión de salida. | PASS, HOLD, FAIL o PENDING según contrato y evidencia. PDF vigente, rastro de validación y aprobación humana de ser aplicable. |

### Bases de NOI y período

| Indicador | Base para el cálculo |
| --- | --- |
| Operación | Ingresos y gastos reconocidos en la ventana operativa. La caja registra cobros y pagos fechados por separado. |
| NOI_uw | NOI del período después de reservas de reposición. Base de YoC y CoC del perfil de evaluación. |
| Spread | YoC en la base y ventana del cap comparable menos ese cap. Si el cap usa NOI antes de reservas, se usa el YoC antes de reservas para esta comparación. |
| Banco | NOI de sizing según las condiciones de crédito. Puede incorporar vacancia incremental H08, reservas u otros ajustes documentados. |
| Valoración de refi | NOI compatible con la evidencia del cap C66 en su ventana de valoración. |
| Venta | NOI forward del comprador, usualmente 12 meses en el perfil ensayado, con impuesto aplicable en la ventana y base del cap C67. |

### Efecto de una corrección

- **Área compartida.** Una discrepancia en el GSF de A101/A601 bloquea el costo por GSF y los flujos dependientes en ambos escenarios cuando usan el mismo plano. Corregir el respaldo y su cita restituye la evaluación de M3 y M5. Si cambia el dato real, revisar los usos dependientes y la caja. Si se restituye la fuente sin cambiar el valor, el nuevo expediente debe conciliar con el caso de control. [D222–D225](workbook-combined-citation-orders-D225.md).
- **Límite de Downside.** Una cita faltante o un cambio en C72 afecta la capacidad de refinanciación de Downside. B12 bloquea la salida que depende del préstamo, y el cálculo de capacidad vuelve a correr cuando se corrige su fuente. Base y la ruta sin refi se evalúan con sus propias dependencias. [D221](workbook-dscr-citation-recovery-D221.md) · [D237](worksheet-annual-sale-without-refinance-D237.md).
- **Costo de salida.** Cambiar C68 afecta la deducción sobre precio bruto. Manteniendo el precio y los otros flujos, Δ cobro neto de venta = −precio bruto × ΔC68. Cada movimiento por USD 10 conserva fecha y escala. La revisión corregida vuelve a pasar por B16. [D217](worksheet-technical-acceptance-D200.md#corrección-financiera-y-recálculo-para-la-entrega).

## 5. Carril humano y cierre real

| Intervención | Qué acredita | Dónde impacta |
| --- | --- | --- |
| Dueño de la información y equipo del proyecto | Planillas y documentos vigentes, supuestos por escenario, alcance de área y cotización, mercado y seguro. | B02–B09, M1–M5 y M7. |
| GC y banco | Alcance y costos de obra, términos y plazos bancarios, disponibilidad, cargos, vencimientos y covenants. | B08–B09, elegibilidad y capacidad M5–M6. |
| Custodio oficial | Autoridad de la fuente, copia, cita, jurisdicción, fecha y aplicabilidad, incluidos fiscal y AMI cuando correspondan. | B10–B11, M2 y validación real del programa. |
| Responsable de criterios | Definiciones SRC-02/SRC-03, bases y ventanas, umbrales por escenario, alcance del RLV sin refi y precedencia de un FAIL verificado con otros faltantes. | B14, M8–M9 y dictamen real. |
| Revisor financiero | Calcula referencia independiente, concilia cada flujo y compara métricas y dictamen en la versión vigente. | Cierre del piloto, hallazgos y autorización técnica registrada. |
| Aprobador autorizado | Autoriza el tratamiento de datos reales, registra su alcance y acredita la aprobación del paso a Full UW cuando corresponde. | Inicio del piloto y decisión humana explícita sobre el siguiente proceso. |

1. **Primer expediente autorizado.** Documentos Base y Downside, revisión financiera independiente, evidencia fiscal real y cotejo de los bots por dato crítico. El piloto puede documentar un FAIL o un PENDING fundado con trazabilidad completa.
2. **Backtest.** Comparar con 3–5 proyectos cerrados y explicar diferencias por fuente, plazo, costo, NOI, servicio, venta y aportes o cobros.
3. **Corrida en paralelo.** Comparar los 2–3 primeros expedientes con el proceso actual y registrar resolución de las diferencias y quién autoriza.
4. **Operación.** Documentar responsables y adopción de criterios. Los umbrales candidatos y la evidencia sintética quedan ligados a sus propias revisiones. El reparto personal queda PENDING hasta acreditar participación, capital, waterfall y términos de impuestos.

El 1101 real conserva el dictamen y el retorno histórico **PENDING**. El ensayo D249 de obra y venta corresponde a una sensibilidad sintética separada. El alcance de este informe es Mini-UW v1. El Full UW queda para su etapa de desarrollo.

**Referencias.** [Checklist D197](review/MiniUW_Cierre_Tecnico_y_Piloto_D197.md) · [Paquete de piloto D190](review/piloto-real-D190/README.md) · [Propuestas de dictamen D218](workbook-professional-proposals-D218.md) · [Screening D230](lorena-screening-D230.md) · [RLV y ruta sin refi D237](worksheet-annual-sale-without-refinance-D237.md).

## 6. Mapa de los 55 campos y ocho complementarios

El valor de cada campo original se lee en `Inputs!C<n>` por escenario y su definición documental se localiza en `Inputs!A<n>:F<n>`. Las filas complementarias se identifican por ID H01–H08. La [matriz CSV](review/MiniUW_Matriz_Campos_y_Conexiones_D250.csv) incluye documento original, ubicación, SHA‑256, unidad literal, fórmula o función de cada input, validación y evidencia real requerida. La [matriz documental de 398 requisitos](coverage-matrix.csv) preserva el inventario histórico de fuentes, conflictos y requisitos fuera del traspaso. Las tablas siguientes actualizan las conexiones que tienen evidencia posterior al inventario.

| Ubicación y unidad | Variable y cálculo | Módulo | Validación y pendiente |
| --- | --- | --- | --- |
| Inputs!C7 · PER UNIT / PER SF | **Rent basis**. Selecciona la unidad de renta de C8–C11. Por unidad usa la tarifa mensual. Por SF multiplica por área rentable por unidad. | M2 | [D140](workbook-rental-inputs-D140.md) · precios por unidad y por SF con cantidades y área respaldadas. Para uso real: Unidad de renta y plano. |
| Inputs!C8 · $ | **Market rent – Studio**. Renta mensual studio × unidades studio × meses, luego pérdidas y concesiones C14–C15. | M2 | [D140](workbook-rental-inputs-D140.md) · movimientos de renta por tipo y promedio cotejado. Para uso real: Tarifa y cantidad studio. |
| Inputs!C9 · $ | **Market rent – 1BR**. Renta mensual 1BR × unidades 1BR × meses, con factor C75 cuando aplica. | M2 | [D140](workbook-rental-inputs-D140.md) · efecto de tarifa y base alternativa en NOI y caja. Para uso real: Tarifa y cantidad 1BR. |
| Inputs!C10 · $ | **Market rent – 2BR**. Renta mensual 2BR × unidades 2BR × meses, según C7 y factor C75. | M2 | [D140](workbook-rental-inputs-D140.md) · conciliación de ingresos por tipo. Para uso real: Tarifa y cantidad 2BR. |
| Inputs!C11 · $ | **Market rent – 3BR**. Renta mensual 3BR × unidades 3BR × meses, según C7 y factor C75. | M2 | [D140](workbook-rental-inputs-D140.md) · conservación de grupos elegibles y montos. Para uso real: Tarifa y cantidad 3BR. |
| Inputs!C12 · text | **Rent comps reference**. Referencia a comparables de renta. B08 coteja mínimo ≤ renta ≤ máximo, con misma base y unidad. La referencia acredita el valor. | M2 y B08 | [D166](workbook-market-evidence-D166.md) · cita, rango y vigencia del comprobante de mercado. Para uso real: Comparables, citas, fechas y alcance. |
| Inputs!C13 · $/unit/month | **Other income**. Otros ingresos mensuales por unidad × unidades elegibles × meses. Su inclusión en la base de administración debe estar declarada. | M2 | [D140](workbook-rental-inputs-D140.md) · cero explícito y conciliación de otros ingresos. Para uso real: Elegibilidad, alcance y período. |
| Inputs!C14 · decimal | **Residential vacancy & credit loss**. Pérdida residencial = renta potencial × fracción de vacancia/pérdida. H08 aplica al NOI bancario. La ocupación física requiere separar pérdida crediticia y concesiones. | M2 y M6 | [D140](workbook-rental-inputs-D140.md) · impacto en renta efectiva y capacidad, C14 sin desglose en D184. Para uso real: Desglose y ajuste bancario H08. |
| Inputs!C15 · decimal of rent | **Lease-up concessions**. Concesión = fracción × base declarada. Si el contrato registra una deducción previa, aplicar el tratamiento documentado una sola vez. | M2 | [D140](workbook-rental-inputs-D140.md) · variación de concesión y base confirmada. Para uso real: Base, calendario y cobertura de la concesión. |
| Inputs!C16 · $/SF/yr | **Retail rent NNN**. Área retail elegible × tarifa NNN anual × meses reconocidos / 12. | M2 | [D141](workbook-commercial-inputs-D141.md) · calendario comercial y áreas por uso. Para uso real: Área y tarifa retail aplicables. |
| Inputs!C17 · $/SF/yr | **Restaurant rent NNN**. Área restaurante elegible × tarifa NNN anual × meses reconocidos / 12. | M2 | [D141](workbook-commercial-inputs-D141.md) · renta por uso y ausencia de aplicación por tipo. Para uso real: Área y tarifa restaurante aplicables. |
| Inputs!C18 · $/SF/yr | **Office rent NNN**. Área oficina elegible × tarifa NNN anual × meses reconocidos / 12. | M2 | [D141](workbook-commercial-inputs-D141.md) · ventana comercial efectiva por uso. Para uso real: Área y tarifa oficina aplicables. |
| Inputs!C19 · decimal | **Commercial vacancy**. Pérdida comercial = renta bruta comercial reconocida × fracción de vacancia. | M2 | [D141](workbook-commercial-inputs-D141.md) · conciliación anual, inicio diferido y vacío. Para uso real: Vacancia, fuente y ventana. |
| Inputs!C20 · decimal | **Commercial non-recoverable**. No recuperables comerciales = renta comercial después de vacancia × fracción, bajo la base NNN del perfil. | M2 | [D141](workbook-commercial-inputs-D141.md) · costo no recuperable y NOI por período. Para uso real: Contratos NNN y definición de gasto. |
| Inputs!C21 · months | **Commercial lease start after TCO**. Inicio de renta comercial = TCO + meses C21, limitado al período elegible. | M2 y M4 | [D141](workbook-commercial-inputs-D141.md) · demora que cambia meses reconocidos. Para uso real: TCO, cláusula y plazo. |
| Inputs!C25 · $/month | **Utility allowance – Studio**. Servicio studio = tarifa mensual × studios elegibles × meses. | M2 | [D142](workbook-utility-inputs-D142.md) · elegibilidad, variación de gasto y chequeo de duplicación. Para uso real: Servicio pagado por el propietario y unidades studio. |
| Inputs!C26 · $/month | **Utility allowance – 1BR**. Servicio 1BR = tarifa mensual × 1BR elegibles × meses. | M2 | [D142](workbook-utility-inputs-D142.md) · detalle de servicio por tipología. Para uso real: Servicio y unidades 1BR. |
| Inputs!C27 · $/month | **Utility allowance – 2BR**. Servicio 2BR = tarifa mensual × 2BR elegibles × meses. | M2 | [D142](workbook-utility-inputs-D142.md) · conciliación con gasto total. Para uso real: Servicio y unidades 2BR. |
| Inputs!C28 · $/month | **Utility allowance – 3BR**. Servicio 3BR = tarifa mensual × 3BR elegibles × meses. | M2 | [D142](workbook-utility-inputs-D142.md) · variación del gasto, NOI y flujos. Para uso real: Servicio y unidades 3BR. |
| Inputs!C32 · $ | **Land / asking price**. Precio pedido cotejado con precio evaluado. Compra a efectos de usos = precio evaluado + su cierre C33. Precio pedido se guarda por separado para RLV. | M3, M5 y M8 | [D143](workbook-development-inputs-D143.md) · precio compatible, diferencia bloqueada y efecto en aportes. Para uso real: Precio evaluado y respaldo del precio pedido. |
| Inputs!C33 · decimal | **Land closing costs**. Cierre = precio evaluado × C33. En RLV a deuda fija, ΔTDC = Δequity = Δprecio × (1 + C33). | M3 y M8 | [D143](workbook-development-inputs-D143.md) · cálculo de cierre y efecto en grilla D184/D233. Para uso real: Costos incluidos y criterio de RLV. |
| Inputs!C34 · $/GSF / $/UNIT / TOTAL | **Hard cost basis**. Selector de costo vertical: total, por unidad o por GSF. | M3 | [D143](workbook-development-inputs-D143.md) · variantes de base y correspondencia con el plano. Para uso real: Alcance y unidad de cotización. |
| Inputs!C35 · per basis | **Hard cost value**. Costo vertical = C35 × magnitud compatible con C34, o C35 en modo total. | M3 y M5 | [D143](workbook-development-inputs-D143.md) · conciliación con cotización de GC D147. Para uso real: Tarifa/monto vertical, moneda y alcance. |
| Inputs!C36 · SF | **Building GSF**. GSF para la base por SF. En el perfil D143, el plano documentado manda si declara GSF. El dato de planilla necesita habilitación de la rama y respaldo. | M1 y M3 | [D143](workbook-development-inputs-D143.md) · rama de GSF, unidad y conflictos documentales D208–D209. Para uso real: GSF y alcance de plano revisado. |
| Inputs!C37 · $/space | **Parking cost**. Parking = costo por plaza × plazas documentadas. | M3 y M5 | [D144](workbook-construction-budget-D144.md) · variación del costo por plaza y aportes. Para uso real: Conteo de plazas y costo. |
| Inputs!C38 · $ | **Site work**. Monto de trabajos de sitio como partida separada del costo vertical y parking. | M3 y M5 | [D144](workbook-construction-budget-D144.md) · variación de costo de sitio y caja por fecha. Para uso real: Alcance de obra de sitio. |
| Inputs!C39 · decimal | **Hard contingency**. Contingencia = fracción × hard directo de vertical, parking y sitio. | M3 y M5 | [D144](workbook-construction-budget-D144.md) · reserva fondeada y sensibilidad de base. Para uso real: Base y política de contingencia. |
| Inputs!C40 · decimal of hard | **Soft costs (incl. dev fee)**. Soft costs = fracción × hard después de contingencia en el piloto. Honorario de desarrollo incluido según alcance. | M3 y M4 | [D144](workbook-construction-budget-D144.md) · variación de soft costs y uso de calendario. Para uso real: Base, fee, seguro de obra y exclusiones. |
| Inputs!C41 · $/commercial SF | **TI / LC**. TI/LC = tarifa × SF comercial elegible. Cero o N/A se documentan si aplica. | M3 y M5 | [D144](workbook-construction-budget-D144.md) · ausencia, aplicabilidad y área comercial. Para uso real: TI/LC y área elegible. |
| Inputs!C42 · decimal | **Soft costs drawn up front (months 1–3)**. Soft temprano = soft total × C42. El restante se fecha en su hito posterior. | M4 y M5 | [D144](workbook-construction-budget-D144.md) · 0 % y 100 % mueven la fecha y conservan el total. Para uso real: Curva de pagos tempranos y fechas. |
| Inputs!C46 · months | **Construction period**. Fecha de fin de obra = inicio + meses C46, cotejada con TCO y desembolsos. | M4 y M5 | [D145](workbook-project-calendar-D145.md) · incompatibilidad temporal y calendario verificado. Para uso real: Inicio, término y TCO respaldados. |
| Inputs!C47 · months | **Lease-up period**. Lease-up = duración desde TCO al corte de estabilización del perfil. Meses y caja de absorción definen el calendario posterior. | M4, M5 y M7 | [D145](workbook-project-calendar-D145.md) · variación de plazo, soporte de mercado D166 y fechas de caja. Para uso real: Plazo de absorción y ventana estabilizada. |
| Inputs!C51 · decimal | **LTC**. Compromiso = min(LTC × costo elegible, tope contractual). Los desembolsos se limitan por fechas y saldo disponible. | M5 | [D146](workbook-construction-financing-D146.md) · cotejo de límite, disposición y fechas de deuda. Para uso real: Base de costo elegible, disponibilidad y monto. |
| Inputs!C52 · decimal | **Interest rate**. Interés simple trimestral = (principal de apertura + desembolso inicial) × nominal anual/4 en D146. | M5 | [D146](workbook-construction-financing-D146.md) · reconciliación de interés, principal y saldo. Para uso real: Convención, tasa y tratamiento de intereses. |
| Inputs!C53 · decimal | **Origination fee**. Comisión inicial = compromiso × C53 en D146. | M5 | [D146](workbook-construction-financing-D146.md) · comisión, uso de caja y aporte por fecha. Para uso real: Base y cobro de comisión bancaria. |
| Inputs!C57 · $/unit/yr | **Controllable opex**. Controlables = costo anual por unidad × unidades. Deducir servicios incluidos de la partida antes de sumarlos individualmente. | M2 | [D148](workbook-operating-costs-D148.md) · cotejo de alcance y bloqueo por servicios superiores al total. Para uso real: Gasto por unidad y partidas incluidas. |
| Inputs!C58 · decimal of res. EGI | **Management fee**. Administración = C58 × ingreso residencial efectivo de la base documentada. | M2 | [D148](workbook-operating-costs-D148.md) · reproducción sobre EGI en cada ventana. Para uso real: Contrato de gestión y base elegible. |
| Inputs!C59 · $/unit/yr | **Insurance**. Seguro = prima anual por unidad × unidades aseguradas, prorrateado por período. | M2 | [D148](workbook-operating-costs-D148.md) · prima y alcance cotejados con respaldo D166. Para uso real: Cotización vigente y unidades aseguradas. |
| Inputs!C60 · $/unit/yr | **Replacement reserves**. Reserva = tarifa anual × unidades elegibles y período. Depositar y liquidar en cuenta restringida, con liberación autorizada. | M2 y M7 | [D149](workbook-replacement-reserve-D149.md) · conciliación de depósito, pago y remanente. Para uso real: Base, elegibilidad y condiciones de liberación. |
| Inputs!C61 · decimal | **Assessment ratio (assessed ÷ market value)**. Ratio tasado/mercado de la rama proxy. En M2 D203 se usan avalúos y millages por separado bajo la evidencia del caso. | M2 | [D150](workbook-property-tax-D150.md) · rama circular y evidencia fiscal separada D203. Para uso real: Ratio aplicable y avalúos oficiales. |
| Inputs!C62 · $/unit/yr | **Property tax comps**. Piso fiscal de la rama por comparable = C62 × unidades comparables. PRELIMINAR v4 usa padrones y tasas documentados. | M2 | [D150](workbook-property-tax-D150.md) · cotejo del piso y variante fiscal D204. Para uso real: Impuesto comparable o fuente fiscal específica. |
| Inputs!C66 · decimal | **Market cap rate at refinance**. Valor de refi = NOI de valoración compatible / cap C66. Alimenta el límite LTV. | M6 | [D151](workbook-exit-pricing-D151.md) · cotejo del precio de valoración y la capacidad. Para uso real: Cap, base de NOI y ventana de valoración. |
| Inputs!C67 · decimal | **Exit cap rate**. Precio bruto = NOI forward compatible / cap de salida positivo. En sensibilidades se puede fijar precio bruto explícito. | M7 | [D151](workbook-exit-pricing-D151.md) · conciliación de salida, impuesto comprador D173/D203 y precio fijo D249. Para uso real: Cap de salida, fuente, base y ventana. |
| Inputs!C68 · decimal | **Sale costs**. Costo proporcional de venta = precio bruto × C68. Añadir costo fijo H07 separado. | M7 | [D151](workbook-exit-pricing-D151.md) · corrección financiera, recálculo B16 y PDF vigente D217. Para uso real: Comisión, cargos y exclusiones. |
| Inputs!C69 · decimal | **Perm loan rate**. Tasa por período = nominal anual / frecuencia según términos. Afecta servicio, capacidad y saldo. | M6 y M7 | [D152](workbook-permanent-loan-D152.md) · cuota, principal y prueba de tasa cero. Para uso real: Tasa, frecuencia, tipo, IO y términos. |
| Inputs!C70 · years | **Amortization**. Número de cuotas amortizantes = años × frecuencia. El vencimiento H02 es un término aparte. | M6 y M7 | [D152](workbook-permanent-loan-D152.md) · plazo, cuota y saldo a venta. Para uso real: Amortización y vencimiento separado. |
| Inputs!C71 · decimal | **Max LTV**. Capacidad LTV = fracción máxima × valor de refi. | M6 | [D152](workbook-permanent-loan-D152.md) · casos donde LTV limita o deja paso al DSCR. Para uso real: Máximo LTV y valor de garantía. |
| Inputs!C72 · x | **Min DSCR**. Capacidad DSCR = NOI bancario / (DSCR mínimo × constante anual). | M6 | [D152](workbook-permanent-loan-D152.md) · bloqueo por capacidad y recuperación de cita D221. Para uso real: Mínimo DSCR, base NOI y ventana. |
| Inputs!C73 · decimal of loan | **Refi costs**. Costo al refinanciar = principal solicitado × tasa de comisión, según base del préstamo. | M6 | [D153](workbook-refinance-costs-D153.md) · neto de cierre y fuente de costo. Para uso real: Término de comisión y costos fijos. |
| Inputs!C74 · $/unit | **Perm reserves**. Reserva permanente inicial = tarifa × unidades elegibles. Reduce cash-out y se liquida según términos al vender. | M6 y M7 | [D153](workbook-refinance-costs-D153.md) · saldo restringido y liquidación. Para uso real: Unidades, tarifa y disposición al vender. |
| Inputs!C75 · decimal / yr | **Rent growth**. Crecimiento de renta por aniversario = (1 + C75) elevado al número de aniversarios cumplidos. | M2, M6 y M7 | [D154](workbook-growth-D154.md) · NOI por ventana y refi por capacidad. Para uso real: Tasa, ancla, período y alcance. |
| Inputs!C76 · decimal / yr | **Expense growth**. Crecimiento de gastos según C76 y aniversario. La administración se recalcula sobre su propio ingreso elegible y los impuestos bajo su régimen. | M2, M6 y M7 | [D154](workbook-growth-D154.md) · prorrateo, tasa 0 % y variaciones de gastos. Para uso real: Componentes indexados, frecuencia y evidencia. |
| Inputs!C80 · input = value | **Alternative 1**. Primer espacio de alternativa. D155 ensaya cap de salida C67 con cambio estructurado y fuente. | M8 | [D155](workbook-alternatives-D155.md) · variante vuelve a correr venta y retorno. Para uso real: Instrucción de cambio tipada y confirmada. |
| Inputs!C81 · input = value | **Alternative 2**. Segundo espacio de alternativa. D155 ensaya costo de venta C68, incluido cero explícito. | M8 | [D155](workbook-alternatives-D155.md) · variante vuelve a correr cierre de venta. Para uso real: Cambio de base, unidad y aplicabilidad. |
| Inputs!C82 · input = value | **Alternative 3**. Tercer espacio de alternativa. D155 ensaya crecimiento de renta C75. Cada slot acepta los reemplazos soportados. | M8 | [D155](workbook-alternatives-D155.md) · variante recalcula NOI y puede bloquear por DSCR. Para uso real: Cambio confirmado y escenario de origen. |
| H01 · Fecha | **Fecha o horizonte de venta**. Define fecha de salida, último servicio de deuda y ventana forward. D234/D237 cubren cuatro trimestres según ruta. | M4 y M7 | [D237](worksheet-annual-sale-without-refinance-D237.md) · calendario, orden y cobro neto de la ruta anual. Para uso real: Calendario y horizonte contractual respaldados. |
| H02 · Cuotas | **Vencimiento de préstamo permanente**. Límite de calendario del préstamo. Saldo remanente se liquida según términos. C70 conserva amortización por separado. | M6 y M7 | [D174](workbook-supplemental-scope-D174.md) · vencimiento compatible y bloqueo por fecha. Para uso real: Fuente, vencimiento y balloon. |
| H03 · Declaración | **Aplicabilidad Live Local**. Selecciona aplicabilidad bajo la evidencia del programa. El perfil ensayado admite no aplicabilidad explícita. | M1 y M2 | [D174](workbook-supplemental-scope-D174.md) · bloqueo sin evidencia y perfil no aplicable. Para uso real: Elegibilidad y vigencia oficiales. |
| H04 · Cantidad o % | **Unidades o participación asequible**. Identifica el grupo de unidades alcanzadas, con evidencia de conteo y alcance. Cualquier ajuste de renta depende de elegibilidad. | M1 y M2 | [D174](workbook-supplemental-scope-D174.md) · captura y revisión de aplicabilidad. Para uso real: Identificación de unidades y regla aplicable. |
| H05 · Nivel documentado | **Niveles AMI**. Declara tramo AMI y fuente. Un límite de renta o beneficio exige términos y evidencia vigentes. | M1 y M2 | [D174](workbook-supplemental-scope-D174.md) · captura sin aplicar una regla sin evidencia. Para uso real: Límites y documentación AMI. |
| H06 · Referencia | **Definición de Downside integrado**. Vincula los dos XLSX con su revisión. Aplica conjuntamente los supuestos aprobados del escenario. | M8 | [D174](workbook-supplemental-scope-D174.md) · huellas por escenario y revisión. Para uso real: Supuestos de Downside y su autoridad. |
| H07 · USD | **Costos fijos de venta**. Costo total de salida = precio × C68 + costo fijo H07 documentado, con inventario sin solapamiento. | M7 | [D174](workbook-supplemental-scope-D174.md) · USD 0 explícito y diferencia exacta de cobro. Para uso real: Cargos y exclusiones de cierre. |
| H08 · Fracción | **Vacancia adicional bancaria**. Pérdida de sizing bajo el perfil = C14 + H08. Alimenta el NOI bancario y el DSCR, según términos. | M6 | [D174](workbook-supplemental-scope-D174.md) · ajuste bancario y cero explícito. Para uso real: Regla de banco aprobada y unidad. |

## 7. Catálogo de fórmulas y perfiles

Los símbolos representan magnitudes de la misma moneda, unidad y ventana. Los cálculos de caja y comparaciones preservan cantidades exactas y redondean la presentación. «Perfil sintético» identifica un cálculo ejecutado en las entradas ensayadas. «Referencia» identifica una fórmula documentada con su alcance. Las ramas de uso real requieren base, aplicabilidad y autorización.

### M1 · Entradas, unidades, áreas y evidencia

**GSF, NRSF y cantidades.** Área bruta = Σ áreas brutas documentadas de alcance disjunto. NRSF de un grupo = unidades × área rentable por unidad cuando esa base está declarada. Área total de sitio, estacionamiento y áreas rentables por uso se conservan por separado.

*Perfil sintético documentado.* Referencia: `docs/model-input-evidence.md; tools/worksheet_development_inputs_D143.py`.

**Conversión y control cruzado.** m² = SF × 0,09290304. SF = m² / 0,09290304. Diferencia de área = lectura A − lectura B o plano conciliado − GC, según el cotejo. Comparar alcance y unidad antes de aplicar la tolerancia declarada.

*Perfil sintético documentado.* Referencia: `tools/worksheet_documented_finance_D147.py; tools/worksheet_local_sources_D127.py`.

**Fracciones y unidades.** % mostrado = 100 × fracción. Un punto porcentual = 0,01; un punto básico = 0,0001. Conservar cantidades exactas hasta la presentación.

*Perfil sintético documentado.* Referencia: `docs/model-scenarios-price.md; src/miniuw_foundation/debt_service.py`.

**Cotejo de evidencia.** Para el piloto D166, mínimo ≤ valor de planilla ≤ máximo con misma unidad y base. Vigencia = fecha observada ≤ fecha del expediente ≤ válida hasta. Seguro = coincidencia de prima unitaria, cantidad y alcance. Los términos bancarios y el presupuesto se cotejan con sus respectivos documentos.

*Perfil sintético documentado.* Referencia: `tools/worksheet_market_evidence_D166.py; tools/worksheet_evidence_pdf_D156.py`.

**Escaneos y alcance.** Gris = piso((299 R + 587 G + 114 B + 500)/1000). Tras normalizar giro y recorte se cotejan las citas visibles. Confianza, páginas faltantes, duplicados y discrepancias bloquean según el perfil.

*Perfil sintético documentado.* Referencia: `tools/worksheet_evidence_scan_D158.py; tools/worksheet_plan_crop_D138.py`.

**Áreas y normas reales.** Tolerancia de discrepancias, método de medición, elegibilidad AMI y autoridad de la fuente requieren definición aplicable. Las cantidades de un plano se toman de datos explícitos en los perfiles probados.

*Aplicabilidad o evidencia real PENDING.* Referencia: `M1-01 a M1-08; docs/requirements-conflicts.md`.

**Identidad de área de una hoja y diferencia de plano.** Valor cotejado = dato explícito con misma unidad, revisión y alcance. Diferencia = valor documentado A − valor documentado B. Una hoja faltante, duplicada o con moneda/base incompatible no se resuelve por promedio.

*Sintético y cotejo documental acotado del 1101.* Referencia: `docs/workbook-plan-set-D135.md; docs/workbook-documentary-intake-D208.md; docs/workbook-plan-checklist-D209.md`.


### M2 · Rentas, operación, NOI, impuestos y ocupación

**Renta por tipo y base · C7–C11.** Renta mensual unitaria = tasa por unidad, o tasa por SF rentable × SF rentable por unidad. Renta potencial del grupo = unidades × renta mensual unitaria × meses. Sumar grupos disjuntos.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/rental_operations.py`.

**Vacancia, pérdidas y concesiones · C14–C15.** Pérdida = renta potencial × fracción de pérdida. Renta posvacancia = potencial − pérdida. Concesión = fracción × base declarada (potencial o posvacancia); si ya está descontada, concesión adicional = cero documentado. Renta efectiva = posvacancia − concesión. El NOI bancario del piloto aplica su pérdida incremental declarada.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/rental_operations.py; tools/worksheet_rental_inputs_D140.py`.

**Otros ingresos · C13.** Otros ingresos = importe mensual por unidad elegible × unidades elegibles × meses. Base de management según el alcance declarado.

*Perfil sintético documentado.* Referencia: `tools/worksheet_rental_inputs_D140.py`.

**Comercial NNN · C16–C21.** Inicio = TCO + meses de demora. Meses reconocidos = max(0, inicio de ventana + 12 − max(inicio de ventana, inicio de renta)), en índices de mes. Bruto = Σ(área por uso × tarifa anual) × meses equivalentes / 12. Pérdida = bruto × vacancia. No recuperable = (bruto − pérdida) × fracción. Neto = bruto − pérdida − no recuperable.

*Perfil sintético documentado.* Referencia: `tools/worksheet_commercial_inputs_D141.py`.

**Gastos por tipo de unidad · C25–C28.** Servicios anuales = Σ(tarifa mensual del tipo × unidades elegibles × 12). Los servicios incluidos en controlables se restan del subtotal controlable antes de sumarlos como partidas separadas.

*Perfil sintético documentado.* Referencia: `tools/worksheet_utility_inputs_D142.py; tools/worksheet_operating_costs_D148.py`.

**Controlables, administración y seguro · C57–C59.** Controlables = C57 × unidades declaradas. Administración = C58 × EGI residencial de la base aplicable. Seguro = C59 × unidades aseguradas. Gasto unitario anual prorrateado = tarifa × unidades × meses/12. Gasto fijo = importe del período.

*Perfil sintético documentado.* Referencia: `tools/worksheet_operating_costs_D148.py; src/miniuw_foundation/rental_operations.py`.

**Reserva de reposición · C60.** Depósito = tarifa × unidades elegibles. Saldo restringido final = saldo inicial + depósitos − usos − liberaciones. Liberado en venta = saldo × fracción documentada; remanente = saldo − liberado. Separar NOI, gasto y movimiento de caja.

*Perfil sintético documentado.* Referencia: `tools/worksheet_replacement_reserve_D149.py; tools/plan_refinance_D108.py; src/miniuw_foundation/operating_cash.py`.

**NOI antes de impuesto.** A = renta residencial efectiva + otros ingresos + ingreso comercial neto + otros ingresos explícitos − gastos operativos sin impuesto. NOI = A − impuesto. La caja distribuible usa cobros y pagos fechados.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/rental_noi.py; src/miniuw_foundation/operating_noi.py`.

**Impuesto y NOI circular · C61–C62.** F = impuesto comparable anual por unidad × unidades comparables. k = ratio de assessment × tasa aplicable / cap proxy. N = A − max(F, kN). Solución N = min(A − F, A/(1+k)); T = A − N. En rama de impuesto fijo, N = A − T fijo.

*Perfil sintético documentado.* Referencia: `tools/worksheet_property_tax_D150.py; src/miniuw_foundation/operating_noi.py`.

**Crecimiento de rentas y gastos · C75–C76.** Factor de un mes = (1 + crecimiento anual)^floor(meses desde ancla / 12). El factor de una ventana de 12 meses es el promedio de sus factores mensuales. Para el ingreso comercial usar los meses aplicables; los costos y sus bases conservan su alcance.

*Perfil sintético documentado.* Referencia: `tools/worksheet_growth_D154.py; tools/worksheet_commercial_inputs_D141.py`.

**Prorrateo y reconocimiento.** Meses aplicables por intersección de la disponibilidad documentada y la ventana. Reconocimiento por tramo = cantidad elegible × tarifa × fracción temporal declarada. Cobros, devengo y gastos reconocidos conservan sus fechas.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/rental_calendar.py; src/miniuw_foundation/phased_rental.py`.

**Ocupación de equilibrio.** Con A(q) = s q + b e impuesto max(F,kN), N(q) ≥ DS si s q + b ≥ DS + max(F,kDS). Para s>0, q* = [DS + max(F,kDS) − b]/s. Intersectar con el dominio declarado. s=0, pendiente negativa o frontera imposible requieren tratamiento explícito.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `docs/model-operations-contract.md; tools/check_breakeven_occupancy_D72.py`.

**Impuesto, AMI y mercado reales.** La aplicabilidad a cada inmueble requiere jurisdicción, régimen, comprobantes, fechas de valuación, exenciones y tasas certificadas. D203 y D204 prueban el cálculo fiscal bajo evidencia sintética por ventana. Mercado y seguro deben tener fuente, fecha y base.

*Aplicabilidad o evidencia real PENDING.* Referencia: `M2-01 a M2-08; docs/workbook-market-evidence-D166.md`.

**NOI de underwriting.** NOI_uw = NOI antes de reservas − reserva de reposición de la ventana. En el ensayo anual, reserva anual C60 por unidades elegibles se carga según su regla y período. El descuento de reserva en la métrica se concilia por separado con su movimiento de caja restringida.

*Perfil sintético.* Referencia: `docs/workbook-performance-policy-D184.md; tools/worksheet_definition_screening_D193.py`.

**Ocupación económica de equilibrio · SRC-02.** Con ingreso neto previo a impuesto A(q) = s × q + b y s positivo, definir X = servicio anual de deuda + reserva anual. q económica = max(0, [X + max(F, k × X) − b] / s) para la rama fiscal ensayada antes de reservas. Si q>1, el equilibrio no es alcanzable en el dominio. En la rama fija el término de impuesto es el monto fijo.

*Perfil sintético. Adopción y base real pendientes.* Referencia: `tools/worksheet_performance_policy_D184.py · equilibrium; tools/worksheet_definition_screening_D193.py · occupancy`.

**Ocupación física de equilibrio.** q física = q económica / [(1 − pérdida de crédito) × (1 − concesiones)] sólo con ambos factores desagregados y compatibles. C14 combinado deja la física PENDING. El mayor que 100 % se conserva como no alcanzable.

*Perfil sintético.* Referencia: `docs/workbook-performance-policy-D184.md; tools/worksheet_performance_policy_D184.py · equilibrium`.

**Corte fiscal de obra.** Base sintética al 1 de enero = terreno más mejoras que cumplen la condición documentada de utilización al corte. Una mejora sin fecha o clasificación aplicable bloquea el cálculo. El ejemplo D199 verifica fechas antes, en y después del corte.

*Ensayo de corte, validación del predio pendiente.* Referencia: `docs/worksheet-technical-acceptance-D200.md; tools/check_worksheet_technical_acceptance_D200.py`.

**Florida 2027 y retasación.** En el perfil alcanzado, en año sin ajuste: tasación no escolar = min(valor justo, tasación previa × 1,05) desde el padrón 2027. Ante retasación aplicable y respaldada, se usa valor justo del padrón definido por el caso. Mantener base imponible escolar aparte. Clasificar exclusiones, ajustes y mejoras; el tope aplica a tasación, el impuesto usa millage.

*Perfil sintético D203, aplicabilidad real PENDING.* Referencia: `tools/worksheet_florida_tax_D203.py · assessed_value; docs/workbook-florida-tax-D203.md`.

**Millage y ponderación mensual.** Impuesto anual = (base imponible escolar × millage escolar + base imponible no escolar × millage no escolar) / 1.000. Para una ventana que cruza padrones, impuesto de ventana = Σ impuesto de cada padrón × meses aplicables / 12. Ajustar el NOI de salida con el padrón del comprador según fecha y evidencia.

*Perfil sintético.* Referencia: `tools/worksheet_florida_tax_D203.py · window_taxes; docs/workbook-preliminary-tax-D204.md`.


### M3 · Adquisición, presupuesto y TDC

**Compra y cierre · C32–C33.** Cierre de compra = precio evaluado × fracción de cierre. Total de terreno = precio evaluado + cierre. Mantener asking y precio evaluado separados.

*Perfil sintético documentado.* Referencia: `tools/worksheet_development_inputs_D143.py`.

**Obra vertical · C34–C36.** Costo vertical = tarifa × cantidad compatible: unidades, GSF, NRSF u otra base explícita del perfil. Cotización GC conciliada por costo, moneda, alcance y área.

*Perfil sintético documentado.* Referencia: `tools/worksheet_development_inputs_D143.py; tools/worksheet_documented_finance_D147.py`.

**Parking, sitio y contingencia · C37–C39.** Parking = costo por espacio × cantidad. Hard directo = vertical + parking + sitio. Contingencia = hard directo × fracción. Hard total = hard directo + contingencia.

*Perfil sintético documentado.* Referencia: `tools/worksheet_construction_budget_D144.py`.

**Soft, TI/LC y adelanto · C40–C42.** Soft = tasa × hard del alcance declarado. TI/LC = tarifa × área comercial elegible. Soft temprano = soft × fracción inicial. Soft restante = soft − soft temprano.

*Perfil sintético documentado.* Referencia: `tools/worksheet_construction_budget_D144.py`.

**Costo total y conciliación.** Presupuesto antes de financiación = terreno + hard + soft + TI/LC. TDC all-in = Σ partidas mutuamente excluyentes, con financiación y reservas sólo según su alcance documentado. Equity/TDC = equity aplicado al corte / TDC compatible, con TDC positivo y cuadre de usos y fuentes.

*Perfil sintético documentado.* Referencia: `tools/worksheet_construction_budget_D144.py; tools/worksheet_yoc_spread_D123.py; tools/check_equity_tdc_D71.py`.

**Escalamiento contractual y honorarios.** Ajuste de costos por índice, banda o fórmula polinómica depende de coeficientes, fechas base, alcance, pesos y topes documentados. No hay coeficiente general aprobado.

*Aplicabilidad o evidencia real PENDING.* Referencia: `docs/model-budget-schedule.md`.

**Sensibilidad de recorte directo.** Con recorte r, multiplicar vertical, parking y sitio por 1 − r. Recalcular contingencia, soft según su base, costos por etapa, desembolsos, intereses y caja. Mantener precios, alcance no afectado y la deuda conforme a sus reglas.

*Perfil sintético D241–D249.* Referencia: `tools/worksheet_annual_crossover_construction.py · construction_at_cut; docs/worksheet-downside-additional-construction-cut-D248.md`.


### M4 · Calendario, devengo, desembolsos y estabilización

**Hitos de obra y operación · C46–C47.** Fin de obra = inicio + meses C46. TCO explícito. Estabilización = TCO + meses C47. El perfil trimestral D145 toma el corte previo al TCO, le suma C47, fija refi a +9 meses y venta a +12 meses desde ese corte. La salida usa 12 meses forward.

*Perfil sintético documentado.* Referencia: `tools/worksheet_project_calendar_D145.py`.

**Curva y pagos.** Pago de partida j en t = presupuesto j × peso jt. En programación completa, Σ_t peso jt = 1 y cada peso ≥0. Saldo sin asignar = presupuesto − Σ pagos. Los pesos de obra temprana y soft inicial se aplican por separado.

*Perfil sintético documentado.* Referencia: `docs/model-budget-schedule.md; tools/worksheet_construction_budget_D144.py`.

**Estabilización y aportes tempranos.** Reserva de estabilización del piloto = faltante mensual declarado × meses de lease-up. Aporte temprano sin deuda de ese perfil = max(0, usos tempranos − equity inicial); aporte posterior = costo total − equity inicial − aporte temprano.

*Perfil sintético documentado.* Referencia: `tools/worksheet_project_calendar_D145.py; tools/worksheet_construction_budget_D144.py`.

**Devengos, cuentas por pagar y anticipos.** CxP final = CxP inicial + devengos − pagos + ajustes. Anticipos finales = anticipos iniciales + nuevos anticipos − aplicaciones − devoluciones. El libro de caja lleva desembolsos efectivos.

*Perfil sintético documentado.* Referencia: `docs/model-cash-contracts.md; src/miniuw_foundation/expense_cash_detail.py`.

**Forma de curva y retrasos.** La curva histórica sin² requiere discretización, pesos, alcance y fechas aprobadas. Los retrasos cambian gastos y calendario sólo según los términos aplicables.

*Aplicabilidad o evidencia real PENDING.* Referencia: `M4-02 a M4-06; docs/model-budget-schedule.md`.


### M5 · Financiación de obra, cuentas y reservas

**Compromiso y desembolso · C51.** Compromiso = min(LTC × costo elegible, tope contractual). Draw = menor de la solicitud admisible y límites de disponibilidad por fecha y saldo de compromiso según el contrato. Las fuentes de fondos no desembolsadas se conservan como capacidad.

*Perfil sintético documentado.* Referencia: `tools/worksheet_construction_financing_D146.py; src/miniuw_foundation/construction_cash.py`.

**Interés y comisión · C52–C53.** En el perfil de obra D146, interés trimestral = (principal de apertura + draw) × nominal anual/4. Comisión de origen = compromiso × tasa C53. Otros perfiles usan base y fracción temporal explícitas. Conciliar pagado, capitalizado y cambio en intereses por pagar.

*Perfil sintético documentado.* Referencia: `tools/worksheet_construction_financing_D146.py; docs/model-construction-finance.md`.

**Recurrencia del principal.** Principal final = inicial + draws + interés capitalizado + incrementos − amortización − otras reducciones. Liquidación = principal pendiente + intereses/fees/ajustes exigibles. Validar corte y vencimiento antes de usar deuda en otro módulo.

*Perfil sintético documentado.* Referencia: `docs/model-construction-finance.md; src/miniuw_foundation/preopening_cash.py; src/miniuw_foundation/debt_closing.py`.

**Caja, financiación y déficit.** Caja final = caja inicial + cobros y financiación − pagos y distribuciones. Separar caja libre y restringida. Necesidad de equity por fecha = usos − caja y desembolsos aplicables, bajo la regla de financiación documentada. Un déficit no financiado conserva el bloqueo.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/preopening_cash.py; src/miniuw_foundation/project_cash.py; tools/worksheet_construction_financing_D146.py`.

**Cierre circular reducido TDC/interés.** Si C es costo previo, L=λT, comisión=fL, interés=kL y q=λ(f+k), entonces T=C+qT; T=C/(1−q) y E=(1−λ)T cuando procede. Para C>0 y 0≤q<1, T_(n+1)=C+qT_n converge. q=1 puede dejar la ecuación sin solución o indeterminada.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `docs/model-construction-finance.md; references/validate_m5_algebra.py`.

**Financiación por etapas.** Draw por fecha = importe elegible × cuota de desembolso documentada, sujeto a compromiso y disponibilidad. Diferencia de financiación de cada fecha = usos, cargos e intereses menos caja de apertura y draws. Después de la compra se aporta max(0, diferencia) bajo D146. El primer aporte está identificado por separado.

*Perfil sintético.* Referencia: `tools/worksheet_construction_financing_D146.py · staged_construction_financing; tools/worksheet_preliminary_stages_D188.py`.


### M6 · Refinanciación, capacidad y deuda permanente

**Valor y límites · C66, C71, C72.** Valor refi = NOI de valoración / cap refi. Límite LTV = máximo LTV × valor. Límite DSCR = NOI bancario / (DSCR mínimo × constante anual de deuda). Capacidad = mínimo de los límites documentados.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/refinance_capacity.py; tools/worksheet_permanent_loan_D152.py`.

**Tasa, amortización y cuota · C69–C70.** i = nominal anual / pagos por año bajo la convención del piloto. n = años × frecuencia. Factor de cuota a = i/[1−(1+i)^(-n)] si i>0; a=1/n si i=0. Cuota = principal × a. Constante anual = frecuencia × a.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/debt_service.py; tools/worksheet_permanent_loan_D152.py`.

**Tabla de deuda y balloon.** Interés t = principal de apertura × i. Capital de cuota = cuota − interés. Saldo final = saldo inicial − capital de cuota. Balloon al vencimiento = saldo remanente después de cuota. Servicio fechado = cuotas dentro de la ventana según inclusión de balloon declarada.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/debt_service.py; src/miniuw_foundation/debt_dscr.py`.

**LTV y DSCR realizados en sizing.** LTV = principal seleccionado / valor positivo. DSCR de sizing = NOI bancario / (principal seleccionado × constante anual), con servicio positivo. DSCR fechado = NOI de ventana / servicio compatible. Préstamo sobre capacidad queda PENDING en el piloto.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/refinance_capacity.py; src/miniuw_foundation/debt_dscr.py`.

**Costos, reservas y cash-out · C73–C74.** Cargo proporcional = préstamo × tasa; reserva = base elegible × tarifa declarada. Neto refi = proceeds recibidos + caja autorizada + liberaciones − cancelaciones − cargos − depósitos restringidos. Distribución = max(neto,0); cash-in = max(−neto,0) si la regla lo admite.

*Perfil sintético documentado.* Referencia: `tools/worksheet_refinance_costs_D153.py; src/miniuw_foundation/closing_cash.py`.

**Debt yield y préstamos reales.** El uso de debt yield, la base de NOI, el denominador, el umbral y el tratamiento en el sizing requieren términos bancarios aplicables. Validación de disponibilidad y condiciones reales permanece pendiente.

*Aplicabilidad o evidencia real PENDING.* Referencia: `docs/model-refinance-contract.md; revisión profesional p. 3`.

**Interés solo seguido de amortización.** En IO, pago = saldo × tasa periódica y principal pagado = 0. Después de IO, el perfil ensayado calcula la cuota con los períodos de amortización remanentes. Para sizing usa el servicio anual amortizante. Cancelar por el saldo verificado tras la última cuota aplicable.

*Perfil anual con refi.* Referencia: `tools/worksheet_calendar_routes_D199.py; docs/worksheet-annual-holding-D234.md`.

**Debt yield si aplica.** Debt yield = NOI bancario / principal del préstamo, con ambos definidos en los términos. Un límite por debt yield sólo entra con umbral y regla bancaria aplicables; las rutas principales de planilla ensayadas dimensionan con LTV y DSCR.

*Definición contractual, integración para el caso real pendiente.* Referencia: `docs/model-refinance-contract.md; docs/workbook-permanent-loan-D152.md`.


### M7 · Tenencia, venta, caja, métricas y reparto

**Operación, liquidez y deuda.** Caja neta operativa = cobros − pagos − servicio de deuda − depósitos + liberaciones, conforme al inventario. Distribución y aporte se registran como eventos brutos separados. Pico de financiación y faltante se calculan sobre la secuencia de caja, con el orden intradía declarado.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/operating_cash.py; src/miniuw_foundation/cash_risk.py; src/miniuw_foundation/participant_cash_risk.py`.

**Valor de salida y costo · C67–C68.** Valor = NOI forward 12 meses / cap de salida positivo. Costo total de venta = Σ costos fijos + precio bruto × Σ tasas sobre precio. En intervalos se aplican los límites declarados.

*Perfil sintético documentado.* Referencia: `tools/worksheet_exit_pricing_D151.py; src/miniuw_foundation/sale_costs.py; src/miniuw_foundation/bounded_sale_costs.py`.

**Cobro de venta y liquidación.** Neto de venta = precio cobrado + caja libre autorizada + liberaciones − costos − impuestos aplicables − deuda y demás obligaciones. Reserva transferida = saldo restringido − liberado − otros usos autorizados. Conservar caja, deuda y reserva final.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/closing_cash.py; src/miniuw_foundation/hold_sale_cash.py; tools/plan_refinance_D108.py`.

**Caja por USD 10 y ganancia.** Factor = 10 / aporte inicial verificado. Cada importe normalizado = importe bruto × factor; fecha intacta. Ganancia = Σ cobros − Σ aportes. Sin recuperar al cierre = max(0, aportes − cobros). Equity Multiple = Σ cobros / Σ aportes, con denominador positivo.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/investor_returns.py; tools/worksheet_investor_D74.py`.

**TIR periódica y anual · D167.** VAN(r) = Σ flujo_neto_t/(1+r)^t, r>−1. Con x=1/(1+r)>0 aislar todas las raíces de Σ flujo_neto_t x^t. Si hay una sola raíz y la grilla es compatible, anualizar (1+r)^frecuencia−1. D166 usa 4 trimestres/año. Si la evidencia es incompleta, conservar PENDING.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/primitive_periodic_returns.py; tools/check_worksheet_return_metrics_D167.py`.

**CoC del tramo · D126 y D167.** CoC = cobros operativos de la ventana / base de capital positiva. D167 usa aportes brutos acumulados hasta refi y cobros registrados después de refi y hasta venta. Excluye refi y venta, sin anualizar. El cobro operativo al cierre puede contener caja acumulada anterior.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `tools/worksheet_final_metrics_D126.py; tools/check_worksheet_return_metrics_D167.py`.

**Otras métricas de inversión.** YoC = NOI estabilizado / TDC. Spread = YoC − cap de referencia compatible. En D120, equity recuperado = distribución de refi normalizada / 10. Cash-in = aporte de refi normalizado / factor de escala, para obtener el importe del proyecto. Las métricas reales requieren definición y base confirmadas. El cotejo distingue estas bases de las del CoC, TIR y EM.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `tools/worksheet_yoc_spread_D123.py; tools/worksheet_screening_pilot_D120.py; docs/workbook-complete-pilot-D126.md`.

**Recuperación, descuento y dependencia de venta.** VP = Σ flujo_t/(1+r)^t bajo la grilla y tasa declaradas. Cobro mínimo al vender = max(0, −VP antes de venta × (1+r)^T). Brecha = cobro de venta previsto − mínimo. Dependencia de venta usa el cobro de venta y el total de distribuciones, con base positiva.

*Perfil sintético documentado.* Referencia: `tools/worksheet_discounted_recovery_D83.py; tools/check_sale_cash_recovery_D33.py; src/miniuw_foundation/cash_risk.py`.

**Reparto proporcional · D168.** Movimiento de rol = movimiento del proyecto × participación del rol. Σ participaciones = 1. Reexpresión por rol = importe × 10 / aporte inicial propio. Cuadrar por evento, categoría, año y total antes de redondear.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/cash_participation.py; tools/check_worksheet_lp_gp_D168.py`.

**Capital, preferente y remanente · D169.** Capital devuelto por cobro = min(caja disponible, capital pendiente total), repartido según saldos. Preferente LP del trimestre = capital LP inicial del trimestre × tasa anual simple / 4. Preferente pagado = min(caja después de capital, preferente pendiente). Remanente = caja − capital devuelto − preferente pagado.

*Perfil sintético documentado.* Referencia: `tools/check_worksheet_preferred_lp_gp_D169.py`.

**Catch-up GP · D170.** Meta acumulada = preferente LP pagado acumulado × cuota GP/(1−cuota GP). Catch-up por cobro = min(caja después de capital y preferente, meta − catch-up pagado acumulado). Remanente posterior se distribuye con las participaciones declaradas. Saldo impago se conserva como evidencia.

*Perfil sintético documentado.* Referencia: `tools/check_worksheet_preferred_lp_gp_D169.py; tools/check_worksheet_gp_catch_up_D170.py`.

**Métricas y distribución personales.** Retorno personal, retenciones y tratamiento fiscal, equity retenido, base profesional de capital remanente, TIR de fechas irregulares y reglas contractuales adicionales siguen sujetos a definición y evidencia.

*Aplicabilidad o evidencia real PENDING.* Referencia: `docs/model-hold-exit-returns.md; M7-11 y M7-12`.

**Venta sin refi.** Saldo de deuda de obra vigente hasta venta según plazo documentado. Por período, interés = principal de obra vigente × fracción del intervalo, según términos. Neto de venta cancela saldo de obra y reconoce los costos y reservas aplicables. D237 limita el ejemplo a extensión documentada de comisión cero.

*Perfil anual sin refi.* Referencia: `tools/worksheet_calendar_routes_D199.py; docs/worksheet-annual-sale-without-refinance-D237.md`.

**Capital remanente a la refi.** Equity remanente en la métrica CoC = aporte bruto acumulado hasta la refi, incluido el aporte al cierre, menos cobro neto de refi. La métrica exige correspondencia con el libro fechado y saldo positivo; cero verificado se trata según aplicabilidad. El valor retenido del inmueble requiere su propia valoración y evidencia.

*Métrica sintética, valoración personal PENDING.* Referencia: `docs/worksheet-annual-coc-D232.md; docs/technical-implementation-T98.md`.

**Cash-on-cash anual posrefi.** CoC = [Σ NOI después de reservas de cuatro trimestres − Σ servicio de deuda programado de la misma ventana] / equity remanente en refi. Excluye el principal de cancelación por venta. Una ruta de tres meses mantiene el CoC anual pendiente.

*Perfil anual vigente.* Referencia: `tools/worksheet_annual_coc.py; docs/worksheet-annual-coc-D232.md`.

**Pico de financiación y dependencia de la venta.** Caja sin recuperar por fecha = max(0, aportes acumulados − cobros acumulados); pico de cierres = máximo de esa serie. Si el orden intradía es desconocido, el límite superior considera los aportes del día antes del cobro. Dependencia de venta = cobro neto en venta / total de cobros si es positivo.

*Perfil de riesgo por flujo.* Referencia: `docs/technical-implementation-T105.md; src/miniuw_foundation/cash_risk.py`.

**Precio mínimo al 2 % y recorte de obra.** Si ΔP sólo mueve el precio final, ΔVAN por USD 10 = ΔP × (1 − comisión) × [10 / aporte inicial] / (1 + tasa)^mes de venta. Si falta valor presente, se divide el faltante por ese factor y se suma a la venta de partida. D247 y D249 certifican el primer centavo. D248 fija la venta y recorre el costo de obra hasta alcanzar VAN ≥ 0.

*Perfiles sintéticos.* Referencia: `tools/worksheet_annual_crossover_sale_price.py · certified_sale_price; docs/worksheet-downside-minimum-sale-55-cut-D249.md`.


### M8 · Escenarios, sensibilidades y precio soportado

**Transformaciones y comparación.** Cambio relativo: x' = x(1+δ). Puntos porcentuales: x' = x+δ/100. Puntos básicos: x' = x+δ/10000. Reemplazo absoluto: x'=v. Cambio de plazo se aplica en meses. Δ = resultado variante − referencia.

*Perfil sintético documentado.* Referencia: `docs/model-scenarios-price.md; tools/worksheet_alternatives_D155.py`.

**Escenarios y alternativas · C80–C82.** En los tres espacios D155 prueba respectivamente C67, C68 y C75. Cada espacio acepta los reemplazos soportados con confirmación tipada. El Downside integrado reejecuta los cambios simultáneos de su revisión.

*Perfil sintético documentado.* Referencia: `tools/worksheet_alternatives_D155.py; tools/worksheet_market_evidence_D166.py`.

**Venta mínima y sensibilidad conjunta.** Con costo de venta proporcional c y otros flujos de cierre fijos, venta bruta mínima = (cobro de venta requerido + usos fijos netos)/ (1−c) cuando c<1 y el modelo conserva la base. Se reevalúan deuda, tenencia y descuento en la fecha nueva de cada variante.

*Perfil sintético documentado.* Referencia: `tools/refinance_sale_combinations_D87.py; tools/fixed_sale_delay_D92.py; tools/worksheet_discounted_recovery_D83.py`.

**Cotas y precio afín.** Si C(P)=a+bP, NOI N independiente, YoC objetivo y>0: P≤(N/y−a)/b. Con aporte único y cobro H, IRR=H/C(P)−1 y P≤[H/(1+r_obj)−a]/b. Requiere hipótesis y dominio documentados.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `docs/model-scenarios-price.md; docs/affine-price-support.md`.

**Precio soportado de grilla · D126.** TDC(P) = TDC + P − compra evaluada; equity inicial cambia por la misma diferencia en el perfil. Probar YoC y múltiplo en cada precio autorizado, seleccionar el máximo factible si existe y verificar la frontera. Asking/precio soportado = precio pedido / soporte positivo.

*Referencia histórica o perfil anterior. Ver definición vigente en este módulo..* Referencia: `tools/worksheet_final_metrics_D126.py`.

**RLV de la casa y sensibilidad de políticas.** D184, D193 y D233 prueban fronteras sintéticas con distintas reglas versionadas. La adopción de la regla de cada ruta, del dominio de precio y de la agregación del dictamen requiere aprobación. Un límite sólo cubre la grilla evaluada.

*Aplicabilidad o evidencia real PENDING.* Referencia: `docs/model-scenarios-price.md; docs/requirements-conflicts.md; METRIC-ASKING`.

**Cruce con y sin refinanciación.** Descontar ambas rutas a la misma fecha e igualar sus VAN. Resolver Σ [flujo_con_refi,t − flujo_sin_refi,t] / (1 + r)^t = 0. El ensayo sólo certifica unicidad si el adelanto positivo y las diferencias posteriores satisfacen la condición de signo del verificador. El cruce pertenece a esos flujos y cambia si se repricia la obra.

*Perfil sintético.* Referencia: `tools/worksheet_annual_discount_crossover.py · bracket_crossover; docs/worksheet-downside-fixed-sale-crossover-D245.md`.

**RLV desde las reglas de la revisión.** A deuda fija, ΔTDC = Δequity = Δprecio del terreno × (1 + C33). D193 prueba un rendimiento vinculante, YoC o spread, en su perfil. D233 prueba conjuntamente las nueve métricas de Base de D230. Máximo de la grilla que cumple y comprobación del vecino; frontera previa a FAIL se verifica aparte si existe. Valor firmado si es negativo. Sin caso que cumpla, queda no alcanzable y PENDING.

*Perfiles sintéticos. RLV Base sin refi pendiente de regla.* Referencia: `docs/workbook-performance-policy-D184.md; docs/worksheet-joint-rlv-D233.md; tools/worksheet_lorena_screening.py`.

**Prima de precio sobre RLV.** Con RLV positivo y precio pedido comparable, prima (%) = 100 × (precio pedido / RLV − 1). Con RLV no positivo o intervalo indeterminado retener la comparación según el contrato.

*Perfil D230. Aprobación real pendiente.* Referencia: `src/miniuw_foundation/lorena_screening.py; docs/worksheet-lorena-screening-D231.md`.


### M9 · Comparación, revisión, vigencia y salida

**Cotejo de criterios.** Comparar valor exacto y umbral con operador declarado, misma definición, unidad, período, base y escenario. En intervalos de TIR, la condición sólo se afirma cuando el intervalo completo permite el cotejo. Si hay faltante, incompatibilidad o banda, PENDING.

*Perfil sintético documentado.* Referencia: `src/miniuw_foundation/screening.py; src/miniuw_foundation/irr_interval_output.py`.

**Vigencia y auditoría.** Una fuente coincide si sus huellas y vínculos de caso/revisión coinciden. B16 vuelve a ejecutar desde fuentes y coteja los bytes esperados. Una revisión anterior conserva su resultado histórico. El PDF del deal es de una página.

*Perfil sintético documentado.* Referencia: `tools/worksheet_revision_D128.py; tools/miniuw_worksheet_v1.py`.

**Agregación y autorización reales.** Los criterios aplicables y su agregación requieren una revisión vigente. Full UW requiere PASS aplicable y aprobación final auténtica, con autoridad y alcance acreditados. Autorización y revisión financiera independiente permanecen pendientes.

*Aplicabilidad o evidencia real PENDING.* Referencia: `docs/model-decision-audit.md; docs/review/MiniUW_Flujo_Dots_y_Bots_para_Lorena_D165.pdf`.

**YoC, spread y capital sobre costo.** YoC = NOI_uw estabilizado / TDC. Spread en pb = 10.000 × [(NOI de la base del cap / TDC) − cap comparable]. Equity/TDC = equity aplicado a los usos del corte / TDC de los mismos usos. Cruzar definiciones, fuentes, moneda, reservas y período antes de comparar.

*Perfil de métricas sintético.* Referencia: `docs/workbook-performance-policy-D184.md; docs/worksheet-lorena-screening-D231.md`.

**Recuperación y aporte en refi.** Recuperación = cobro neto de refi / equity aportado hasta estabilización según contrato D230. Aporte en refi = aporte al cierre / esa base declarada. La ruta sin refi marca ambas N/A, junto con CoC posrefi.

*Perfil D230.* Referencia: `tools/worksheet_lorena_screening.py; docs/worksheet-lorena-screening-D231.md; docs/worksheet-annual-sale-without-refinance-D237.md`.

**PRELIMINAR y ranking.** Múltiplo Downside = cobros Downside / aportes brutos Downside. Orden descendente entre casos comparables, con posiciones empatadas por múltiplo. Sólo entra un caso con ambos escenarios completos, mínimos y capacidad y evidencia aplicables verificados. Dictamen formal PENDING.

*Perfil sintético PRELIMINAR.* Referencia: `tools/worksheet_preliminary_D185.py · finish_preliminary; docs/preliminary-pilot-readiness-D189.md`.

**Falso verde documental.** Tasa observada = falsos verdes / datos críticos definidos en la muestra. Cada dato, compartido o por escenario, se cuenta una vez. Hay falso verde si un dato declarado válido discrepa en valor, unidad, fuente, localizador, huella o revisión frente a una referencia independiente. D219 documenta 0/48 sintético.

*Ensayo sintético. Medición real pendiente.* Referencia: `docs/workbook-critical-evidence-audit-D219.md; tools/audit_worksheet_critical_evidence_D219.py`.


## 8. Anexo de movimientos por USD 10 de D238

Las 52 filas corresponden a las cuatro rutas del mismo ensayo. «Aporta» y «cobra» son importes brutos normalizados. Los ceros del libro se mantienen a nivel de reporte cuando hay una fila de movimiento. Sumar antes de redondear.

| Ruta | Fecha | Etapa | Aporta USD | Cobra USD |
| --- | --- | --- | --- | --- |
| Base con refi | 30/03/2027 | Compra u obra | 10,00 | 0,00 |
| Base con refi | 30/09/2027 | Compra u obra | 4,66 | 0,00 |
| Base con refi | 30/12/2027 | Compra u obra | 0,05 | 0,00 |
| Base con refi | 30/03/2028 | Compra u obra | 0,05 | 0,00 |
| Base con refi | 30/06/2028 | Compra u obra | 0,05 | 0,00 |
| Base con refi | 30/09/2028 | Compra u obra | 0,05 | 0,00 |
| Base con refi | 30/09/2028 | Refi | 0,00 | 2,03 |
| Base con refi | 30/12/2028 | Operación | 0,00 | 0,32 |
| Base con refi | 30/03/2029 | Operación | 0,00 | 0,31 |
| Base con refi | 30/06/2029 | Operación | 0,00 | 0,34 |
| Base con refi | 30/09/2029 | Operación | 0,00 | 0,24 |
| Base con refi | 30/09/2029 | Venta | 0,00 | 13,68 |
| Base sin refi | 30/03/2027 | Compra u obra | 10,00 | 0,00 |
| Base sin refi | 30/09/2027 | Compra u obra | 4,66 | 0,00 |
| Base sin refi | 30/12/2027 | Compra u obra | 0,05 | 0,00 |
| Base sin refi | 30/03/2028 | Compra u obra | 0,05 | 0,00 |
| Base sin refi | 30/06/2028 | Compra u obra | 0,05 | 0,00 |
| Base sin refi | 30/09/2028 | Compra u obra | 0,05 | 0,00 |
| Base sin refi | 30/12/2028 | Operación | 0,00 | 0,33 |
| Base sin refi | 30/03/2029 | Operación | 0,00 | 0,36 |
| Base sin refi | 30/06/2029 | Operación | 0,00 | 0,38 |
| Base sin refi | 30/09/2029 | Operación | 0,00 | 0,28 |
| Base sin refi | 30/09/2029 | Venta | 0,00 | 15,73 |
| Downside con refi | 30/03/2027 | Compra u obra | 10,00 | 0,00 |
| Downside con refi | 30/06/2027 | Compra u obra | 0,76 | 0,00 |
| Downside con refi | 30/09/2027 | Compra u obra | 0,04 | 0,00 |
| Downside con refi | 30/12/2027 | Compra u obra | 7,03 | 0,00 |
| Downside con refi | 30/03/2028 | Compra u obra | 0,07 | 0,00 |
| Downside con refi | 30/06/2028 | Compra u obra | 0,07 | 0,00 |
| Downside con refi | 30/09/2028 | Compra u obra | 0,07 | 0,00 |
| Downside con refi | 30/12/2028 | Compra u obra | 0,07 | 0,00 |
| Downside con refi | 30/03/2029 | Compra u obra | 0,07 | 0,00 |
| Downside con refi | 30/03/2029 | Refi | 0,00 | 1,64 |
| Downside con refi | 30/06/2029 | Operación | 0,00 | 0,10 |
| Downside con refi | 30/09/2029 | Operación | 0,00 | 0,05 |
| Downside con refi | 30/12/2029 | Operación | 0,00 | 0,07 |
| Downside con refi | 30/03/2030 | Operación | 0,13 | 0,00 |
| Downside con refi | 30/03/2030 | Venta | 0,00 | 3,08 |
| Downside sin refi | 30/03/2027 | Compra u obra | 10,00 | 0,00 |
| Downside sin refi | 30/06/2027 | Compra u obra | 0,76 | 0,00 |
| Downside sin refi | 30/09/2027 | Compra u obra | 0,04 | 0,00 |
| Downside sin refi | 30/12/2027 | Compra u obra | 7,03 | 0,00 |
| Downside sin refi | 30/03/2028 | Compra u obra | 0,07 | 0,00 |
| Downside sin refi | 30/06/2028 | Compra u obra | 0,07 | 0,00 |
| Downside sin refi | 30/09/2028 | Compra u obra | 0,07 | 0,00 |
| Downside sin refi | 30/12/2028 | Compra u obra | 0,07 | 0,00 |
| Downside sin refi | 30/03/2029 | Compra u obra | 0,07 | 0,00 |
| Downside sin refi | 30/06/2029 | Operación | 0,00 | 0,11 |
| Downside sin refi | 30/09/2029 | Operación | 0,00 | 0,14 |
| Downside sin refi | 30/12/2029 | Operación | 0,00 | 0,16 |
| Downside sin refi | 30/03/2030 | Operación | 0,04 | 0,00 |
| Downside sin refi | 30/03/2030 | Venta | 0,00 | 4,82 |

## 9. Evidencia, reproducción y pendientes

**Cadena base de aceptación.** D200 reproduce las fuentes y los flujos de un expediente completo, uno adverso, uno incompleto y uno corregido. El cotejo D179 deriva independientemente NOI, deuda, venta, caja, múltiplo y TIR desde el expediente y los XLSX sintéticos. D225 verifica ambos órdenes de reparación de citas. D227 comprueba la vigencia inmediatamente antes de exportar. D237–D238 verifican los calendarios anuales y sus fechas. D249 certifica los dos precios mínimos bajo recorte de 55 %.

**Para repetir el cierre.** Verificar el manifiesto del corte de código, preparar la versión OCR y las dependencias del expediente, y usar Python 3.12.3 en el VPS. Desde la raíz del repositorio, correr con `OMP_THREAD_LIMIT=1` y `PYTHONPATH=src:tests:tools`. Registrar versión, huella, tiempos y errores.

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_reference_package.py
python3 tools/check_integral_miniuw_D102.py
python3 tools/check_worksheet_technical_acceptance_D200.py --output /tmp/miniuw-d250-aceptacion
```

**Condición de entrega.** El informe de un deal permanece ligado a su expediente y su única página. Este documento es el informe interno de revisión del modelo. Para habilitar uso real, ejecutar el checklist del apartado 5 sobre un expediente autorizado. Revisar por separado el criterio del RLV sin refi, el contrato de extensión de deuda de obra con costo si el caso lo requiere y la convivencia de un FAIL verificado con otros faltantes materiales. La revisión del 1101 continúa PENDING.

**Referencias.** [Cotejo independiente D179](workbook-independent-reconciliation-D179.md) · [Prueba de vigencia](worksheet-technical-acceptance-D200.md#entrega-vigente-del-informe-integral) · [Calendarios de venta D237](worksheet-annual-sale-without-refinance-D237.md) · [Sensibilidad D249](worksheet-downside-minimum-sale-55-cut-D249.md) · [Reglas de decisión](decision-input-contract.md).
