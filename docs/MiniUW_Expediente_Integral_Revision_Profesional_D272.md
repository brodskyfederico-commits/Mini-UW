# Mini-UW v1 · Expediente integral para revisión profesional

## 1. Corte, alcance y cómo revisar este expediente

Este expediente documenta el modelo completo disponible al 20/11/2026, hora de Nueva York, sobre el commit `e332f33f23cf31d00897137322e345b081830297`. El código coincide con el corte D270 probado en D271. No modifica fórmulas, datos, umbrales, políticas o autorizaciones. El dictamen real y el retorno histórico siguen PENDING; despliegue deshabilitado.

La lectura principal reúne procesos, los siete Dots y los 17 bots, entradas y complementos, conexiones, catálogo financiero, estados, reglas de dictamen, fuentes, controles, validación y pendientes. Los anexos conservan las especificaciones anteriores con su perfil y fecha: una referencia histórica no se convierte en regla vigente por aparecer aquí.

**Integridad del contenido.** El PDF incorpora como adjunto un ZIP con los 681 archivos Python íntegros del corte, todos los templates registrados, los documentos Markdown del modelo, matrices y contratos estructurados seleccionados, la tabla de Lorena de referencia y el catálogo literal de operaciones y reglas. El índice y los hashes permiten rastrear cualquier cálculo hasta el archivo exacto. El código incluye sus perfiles anteriores, verificadores y pruebas, etiquetados por ruta. Su presencia no significa que todos se ejecuten a la vez ni que sean reglas aprobadas.

**Cómo acceder al anexo electrónico.** Abrir el panel Adjuntos/Archivos del lector PDF compatible y extraer `MiniUW_Anexo_Tecnico_D272.zip`. Se entrega también el mismo ZIP por separado para lectores que no muestran adjuntos. Los nombres de archivo no son instrucciones para ejecutar scripts. La lectura profesional puede empezar por las secciones 2–4 y el catálogo financiero, y consultar código y referencias al revisar cada observación.

El documento es un expediente de revisión del modelo, distinto de la página de resultados de un deal. La entrega al cliente del deal continúa limitada a una página. No contiene un nuevo análisis real de 1101 ni One Hollywood.

La regresión cerrada en D271 aprobó 1.766 unitarias, 26 suites de referencia, D102 integral, D200 aceptación 16/16 y preservación de fuentes. Su tiempo de 9.413 segundos corresponde a calidad de una versión; no es una promesa de duración de análisis de un proyecto.

## 2. Énfasis: qué falta de Lorena y qué resultado bloquea

**No falta toda la información histórica.** Ya se dispone de la tabla de diez métricas y 29 umbrales numéricos del DOCX de estándares, y se compiló para ensayos D230. El perfil se identifica explícitamente como `synthetic_rehearsal_only`, con `criteria_adopted=False`. Los campos E7:H16 de la planilla de confirmación permanecen vacíos en el template. Una tabla histórica probada no autentica la vigencia para un deal nuevo.

**Se necesita de Lorena o del responsable de criterios:** confirmar operador y umbral aplicables a Base/Downside, base/denominador/período de cada métrica, aplicabilidad por estrategia y revisión/vigencia/fuente. También las reglas de agregación que sigan abiertas. Puede confirmar los valores originales; no tiene que inventar valores nuevos. Para Downside, «Sin FAIL» es una declaración de política, no un umbral cero. Un «No aplica» requiere motivo y alcance.

**Se puede calcular sin conocer un umbral de inversión:** ingresos, NOI, TDC, deuda, capacidad bajo condiciones bancarias documentadas, caja, venta, múltiplo y TIR válida. Sus números requieren datos del proyecto y términos, que aporta el equipo correspondiente. Sin umbral vigente puede existir un valor financiero, pero su clasificación autorizada sigue PENDING.

**No se puede certificar sin criterios/definiciones vigentes:** el PASS/FAIL formal; la distancia oficial a PASS; el RLV de la casa y el máximo precio que satisface todas sus condiciones; ajustes de renta/costo/estructura para alcanzar ese PASS; el avance autorizado a Full UW. Las simulaciones con referencias históricas conservan la etiqueta de ensayo.

La tabla siguiente reproduce las referencias originales desde el compilador y sus unidades, no las activa. No se exige un número en una celda declarada inaplicable; sí se exige resolver su aplicabilidad. La referencia original no contiene FAIL Downside.

| Métrica | PASS Base histórico | PASS Down histórico | FAIL Base histórico | Confirma Lorena en XLSX | Valor financiero y dependencia |
| --- | --- | --- | --- | --- | --- |
| Yield on Cost (YoC) | >= 6,50 % | >= 5,75 % | < 5,25 % | 'Criterios PASS FAIL'!E7:H7; I7 | Calculable con NOI_uw estabilizado y TDC reconciliado; el umbral no forma parte de su aritmética. |
| Spread de desarrollo | >= 100,00 pb | >= 50,00 pb | < 0,00 pb | 'Criterios PASS FAIL'!E8:H8; I8 | Calculable con YoC y cap comparable de la misma base; sin base de cap documentada, PENDING por evidencia. |
| Equity recuperado en refi | >= 60,00 % | >= 40,00 % | < 25,00 % | 'Criterios PASS FAIL'!E9:H9; I9 | Calculable con cash-out neto y equity aportado hasta estabilización; N/A sólo con estrategia sin refi documentada. |
| Aporte de equity en refi | <= 5,00 % | <= 10,00 % | > 20,00 % | 'Criterios PASS FAIL'!E10:H10; I10 | Calculable con cash-in de cierre y equity hasta estabilización; no convertir USD a % sin denominador. |
| Ocupación de equilibrio | <= 85,00 % | <= 90,00 % | > 93,00 % | 'Criterios PASS FAIL'!E11:H11; I11 | Económica calculable con la función de ingresos/costos/deuda; la física requiere desglose de C14. Falta de desglose es un dato/regla aparte del umbral. |
| Cash-on-cash anual posrefi | >= 6,00 % | >= 4,00 % | < 3,00 % | 'Criterios PASS FAIL'!E12:H12; I12 | Calculable con un año completo, NOI_uw, servicio y equity remanente; denominador cero acreditado requiere la salida N/A del contrato. |
| Precio pedido frente al RLV | <= 0,00 % | Sin valor numérico original; aplicabilidad por confirmar | > 15,00 % | 'Criterios PASS FAIL'!E13:H13; I13 | El RLV vigente depende de todos los criterios aplicables, su dominio y estrategia. Sin ellos, no hay RLV de la casa ni prima sobre RLV certificable. |
| Equity / TDC | <= 35,00 % | <= 40,00 % | > 45,00 % | 'Criterios PASS FAIL'!E14:H14; I14 | Calculable con equity aplicado hasta el corte y TDC de igual alcance; la condición especial de equity bajo requiere regla de financiación. |
| TIR anual apalancada | >= 15,00 % | >= 12,00 % | < 10,00 % | 'Criterios PASS FAIL'!E15:H15; I15 | Calculable/acotable con todos los movimientos, fechas y una raíz admisible única probada. Sin prueba suficiente, PENDING numérico, aunque existan criterios. |
| Múltiplo de equity | >= 1,75 x | >= 1,50 x | < 1,35 x | 'Criterios PASS FAIL'!E16:H16; I16 | Calculable con cobros brutos / aportes brutos positivos, en el horizonte declarado; faltantes no se rellenan con cero. |

**Ubicación de la fuente.** DOCX `sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx`, SHA-256 `38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9`. Las diez filas compiladas citan `word/document.xml/table[2]/row[1..10]/cell[1..3]`. La receta D230 contiene además localizadores descriptivos de tabla; se preservan ambos sin reinterpretar sus índices. El localizador específico de cada umbral se conserva en el anexo electrónico.

La fecha literal del DOCX es `10/12/2026`. Este expediente no decide su formato calendario ni su vigencia por el nombre o la fecha del archivo. Se requiere confirmación aplicable. La planilla permite indicar versión/vigencia/fuente en la fila 18, regla de Downside en la 19 y aclaraciones por métrica en I7:I16.

## 3. Lista concreta para el responsable de criterios

| ID | Confirmación necesaria | Salida que sigue PENDING |
| --- | --- | --- |
| L01 | Confirmar los criterios E7:H16 e identificar su versión y vigencia | PASS/FAIL por fila y agregado. Los originales son referencia hasta confirmación. |
| L02 | Confirmar alcance, igualdad, unidades, bases y ventanas de las diez métricas | Comparación coherente; no equiparar un porcentaje con USD ni un trimestre con un año. |
| L03 | Declarar por escenario Sin FAIL / No aplica cuando corresponda y motivo | Evita que una ausencia se transforme en 0 o en FAIL inventado. |
| L04 | Confirmar criterio y alcance de RLV por estrategia, incluido sin refi y Downside | RLV, prima del precio y precio máximo vigente; sin definición completa, PENDING. |
| L05 | Resolver la precedencia de un FAIL verificado con otros faltantes materiales | Dictamen formal. Las variantes D218 están ensayadas, pero no se activan por ese hecho. |
| L06 | Acreditar cualquier excepción a shocks, materialidad, fuente de área o beneficio fiscal | La autoridad no se presume de un nombre o una casilla; no todos estos roles corresponden a Lorena. |
| L07 | Confirmar regla de ranking para su uso real | El ranking PRELIMINAR sintético por EM Downside no se transforma en recomendación real. |

**Decisiones ya establecidas que se conservan.** El usuario decidió que una banda intermedia completa se mantenga PENDING; no se vuelve a convertir automáticamente en FAIL. La definición de desempeño utiliza NOI_uw después de reservas; el spread exige una base compatible con el cap comparable. Si ese cap está antes de reservas, se calcula el YoC de esa base sólo para el spread y se rotula. DSCR/debt yield del banco y valoraciones conservan sus bases documentadas. No se reabren esas decisiones como si no existieran.

El responsable debe ratificar el alcance y la versión aplicables al expediente real. Esto es distinto de pedir que rediseñe las fórmulas ya implementadas. Los términos de reparto, datos del proyecto, cotizaciones, préstamos y copias oficiales tienen responsables propios; no se atribuyen todos a Lorena.

## 4. Responsables y diferencia entre criterio ausente y dato ausente

| Quién | Qué aporta o confirma | Qué bloquea |
| --- | --- | --- |
| Lorena / responsable de criterios | Umbrales, operadores, definiciones aplicables, política y versión | Comparaciones, RLV vigente y dictamen. |
| Equipo del proyecto / desarrollador | Unidades, áreas, precio, presupuesto, rentas, gastos, calendario, planillas y respaldos | Métricas, caja y retorno real. Sin estos hechos, un umbral no genera números. |
| GC y banco | Alcance de costos, exclusiones, compromiso, draws, tasa, frecuencia, disponibilidad, vencimiento, IO/covenants/debt yield | Costo, interés, capacidad y cierre; no son criterios de inversión de Lorena. |
| Custodio de evidencia oficial / responsable legal-fiscal | Fuente oficial, jurisdicción, vigencia, AMI, millage, bases y aplicabilidad del programa | Regulación y beneficios; ningún beneficio se presume. |
| Socios / inversores y documentación jurídica | Aportes, participación, honorarios, preferente, catch-up y waterfall reales | Retorno personal; el equity agregado no se atribuye automáticamente a una persona. |
| Revisor financiero y aprobador | Cotejo independiente, identidad y autoridad, alcance de aprobación y autorización de uso real | Dictamen operativo y avance a Full UW. |

Una métrica puede ser calculable y tener dictamen PENDING por criterio ausente. Una métrica con datos mínimos ausentes no se calcula como cero. Un parámetro explícito cero se conserva; si está fuera del dominio permitido se rechaza con causa, conservando el dato original. Una tasa no definida no es 0 %. Un valor retenido no es un cobro. Un hash verifica bytes, no la identidad o autoridad de quien aprobó la fuente.

## 5. Reglas inquebrantables y estados

| Regla | Comportamiento |
| --- | --- |
| Vacío ≠ cero | No completar por suma, promedio, copia de Base o default escondido. N/A necesita declaración compatible. |
| Datos, criterios y autorización separados | No usar condiciones bancarias como umbral de inversión ni una prueba aprobada como firma humana. |
| Moneda, unidad, base y período compatibles | No comparar USD con %, SF con m² sin conversión declarada, ni NOI antes/después de reservas indistintamente. |
| Base y Downside propios | Revisión y fuentes vinculadas; Upside informativo no rescata un Base insuficiente. |
| Caja bruta fechada | Aportes y cobros separados, factor 10/aporte inicial verificado, aportes posteriores fuera del denominador inicial. |
| Restricciones bancarias | Compromiso, disponibilidad, costo elegible, plazo y menor límite aplicable. No recortar un préstamo automáticamente para producir PASS. |
| Reservas y saldos | Libre/restringida separados; depósito, liberación, deuda cancelada y venta se registran una vez. |
| Vigencia y trazabilidad | Originales preservados; cita, unidad, fecha, revisión y huella. Corregir obliga a recalcular dependientes. |
| Falsos verdes | Un verde sin respaldo retira el cálculo afectado y bloquea la entrega según perfil. |
| PDF | B16 reconstruye y comprueba revisión inmediatamente antes de exportar. Revisión anterior no se entrega como vigente. |
| Raíces y valores indefinidos | Varias TIR o inventario incompleto: PENDING, no elegir la favorable. RLV negativo se conserva con bandera; inalcanzable no se vuelve 0. |
| Activación | Sin despliegue ni decisiones reales. Un PASS de screening no autoriza inversión ni Full UW por sí solo. |

**Estados distintos.** PENDING identifica faltantes/conflictos/indefinición o banda bajo el contrato vigente. N/A exige inaplicabilidad declarada. PRELIMINAR permite priorización con supuestos identificados, sin PASS formal; si falta un mínimo o se excede capacidad, fuera del ranking. PASS/FAIL/HOLD de las configuraciones D230 son resultados de ensayo bajo su contrato; no se generaliza HOLD ni se reemplaza la banda PENDING elegida por el usuario. VIGENTE/obsoleto describe revisión, no rentabilidad. Verde verificado describe respaldo, no aprobación de inversión.

## 6. Procedimientos completos de ingreso, corrección y entrega

**Procedencia del catálogo: D250.** Las conexiones se preservan; las ampliaciones D251–D270 y sus límites se detallan después. Los hitos de evidencia de cada fila identifican su perfil, no una aprobación real. En particular H01 se amplía al horizonte explícito D266/D267 y H04/H05 tienen productor anual por unidad D269.


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

## 7. Los siete Dots y cada uno de los 17 bots

**Procedencia del catálogo: D250.** Las conexiones se preservan; las ampliaciones D251–D270 y sus límites se detallan después. Los hitos de evidencia de cada fila identifican su perfil, no una aprobación real. En particular H01 se amplía al horizonte explícito D266/D267 y H04/H05 tienen productor anual por unidad D269.


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

## 8. Módulos, dependencias y bases de NOI

**Procedencia del catálogo: D250.** Las conexiones se preservan; las ampliaciones D251–D270 y sus límites se detallan después. Los hitos de evidencia de cada fila identifican su perfil, no una aprobación real. En particular H01 se amplía al horizonte explícito D266/D267 y H04/H05 tienen productor anual por unidad D269.


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

## 9. Carril humano: controles y autorización

**Procedencia del catálogo: D250.** Las conexiones se preservan; las ampliaciones D251–D270 y sus límites se detallan después. Los hitos de evidencia de cada fila identifican su perfil, no una aprobación real. En particular H01 se amplía al horizonte explícito D266/D267 y H04/H05 tienen productor anual por unidad D269.


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

## 10. Todas las celdas nativas y los ocho complementarios

**Procedencia del catálogo: D250.** Las conexiones se preservan; las ampliaciones D251–D270 y sus límites se detallan después. Los hitos de evidencia de cada fila identifican su perfil, no una aprobación real. En particular H01 se amplía al horizonte explícito D266/D267 y H04/H05 tienen productor anual por unidad D269.


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

## 11. Catálogo financiero integral: todas las familias de fórmulas

Las expresiones siguientes cubren las familias del catálogo completo, incluidas variantes históricas rotuladas. Cada resultado necesita sus operandos y su dominio. «Perfil sintético» identifica implementación ensayada, no regla vigente aprobada. El siguiente apartado agrega íntegramente los contratos y fórmulas posteriores. El código exacto y el inventario literal del adjunto permiten auditar detalles numéricos, condiciones y versiones sin reconstruirlos desde un resumen.


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

## 12. Entradas adicionales de los contratos actuales

| Contrato | Todos los grupos mínimos adicionales | Faltante / restricción |
| --- | --- | --- |
| Horizonte D266/D267 | Perfil/regla/fuente; meses de tenencia; compra/obra/estabilización/venta; grilla trimestral; declaraciones fiscales por escenario y ventanas preoperativas, operativas y forward; exclusión del impuesto previo del presupuesto; padrones, valores separados escolar/no escolar, millage, eventos de retasación y fecha de cada pago | Sin duración o cobertura fiscal no hay caja soportada. No sustituir por proxy ni promedio anual. |
| Fuentes independientes v34 | Los dos libros, plano, evidencia financiera, criterios y sexto archivo Independent_Reference.json; identidad/revisión y huellas; inventario completo de programa, banco, mercado, GC, fiscalidad y inputs_sha256 | Inventario incompleto, otro deal o fuente alterada: PENDING. La referencia no se toma de resultados del motor. |
| Programa D268 | Base; 15 drivers tipados, unidad y delta explícitos; aplicabilidad/excepción con fuente y motivo; packet_sha256 de variantes aisladas, conjunta e informativa Upside; política de stress fiscal declarada | No activar shocks históricos; no tocar principal o equity inicial fuera del cambio declarado; NOT_EXECUTED visible cuando no se ejecuta un caso. |
| AMI D269 | Por escenario: moneda, perfil/reglas, fuentes, déficit neto de lease-up con referencia, unidades reguladas/mercado para los cuatro grupos; cada anualidad y forward con vigencia y tipo de evidencia; hogar imputado/base; AMI anual; fracción de ingreso; proporción para renta; utility allowance; valor/unidad/fuente de cada operando | No heredar un cap a otro año. Tope neto negativo, faltante, mezcla inconsistente, PER SF sin contrato o cambio dentro de ventana: PENDING. |
| TIR D270 | Perfil, reglas, source_ref y algorithm_sha256; todos los movimientos observados de cada fecha, incluido 0 explícito; kind, USD, importe racional; grilla completa de cuatro períodos por año | Algoritmo o regla cambiados, fecha ausente, moneda/tipo inválido, varias raíces, inventario no probado o recurso agotado: PENDING. |
| Reparto | Inversores/roles, aportes y derechos, fechas, retorno de capital, preferente y base temporal, catch-up y promote, comisiones, distribución residual y fuentes | Sin términos no hay retorno personal aprobado; no usar porcentajes sintéticos de LP/GP como datos del cliente. |

Los contratos completos y sus claves se incluyen sin omisiones en los archivos JSON y módulos del anexo. Los templates contienen valores ficticios de prueba y límites técnicos; no son una planilla completada por Lorena ni defaults de un proyecto. Sus cifras se distinguen de umbrales históricos y de criterios vigentes.

## 13. Cambios posteriores al catálogo: D251–D270

Se reproducen las 19 especificaciones posteriores disponibles. La auditoría D252 describe un corte anterior: sus conteos de cobertura y rótulos «Falta» son históricos. Los avances D266–D270 y el cierre D271 actualizan sus brechas técnicas en los contratos definidos. Ningún anexo convierte una política no adoptada en activa; sigue sin certificarse la totalidad de las 33 políticas.

D266: horizonte explícito y duración alternativa; D267: M2 fechado y auditor; D268: 15 drivers; D269: AMI/renta; D270: TIR con prueba de unicidad. Las fórmulas de esos documentos complementan o delimitan las del catálogo anterior, sin borrar la trazabilidad histórica.

## 13.1 · D251 · Matriz de las 33 políticas frente al informe D250

**Fuente íntegra:** `docs/worksheet-policy-review-D251.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


[PDF recibido y preservado íntegramente](review/MiniUW_Matriz_33_Politicas_vs_D250.pdf) · [Informe integral D250](MiniUW_Informe_Integral_D250.md) · [Configuración de ensayo de criterios D230](lorena-screening-D230.md).

El PDF es una revisión documental aportada por el usuario. Compara las 33 políticas de la sección 4 de los estándares que cita con el informe D250 y el perfil D230. Incluye una observación adicional de renta asequible que remite al Input Sheet. La matriz declara que puede haber funciones del código que el informe D250 no menciona. Los estados siguientes son las conclusiones de esa revisión.

| Fuente y corte de la revisión | Localizador |
| --- | --- |
| Original | `MiniUW_Matriz_33_Politicas_vs_D250.pdf`, 3 páginas, 55.383 bytes |
| SHA-256 | `68ff3c988486b9cdf6fa60c4a1a937f0808138e107aba2517a7924b9f3eb03af` |
| Informe comparado | D250, `9de8ca4af4be86bbb6551e7f61d7013c7b12840d` |
| Estándares citados | «Estándares de underwriting de Lorena Muzo (10/12/2026)», sección 4, según el encabezado del PDF. El perfil D230 conserva la identificación y la huella de su DOCX de origen. |

| Estado según la revisión | Políticas | Cantidad |
| --- | --- | ---: |
| Cumple | 1, 2, 6, 7, 8, 9, 10 y 12 | 8 |
| Parcial | 3, 11, 13, 14, 15, 17 y 18–32 | 21 |
| No cumple | 4, 5, 16 y 33 | 4 |

La fila de renta asequible está en la página 3, después de la política 33. La revisión la clasifica como «No cumple» y la mantiene fuera del total de 33.

### Conexiones que se incorporan al índice de revisión

| PDF y ubicación | Conexión en el modelo | Evidencia a cotejar y punto por resolver |
| --- | --- | --- |
| p. 1, política 3. pp. 2–3, políticas 18–33 | M8 · Downside integrado, transformación de drivers y perfil informativo Upside | D155 y D238 prueban variantes y escenarios. La matriz pide los 15 drivers, valores por defecto de la sección 3, excepciones con fuente y Upside informativo. Confirmar alcance y vigencia de esa política antes de usar defaults en dictamen. |
| p. 1, política 4 | M1, B05–B09, C36 y costo vertical | D143 prueba uso documentado de GSF. La recomendación de takeoff para GBA TBD entra en el conflicto SRC-01. Confirmar método, fuente, alcance y tolerancia antes de aceptar el GBA derivado. |
| p. 1, políticas 5–6. p. 3, política 29 y fila extra | M2 · Fiscal, elegibilidad y rentas asequibles | D150 prueba proxy y comparables. D203 ensaya avalúos y millage por componente. H03–H05 registran aplicabilidad y AMI. C25–C28 se verifican como gasto de propietario en D142. El beneficio condicional y el límite de renta requieren su evidencia y regla propia. |
| p. 1, política 11. p. 2, política 14 | M2 y M3 · Ocupación y equity/TDC | D184 prueba ocupación económica y física con desglose. D231 vincula equity aplicado y TDC. Confirmar definición de ocupación y corte de equity, incluido el tratamiento del aporte en refi, y la evidencia para evaluar apalancamiento. |
| p. 2, política 13 | M8–M9 · RLV y prima del precio pedido | D184, D193 y D233 ensayan búsquedas de precio. D237 conserva PENDING para RLV Base sin refi por regla pendiente. Cotejar qué fronteras y salidas corresponden al criterio de la matriz. |
| p. 2, políticas 15–16 | M4 y M7 · Horizonte de tenencia, TIR y múltiplo | D234–D238 verifican calendarios anuales de cuatro trimestres. La matriz pide cinco años desde estabilización como horizonte por defecto, con excepciones respaldadas. El horizonte de evaluación y su criterio requieren revisión del calendario. |
| p. 2, política 17 | M9 y B14 · PASS, HOLD, FAIL y PENDING | D230 ensaya estados de clasificación y deja PENDING una combinación de FAIL verificado con faltante material. D218 prueba una propuesta alternativa en sintético. La matriz pide unificar la clasificación y confirmar precedencia y condición para pasar. |

Los comentarios quedan registrados para el cotejo con el repositorio y con el responsable de criterios. La incorporación documental conserva el perfil sintético, las configuraciones vigentes y el 1101 real **PENDING**.

**Referencias.** [Conflictos y autoridad de fuentes](requirements-conflicts.md) · [Planilla y Live Local D174](workbook-supplemental-scope-D174.md) · [M2 D203](workbook-florida-tax-D203.md) · [Propuestas D218](workbook-professional-proposals-D218.md) · [Ruta sin refi D237](worksheet-annual-sale-without-refinance-D237.md).

El [cotejo D252 contra el código y las pruebas](worksheet-policy-implementation-audit-D252.md) registra el estado verificado por política y los pendientes de implementación.

## 13.2 · D252 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/worksheet-policy-implementation-audit-D252.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


### D252 · Auditoría de las 33 políticas de D251 contra el Mini-UW

**Resultado.** En el perfil sintético auditado, **7 políticas están cubiertas, 24 tienen cobertura parcial y 2 carecen de la función que exigen**. El dictamen y el retorno histórico del **1101 real siguen PENDING**. El cotejo se realizó sobre el corte `0c585dc9e33270850e4daa0716a2770f92e5d160`, en el VPS. Es una auditoría de implementación y pruebas. El perfil de criterios D230 continúa siendo un ensayo sintético.

**Fuentes.** [Matriz D251, páginas 1 a 3](review/MiniUW_Matriz_33_Politicas_vs_D250.pdf) · [Estándares preservados, §§2–4](../sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx) · [Constancia de regresión D250](review/MiniUW_Validacion_D250.json). El DOCX corresponde a la huella fijada en el perfil D230. Los shocks y umbrales transcritos abajo se usan para identificar requisitos de auditoría.

**Criterio de evaluación.** Cubre significa cálculo y condiciones observables probados para el perfil indicado cuando la política aplica. Parcial significa que alguna parte relevante está probada y queda pendiente una rama, propagación, regla u horizonte. Falta identifica la ausencia del proceso operativo que pide la política. Las condiciones de autorización de un expediente real siguen su propio carril.

### Diferencias respecto de D251

- **#4, GBA TBD:** D143 ya acepta un C36 confirmado con fuente. Falta la medición auditable desde planos y el criterio de materialidad que habilitaría ese uso.
- **#6, impuesto:** la rama D150 ya prueba el mayor de proxy y comparables. Queda parcial porque la política también exige llevar incertidumbre material al Downside.
- **#16, múltiplo:** la fórmula y los umbrales en ensayo existen. La brecha es el horizonte por defecto de cinco años desde estabilización y su cobertura integrada.

La [salida de caja por USD 10 de D238](worksheet-annual-comparison-D238.md) sigue disponible como evidencia de las cuatro rutas sintéticas con y sin refi.

### Verificación ejecutada

En el VPS pasaron **46 pruebas unitarias dirigidas** de screening, caja anual con y sin refinanciación, CoC y NOI/impuesto. Se volvió a ejecutar D143 (11 casos, 7 PENDING esperados) y D155 (4 corridas de planilla, 5 alternativas calculadas y 1 bloqueada por capacidad). La regresión completa D250 de 1.676 pruebas es evidencia previa del mismo código. Los verificadores específicos de otros módulos se enlazan por fila como evidencia existente.

### Matriz por política

| Política y página D251 | Estado | Código y comportamiento | Pendiente | Evidencia |
| --- | --- | --- | --- | --- |
| **1. TIR y múltiplo de equity** · p. 1 | Cubre | El motor registra aportes y cobros brutos y calcula múltiplo y TIR del equity apalancado. En D167/D238 el calendario fechado trimestral alimenta la TIR. Las raíces ambiguas quedan sin TIR seleccionada. | #15–16 especifican timing y horizonte con más detalle. | [investor returns](../src/miniuw_foundation/investor_returns.py#L107) · [Verificador worksheet return metrics D167](../tools/check_worksheet_return_metrics_D167.py#L52) · [Prueba investor returns](../tests/test_investor_returns.py#L19) · [Prueba worksheet annual comparison](../tests/test_worksheet_annual_comparison.py#L33) |
| **2. Retorno de proyecto y LP** · p. 1 | Cubre | La métrica principal es equity agregado del proyecto. Existe un ensayo de reparto LP/GP con términos sintéticos declarados y una salida separada. | Para atribuir retorno personal, acreditar términos de JV, aportes, comisiones/promote y waterfall del caso. | [Verificador worksheet lp gp D168](../tools/check_worksheet_lp_gp_D168.py#L71) · [Verificador worksheet technical acceptance D200](../tools/check_worksheet_technical_acceptance_D200.py#L143) |
| **3. Downside conjunto y un driver a la vez** · p. 1 | Parcial | Downside conjunto se ejecuta desde una planilla propia ligada a Base por huellas. D155 recalcula alternativas de cap de salida, costo de salida y crecimiento de renta. El ranking de referencia ordena deltas recibidos. | Conectar una corrida por cada uno de los 15 drivers aplicables y el recálculo simultáneo, usando el mismo Base y métricas comparables. El ranking debe recibir resultados del motor, con faltantes visibles. | [worksheet scope D174](../tools/worksheet_scope_D174.py#L25) · [worksheet alternatives D155](../tools/worksheet_alternatives_D155.py#L46) · [Verificador worksheet alternatives D155](../tools/check_worksheet_alternatives_D155.py#L53) · [validate sensitivity ranking](../references/validate_sensitivity_ranking.py#L16) |
| **4. GBA de trabajo si el plano queda TBD** · p. 1 | Parcial | D143 acepta C36 confirmado con fuente si el GSF del plano figura TBD. En el flujo documentado B09 coteja la cantidad con el área verificada del plano. | Falta la cadena de takeoff con hojas, método, conciliación, marca PLAN-DERIVED y bloqueo por incertidumbre material. Resolver primero SRC-01 y la autoridad para esa fuente. | [worksheet development inputs D143](../tools/worksheet_development_inputs_D143.py#L30) · [Verificador worksheet development inputs D143](../tools/check_worksheet_development_inputs_D143.py#L137) · [worksheet documented finance D147](../tools/worksheet_documented_finance_D147.py#L62) |
| **5. Beneficio fiscal condicional** · p. 1 | Falta | D174 sólo ejecuta con no aplicabilidad explícita. D203 modela padrones y retasación de su perfil, con exenciones fuera del alcance. | Faltan beneficio respaldado y marcado, detracción en Downside y control que impida PASS si la economía depende materialmente del beneficio sin documentar. Acreditar elegibilidad, vigencia, evidencia y regla de materialidad. | [worksheet scope D174](../tools/worksheet_scope_D174.py#L32) · [Verificador worksheet scope D174](../tools/check_worksheet_scope_D174.py#L113) · [worksheet florida tax D203](../tools/worksheet_florida_tax_D203.py#L71) |
| **6. Mayor impuesto entre proxy y comparables** · p. 1 | Parcial | D150 y el motor de NOI calculan el mayor de ambos en la rama soportada. D203 tiene un camino de tasación documentada independiente. | Falta vincular la incertidumbre fiscal material con el stress específico de Downside, y definir cuándo una excepción documentada sustituye el mayor. Ver #5 y #29. | [operating noi](../src/miniuw_foundation/operating_noi.py#L115) · [Prueba operating noi](../tests/test_operating_noi.py#L27) · [Verificador worksheet property tax D150](../tools/check_worksheet_property_tax_D150.py#L51) |
| **7. YoC en conjunto con el spread** · p. 1 | Cubre | El perfil auditado divide NOI estabilizado después de reservas por TDC reconciliado. D230 recibe YoC y spread como controles distintos, ambos exigidos para PASS donde aplican. | Validar composición all-in y bases de NOI para el expediente autorizado. | [worksheet integrated screening D181](../tools/worksheet_integrated_screening_D181.py#L44) · [worksheet definition screening D193](../tools/worksheet_definition_screening_D193.py#L213) · [Prueba worksheet lorena screening](../tests/test_worksheet_lorena_screening.py#L102) |
| **8. Spread de desarrollo** · p. 1 | Cubre | El adaptador coteja el cap y el NOI en la misma base y ventana. El D230 sintético exige spread positivo para PASS. A 0 pb no alcanza el PASS; el FAIL estricto queda por debajo de 0 pb. | Acreditar cap comparable y revisión aplicable al usar criterios reales. | [worksheet lorena annual route](../tools/worksheet_lorena_annual_route.py#L72) · [lorena screening](../src/miniuw_foundation/lorena_screening.py#L118) · [Prueba lorena screening](../tests/test_lorena_screening.py#L79) |
| **9. Equity recuperado en refi** · p. 1 | Cubre | Cash-out neto al equity, conciliado con el libro por fecha, dividido por equity aportado hasta estabilización. Queda N/A en la ruta sin refi. | Acreditar importe, cancelaciones, costos, reservas y fuentes bancarias al pasar al piloto. | [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L39) · [worksheet annual coc](../tools/worksheet_annual_coc.py#L28) · [Prueba worksheet lorena screening](../tests/test_worksheet_lorena_screening.py#L142) · [Prueba worksheet annual sale without refi](../tests/test_worksheet_annual_sale_without_refi.py#L45) |
| **10. Cash-in de equity en refi** · p. 1 | Cubre | Aporte de cierre verificado dividido por el equity hasta estabilización. Usa la caja fechada y respeta cero y N/A sin refi. | Acreditar condiciones y montos de la refi real. | [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L39) · [Prueba lorena screening](../tests/test_lorena_screening.py#L123) · [Prueba worksheet annual coc](../tests/test_worksheet_annual_coc.py#L81) |
| **11. Ocupación de equilibrio** · p. 1 | Parcial | D184/D193 calculan ocupación económica y, con desglose, física. El adaptador D230 usa la económica con NOI y servicio conciliados; C14 combinado bloquea la física. | Aprobar la definición de screening, la base de servicio y la reconciliación del NOI anual. Confirmar tratamiento de concesiones, pérdida crediticia y reservas. | [worksheet performance policy D184](../tools/worksheet_performance_policy_D184.py#L24) · [Verificador worksheet performance policy D184](../tools/check_worksheet_performance_policy_D184.py#L64) · [worksheet lorena annual route](../tools/worksheet_lorena_annual_route.py#L84) |
| **12. CoC anual posrefi** · p. 2 | Cubre | D232/D234 concilian cuatro trimestres de NOI después de reservas, servicio programado y equity remanente. Año incompleto queda PENDING; equity remanente cero acreditado queda N/A. | Verificar términos permanentes y ventana en cada expediente. | [worksheet annual coc](../tools/worksheet_annual_coc.py#L57) · [Prueba worksheet annual coc](../tests/test_worksheet_annual_coc.py#L37) · [Prueba worksheet annual coc](../tests/test_worksheet_annual_coc.py#L75) |
| **13. Precio pedido y RLV** · p. 2 | Parcial | D193 y D233 calculan fronteras sobre grilla y deuda fija. D233 prueba criterios conjuntos, evidencia para precio negativo o inalcanzable y prima con RLV positivo. D230 ensaya el límite Base de +15 % con operador estricto. | Aprobar un RLV por estrategia, en especial sin refi, su dominio y tratamiento de límites. Integrar en el informe el máximo soportable aun si el precio pedido falla, cuando se pueda certificar. | [worksheet definition screening D193](../tools/worksheet_definition_screening_D193.py#L92) · [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L77) · [Prueba worksheet lorena screening](../tests/test_worksheet_lorena_screening.py#L169) · [Prueba lorena screening](../tests/test_lorena_screening.py#L92) |
| **14. Equity / TDC y control de apalancamiento** · p. 2 | Parcial | D230 calcula equity acumulado hasta estabilización / TDC conciliado. Los controles LTC, LTV y DSCR existen en obra y refi. La fórmula del ratio no incorpora por sí sola el control específico de equity bajo 25 %. | Acreditar ventana, tratamiento de aportes coincidentes con refi y financiación de mercado. Vincular la condición de equity bajo 25 % y cualquier excepción documentada al control del dictamen. | [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L25) · [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L167) · [Prueba worksheet lorena screening](../tests/test_worksheet_lorena_screening.py#L153) · [Prueba refinance capacity](../tests/test_refinance_capacity.py#L27) |
| **15. TIR apalancada con fechas y criterios** · p. 2 | Parcial | La TIR usa flujos de equity fechados en una grilla periódica compatible. D230 coteja el intervalo, con 15 % Base, 12 % Downside y FAIL estricto debajo de 10 % Base en el ensayo. | Extender y probar el calendario compatible con el horizonte de la #16 y explicitar el tratamiento de fechas fuera de grilla. Reconciliar la TIR junto con múltiplo, recovery, capital y Downside. | [Verificador worksheet return metrics D167](../tools/check_worksheet_return_metrics_D167.py#L52) · [worksheet lorena annual route](../tools/worksheet_lorena_annual_route.py#L42) · [Prueba lorena screening](../tests/test_lorena_screening.py#L132) |
| **16. Múltiplo y horizonte de cinco años** · p. 2 | Parcial | El múltiplo divide distribuciones brutas por aportes brutos positivos. D230 ensaya 1,75x / 1,50x y 1,35x de FAIL Base. El perfil base de planilla y las variantes anuales soportan ventanas acotadas, con anclas distintas según la ruta. | Falta un perfil integrado probado con salida a cinco años desde estabilización por defecto si se aprueba, y otra tenencia con evidencia. Recalcular operación, deuda, reservas, NOI forward, venta, TIR y múltiplo. | [worksheet lorena screening](../tools/worksheet_lorena_screening.py#L199) · [worksheet project calendar D145](../tools/worksheet_project_calendar_D145.py#L60) · [worksheet calendar routes D199](../tools/worksheet_calendar_routes_D199.py#L282) · [Prueba worksheet annual comparison](../tests/test_worksheet_annual_comparison.py#L33) |
| **17. Reglas de dictamen** · p. 2 | Parcial | D230 ejecuta PASS, FAIL, HOLD por diligencia y HOLD económico en el ensayo. FAIL verificado con faltante material queda PENDING. El contrato vigente conserva PENDING para la banda intermedia y D218 ensaya otra precedencia. | Aprobar un contrato por versión, precedencia entre FAIL y faltantes, y salida que explique deficiencia principal y condición concreta para pasar. Definir cuándo precio/JV inviable puede motivar FAIL con evidencia. | [lorena screening](../src/miniuw_foundation/lorena_screening.py#L167) · [Prueba lorena screening](../tests/test_lorena_screening.py#L109) · [Prueba lorena screening](../tests/test_lorena_screening.py#L85) · [Prueba worksheet professional proposals D218](../tests/test_worksheet_professional_proposals_D218.py) |
| **18. Renta residencial −10 % / +5 %** · p. 2 | Parcial | C7–C11 producen renta residencial por unidad o superficie con comparables. D140 prueba recálculo con planillas separadas. | Agregar shock relativo sobre renta alcanzable validada, recálculo aislado e integrado, con la excepción respaldada y el Upside informativo. | [worksheet rental inputs D140](../tools/worksheet_rental_inputs_D140.py#L36) · [Verificador worksheet rental inputs D140](../tools/check_worksheet_rental_inputs_D140.py#L83) |
| **19. Renta comercial −10 % / +5 %** · p. 2 | Parcial | C16–C18 generan renta NNN por uso, fecha y superficie, aparte de residencial. | Conectar shock relativo y cotejo de comparables comerciales al runner, con controles de áreas, contratos y aplicabilidad. | [worksheet commercial inputs D141](../tools/worksheet_commercial_inputs_D141.py#L66) · [Verificador worksheet commercial inputs D141](../tools/check_worksheet_commercial_inputs_D141.py#L49) |
| **20. Vacancia residencial +3 / −1 pp** · p. 2 | Parcial | C14 alimenta las pérdidas residenciales. H08 puede añadir stress sólo al NOI de banco, una base distinta del shock de escenario residencial. | Sumar o restar puntos porcentuales a la vacancia elegible de Base, declarar dominio y propagar a operación, refi y salida según evidencias. | [worksheet rental inputs D140](../tools/worksheet_rental_inputs_D140.py#L95) · [Verificador worksheet rental inputs D140](../tools/check_worksheet_rental_inputs_D140.py#L83) |
| **21. Vacancia comercial +5 / −2 pp** · p. 2 | Parcial | C19 afecta la renta comercial sin modificar la vacancia residencial. | Aplicar puntos porcentuales a la base comercial, con dominio, recálculo de netos y condición de aplicabilidad del componente comercial. | [worksheet commercial inputs D141](../tools/worksheet_commercial_inputs_D141.py#L66) · [Verificador worksheet commercial inputs D141](../tools/check_worksheet_commercial_inputs_D141.py#L49) |
| **22. Obra directa +10 % / −5 %** · p. 2 | Parcial | D241–D249 ensayan reducciones porcentuales de vertical, parqueo y sitio con efecto en contingencia, soft, deuda y aportes. El helper de recorte limita el delta a reducciones. | Agregar shock de aumento y reducción al runner 33, con alcance, exclusiones y respaldo de ahorros. | [worksheet annual crossover construction](../tools/worksheet_annual_crossover_construction.py#L24) · [Prueba worksheet annual comparison](../tests/test_worksheet_annual_comparison.py#L33) |
| **23. Plazo de obra +6 / −3 meses** · p. 2 | Parcial | C46 recalcula fechas, curva admitida y financiación. D199/D200 ensayan un corte fiscal de obra. | Conectar shock de meses y verificar todos los costos de tiempo aplicables, especialmente seguro de obra, generales, tasas, gastos y carry. Usar calendario y ejecución acreditados. | [worksheet project calendar D145](../tools/worksheet_project_calendar_D145.py#L33) · [Verificador worksheet project calendar D145](../tools/check_worksheet_project_calendar_D145.py) · [Verificador worksheet technical acceptance D200](../tools/check_worksheet_technical_acceptance_D200.py) |
| **24. Lease-up +6 / −3 meses** · p. 2 | Parcial | C47 mueve estabilización y ventana posterior; en D145 el dinero de lease-up usa un déficit mensual declarado por el plazo, y D146 sigue el calendario de financiación. | Conectar stress, absorción sustentada y prueba de efecto en caja operativa, interés, fecha de refi, recuperación y salida. | [worksheet project calendar D145](../tools/worksheet_project_calendar_D145.py#L40) · [Verificador worksheet project calendar D145](../tools/check_worksheet_project_calendar_D145.py) · [worksheet construction financing D146](../tools/worksheet_construction_financing_D146.py#L31) |
| **25. Tasa de obra +150 / −50 pb** · p. 2 | Parcial | C52 alimenta la tasa y los intereses por el perfil de desembolsos. D146 usa interés simple trimestral; calcula draw, saldo y compromiso. | Ejecutar shocks en pb con el perfil y la frecuencia aplicables. Validar con términos si se requiere devengo mensual. El estándar exige el calendario aplicable y D251 propone concretamente mensual. | [worksheet construction financing D146](../tools/worksheet_construction_financing_D146.py#L31) · [Verificador worksheet construction financing D146](../tools/check_worksheet_construction_financing_D146.py#L49) |
| **26. Tasa permanente +100 / −50 pb** · p. 2 | Parcial | C69 repercute en servicio y capacidad. Se calcula el menor límite aplicable de LTV/DSCR y se bloquea el principal seleccionado por encima. | Agregar el driver en pb, sincronizar términos y propagar al crédito y a los rendimientos manteniendo los límites. | [worksheet permanent loan D152](../tools/worksheet_permanent_loan_D152.py#L15) · [refinance capacity](../src/miniuw_foundation/refinance_capacity.py#L130) · [Prueba refinance capacity](../tests/test_refinance_capacity.py#L19) |
| **27. Cap de refi +50 / −25 pb** · p. 3 | Parcial | C66 y NOI de valoración calculan valor de refi y límite LTV; el NOI bancario conserva su base. | Aplicar el shock versionado de C66 con evidencia de cap y base compatible; recalcular valor, límite vinculante y cierre. | [refinance capacity](../src/miniuw_foundation/refinance_capacity.py#L87) · [Verificador worksheet exit pricing D151](../tools/check_worksheet_exit_pricing_D151.py) · [Prueba refinance capacity](../tests/test_refinance_capacity.py#L31) |
| **28. Seguro +20 % / −10 %** · p. 3 | Parcial | C59 calcula prima anual por unidad asegurada y el cotejo D166 exige fuente de mercado. | Implementar shock relativo y excepción documentada más severa cuando aplique, con alcance y tipo de riesgo. | [worksheet operating costs D148](../tools/worksheet_operating_costs_D148.py#L43) · [Verificador worksheet operating costs D148](../tools/check_worksheet_operating_costs_D148.py#L54) · [Verificador worksheet market evidence D166](../tools/check_worksheet_market_evidence_D166.py) |
| **29. Impuesto estabilizado +15 % / −10 %** · p. 3 | Parcial | Hay proxy, comparables y cálculo por padrones. Cada planilla puede declarar un tratamiento propio compatible con su perfil. | Agregar stress sobre impuesto estabilizado, con regla de orden y trazabilidad respecto de beneficios condicionales de #5. Verificar que el ajuste se aplique una sola vez. | [worksheet property tax D150](../tools/worksheet_property_tax_D150.py#L18) · [worksheet florida tax D203](../tools/worksheet_florida_tax_D203.py#L71) · [Verificador worksheet property tax D150](../tools/check_worksheet_property_tax_D150.py#L51) |
| **30. LTV permanente −5 / +5 pp** · p. 3 | Parcial | C71 limita la capacidad junto al DSCR. El productor permite principal documentado por debajo de capacidad. La política 30 usa la expresión literal sobre proceeds iguales al menor límite. | Agregar shock de puntos porcentuales con términos de mercado y acordar el tratamiento de solicitudes menores frente a la redacción de la política. | [refinance capacity](../src/miniuw_foundation/refinance_capacity.py#L139) · [Prueba refinance capacity](../tests/test_refinance_capacity.py#L24) · [Verificador worksheet permanent loan D152](../tools/check_worksheet_permanent_loan_D152.py#L46) |
| **31. Cap de salida +50 / −25 pb** · p. 3 | Parcial | C67 valora la venta con NOI forward compatible. D155 ya prueba un reemplazo absoluto aislado de C67. | Convertir el shock en pb respecto de Base, con la fuente de NOI/cap, y conectarlo a corridas individuales y conjunta. | [worksheet alternatives D155](../tools/worksheet_alternatives_D155.py#L17) · [Verificador worksheet alternatives D155](../tools/check_worksheet_alternatives_D155.py#L53) · [worksheet calendar routes D199](../tools/worksheet_calendar_routes_D199.py#L344) |
| **32. Crecimiento de renta −1 / +0,5 pp anuales** · p. 3 | Parcial | C75 proyecta renta por aniversario; D155 recalcula su reemplazo absoluto. | Conectar el cambio en puntos por año, anclarlo al horizonte aprobado y acreditar el rango de mercado. | [worksheet growth D154](../tools/worksheet_growth_D154.py#L47) · [Verificador worksheet alternatives D155](../tools/check_worksheet_alternatives_D155.py#L53) |
| **33. Valores por defecto, excepciones y Upside** · p. 3 | Falta | La proyección recibe Downside explícito y vinculado a su fuente. D230 limita el dictamen a Base/Downside. El repositorio documenta transformaciones y soportes parciales de #3. | Falta el orquestador versionado que derive Downside de Base con los 15 defaults aplicables, registre cada excepción con fuente y motivo, emita las corridas individuales y deje Upside informativo. Confirmar autorización para valores por defecto frente a CUR-01 y REQ-06. | [worksheet scope D174](../tools/worksheet_scope_D174.py#L28) · [lorena screening](../src/miniuw_foundation/lorena_screening.py#L149) · [Prueba lorena screening](../tests/test_lorena_screening.py#L149) · [model-scenarios-price](model-scenarios-price.md) |

### Observación adicional del Input Sheet

D251 p. 3 incluye **renta asequible** fuera de las 33 políticas. El lector puede inventariar unidades y el perfil H03–H05 registra el alcance de elegibilidad. C25–C28 calculan servicios pagados por el propietario en D142. Para calcular la renta regulada falta un productor con AMI por unidad y vigencia, regla del tope, utility allowance con su tratamiento regulatorio y cotejo contra renta de mercado. El cálculo debe separar qué paga el propietario de la deducción aplicable al tope. [Ingreso de unidades](../tools/worksheet_documentary_intake.py) · [Alcance D174](workbook-supplemental-scope-D174.md) · [Gasto de servicios D142](workbook-utility-inputs-D142.md).

### Secuencia de trabajo antes de cambiar reglas

1. **Escenarios #3 y #18–33.** Definir el contrato de procedencia para Base, shocks tipados, aplicabilidad y excepciones. Implementar recálculo completo por driver y conjunto, y salida de diferencias por USD 10, junto con un Upside informativo. D155 y el ranking de referencia aportan componentes. Acordar primero si la sección 3 puede actuar como default y qué autoridad aprueba excepciones. La decisión incluye el alcance de la restricción bancaria de #30 para un principal solicitado menor que la capacidad.
2. **Calendario #15–16.** Preparar un perfil de prueba con 60 meses desde estabilización y otro de duración documentada. Cotejar operación, deuda, reservas, venta, TIR y múltiplo con y sin refi. La fórmula de TIR no necesita sustituirse para extender un calendario regular. Determinar qué política vale para fechas irregulares.
3. **Criterios #11, #13, #14 y #17.** Aprobar la base de ocupación, el test de financiación sostenible cuando equity queda debajo de 25 %, el RLV por estrategia y su salida en FAIL/HOLD. Resolver la precedencia del FAIL verificado con faltantes, y cómo distinguir diligencia y economía en la salida. Conservar el estado vigente PENDING de la banda hasta la decisión autorizada.
4. **Evidencia #4, #5 y #29 más la fila asequible.** Resolver SRC-01 para GBA derivado y acordar materialidad. Acreditar la regla fiscal o de renta, jurisdicción, vigencia y aplicabilidad. Después implementar el escenario condicional y los bloqueos que dependan de esas fuentes.

[Requisitos y conflictos de fuentes](requirements-conflicts.md) · [Contrato de escenarios](model-scenarios-price.md) · [Revisión original D251](worksheet-policy-review-D251.md).

## 13.3 · D253 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-sensitivities-D253.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D253 recalcula sensibilidades explícitas de cap de salida (C67), costo de venta (C68) y crecimiento de rentas (C75). La prueba usa el expediente sintético de aceptación D200. Los montos representan caja del proyecto por cada USD 10 de equity inicial verificado.

| Escenario y variante | Aporte adicional | Cobro de refi | Cobro operativo al cierre | Venta neta al cierre | Cobro total | Sin recuperar |
|---|---:|---:|---:|---:|---:|---:|
| Base original | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,78 | USD 18,06 | USD 0,00 |
| Base con los tres cambios | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,26 | USD 17,54 | USD 0,00 |
| Downside original | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,08 | USD 6,08 | USD 12,11 |
| Downside con C68 en 0 % | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,72 | USD 6,72 | USD 11,47 |
| Downside con los tres cambios | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

El aporte inicial en ambos escenarios es el 30/03/2027. En Base se agregan USD 4,66 el 30/09/2027 y cerca de USD 0,05 por trimestre entre el 30/12/2027 y el 30/09/2028. La refi se cobra el 30/09/2028 y la operación y la venta el 30/12/2028. En Downside se agregan USD 0,76 el 30/06/2027, USD 0,04 el 30/09/2027, USD 7,03 el 30/12/2027 y cerca de USD 0,07 por trimestre entre el 30/03/2028 y el 30/03/2029. La refi se cobra el 30/03/2029 y la operación y la venta el 30/06/2029. El expediente guarda cada importe exacto y calcula los totales antes de redondear.

En Base, C67 sube de 8,75 % a 9,25 % y, por separado, reduce el cobro a USD 17,02. C75 baja de 3 % a 2 % anual y reduce el cobro a USD 17,82. C68 baja de 4 % a 0 % y eleva el cobro a USD 18,86. La corrida conjunta vuelve a calcular el NOI y el cierre, por lo que recoge la interacción entre precio y costos de venta.

En Downside, C67 en 12,50 % queda PENDING por exceder el rango de mercado documentado en el caso sintético. C75 en −12 % anual deja la refi solicitada por encima de la capacidad. C68 en 0 % se calcula por separado. La combinación y el ranking de Downside quedan PENDING. El dictamen y el retorno histórico del 1101 real siguen PENDING.

### Entrada, salida y bloqueos

En el ensamblador D198, el perfil sintético de aceptación técnica admite `rent_inputs.sensitivities` de tipo `miniuw.synthetic-worksheet-sensitivities.v1`. Debe declarar `scenarios.Base.changes` y `scenarios.Downside.changes`. Cada lista admite de uno a tres cambios con celdas distintas. Cada cambio lleva `target_cell`, `operation`, `unit`, `value` como fracción exacta y `source_ref` sintético declarado.

| Operación | Unidad | Recálculo |
|---|---|---|
| `replace_absolute` | Unidad de la celda | Valor de reemplazo explícito, incluido cero |
| `relative_change` | `fraction_of_baseline` | Valor original × (1 + cambio) |
| `basis_point_change` | `bps` | Valor original + cambio ÷ 10.000 |
| `percentage_point_change` | `percentage_points` | Valor original + cambio ÷ 100 |

Cada cambio guarda la celda original, los valores antes y después y la referencia al expediente. La corrida vuelve a pasar por los controles de evidencia, parámetros y capacidad del motor. La falta de una fuente vigente, una unidad inválida o un bloqueo financiero impide publicar la caja afectada. El ranking requiere todas las corridas individuales y ordena de menor a mayor por el cambio en cobros menos aportes, sin descuento. Los empates comparten posición. La corrida conjunta se informa por separado.

`results.json` registra los resultados en `sensitivity_evaluation`. Incluye aportes y cobros fechados por USD 10 y sus diferencias frente al original, para la ruta principal de caja del expediente. Las sensibilidades son un análisis sintético separado del PDF de decisión y del dictamen. La derivación automática de Downside, los demás drivers y el Upside de la Política 33 quedan pendientes de implementación y, donde corresponda, de aprobación de criterios.

### Reproducción en el VPS

Con las dependencias de referencia y OCR del repositorio:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_sensitivities
PYTHONPATH=src:tools python3 tools/check_worksheet_alternatives_D155.py --output /tmp/miniuw-d155
```

La prueba nueva ensambla el expediente original y las variantes, verifica los cobros contra sus movimientos y el precio de salida, reproduce el expediente por B16 y prueba unidad inválida y revisión financiera desactualizada. D155 verifica la compatibilidad de las alternativas C80–C82.

La ampliación optativa [D254](workbook-operating-sensitivities-D254.md) incorpora rentas, vacancia, concesiones y crecimiento de gastos mediante el esquema v2. El contrato v1 y sus expedientes anteriores conservan su reproducción original.

## 13.4 · D254 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-operating-sensitivities-D254.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D254 amplía las sensibilidades explícitas del modelo usando el expediente sintético D200. Cada variante recalcula ingresos, NOI, capacidad bancaria y caja fechada por USD 10 de equity inicial verificado. La inversión personal requiere sus propios términos de reparto. El dictamen operativo permanece PENDING.

| Escenario sintético | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar después de venta |
|---|---:|---:|---:|---:|
| Base original | USD 10,00 | USD 4,87 | USD 18,06 | USD 0,00 |
| Base con once cambios operativos simultáneos | USD 10,00 | USD 4,87 | USD 17,79 | USD 0,00 |
| Downside original | USD 10,00 | USD 8,19 | USD 6,08 | USD 12,11 |
| Downside con renta fuera de evidencia y crecimiento de gastos que supera capacidad | USD 10,00 de referencia | PENDING | PENDING | PENDING |

La entrada inicial es el 30/03/2027. En Base, los aportes adicionales ocurren entre el 30/09/2027 y el 30/09/2028; la refinanciación se cobra el 30/09/2028 y los cobros operativos y de venta el 30/12/2028. En Downside original, los aportes adicionales ocurren entre el 30/06/2027 y el 30/03/2029; la refi se cobra el 30/03/2029 y la operación y venta el 30/06/2029. Cada importe y fecha se conservan sin redondear en `cash_per_usd_10.events`. Los importes de esta tabla se redondean después de sumar.

### Alcance y contrato

La entrada optativa `rent_inputs.sensitivities` admite el esquema `miniuw.synthetic-worksheet-sensitivities.v2` dentro del perfil sintético de aceptación técnica. Conserva la estructura de [D253](workbook-sensitivities-D253.md): inventario explícito Base/Downside, celdas únicas y cada cambio con operación, unidad, valor y fuente sintética. El máximo es catorce celdas distintas por escenario.

| Entrada | Unidad de reemplazo | Conexión comprobada |
|---|---|---|
| C8–C11, renta residencial por tipología | `USD_per_unit_per_month` o `USD_per_rentable_sf_per_month`, según C7 | Renta potencial y efectiva, NOI, refi, venta y caja |
| C14, pérdida residencial; C15, concesiones | `fraction` | Descuentos de renta separados, NOI y caja |
| C16–C18, renta comercial | `USD_per_rentable_sf_per_year` | Superficie y vigencia comercial ya documentadas, ingreso reconocido y NOI |
| C19, vacancia comercial | `fraction` | Pérdida comercial, ingreso neto y NOI |
| C76, crecimiento de gastos | `annual_effective_growth_fraction` | Proyección de gastos bajo la convención vigente, NOI y capacidad |
| C67, C68 y C75 | Unidades originales de D253 | Cap de venta, costo de venta y crecimiento de rentas |

La sustitución absoluta y el cambio relativo admiten rentas y fracciones. Los cambios en puntos básicos o porcentuales se admiten sólo en las fracciones. La base de renta residencial debe estar confirmada por C7. Un componente comercial declarado N/A no se convierte en un ingreso mediante una sensibilidad.

C14 conserva su composición documentada. El cambio no inventa el desglose de pérdidas necesario para calcular un equilibrio físico cuando ese desglose falta.

Cada observación v2 conserva los valores originales y propuestos, su fuente, los NOI por período, las fuentes por celda, los términos comerciales y de crecimiento, la capacidad y cada aporte y cobro por USD 10. La corrida conjunta vuelve a ejecutar el motor: el resultado incluye las interacciones entre cambios. La caja y el dictamen del expediente original se preservan. La sensibilidad se registra en `results.json`; no reemplaza el PDF integral vigente.

### Ensayos y bloqueos

En Base, el ensayo declara una reducción relativa del 1 % en C8–C11 y C16–C18 y un aumento de 1 pb en C14, C15, C19 y C76. Son once cambios de prueba explícitos. Se cotejan individualmente y en conjunto; cada uno reduce el NOI de salida y afecta la caja. La combinación produce un resultado distinto de sumar los once impactos aislados.

En Downside, C8 se reemplaza por cero mediante un cambio relativo de −100 %: el cero es explícito y el control de mercado bloquea el resultado por estar fuera del respaldo. Por separado, C76 se reemplaza por 50 % anual y se bloquea la refi porque el principal solicitado supera la capacidad. Son ensayos de bloqueo, sin adopción como escenario financiero del modelo. La combinación y el ranking quedan PENDING.

Los once nuevos campos prueban valor vacío, texto vacío y espacios tanto en el cambio como en la base. Ninguno se convierte en cero. El cero numérico explícito se conserva en el enlace y después debe satisfacer los controles financieros y de evidencia. La falta de vigencia o de fuente sigue bloqueando el cálculo afectado y la entrega correspondiente.

### Reproducción

Con las dependencias de referencia y OCR instaladas:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_operating_sensitivities test_worksheet_sensitivities
PYTHONPATH=src:tools python3 tools/check_worksheet_blanks_and_zero_D171.py
PYTHONPATH=src:tools python3 tools/check_worksheet_alternatives_D155.py --output /tmp/miniuw-d254-d155
```

La prueba integrada ensambla desde los respaldos sintéticos, coteja los movimientos y la interacción, y reproduce la revisión vigente mediante B16. La regresión D253 comprueba sus controles anteriores. La evidencia del VPS y los expedientes generados se guardan fuera de GitHub; el repositorio conserva código, pruebas y esta descripción reproducible.

En el VPS pasaron las tres pruebas nuevas y el ensayo de regresión D253. D171 verificó 440 vacíos con valor nulo (436 PENDING y cuatro N/A declarados), 98 ceros numéricos conservados y doce ceros rechazados en campos no numéricos, más sus casos integrados. D155 verificó cuatro planillas, cinco alternativas calculadas y una bloqueada por capacidad. B16 reprodujo sin diferencias el expediente D200 ya guardado y un expediente de sensibilidades v1 generado con el código original D253. La batería general completa de D253 es el antecedente; este hito ejecuta las verificaciones dirigidas descritas.

Las políticas de escenarios de [D252](worksheet-policy-implementation-audit-D252.md) continúan parcialmente implementadas: aún quedan otros drivers, la derivación aprobada de Downside, las excepciones y el Upside. Esta ampliación técnica requiere cambios declarados y conserva los criterios vigentes. Las políticas financieras pendientes y las recomendaciones del Automation Spec no se activan mediante este hito. Los dictámenes reales y retornos históricos permanecen PENDING.

[D255](workbook-budget-sensitivities-D255.md) agrega el presupuesto C37–C42 y su conexión con deuda y caja mediante el esquema optativo v3. Conserva los resultados y contratos anteriores.

## 13.5 · D255 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-budget-sensitivities-D255.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D255 conecta las sensibilidades explícitas del presupuesto C37–C42 con la deuda de obra, sus intereses, el cierre de refinanciación y la caja fechada por USD 10 de equity inicial. Usa los respaldos sintéticos de aceptación D200. El dictamen operativo y los retornos reales permanecen PENDING; los términos de reparto personales requieren su propia evidencia.

| Escenario sintético | Aporte inicial | Aportes adicionales | Cobro de refi | Cobro operativo | Cobro neto de venta | Cobro total | Caja sin recuperar |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base original | USD 10,00 | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,78 | USD 18,06 | USD 0,00 |
| Base con siete cambios conjuntos | USD 10,00 | USD 4,90 | USD 2,84 | USD 1,43 | USD 13,77 | USD 18,05 | USD 0,00 |
| Downside original | USD 10,00 | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,08 | USD 6,08 | USD 12,11 |
| Downside con siete cambios conjuntos | USD 10,00 | USD 6,92 | USD 2,44 | USD 0,55 | USD 3,08 | USD 6,07 | USD 10,85 |

El aporte inicial es el 30/03/2027. En Base conjunto se aportan aproximadamente USD 4,69 el 30/09/2027 y USD 0,05 por trimestre entre el 30/12/2027 y el 30/09/2028. La refi se cobra el 30/09/2028 y la operación y venta el 30/12/2028. En Downside conjunto se aportan aproximadamente USD 6,56 el 30/12/2027 y USD 0,07 por trimestre entre el 30/03/2028 y el 30/03/2029. La refi se cobra el 30/03/2029 y la operación y venta el 30/06/2029. Los totales se calculan con fracciones exactas antes de redondear; el expediente conserva cada fecha e importe en `cash_per_usd_10.events`.

Los importes corresponden a ensayos del motor. La eliminación explícita de contingencia y de pagos anticipados en Downside prueba el comportamiento del cero y sus interacciones; no es una recomendación financiera ni una nueva política de Downside.

### Conexiones implementadas

La entrada optativa `rent_inputs.sensitivities` agrega el esquema `miniuw.synthetic-worksheet-sensitivities.v3`. Conserva los contratos v1 y v2 de [D253](workbook-sensitivities-D253.md) y [D254](workbook-operating-sensitivities-D254.md). Admite hasta veinte celdas distintas por escenario: las catorce existentes y las seis siguientes. Cada cambio exige celda, operación, unidad, valor numérico explícito y fuente sintética. Las celdas originales conservan valor, unidad, fuente y revisión.

| Celda y requisito | Definición vigente en el perfil sintético | Unidad de reemplazo | Módulo y evidencia de validación | Estado |
|---|---|---|---|---|
| Inputs!C37, estacionamiento | Tarifa × espacios acreditados; integra obra directa elegible | `USD_per_parking_space` | D144 → D146; presupuesto, compromiso, draws e intereses cotejados | Conectado en sintético |
| Inputs!C38, trabajos de sitio | Importe total separado de obra vertical y estacionamiento | `USD_total` | D144 → D146; fuentes y usos por fecha | Conectado en sintético |
| Inputs!C39, contingencia | Fracción de obra directa vertical + estacionamiento + sitio | `fraction` | D144; reserva financiada separada del costo elegible para draws | Conectado en sintético |
| Inputs!C40, costos indirectos | Fracción del presupuesto de obra con contingencia; incluye developer fee según el alcance declarado | `fraction` | D144; TDC y aportes recalculados | Conectado en sintético |
| Inputs!C41, TI/LC | Tarifa × superficie comercial acreditada; N/A requiere declaración y queda protegido | `USD_per_rentable_sf` | D141 → D144; fuente de superficie conservada, TDC y caja cotejados | Conectado en sintético |
| Inputs!C42, pago anticipado de indirectos | Fracción de indirectos pagada en la fecha inicial de obra; resto al terminar | `fraction` | D144 → D146; pagos, caja libre y aportes por fecha | Conectado en sintético |

Las fórmulas se mantienen en [presupuesto D144](../tools/worksheet_construction_budget_D144.py) y [financiación D146](../tools/worksheet_construction_financing_D146.py). La ampliación conecta esos productores con el runner de sensibilidades y sus pruebas; conserva las bases, frecuencias y restricciones declaradas. Las tarifas admiten reemplazo absoluto o cambio relativo; los puntos básicos y porcentuales corresponden sólo a fracciones.

Cada variante conserva el presupuesto completo, costos de desarrollo, calendario, detalle de financiación, cierre de refi, NOI por período, capacidad y movimientos por USD 10. La cita de cada celda modificada enlaza al cambio exacto. La combinación ejecuta otra corrida y recoge las interacciones; no suma impactos aislados. El expediente original y su PDF integral conservan sus resultados.

### Casos de prueba y conciliaciones

En ambos escenarios se declaran aumentos relativos del 1 % en C37, C38 y C41, un aumento de 10 pb en C40 y una reducción relativa del 0,1 % en la renta C9. Base añade 10 pb a C39 y un punto porcentual a C42. Downside reemplaza C39 y C42 por cero explícito. Cada cambio se ejecuta solo y después junto con los otros seis. Estos valores sólo identifican el ensayo y no se cargan como valores por defecto.

El presupuesto Base pasa de USD 4.100.700,00 a USD 4.108.927,842 y los intereses de obra de USD 57.150,00 a USD 57.195,00. Downside pasa de USD 4.809.792,00 a USD 4.505.823,64 y los intereses de USD 102.900,00 a USD 102.991,50. El presupuesto baja al eliminar la contingencia, mientras los costos directos elegibles crecen y aumentan los draws e intereses. Son conexiones diferentes, que se cotejan separadamente.

La prueba verifica presupuesto por componentes, compromiso igual al menor límite contractual/LTC, principal por período, interés del perfil trimestral, fuentes y usos por fecha, repago de obra en refi y cierre de refi. También concilia los aportes y cobros exactos con sus totales y el saldo de caja sin recuperar. Los cambios de presupuesto aislados preservan el NOI; la combinación con C9 recalcula el NOI y la caja posterior.

En C42, cambiar cuándo se pagan los indirectos conserva el costo total y los cobros. En Base el pago anticipado adicional usa la caja inicial disponible y no genera otro llamado de capital. En Downside el cero explícito difiere aportes hasta el cierre de obra. Se cotejan las dos conductas con sus pagos y saldos por fecha.

Los seis campos prueban valores vacíos, ausencia de valor o fuente, unidades incompatibles y N/A. Ningún vacío se convierte en cero. Otro ensayo declara C37 en USD 1.000.000 por espacio para superar el compromiso documentado: la financiación y la caja afectadas quedan PENDING, con los bloqueos y el detalle de deuda visibles; C40 se calcula por separado y la combinación queda fuera del ranking.

### Reproducción y alcance restante

Con las dependencias de referencia y OCR instaladas:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_budget_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_construction_budget_D144.py --output /tmp/miniuw-d255-d144
```

La prueba integrada parte de los respaldos sintéticos, ensambla el expediente y lo reproduce con B16. Los registros y artefactos del VPS quedan fuera de GitHub; el repositorio conserva código, ensayos sintéticos y esta descripción.

En el VPS pasaron las tres pruebas nuevas, con catorce corridas individuales y dos conjuntas en el ensayo válido, más el ensayo con compromiso excedido. El verificador D144 pasó sus diecisiete casos de planilla, incluidos nueve PENDING esperados. B16 reprodujo sin diferencias los expedientes guardados con sensibilidades v1 y v2. Se ejecutaron verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

La matriz histórica [D252](worksheet-policy-implementation-audit-D252.md) conserva sus pendientes de escenarios: aún faltan otros drivers, la derivación aprobada de Downside, sus excepciones y el Upside. El precio vertical de C35 sigue ligado a su cotización y no se sustituye mediante este contrato. Los plazos, las condiciones bancarias y las reglas fiscales conservan sus respaldos y controles. Este hito no adopta nuevas reglas del Automation Spec ni habilita datos reales o despliegue.

[D256](workbook-calendar-sensitivities-D256.md) conecta C46–C47 con intereses y caja mediante un contrato sintético separado de calendario, con soportes explícitos para cada variante. Conserva la reproducción de v3.

## 13.6 · D256 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-calendar-sensitivities-D256.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D256 conecta cambios explícitos de C46 (meses de obra) y C47 (meses desde TCO hasta estabilización) con los desembolsos, intereses, aportes y cobros fechados. El ensayo utiliza el expediente sintético D200 y un respaldo sintético de absorción declarado para estos plazos. La escala sigue siendo USD 10 de los USD 2.400.000 de equity inicial verificados. Los aportes posteriores se muestran aparte; los criterios y el dictamen operativo permanecen PENDING.

| Escenario y ensayo | Aporte adicional por USD 10 iniciales | Cobro total | Fecha de refi | Fecha de operación y venta | Caja sin recuperar después de venta |
|---|---:|---:|---|---|---:|
| Base original: C46 = 6, C47 = 3 | USD 4,87 | USD 18,06 | 30/09/2028 | 30/12/2028 | USD 0,00 |
| Base: sólo C46 = 9 y TCO respaldado al 01/01/2028 | USD 4,89 | USD 18,06 | 30/12/2028 | 30/03/2029 | USD 0,00 |
| Base: sólo C47 = 0 explícito | USD 4,69 | USD 17,98 | 30/06/2028 | 30/09/2028 | USD 0,00 |
| Base conjunto: C46 = 9 y C47 = 0 | USD 4,72 | USD 17,98 | 30/09/2028 | 30/12/2028 | USD 0,00 |
| Downside original: C46 = 9, C47 = 6 | USD 8,19 | USD 6,08 | 30/03/2029 | 30/06/2029 | USD 12,11 |
| Downside: sólo C46 = 6 | USD 8,23 | USD 6,08 | 30/03/2029 | 30/06/2029 | USD 12,15 |
| Downside: sólo C47 = 9 | USD 8,51 | USD 6,12 | 30/06/2029 | 30/09/2029 | USD 12,39 |
| Downside conjunto: C46 = 6 y C47 = 9 | USD 8,55 | USD 6,12 | 30/06/2029 | 30/09/2029 | USD 12,43 |

El aporte inicial de USD 10 ocurre el 30/03/2027 en todos los casos. En Base conjunto se agregan USD 4,556833 el 30/12/2027 y USD 0,052917 por trimestre del 30/03/2028 al 30/09/2028. Se cobran USD 2,846667 en refi y USD 1,355177 de operación más USD 13,781629 de venta en las fechas de la tabla. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 7,284046 el 30/09/2027 y USD 0,071458 por trimestre del 30/12/2027 al 30/06/2029. Se cobran USD 2,445833 de refi y USD 0,590198 de operación más USD 3,081180 de venta. Los importes exactos y cada fecha se conservan en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

Son pruebas de conexiones con valores declarados. C47 = 0 es un supuesto sintético de estabilización inmediata y no una regla por defecto. El retorno personal requiere términos de reparto propios; la caja sin recuperar al cierre es una medida del horizonte del caso.

El respaldo sintético de absorción del ensayo declara un rango de cero a doce meses con fuente y huella propias. El runner no amplía los rangos recibidos para acomodar una variante.

### C46–C47, intereses y calendario

| Ensayo | Intereses de obra del proyecto en Base, USD | Intereses de obra del proyecto en Downside, USD |
|---|---:|---:|
| Original | 57.150 | 102.900 |
| Sólo C46 | 63.500 | 111.475 |
| Sólo C47 | 44.450 | 120.050 |
| Conjunto | 50.800 | 128.625 |

Los intereses de esta tabla son importes del proyecto completo. Se cotejan por período como saldo inicial más draw al inicio, multiplicado por la fracción trimestral documentada. Mover un desembolso puede aumentar intereses aun cuando la obra termina antes. Mover la estabilización cambia los períodos hasta refinanciar, el déficit reservado de lease-up, las ventanas de NOI y las fechas de los cobros. El runner ejecuta cada caso y su conjunto con el motor existente.

| Requisito y ubicación | Definición vigente | Módulo afectado | Evidencia de validación | Estado |
|---|---|---|---|---|
| Inputs!C46 | Meses de obra en la grilla trimestral; mínimo tres; TCO independiente y posterior al fin de obra | D145 → D144 → D146 | Fecha de terminación, pagos, draws, principal e interés por período | Conectado en sintético |
| Inputs!C47 | Meses de TCO a estabilización; cero explícito permitido con respaldo; horizonte compatible | D145 → D154 → D146 y renta/NOI | Estabilización, fondo de lease-up, refi, venta y caja fechada | Conectado en sintético |
| TCO, venta y ventana fiscal | Sólo cambian mediante registros sintéticos explícitos con fuente; se comprueban contra el calendario | Soportes D256, alcance D174 y revisión D173 | Falta de fecha de venta o de ventana fiscal deja PENDING el cálculo afectado | Validado en el perfil de prueba |
| Deuda permanente | Ocho pagos desde la originación, según el PDF bancario del ensayo | D152 y B08 | El plazo se conserva; la fecha absoluta se deriva de la nueva originación. Alterar el plazo sin otro respaldo queda PENDING | Validado en sintético |
| Deuda de obra | Vencimiento absoluto de la cotización, compromiso y disponibilidad por draw conservados | D146 y productor de deuda | Refi posterior al vencimiento produce `schedule_past_maturity_no_extension_inferred` | Validado en sintético |
| Base de USD 10 | Mismo aporte inicial y fecha de compra, aportes/cobros brutos por fecha | Runner D253/D256 | Conciliación exacta con totales, refi y saldo sin recuperar | Validado en sintético |

La obra Base de nueve meses exige un TCO nuevo al 01/01/2028, aportado explícitamente en el ensayo. Al combinarla con C47 = 0, la fecha de venta vuelve a la del original. En Downside se conserva el TCO original y los efectos de C46 y C47 se acumulan. No se mueve el TCO sólo porque cambió C46.

### Entrada y soportes de cada variante

El esquema optativo `miniuw.synthetic-worksheet-sensitivities.v4` se declara en `rent_inputs.sensitivities` del perfil de aceptación técnica. Este contrato se concentra en C46–C47; los contratos anteriores de [D255](workbook-budget-sensitivities-D255.md) conservan su alcance y reproducción.

Cada escenario contiene `changes` y `calendar_support`. Cada cambio declara celda, operación `month_change` o `replace_absolute`, unidad `months`, valor entero explícito y fuente sintética. El resultado debe satisfacer los límites y la grilla trimestral vigentes.

`calendar_support` exige `individual` con una entrada por celda y `combined` para el conjunto. Cada entrada exige `source_ref` y admite sólo TCO, fecha de venta, número de pagos al vencimiento permanente y respaldo fiscal del comprador para la ventana exacta. Los campos ausentes conservan sus respaldos originales; si resultan incompatibles, el motor bloquea el cálculo. El TCO del conjunto debe conservar el respaldo independiente utilizado en los casos individuales. Las fechas derivadas de venta y sus ventanas deben corresponder al calendario conjunto, que puede diferir de cada caso aislado.

El runner conserva la cita de cada cambio, las fechas originales y nuevas, los soportes y sus huellas, presupuesto, financiación por fecha, términos bancarios, capacidad, NOI y caja. La validación bancaria vuelve a cotejar los términos con el PDF original; el soporte estructurado no reemplaza una cotización contradictoria. La revisión del expediente enlaza la solicitud completa. La comparación de deltas de caja es nominal y no decide qué calendario conviene por valor presente.

### Bloqueos y reproducción

Las pruebas verifican vacíos de C46/C47 tanto en la base como en el cambio, unidades inválidas y fracciones de mes. Ningún vacío se convierte en cero. El ensayo válido conserva C47 = 0 como valor explícito. Los controles integrados retiran la fecha de venta de Downside y el respaldo fiscal de Base: ambos cálculos afectados quedan PENDING. Otro control altera a siete pagos el plazo de ocho del PDF y queda PENDING por discrepancia bancaria. Un plazo de lease-up Downside de doce meses lleva la refi después del vencimiento absoluto de obra: tanto el cambio individual como el conjunto quedan PENDING, sin inferir prórroga.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_calendar_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_project_calendar_D145.py --output /tmp/miniuw-d256-d145
```

Se utilizan las dependencias de referencia y OCR del repositorio. La aceptación ensambla desde los respaldos sintéticos y reproduce el expediente vigente con B16. Los artefactos generados y registros del VPS quedan locales. GitHub conserva el código, las pruebas y esta descripción; el PDF de decisión original mantiene su alcance.

En el VPS pasaron las tres pruebas nuevas: cuatro cambios individuales y dos conjuntos válidos, más los controles de faltantes y deuda. D145 pasó sus trece casos de planilla, con diez PENDING esperados. B16 reprodujo sin diferencias el expediente D255 de sensibilidades v3 guardado. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

Se conservan las convenciones del perfil de financiación trimestral y el déficit mensual de lease-up declarado. Otros costos de tiempo, seguros de obra o gastos generales requieren su propio alcance y respaldo antes de recalcularse; no se agregan coeficientes. Los plazos del ensayo no se adoptan como escenarios automáticos, y la validación profesional y el uso real siguen pendientes.

[D257](workbook-construction-sensitivities-D257.md) conecta C51–C53 con desembolsos, intereses, comisiones y caja mediante cotizaciones PDF sintéticas ligadas al respaldo original. Conserva la reproducción de v4.

## 13.7 · D257 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-construction-sensitivities-D257.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D257 conecta C51 (LTC de obra), C52 (tasa nominal anual) y C53 (comisión sobre el compromiso) con los desembolsos, intereses, repago en refi y caja del proyecto por USD 10 de equity inicial verificado. Cada variante cuenta con una cotización PDF sintética ligada al respaldo original. El aporte inicial sigue siendo el 30/03/2027 y la escala es 10/2.400.000. Los aportes adicionales se muestran aparte. El dictamen operativo y el retorno personal sin términos de reparto permanecen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C51 | USD 4,8702 | USD 18,0594 | USD 0,0000 |
| Base, sólo C52 | USD 4,8968 | USD 18,0594 | USD 0,0000 |
| Base, sólo C53 | USD 4,8035 | USD 18,0594 | USD 0,0000 |
| Base conjunto | USD 4,8333 | USD 18,0594 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C51 | USD 8,1798 | USD 6,0767 | USD 12,1031 |
| Downside, sólo C52 | USD 8,2322 | USD 6,0767 | USD 12,1555 |
| Downside, sólo C53 | USD 8,2154 | USD 6,0767 | USD 12,1387 |
| Downside conjunto | USD 8,2456 | USD 6,0767 | USD 12,1689 |

En Base conjunto se aportan aproximadamente USD 4,595182 el 30/09/2027 y USD 0,059531 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,431058 de operación más USD 13,781629 de venta el 30/12/2028. En Downside conjunto se aportan USD 0,775617 el 30/06/2027, USD 0,039302 el 30/09/2027, USD 7,037619 el 30/12/2027 y USD 0,078604 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,549690 de operación más USD 3,081180 de venta el 30/06/2029. Cada importe exacto y fecha se conserva en `cash_per_usd_10.events`; se redondea después de totalizar.

Los cobros permanecen iguales en estos ensayos porque se conserva el mismo principal de obra efectivamente girado y el costo financiero se cubre con aportes. Cambian los aportes y, por lo tanto, el resultado neto y el múltiplo. Estos valores prueban las conexiones; no son nuevos criterios ni supuestos para un deal real.

### Variables, respaldo y cálculo

| Requisito y ubicación | Definición vigente en el perfil | Conexión y evidencia | Estado |
|---|---|---|---|
| Inputs!C51 | Compromiso = menor entre costo directo elegible × LTC y límite contractual | D146; compromiso cotejado con LTC y límite. Los giros siguen la solicitud de facturas y la disponibilidad por fecha | Conectado en sintético |
| Inputs!C52 | Interés nominal anual simple por trimestre sobre saldo inicial más draw al inicio | D146/T68; interés exacto por período y conciliación con pagos/aportes | Conectado en sintético |
| Inputs!C53 | Comisión de apertura = compromiso × fracción explícita; pagada al abrir | D146; comisión, caja inicial y aportes posteriores conciliados | Conectado en sintético |
| Cotización de cada variante | PDF de una página con escenario, deal, revisión, unidades, convenciones y padre verificado | B08; hash, filas, alcance y coincidencia exacta con las celdas | Validado en sintético |
| Refi y retorno por USD 10 | Repago del principal realmente girado, cierre conciliado y flujos brutos fechados | D146 y motor vigente; fuentes/usos, principal, interés, aportes y cobros cotejados | Validado en sintético |

El ensayo declara, por separado y luego juntos:

- Base: C51 de 60 % a 65 %; C52 de 8 % a 9 % anual; C53 de 1 % a cero explícito.
- Downside: C51 de 50 % a 40 %; C52 de 10 % a 11 % anual; C53 de 1,5 % a 2 %.

| Importe del proyecto completo, USD | Base original | Base conjunto | Downside original | Downside conjunto |
|---|---:|---:|---:|---:|
| Compromiso | 1.524.000 | 1.600.000 | 1.250.000 | 1.097.600 |
| Principal efectivamente girado y repagado | 635.000 | 635.000 | 686.000 | 686.000 |
| Intereses de obra | 57.150 | 64.293,75 | 102.900 | 113.190 |
| Comisión de apertura | 15.240 | 0 | 18.750 | 21.952 |

En Base, subir el LTC lleva el compromiso al límite contractual de USD 1.600.000, pero conserva giros por USD 635.000 porque la solicitud sigue siendo 25 % de las facturas elegibles. En Downside el LTC de 40 % pasa a ser el límite activo. La comisión del conjunto se calcula sobre el compromiso nuevo: no se suman los impactos aislados.

### Contrato sintético v5

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v5` dentro del perfil de aceptación técnica. Este contrato se concentra en C51–C53, con uno a tres cambios únicos por escenario. Los contratos anteriores, incluido [D256](workbook-calendar-sensitivities-D256.md), conservan su alcance y reproducción.

Cada cambio declara `target_cell`, `operation`, `unit`, `value` exacto y `source_ref`. Las unidades de reemplazo son `fraction` para C51, `annual_nominal_fraction` para C52 y `fraction_of_commitment` para C53. También se admiten cambios relativos, puntos básicos y puntos porcentuales con las unidades explícitas de la operación.

Cada escenario agrega `construction_support.individual` por celda y `construction_support.combined` para el conjunto. Cada soporte exige `source_ref`, `revision`, `parent_document_id`, `parent_sha256`, `pdf_sha256` y `pdf_base64`. El PDF debe contener la página bancaria sintética del escenario y deal correctos, con todos sus campos y convenciones. El padre es la cotización ya leída del expediente original. El PDF nuevo se lee como texto, sin atribuirle una lectura OCR.

El PDF sólo puede variar LTC, tasa y comisión. Compromiso contractual máximo, fracción solicitada de facturas, disponibilidad por draw y vencimiento se conservan. El motor vuelve a comparar la cotización con los valores completos de la variante: un cambio no declarado en otra celda también queda PENDING. La evidencia conserva la huella del padre y la del PDF nuevo, su revisión, página, citas y método de lectura. El PDF está incluido en el JSON del caso para que B16 pueda reproducirlo.

Cada PDF está limitado a 32 KiB; el JSON completo v5 del perfil sintético admite hasta 96 KiB. Los contratos anteriores conservan el límite de 48 KiB y los perfiles previos que corresponda conservan además su límite de 32 KiB. La prueba comprueba estas restricciones. Los soportes no amplían límites bancarios ni autentican una aprobación real.

### Pruebas, bloqueos y reproducción

La aceptación verifica seis cambios individuales y dos conjuntos. Conciliaciones: menor límite LTC/contractual, draws y principal por período, interés, comisión, pagos por fecha, repago de obra en refi, cierre y caja por USD 10. El presupuesto, NOI, calendario y cobros originales se conservan donde el cambio no los afecta. La corrida conjunta usa los tres términos simultáneamente y recoge la interacción entre compromiso y comisión.

Los controles prueban vacíos en la base y el cambio, ausencia de valor o fuente, unidades inválidas, hash alterado, padre incorrecto, filas faltantes, escenario equivocado y cambios indebidos de límites. Los cálculos afectados quedan PENDING. Una cotización que no coincide con C53 también queda PENDING. En otro control, C52 = 0 produce interés cero explícito; C51 = 0 conserva ese valor y deja PENDING la financiación porque los giros solicitados superan el compromiso cero. C53 = 0 produce comisión cero en el ensayo válido. Ningún vacío se interpreta como cero.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_construction_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_construction_financing_D146.py --output /tmp/miniuw-d257-d146
```

Se utilizan las dependencias de referencia y OCR del repositorio para los respaldos originales. Los paquetes generados y registros del VPS quedan fuera de GitHub; se preservan código, pruebas y esta descripción. El PDF de decisión original conserva su alcance. El perfil sigue usando interés trimestral simple pagado en caja; otros calendarios y capitalización requieren términos y cálculo compatibles. No se adoptan valores por defecto ni se habilitan despliegue o decisiones reales.

En el VPS pasaron las cuatro pruebas nuevas, con seis corridas individuales y dos conjuntas válidas más los controles PENDING y de cero explícito. D146 pasó sus quince casos, con diez PENDING esperados. B16 reprodujo D256 sin diferencias. La ejecución por consola del expediente v5 coincidió byte por byte en sus diez archivos con el ensamblador D198. Se ejecutaron verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

[D258](workbook-expense-sensitivities-D258.md) conecta C57–C59 con gastos, NOI y caja, conservando las bases de controlables, administración y seguro y la reproducción de v5.

## 13.8 · D258 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-expense-sensitivities-D258.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D258 conecta C57 (gastos controlables), C58 (administración) y C59 (seguro) con gastos, NOI, capacidad de refi y flujos del proyecto. El ensayo utiliza respaldos sintéticos D200 y revisiones explícitas del seguro. Se mantiene la escala de USD 10 sobre USD 2.400.000 de equity inicial verificado, con aportes posteriores separados. El dictamen operativo y el retorno personal sin términos de reparto siguen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C57 | USD 4,8670 | USD 18,0422 | USD 0,0000 |
| Base, sólo C58 | USD 4,8670 | USD 18,0569 | USD 0,0000 |
| Base, sólo C59 | USD 4,8670 | USD 18,0554 | USD 0,0000 |
| Base conjunto | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C57 | USD 8,1893 | USD 6,0594 | USD 12,1299 |
| Downside, sólo C58 | USD 8,1893 | USD 6,0753 | USD 12,1140 |
| Downside, sólo C59 | USD 8,1893 | USD 6,0708 | USD 12,1186 |
| Downside conjunto | USD 8,1893 | USD 6,0521 | USD 12,1372 |

El aporte inicial ocurre el 30/03/2027. En Base conjunto se agregan aproximadamente USD 4,655375 el 30/09/2027 y USD 0,052917 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,429122 de operación más USD 13,759945 de venta el 30/12/2028. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 0,035729 el 30/09/2027, USD 7,034046 el 30/12/2027 y USD 0,071458 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,547629 de operación más USD 3,058660 de venta el 30/06/2029. El expediente conserva fracciones exactas y cada fecha en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

Estos son ensayos del motor con cambios declarados. En ambos escenarios se prueba C57 +1 % relativo, C58 +1 punto básico y C59 +1 % relativo. Se ejecuta cada uno y después los tres juntos. Los giros, intereses y aportes de obra se conservan; los gastos operativos reducen el NOI y los cobros de operación y venta. No se cargan como valores por defecto ni como criterios de inversión.

### Bases y conciliaciones

| Campo y ubicación | Definición vigente | Conexión y evidencia de validación | Estado |
|---|---|---|---|
| Inputs!C57 | Importe anual por unidad residencial controlable, incluyendo C25–C28 | D148: total = tarifa × unidades. Servicios incluidos + controlables sin servicios = total. El NOI resta cada gasto una vez | Conectado en sintético |
| Inputs!C58 | Fracción de renta residencial efectiva más otros ingresos C13; excluye renta comercial | D148: base elegible y comisión verificadas por período; se preservan pérdidas, concesiones y crecimiento de la renta | Conectado en sintético |
| Inputs!C59 | Prima anual por unidad residencial asegurada confirmada | D148/D166: prima × unidades cubiertas; cotejo exacto con respaldo de seguro y cobertura | Conectado en sintético |
| Proyección y NOI | Crecimiento de gastos según la convención vigente; impuesto según el perfil | D154 y motor NOI: gastos y NOI reconciliados en las cuatro ventanas del caso | Validado en sintético |
| Capacidad, caja y cierre | Se recalculan con los NOI bancario, de valoración y de salida propios | Cierre y movimientos por USD 10 reconciliados; los bloqueos existentes se conservan | Validado en sintético |

| Importe anual del proyecto completo, USD | Base original | Base conjunto | Downside original | Downside conjunto |
|---|---:|---:|---:|---:|
| Gastos operativos antes de impuesto | 76.702,4000 | 77.167,0048 | 87.482,8000 | 88.076,4380 |
| NOI operativo | 402.439,1000 | 401.974,4952 | 228.710,1667 | 228.215,4683 |

Las pruebas cotejan por período los controlables, servicios, seguro y administración, además de los gastos fijos del alcance. El NOI se concilia con renta efectiva, otros ingresos, comercial neto, gastos e impuesto. La variación del NOI no se supone igual a la variación del gasto: el impuesto se recalcula según la rama fiscal existente. Se conserva el tratamiento del NOI después de reservas en las métricas que lo requieren; esta conexión no redefine sus bases.

### Contrato sintético v6 y respaldo del seguro

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v6` en el perfil sintético de aceptación técnica. Se concentra en C57–C59, con uno a tres cambios únicos por escenario. Los contratos anteriores, incluido [D257](workbook-construction-sensitivities-D257.md), conservan su alcance y reproducción.

Cada cambio declara celda, operación, unidad, valor exacto y fuente sintética. Las unidades de reemplazo son `USD_per_residential_unit_per_year`, `fraction_of_effective_residential_income_plus_c13` y `USD_per_insured_unit_per_year`. Las tarifas admiten sustitución absoluta o cambio relativo; los puntos básicos y porcentuales corresponden a C58.

Cada escenario agrega `expense_support.individual` por celda y `expense_support.combined`. Cada entrada exige `source_ref`. Si el cambio incluye C59, también exige `insurance`, con `parent_sha256`, `document` y `sha256`. El padre es el respaldo de seguro del expediente original; el documento nuevo conserva las claves del padre y sólo puede modificar su fuente y la prima. La vigencia, escenario, deal, unidad, base, cobertura y cantidad de unidades aseguradas se conservan. El motor D166 vuelve a cotejar la prima con C59. Un soporte de C57 o C58 no puede introducir por sí solo otra cotización de seguro.

En el ensayo, la prima Base pasa de USD 300 a USD 303 por unidad/año; Downside pasa de USD 550 a USD 555,50. Son registros estructurados sintéticos ligados por huellas, no una lectura nueva de PDF u OCR. La evidencia conserva el padre, la revisión, su fuente y la cita del valor cambiado. Los soportes no autentican cotizaciones reales ni modifican criterios de aprobación.

El runner conserva los gastos y NOI por período, fuentes de celdas, respaldo de seguro, capacidad, cierre y cada movimiento por USD 10. La corrida conjunta vuelve a ejecutar el motor. El expediente original y su PDF integral mantienen sus resultados. El JSON v6 conserva el límite anterior de 48 KiB.

### Pruebas de faltantes, cero y reproducción

Los tres campos prueban vacíos tanto en la base como en el cambio, y unidades inválidas. El cero numérico explícito se preserva. El ensayo integrado de cero comprueba que C58 = 0 produce administración cero y C59 = 0 produce seguro cero sólo con su respaldo sintético explícito. Son controles técnicos, no supuestos de gratuidad para un deal real. C57 = 0 queda PENDING cuando los servicios incluidos tienen costo: el modelo no elimina C25–C28 para hacerlo coincidir.

Otros controles retiran el respaldo de C59 o suministran una prima contradictoria; el cálculo afectado queda PENDING y su ranking incompleto queda vacío. Se rechazan hashes o padre incorrectos y cambios silenciosos de cobertura, unidades, vigencia o escenario. Ningún vacío se interpreta como cero.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_expense_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_operating_costs_D148.py --output /tmp/miniuw-d258-d148
```

Se utilizan las dependencias de referencia y OCR del repositorio para los respaldos originales. Los paquetes y registros del VPS quedan fuera de GitHub; se preservan código, pruebas y esta descripción. Los costos y períodos ajenos al alcance declarado requieren sus propias fuentes. La validación profesional, los datos reales y el despliegue siguen pendientes.

En el VPS pasaron las tres pruebas nuevas, con seis cambios individuales y dos conjuntos válidos, además de los controles de faltantes y cero explícito. D148 pasó sus doce casos de planilla, con siete PENDING esperados. B16 reprodujo sin diferencias el expediente D257 guardado con sensibilidades v5. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

[D259](workbook-reserve-sensitivities-D259.md) agrega C60 al conjunto de gastos, preservando por separado la reserva restringida, su liquidación y el fondeo adicional requerido.

## 13.9 · D259 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-reserve-sensitivities-D259.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Continuación: [C61–C62, impuesto, NOI y caja por USD 10 en D260](workbook-tax-sensitivities-D260.md).

D259 conecta C60 con la caja restringida, el cierre y el retorno por USD 10, por separado y junto con los gastos C57–C59 de D258. El ensayo usa respaldos sintéticos D200 y la misma escala de 10/2.400.000 de equity inicial verificado. El aporte inicial ocurre el 30/03/2027; los aportes posteriores se conservan aparte. El dictamen operativo y el retorno personal sin términos de reparto permanecen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C60 +1 % | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, C57–C59 de D258 | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Base, C57–C60 juntos | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C60 +1 % | USD 8,1893 | USD 6,0756 | USD 12,1137 |
| Downside, C57–C59 de D258 | USD 8,1893 | USD 6,0521 | USD 12,1372 |
| Downside, C57–C60 juntos | USD 8,1893 | USD 6,0510 | USD 12,1383 |

En Base conjunto se agregan aproximadamente USD 4,655375 el 30/09/2027 y USD 0,052917 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,427822 de operación más USD 13,761245 de venta el 30/12/2028. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 0,035729 el 30/09/2027, USD 7,034046 el 30/12/2027 y USD 0,071458 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,545462 de operación más USD 3,059743 de venta el 30/06/2029. Cada fecha e importe exacto se conserva en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

### Reserva y liquidación

C60 conserva su definición de caja restringida. En el perfil de prueba se deposita la reserva anual al liquidar la operación, antes de la venta. La política de apertura cero y ausencia de otros movimientos debe estar declarada. La fracción liberada al vendedor y el remanente transferido al comprador tienen fuente propia. Los valores del ensayo no se adoptan como reglas para un deal real.

| Importe del proyecto completo, USD | Base original | Base con C60 +1 % | Downside original | Downside con C60 +1 % |
|---|---:|---:|---:|---:|
| Tarifa anual por unidad elegible | 1.200 | 1.212 | 2.000 | 2.020 |
| Depósito, 26 unidades elegibles | 31.200 | 31.512 | 52.000 | 52.520 |
| Liberación al vendedor al vender | 31.200 | 31.512 | 26.000 | 26.260 |
| Transferencia restringida al comprador | 0 | 0 | 26.000 | 26.260 |

La política declarada del caso devuelve el 100 % en Base y el 50 % en Downside. Por eso, en Base el aumento de C60 cambia la composición entre cobro operativo y venta, conservando el cobro nominal total. En Downside la parte transferida aumenta y el vendedor cobra menos. Se concilian ambos movimientos incluso cuando tienen la misma fecha; no se compensan antes de construir el flujo bruto.

| Variable o proceso | Definición y conexión | Evidencia de validación | Estado |
|---|---|---|---|
| Inputs!C60 | Tarifa anual × unidades elegibles acreditadas | D149: depósito exacto y cita del cambio | Conectado en sintético |
| Caja operativa | NOI menos servicio y depósito, con aporte adicional si falta caja bajo la política declarada | Conciliación D200 de fuentes y usos; aporte y cobro separados | Validado en sintético |
| Caja restringida | Depósito = liberación + transferencia al comprador | Saldos y residuales de operación y venta exactos | Validado en sintético |
| NOI operativo, bancario y de valoración | Conservan su base ante un cambio aislado de C60 | Comparación por período, capacidad y precio bruto de venta sin variación | Validado en sintético |
| NOI operativo después de reserva | NOI del período operativo menos su depósito efectivo | Salida `operating_noi_after_reserve` con período, huella de NOI y cita de C60 | Validado en sintético |
| C57–C60 juntos | Recálculo de gastos y reserva con sus bases separadas | Ocho cambios individuales y dos conjuntos; conciliación de cada flujo por USD 10 | Validado en sintético |

La salida después de reserva corresponde a la ventana operativa declarada. Las métricas de desempeño mantienen sus definiciones y períodos vigentes. La comparación por deltas nominales de caja no constituye un criterio PASS/FAIL: dos variantes pueden cobrar lo mismo y tener distinta necesidad de fondos o distinto NOI después de reservas.

### Contrato sintético v7

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v7` en el perfil de aceptación técnica. Extiende el contrato de gastos [D258](workbook-expense-sensitivities-D258.md) con C60 y hasta cuatro cambios distintos por escenario. Los contratos anteriores conservan su alcance.

C60 exige una operación explícita, valor y fuente. La unidad de reemplazo es `USD_per_eligible_unit_per_year`; también admite cambios relativos. Los puntos básicos y porcentuales siguen reservados a las fracciones, como C58. Se conserva `expense_support` individual y conjunto; sólo los cambios que incluyen C59 requieren revisión del seguro. Elegibilidad, fracción de liberación y política de fondeo de la reserva se toman de sus respaldos originales, sin deducirlos del valor de C60.

El ensayo agrega C60 +1 % relativo a C57 +1 %, C58 +1 pb y C59 +1 % de D258. Cada campo se ejecuta solo y los cuatro juntos. La evidencia agrega el detalle de reserva de reposición, la cuenta permanente separada, el servicio de deuda y el cierre de venta. El JSON conserva el límite de 48 KiB y B16 reproduce el expediente desde sus respaldos. El PDF integral original conserva su alcance.

### Faltantes, cero y necesidad de fondos

Los controles prueban C60 vacío en la base o en el cambio y verifican que nunca se convierta en cero. También prueban ausencia de elegibilidad, de la fracción liberada y de su fuente: el cálculo afectado queda PENDING. Una cantidad elegible igual a cero sólo produce depósito cero cuando está declarada explícitamente.

Otro ensayo declara C60 = 0 en Downside y verifica depósito, saldo restringido, liberación y transferencia cero. Para Base se declara una tarifa de control de USD 100.000 por unidad/año, generando una reserva superior a la caja operativa disponible. La política sintética vigente solicita un aporte antes de liquidar la venta: se conservan USD 9,272275 adicionales por USD 10 iniciales el 30/12/2028 y el cobro de venta posterior de USD 24,484963 en esa misma fecha. Con la liberación completa de Base el beneficio nominal permanece igual, aunque los aportes y cobros brutos aumentan. El perfil conserva el orden declarado de liquidación; la disponibilidad real de esos fondos sigue pendiente de evidencia.

Este control comprueba que un neto total correcto no oculte una llamada de capital. Los escenarios con información faltante permanecen PENDING y su ranking incompleto queda vacío. Los datos de prueba no autorizan fondeo ni decisiones reales.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_reserve_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_replacement_reserve_D149.py --output /tmp/miniuw-d259-d149
```

Se utilizan las dependencias de referencia y OCR del repositorio. Los paquetes generados y registros del VPS quedan locales; GitHub conserva código, pruebas y esta descripción. La validación profesional, otros períodos de reserva y el uso real mantienen sus requisitos de fuente y aprobación. Sin despliegue.

En el VPS pasaron las tres pruebas nuevas: ocho cambios individuales y dos conjuntos válidos, además de los controles de faltantes, aporte adicional y cero explícito. D149 pasó sus trece casos de planilla, con siete PENDING esperados. B16 reprodujo sin diferencias el expediente D258 guardado con sensibilidades v6. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

## 13.10 · D260 · D260 · C61–C62, impuesto inmobiliario, NOI y caja

**Fuente íntegra:** `docs/workbook-tax-sensitivities-D260.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Continuación: [C66–C68, valoración de refi, venta y caja por USD 10 en D261](workbook-pricing-sensitivities-D261.md).

### Si invierto USD 10, ¿cuánto recibo y cuándo?

Ejemplo exclusivamente sintético del perfil D200, normalizado sobre USD 2.400.000 de equity inicial del proyecto: factor fijo `10 / 2.400.000`. No corresponde al 1101 ni a One Hollywood. El retorno personal sigue PENDING sin términos de reparto documentados.

Se prueba C61 de 80 % a 81 % en Base y de 90 % a 91 % en Downside —un punto porcentual— y C62 de USD 1.900 a USD 1.919 y de USD 1.300 a USD 1.313 por unidad comparable/año —1 % relativo—. Son cambios declarados para las pruebas; no son valores recomendados ni criterios de Lorena. Cada cambio se corre por separado y luego ambos juntos contra el mismo original.

| Escenario y corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C61 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C62 | 10,000000 | 4,867042 | 18,057296 | 0,000000 |
| Base C61 + C62 | 10,000000 | 4,867042 | 18,057296 | 0,000000 |
| Downside original | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C61 | 10,000000 | 8,189342 | 6,074943 | 12,114399 |
| Downside sólo C62 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside C61 + C62 | 10,000000 | 8,189342 | 6,074943 | 12,114399 |

Los importes son USD por USD 10 iniciales, calculados sin redondeo intermedio y presentados con seis decimales para hacer visible el efecto fiscal. La caja sin recuperar compara todos los aportes con los cobros hasta el cierre; no certifica una pérdida económica final. El dictamen real conserva PENDING.

### Fechas de la corrida conjunta

| Movimiento | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,000000 | 10,000000 |
| Aporte · 30/06/2027 | — | 0,762275 |
| Aporte · 30/09/2027 | 4,655375 | 0,035729 |
| Aporte · 30/12/2027 | 0,052917 | 7,034046 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,052917 cada fecha | 0,071458 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,071458 cada fecha |
| Cobro neto de refi | 2,846667 · 30/09/2028 | 2,445833 · 30/03/2029 |
| Cobro de operación | 1,429000 · 30/12/2028 | 0,547929 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,781629 · 30/12/2028 | 3,081180 · 30/06/2029 |

Los ceros explícitos de aporte operativo se conservan en los eventos del expediente. La refinanciación solicitada sigue fija en USD 1.400.000: recalcular capacidad no modifica automáticamente el préstamo ni genera un cobro nuevo.

### Qué se conecta y qué base usa

El contrato optativo `miniuw.synthetic-worksheet-sensitivities.v8` admite uno o dos cambios explícitos de C61–C62. Usa la política sintética D150 ya declarada, con sus fuentes, tasas, unidades, alcance y período. No adopta una regla fiscal legal ni una exención, ni modifica el perfil estatutario D203.

Para cada ventana de doce meses del propietario:

```text
F = C62 × unidades comparables documentadas
k = C61 × tasa anual sobre valor fiscal / cap de la estimación fiscal
B = ingresos netos antes del impuesto inmobiliario
NOI = min(B − F, B / (1 + k))
Impuesto = B − NOI = max(F, k × NOI)
Residual = B − Impuesto − NOI = 0
```

Se comprueban operación, banco y valoración de refi de forma independiente. En el ensayo principal, el piso comparable domina la operación de Base; la estimación sobre valor fiscal domina el banco y la valoración de Base y las tres ventanas de Downside. Por eso C61 puede cambiar capacidad sin cambiar el cobro operativo en Base, mientras que C62 puede cambiar su piso sin afectar el impuesto pagadero en Downside. Los datos y sus citas se recalculan aunque no cambie el importe.

| Ventana de la corrida conjunta | Impuesto Base del proyecto | NOI Base del proyecto | Impuesto Downside del proyecto | NOI Downside del proyecto |
|---|---:|---:|---:|---:|
| Operación | 49.894,000000 | 401.945,100000 | 46.164,787800 | 228.287,412200 |
| Banco | 50.735,263751 | 417.574,187249 | 47.339,533217 | 234.096,592833 |
| Valoración de refi | 53.437,721678 | 439.816,639322 | 50.914,015017 | 251.772,601733 |

La venta del perfil D200 usa el impuesto del comprador declarado para su ventana forward: USD 75.000 en Base y USD 70.000 en Downside, separados en escolar/no escolar. Esa evidencia, sus fechas y su fuente permanecen intactas al variar C61–C62. Por eso el precio y el cobro neto de venta no cambian aquí. C61–C62 no reemplazan esa retasación. El modelo D150 anterior, que declara la misma base fiscal para sus cuatro ventanas, conserva su comportamiento original.

El NOI bancario alimenta DSCR y debt yield; el NOI de valoración alimenta el valor y el límite LTV. Se aplica la menor capacidad. La caja de operación deduce el impuesto una vez, antes de deuda y depósito de reserva. `operating_noi_after_reserve` identifica el NOI de esa misma ventana menos el depósito de reposición, sin mezclarlo con las bases bancarias o de valoración.

### Contrato, evidencia y bloqueos

La solicitud conserva `schema` y dos `scenarios`, Base y Downside; cada uno contiene sólo `changes`. Cada cambio exige `target_cell`, `operation`, `unit`, `value` racional explícito y `source_ref` sintético. C61 usa `fraction_of_market_value`; C62, `USD_per_comparable_unit_per_year`. Se admiten reemplazo y cambio relativo, y puntos porcentuales o básicos sólo sobre la fracción C61. No se aceptan celdas repetidas, vacíos, N/A como número ni una tasa sin unidad.

Las fuentes de las celdas cambiadas apuntan al hash de su binding y a `/resulting_value`; las demás mantienen la cita del Excel. El control exige que esa cita llegue efectivamente a la evidencia fiscal. Si otra rama de impuestos ignora esos campos, la variante queda PENDING con `sensitivity_property_tax_basis_not_connected:C61-C62`.

| Requisito o variable y ubicación | Definición vigente en este perfil | Módulo afectado y evidencia de validación | Estado y pendiente |
|---|---|---|---|
| `Inputs!A61:F61` | Razón valor fiscal/valor de mercado, entre cero y uno; tasa anual y cap fiscal separados, documentados | `worksheet_property_tax_D150.declared_property_tax`; prueba de cálculo independiente, fuentes, rango y cero explícito | Conectado en sintético; base y evidencia del deal real pendientes |
| `Inputs!A62:F62` | Impuesto anual del comparable por unidad del alcance declarado; piso por conteo verificado | D150 y M2; prueba aislada, conjunta y de cambio de rama | Conectado en sintético; comparable real y alcance pendientes |
| Capacidad de refi | Menor límite bancario, sin ampliar automáticamente la solicitud | `worksheet_sensitivities_D253`; caso C62 Downside = USD 3.000/unidad/año bloquea caja por capacidad | PENDING si el préstamo excede el límite |
| Caja por USD 10 | Factor sobre equity inicial verificado, aportes y cobros brutos fechados | Conciliación D200 de obra, operación, refi y venta; ecuación exacta de la diferencia de impuesto/caja | Calculable sólo con las fuentes y la capacidad completas |
| Revisión y entrega | B16 reproduce el expediente contra revisión vigente externa | Auditoría del paquete completo y compatibilidad de D259 | El dictamen real conserva PENDING; sin despliegue |

Las pruebas cubren el cambio de piso a estimación y el inverso, ambos valores en cero —impuesto cero sólo en las ventanas donde ésa es la base aplicable—, ausencia de tasa, fuente, conteo o cap fiscal, valores negativos o fuera de rango y capacidad excedida. Un cero de C61 por sí solo no elimina el piso; un cero de C62 por sí solo no elimina la estimación. Si falta C62 en la variante, el cambio C61 válido puede seguir calculado, pero el conjunto y su ranking quedan PENDING. Si falta la fuente fiscal Base, no se inventa su caja ni se retira la información válida de Downside.

### Reproducción

Con el runtime de OCR disponible en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_tax_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_property_tax_D150.py --output /tmp/miniuw-d150
```

Los originales, las políticas financieras abiertas, los criterios de inversión y los expedientes reales se conservan. La entrega externa del motor sigue siendo un PDF de una página; este registro es documentación técnica interna. El respaldo del hito excluye credenciales, datos reales, paquetes generados y registros de ejecución.

Verificación completada en el VPS: cuatro pruebas nuevas, con cuatro cambios individuales y dos conjuntos en el ensayo principal, más cambios de rama, cero, faltantes y capacidad; seis controles unitarios anteriores; catorce casos completos D150, nueve PENDING esperados; B16 reprodujo tanto la variante D260 vigente como D259 sin diferencias. La batería nueva tardó 227,922 segundos. Son verificaciones dirigidas; la batería general completa no se repitió en D260. La aceptación técnica de los sintéticos no habilita decisiones reales.

## 13.11 · D261 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-pricing-sensitivities-D261.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Continuación: [C69–C72, deuda permanente, capacidad y caja por USD 10 en D262](workbook-permanent-sensitivities-D262.md).

D261 conecta los cambios de C66, C67 y C68 en una misma corrida reproducible del perfil sintético D200. C66 modifica la valoración de refinanciación; C67, el precio bruto de venta; C68, el porcentaje de costo de venta sobre ese precio. Cada cambio se ejecuta por separado y luego se recalculan los tres juntos. La valoración y la capacidad disponible no se cuentan como efectivo del inversor.

### Alcance y origen de los valores

Se conserva el equity inicial documentado del proyecto de prueba, USD 2.400.000, y el factor fijo `10 / 2.400.000`. Los aportes adicionales y los cobros se mantienen brutos, fechados y separados. No corresponde al 1101 ni a One Hollywood, ni reemplaza los criterios de Lorena. El retorno personal conserva PENDING sin términos de reparto documentados.

El ensayo principal suma **un punto básico** a cada campo: C66 pasa de 9,50 % a 9,51 % en Base y de 11,50 % a 11,51 % en Downside; C67, de 8,75 % a 8,76 % y de 10,50 % a 10,51 %; C68, de 4,00 % a 4,01 % y de 7,00 % a 7,01 %. Son variaciones declaradas para probar conexiones, no supuestos de mercado adoptados ni umbrales nuevos.

| Corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C66 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C67 | 10,000000 | 4,867042 | 18,037335 | 0,000000 |
| Base sólo C68 | 10,000000 | 4,867042 | 18,057345 | 0,000000 |
| Base conjunto | 10,000000 | 4,867042 | 18,035328 | 0,000000 |
| Downside original | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C66 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C67 | 10,000000 | 8,189342 | 6,068567 | 12,120775 |
| Downside sólo C68 | 10,000000 | 8,189342 | 6,075784 | 12,113557 |
| Downside conjunto | 10,000000 | 8,189342 | 6,067648 | 12,121693 |

Importes en USD por USD 10 iniciales. Se calcula con fracciones exactas y se presenta con seis decimales; el saldo sin recuperar es caja hasta el cierre, no certificación de pérdida económica final. El dictamen real sigue PENDING.

### Fechas de la corrida conjunta

| Movimiento | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,000000 | 10,000000 |
| Aporte · 30/06/2027 | — | 0,762275 |
| Aporte · 30/09/2027 | 4,655375 | 0,035729 |
| Aporte · 30/12/2027 | 0,052917 | 7,034046 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,052917 cada fecha | 0,071458 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,071458 cada fecha |
| Cobro neto de refi | 2,846667 · 30/09/2028 | 2,445833 · 30/03/2029 |
| Cobro de operación | 1,431058 · 30/12/2028 | 0,549690 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,757603 · 30/12/2028 | 3,072125 · 30/06/2029 |

El aporte operativo explícito es cero y permanece en los eventos auditados. En el conjunto, el valor de refi del proyecto es USD 4.630.974,547469 en Base y USD 2.191.475,649797 en Downside; esos valores no son distribuciones. La venta bruta es USD 4.816.688,904110 y USD 2.204.834,338725; los costos totales de venta son USD 203.149,225055 y USD 154.558,887145, respectivamente.

### Conexiones y ecuaciones verificadas

```text
Valor de refi = NOI de valoración / C66
Límite LTV = valor de refi × LTV máximo documentado
Capacidad = mínimo de los límites aplicables LTV, DSCR y debt yield
Precio bruto = NOI forward de salida / C67
Costo de venta = precio bruto × C68 + costo fijo declarado
Cobro neto de venta = precio bruto − costos − principal cancelado + reservas liberadas
Cambio de cobro por USD 10 = cambio de cobro del proyecto × 10 / equity inicial
```

Las bases de NOI, el impuesto del comprador y sus ventanas se conservan. C66 no cambia el NOI bancario ni el de valoración; cambia el divisor y el límite LTV. Tampoco modifica automáticamente la solicitud fija de USD 1.400.000 de refinanciación ni su calendario. Mientras esa solicitud siga dentro de capacidad, el cobro neto de refi conserva su importe. Si el préstamo excede el menor límite, la ruta afectada queda PENDING.

C67 recalcula el precio de venta y el costo porcentual correspondiente. C68 no modifica el precio y conserva el costo fijo de USD 10.000 del proyecto de prueba. Si C68 es cero explícito, el costo porcentual es cero y el fijo sigue aplicándose. El conjunto se recalcula desde los datos; no se suman sus deltas aislados, porque precio y porcentaje interactúan.

### Cobertura, evidencia y pendientes

| Requisito y ubicación | Definición y cálculo afectado | Evidencia de validación | Estado y pendiente |
|---|---|---|---|
| `Inputs!A66:F66` | Cap anual de valoración de refi, positivo y con base documentada | Binding hasta `valuation_and_sale.cell_sources.C66`; valor, LTV y caja; control de cambio del límite activo | Conectado en sintético; evidencia y aprobación real pendientes |
| `Inputs!A67:F67` | Cap anual de salida aplicado al NOI forward de su ventana | Binding, cotejo B08 con rango sintético vigente, precio y costos recalculados | PENDING si falta evidencia o se sale de su alcance |
| `Inputs!A68:F68` | Fracción del precio bruto; inventario completo, costo fijo separado y no superposición | Componentes del productor de costos, fuente de cada costo, cierre y variación exacta del cobro | Cero explícito válido; blanco o inventario sin respaldo, PENDING |
| Capacidad y deuda | Menor límite aplicable, solicitud sin ajuste automático | Conciliación de capacidad con LTV/DSCR/debt yield; control de préstamo excedido | PENDING en la ruta excedida; no se inventa otro préstamo |
| Caja por USD 10 | Equity inicial verificado, aportes brutos, cobros y caja sin recuperar | Conciliaciones D200 de obra, operación, refi y venta; comparación de eventos, no de valuaciones como efectivo | Retorno personal y decisiones reales PENDING |
| Revisión y reproducción | Fuentes y solicitud ligadas a la revisión vigente | B16 reproduce las fuentes guardadas; las citas de los cambios deben llegar al cálculo | Sin despliegue ni aprobación financiera implícita |

El contrato optativo es `miniuw.synthetic-worksheet-sensitivities.v9`, con `schema` y dos `scenarios`, Base y Downside. Cada escenario contiene sólo `changes`, de uno a tres campos, sin duplicados. Cada cambio declara `target_cell`, `operation`, `unit`, `value` racional explícito y `source_ref` sintético. C66 y C67 usan `annual_cap_fraction`; C68, `fraction_of_gross_sale_price`. Las operaciones admitidas son reemplazo, cambio relativo, puntos básicos y puntos porcentuales con su unidad explícita. Se conserva el límite de 48 KiB del JSON del expediente.

Los bindings mantienen el valor y la cita del Excel original junto con el valor propuesto, su fuente y el hash de la solicitud. La variante usa `sha256:<binding>#/resulting_value`. Un campo que no llegue a la base de valoración conserva PENDING con `sensitivity_valuation_basis_not_connected:C66-C68`.

Las pruebas incluyen caps cero/negativos, costo fuera de rango, vacíos `null`, cadena vacía y espacios, ausencia de fuente, unidad incorrecta, inventario incompleto, cita antigua, cap de salida fuera de evidencia y solicitud excedida por menor capacidad. Ningún vacío se convierte en cero. Los caps cero son datos numéricos inválidos para esta fórmula y quedan PENDING antes de dividir. El cero de C68 se respeta.

### Reproducción y límites

Con el runtime de OCR configurado en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_pricing_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_exit_pricing_D151.py --output /tmp/miniuw-d151
```

Las políticas financieras, los criterios, los originales y los expedientes reales se conservan. La entrega externa del motor sigue siendo un PDF de una página; este archivo es documentación técnica interna. El respaldo excluye credenciales, archivos reales de proyectos/clientes, paquetes generados y registros de ejecución.

Validación completada en el VPS: cuatro pruebas nuevas en 303,889 segundos, con seis cambios individuales y dos conjuntos en el ensayo principal, además de capacidad, evidencia, faltantes y ceros; siete controles unitarios anteriores; quince casos completos D151, diez PENDING esperados. B16 reprodujo la variante D261 como VIGENTE y reprodujo D260 sin diferencias. En el control C66 Base = 5 %, el límite activo pasa de LTV a debt yield y la caja sigue igual; C66 Downside = 12 % deja la refi PENDING por capacidad. Son ensayos sintéticos para comprobar la conexión, no términos recomendados ni criterios adoptados. Esta validación es dirigida y no repite la batería general completa.

## 13.12 · D262 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-permanent-sensitivities-D262.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Actualización posterior: [D263 calcula la variante de 5,01 % mediante el contrato optativo v11 de transporte exacto](workbook-exact-cash-D263.md). Este registro conserva los resultados y la limitación originales de v10.

D262 conecta los cambios C69–C72 por separado y en conjunto con la deuda permanente, la capacidad de refinanciación y los movimientos brutos por USD 10 en Base y Downside. Usa exclusivamente el perfil sintético documentado D200. Se conserva el equity inicial verificado de USD 2.400.000 y el factor `10 / 2.400.000`. Los aportes posteriores se muestran separados. El dictamen real y el retorno personal sin términos de reparto permanecen PENDING.

### Valores del ensayo y alcance

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

### Fórmulas y conexiones

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

### Respaldo documental de cada cambio

La variante lleva un PDF bancario sintético de una página, con escenario, caso, revisión nueva y huellas que lo enlazan al respaldo padre verificado. Sólo pueden cambiar tasa, amortización, LTV y DSCR. Principal solicitado, frecuencia, vencimiento y convenciones se conservan. El lector coteja los renglones y las unidades del PDF con las celdas modificadas mediante el control B08 existente; no se omite ese control.

El anexo de debt yield también debe estar declarado expresamente: cita la revisión PDF nueva y la huella del anexo padre, conserva aplicabilidad, base y mínimo, y tiene una fuente sintética nueva. El código no rebaja el mínimo ni adopta otra política para acomodar la variante. Una huella antigua, un cambio de mínimo o la ausencia del respaldo produce PENDING. Los originales permanecen intactos.

Las celdas modificadas citan `sha256:<binding>#/resulting_value`; las demás conservan la cita del Excel. El resultado retiene el PDF leído, los localizadores, la relación con el padre y la evidencia del anexo para la reproducción B16.

### Cobertura y bloqueos

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

### Reproducción

Con el runtime de OCR configurado en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_permanent_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_permanent_loan_D152.py --output /tmp/miniuw-d152
```

Este registro es documentación técnica interna. La entrega externa del motor conserva un PDF de una página. No se modifica el 1101, One Hollywood, los criterios de inversión ni las políticas pendientes. Sin despliegue ni decisiones reales. El respaldo excluye credenciales, expedientes reales, paquetes generados y registros de ejecución.

Validación en el VPS: cuatro pruebas nuevas en 240,051 segundos —ocho cambios individuales y dos conjuntos del ensayo principal, más faltantes, contradicciones, capacidad, ceros y el límite de precisión—; nueve controles unitarios anteriores; diecisiete casos completos D152 con diez PENDING esperados. B16 reprodujo el paquete D262 como VIGENTE y el D261 anterior sin diferencias. Los diez archivos generados por consola coincidieron byte a byte con D198. La prueba integrada está en `tests/test_worksheet_permanent_sensitivities.py`, método `PermanentSensitivityIntegrationTests.test_individual_joint_bank_binding_capacity_missing_and_zero`; los otros tres métodos comprueban el contrato, los límites de tamaño y las revisiones PDF/anexo. Son verificaciones dirigidas: la batería general completa no se repitió. El pendiente de precisión queda abierto aun cuando estas pruebas pasan, porque comprobar un bloqueo seguro no implementa la ampliación que falta.

## 13.13 · D263 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-exact-cash-D263.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D263 resuelve, en el contrato optativo de sensibilidades v11 de C69–C72, el bloqueo de precisión detectado en D262. La tasa Base de **5,01 %** se conserva y llega al cierre y a la caja por USD 10 sin redondear. Downside se prueba con **6,51 %**. Son datos sintéticos con PDF bancario y anexo verificados; no corresponden al 1101 ni a One Hollywood. El dictamen real y el retorno personal sin términos de reparto siguen PENDING.

### Resultado del ensayo

El equity inicial del proyecto es USD 2.400.000, verificado en el perfil D200. Se mantiene el factor `10 / 2.400.000`, sin usar los aportes posteriores como denominador. El ensayo conserva los otros cambios de D262: amortización a 21/12 años, LTV máximo a 64,99 % y DSCR mínimo a 1,251/1,301, respectivamente. La solicitud de refi sigue fija en USD 1.400.000. No son criterios nuevos ni recomendaciones de financiación.

| Corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original, C69 = 5,00 % | 10,00000000 | 4,86704167 | 18,05935435 | 0,00000000 |
| Base conjunto v11, C69 = 5,01 % | 10,00000000 | 4,86704167 | 18,05920852 | 0,00000000 |
| Downside original, C69 = 6,50 % | 10,00000000 | 8,18934167 | 6,07670398 | 12,11263769 |
| Downside conjunto v11, C69 = 6,51 % | 10,00000000 | 8,18934167 | 6,07655815 | 12,11278352 |

USD por USD 10 iniciales. Los números se presentan con ocho decimales; los cálculos conservan numerador y denominador exactos. La caja sin recuperar compara todos los aportes con los cobros hasta el cierre y no certifica una pérdida económica final.

| Movimiento del conjunto | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00000000 | 10,00000000 |
| Aporte · 30/06/2027 | — | 0,76227500 |
| Aporte · 30/09/2027 | 4,65537500 | 0,03572917 |
| Aporte · 30/12/2027 | 0,05291667 | 7,03404583 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,05291667 cada fecha | 0,07145833 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,07145833 cada fecha |
| Cobro neto de refi | 2,84666667 · 30/09/2028 | 2,44583333 · 30/03/2029 |
| Cobro de operación | 1,43416697 · 30/12/2028 | 0,56023938 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,77837487 · 30/12/2028 | 3,07048544 · 30/06/2029 |

El aporte operativo explícito cero se conserva en los eventos. El aumento de tasa reduce el cobro conjunto en USD 0,0001458333 por USD 10: `1.400.000 × 0,0001 / 4 × 10 / 2.400.000`. En este calendario hay una cuota antes de cancelar el préstamo al vender. El cambio de amortización redistribuye operación y venta, conservando su suma si la tasa no cambia. La prueba compara también el cronograma completo y no generaliza esa identidad a otra duración.

### Corrección técnica y versión

El cronograma de D262 ya calculaba correctamente 5,01 %, pero el principal de la cuota generaba 370/366 dígitos de numerador/denominador. Los lectores de los puentes de caja sólo admitían 256 por entero. D263 amplía el transporte exacto a **1.300 dígitos**, conservando el presupuesto aritmético existente de **4.096 bits**, los límites de archivos y el rechazo de datos inválidos. No aplica redondeos, conversión a punto flotante ni sustitución de valores.

El contrato `miniuw.synthetic-worksheet-sensitivities.v11` conserva el inventario de cambios y respaldos de v10. Selecciona un motor de caja con dependencias aisladas para las variantes C69–C72. Las funciones financieras se reutilizan con su mismo código, en espacios de ejecución privados que enlazan los lectores y productores compatibles. No se modifican las variables globales ni los archivos de los módulos anteriores.

Cada variante registra `exact_cash_transport`: perfil, revisión, hash del adaptador, algoritmos y dependencias con sus rutas y SHA-256, límite de dígitos, presupuesto aritmético y ausencia de redondeo. Las huellas de los productores adaptados combinan el hash del algoritmo con la revisión del transporte. Se verifican once fuentes; un cambio de algoritmo no revisado deja PENDING, sin volver automáticamente al motor anterior.

La cadena adaptada comprende NOI a caja, refi, capacidad, cancelación de deuda a la venta, cierre, eventos brutos y retorno. Los tipos, unidades, períodos, ecuaciones, fuentes y controles financieros se conservan. La modificación amplía el dominio numérico, sin adoptar una política financiera o de redondeo.

### Alcance de la activación

V11 es optativo y se aplica a estas sensibilidades documentadas. La corrida de entrada original y los otros contratos conservan su motor y sus reglas. D262 sigue reproduciendo el PENDING histórico de su caso de 5,01 % con v10; D263 calcula esa variante al solicitar v11. No se reescriben expedientes ni se activa un cambio general por defecto. La integración de este transporte en otros productores o en una entrada original que ya supere el dominio anterior requiere su propia revisión y pruebas.

### Cobertura y evidencia

| Requisito o variable | Ubicación / definición | Cálculo y validación | Estado |
|---|---|---|---|
| C69 = 5,01 % Base | `Inputs!A69:F69`, cambio explícito con PDF/anexo de D262 | Cuota, intereses, saldo y flujos exactos por USD 10 | Calculado en v11; v10 conserva su estado anterior |
| C70–C72 aislados y conjunto | `Inputs!A70:F72`, mismos términos y vencimientos documentados | Ocho cambios individuales y dos conjuntos; pago, LTV, DSCR, debt yield y fuentes/usos | Calculados en el ensayo sintético compatible |
| Mayor precisión sin redondeo | `worksheet_exact_cash_D263.exact_fraction` | Fracciones mayores a 256 dígitos; rechazo sobre 1.300; cálculo adicional a 30 años con denominadores mayores a 500 dígitos | Verificado dentro del presupuesto aritmético |
| Aislamiento y versión | `worksheet_exact_cash_D263.cash_engine` | Dos motores creados concurrentemente, identidad del código, enlaces de dependencias y ausencia de mutación global; fuente no reconocida rechazada | Verificado, revisión explícita obligatoria |
| Vacío distinto de cero | Lector racional y contrato de cambio | `null`, cadena vacía, espacios, fuente ausente; tasa cero con interés cero | Faltantes PENDING; cero explícito conservado |
| Capacidad | Solicitud fija y menor límite aplicable | Refi sobre DSCR en Base o LTV en Downside | PENDING, sin cobro ficticio ni ajuste automático |
| Reproducción histórica y actual | B16 y revisión vigente externa | Comparación con D262 y reproducción del paquete nuevo | Cada contrato conserva su revisión |

Pruebas: `tests/test_worksheet_exact_cash.py`. `ExactCashTransportTests` verifica lector, aislamiento, versiones y límites. `ExactCashIntegrationTests.test_precision_case_full_cash_replay_and_legacy_compatibility` coteja v10/v11 en importes y fechas, calcula el caso antes bloqueado y concilia cronogramas y caja con fórmulas independientes. Las citas y huellas pueden cambiar entre versiones; se verifica separadamente que los importes compatibles permanezcan iguales.

### Reproducción y pendientes

Con el runtime de OCR del VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_exact_cash
```

Las reglas de Lorena, la evidencia, los términos de reparto y las aprobaciones reales conservan sus puertas. La precisión sigue acotada: una operación que exceda los presupuestos o carezca de fuente mantiene PENDING; no se garantiza cobertura ilimitada de tasas y plazos. La entrega externa del motor conserva un PDF de una página. Este documento es un registro técnico interno. Datos sintéticos, sin despliegue ni decisiones reales; el respaldo excluye credenciales, expedientes reales, paquetes generados y registros de ejecución.

Validación en el VPS: cinco pruebas nuevas distintas —la integrada y cuatro controles unitarios—, nueve controles anteriores, auditoría B16 del caso histórico D262 y reproducción B16 del paquete nuevo. El ensayo integrado y sus tres primeros controles pasaron en 262,452 segundos; el bloque unitario final pasó en 0,043 segundos. Se probaron ocho cambios individuales y dos conjuntos del caso antes bloqueado, equivalencia financiera v10/v11, 30 años, tasa cero, faltantes y capacidad excedida. Los diez archivos de consola y D198 coincidieron byte a byte. La batería general completa no se repitió en este hito.

## 13.14 · D264 · Si invierto USD 10, ¿cuánto cobro y cuándo?

**Fuente íntegra:** `docs/workbook-integrated-transport-D264.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


D264 conecta el transporte exacto D263 con la entrada original de la planilla y el dictamen integrado. La corrección evita que un valor válido quede bloqueado sólo por el límite anterior de 256 dígitos de una fracción. No redondea cálculos ni modifica umbrales, reglas de precedencia, fechas o términos bancarios.

### Alcance y activación

El perfil técnico sintético admite una configuración explícita en `rent_inputs.cash_transport`:

```json
{"profile":"miniuw.synthetic-integrated-exact-transport.v1","source_ref":"SYNTHETIC-D264-exact-intake"}
```

Su ausencia conserva el transporte anterior. Una configuración inválida o un algoritmo cuya huella no coincide deja ambas cajas PENDING; no vuelve silenciosamente al motor anterior. La configuración no constituye una autorización de uso real ni de despliegue.

`worksheet_integrated_transport_D264.integrated_engines` reutiliza el transporte aislado D263 y añade un espacio de funciones privado para el comparador escalar. Registra perfil, referencia, huellas de adaptadores/algoritmos y revisión, sin modificar las variables globales del motor original. Los lectores de resultados calculados de D167, D173, D181 y D193 admiten 1.300 dígitos. Las entradas y las reglas conservan sus validadores, unidades y fuentes; el presupuesto aritmético sigue siendo acotado. Ausente no significa cero; un cero explícito se conserva sujeto al dominio de cada variable.

### Prueba dirigida

Pasaron **dos pruebas en 121,454 segundos** en el VPS:

- Compatibilidad: con tasas anteriores, el nuevo transporte conserva exactamente los movimientos fechados y totales por USD 10 de Base y Downside.
- Entrada revisada: C69 numérico de 5,01 % / 6,51 % en los XLSX, documentos bancarios sintéticos escaneados coherentes y nueva confirmación explícita del anexo de debt yield. El interés, el saldo, la cancelación y la caja se recalculan sin redondear; las citas y huellas corresponden a la nueva evidencia.
- El principal de cuota Base supera 256 dígitos y llega a caja y al CoC. El paquete completo se reproduce por B16 como VIGENTE. La configuración inválida bloquea ambos escenarios; las huellas no reconocidas también se rechazan.

Los documentos de prueba incluyen JPEG progresivo, giros y orden de páginas alterado. Se preservan los originales del repositorio; los PDF revisados son fuentes sintéticas nuevas. El generador de pruebas usa Pillow y DejaVu Sans Mono del entorno del VPS, sin conexión a fuentes reales. No rebaja los controles de OCR para hacer pasar el ensayo.

Reproducción, con las dependencias de OCR del VPS en el entorno:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_integrated_transport
```

Esta prueba dirigida precede a la batería general de cierre. El dictamen real, la evidencia y los criterios sin confirmar mantienen PENDING. Los perfiles de calendario conservan sus horizontes documentados; D264 no implementa por sí mismo un horizonte general de cinco años ni cierra las políticas parciales de D252. No se atribuye retorno personal sin términos de reparto. Respaldo: código, pruebas y documentación; excluye credenciales, expedientes reales y resultados generados.

## 13.15 · D266 · D266 · Horizonte integrado desde estabilización

**Fuente íntegra:** `docs/workbook-holding-horizon-D266.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


El perfil optativo `miniuw.synthetic-integrated-holding-horizon.v1` conecta las planillas Base y Downside con compra, obra, estabilización, cinco años completos de operación y venta. Produce cuatro historias de caja por USD 10 iniciales: con y sin refinanciación en cada escenario. Es un ensayo sintético; el dictamen real y el retorno personal sin reparto documentado siguen PENDING. No habilita despliegue.

### Contrato de entrada

Se declara `rent_inputs.holding_horizon`, con perfil, referencia, inventario de reglas y ambos escenarios. Cada escenario necesita `holding_months`, fuente, aporte inicial positivo con fuente, inventario de supuestos de caja, política de fondeo del cierre y alcance de la ruta sin refi. Los meses se reciben como entero explícito de 12 a 60 en años completos: **no hay un default financiero de cinco años**. La venta H07 debe coincidir con estabilización más ese plazo.

El aporte inicial proviene del nuevo contrato. No se sustituye por el importe del fixture: los ensayos incluyen otros aportes respaldados. Un importe que no cubra la compra y comisión de apertura bloquea; un exceso documentado se conserva como caja libre y se concilia en el cierre, sin inventar un aporte negativo. Los perfiles históricos conservan su contrato y resultados.

El calendario soportado tiene compra y pagos en el primer día del trimestre, obra C46 en múltiplos de tres meses, TCO al terminar la obra y estabilización después de C47. La refi ocurre al estabilizar. Se exige operación comercial plenamente reconocida o ausencia documentada de usos comerciales. Una brecha de TCO sin fondeo o un primer año comercial parcial no se aproxima en silencio.

La tasa, frecuencia, amortización, principal, LTV, DSCR, debt yield, vencimiento y cotización de cada deuda tienen su respaldo del expediente. La ruta sin refi retiene la misma deuda de obra sólo cuando su vencimiento documentado cubre la venta; una extensión no se presume. El plazo largo usado en el fixture es un supuesto bancario sintético, no una propuesta de mercado.

### Conexiones y fórmulas

| Dato / requisito | Definición aplicada | Productor y ubicación | Evidencia de validación |
|---|---|---|---|
| D252 #15–16, TEC-01 de D265 | Venta = estabilización + meses documentados. Cinco años son cinco anualidades completas y 20 cierres trimestrales. | `worksheet_holding_horizon_D266.horizon_calendar`; despacho en `worksheet_project_calendar_D145.project_calendar`. | Calendario independiente desde TCO/C47; rechazo de fecha de venta contradictoria, duración ausente y brecha sin presupuesto. |
| Aporte inicial y USD 10 | Factor = 10 / primer aporte verificado. Cada aporte posterior conserva importe y fecha; no se netea con un cobro del mismo día. | `configuration`, `investor_story`; D143, D144 y D146 reciben el importe sólo en el perfil nuevo. | Otras bases iniciales, caja excedente, ceros explícitos y sumas brutas de eventos. |
| Obra y lease-up | Usos, desembolsos, comisión y cada interés hasta estabilización permanecen conciliados por fecha. | D143–D146; `construction_rows`, `verify_rows`. | Ecuación de fuentes/usos por fila y continuidad entre saldos. |
| Rentas, gastos y NOI | C75/C76 se componen en aniversarios de estabilización; C13 permanece plano; fees mantienen su propia base. El impuesto usa el mayor de proxy y comparables del perfil D150. | `worksheet_growth_D154.project_window`; `worksheet_rental_inputs_D140` construye cada año. | Cotejo desde literales XLSX de cinco NOI anuales y el NOI forward del año posterior a la salida. |
| Caja operativa | Bajo regla sintética explícita: NOI anual / 4 − servicio trimestral − reserva anual / 4. Déficits son aportes brutos; superávits son cobros brutos. | `operation_rows`, `annual_aggregate`, `yearly_cash`; conciliación T19/T25. | Fechas y netos de las 20 cuotas, sumas de ingresos/gastos y conciliación de caja libre/restringida. |
| Reservas | C60 se deposita trimestralmente, se acumula sin uso intermedio y se liquida con su fracción documentada. La reserva permanente C74 sigue separada. | D149, `sale_close`, `append_sale`; D153 para reserva permanente. | Total de cinco depósitos anuales, liberación/transferencia sin duplicar el cobro. |
| Deuda permanente y capacidad | Cuota regular con tasa C69/4 y C70×4 períodos. Capacidad = menor límite aplicable. Cancelación del saldo después de la última cuota, una sola vez. | D152 y motores de servicio/capacidad; `calculate`. | 20 intereses, amortizaciones y saldos recalculados independientemente. Préstamo sobre capacidad y vencimiento temprano → PENDING en refi. |
| Venta y deuda sin refi | Precio = NOI del año posterior / C67. Costos = precio×C68 + fijo documentado. Deuda de obra se mantiene sólo hasta su vencimiento acreditado. | `without_refinance`, `sale_close`; D151/T68 y conciliación de cierre. | Cotejo de precio, costos, cancelación única y efectivo neto. Vencimiento corto bloquea sólo esa alternativa. |
| TIR, múltiplo y caja no recuperada | TIR anual sobre todos los flujos fechados; múltiplo = cobros/aportes; no recuperado = máximo(0, aportes−cobros). | `horizon_irr` usa el solver exacto D179 y aislamiento existente; `investor_story`. | Ambos extremos del intervalo de TIR se sustituyen en el polinomio de caja; historias brutas de ambas rutas cotejadas. |
| CoC y criterios | CoC del primer año completo post-refi, con NOI después de reservas y equity aún invertido. TIR/múltiplo usan todo el horizonte. YoC/spread, ocupación y RLV conservan bases documentadas D193. | D181 `collect_metrics`; D193 y `verify_annual_coc`. | Revisión de criterios distinta y ligada al nuevo período; criterio ausente → dictamen PENDING sin borrar caja respaldada. Banda → PENDING. |
| Fuente vigente y entrega | Se registra cada fuente; se construye y reproduce el expediente antes de entregar su PDF. | D198, B16 y `render_horizon`. | Cotización discordante, fuente/revisión anterior y entrega bloqueada; sólo sale el PDF íntegro vigente de una página. |

La referencia independiente está en `check_worksheet_holding_horizon_D266.independently_verify`; sus entradas son las celdas literales y los términos declarados, no los NOI o saldos publicados por el motor. Las pruebas están en `tests/test_worksheet_holding_horizon.py`. La constancia final y sus hashes se guardan en `review/MiniUW_Validacion_D266.json`.

### Alcance preciso y pendientes

TEC-01 queda implementado y cotejado para el perfil trimestral explícito de D266, con cinco años y una duración alternativa documentada de tres años. Eso no certifica todos los calendarios o las 33 políticas. Un calendario irregular, frecuencia mensual, comercial parcialmente estabilizado o duración fuera del contrato requiere una implementación específica; el perfil rechaza esos casos.

La caja uniforme por trimestre, impuesto proxy liquidado en cuatro cuotas, capital de trabajo sin cambios, inventario de ceros y ausencia de capex adicional son supuestos **declarados del ensayo**, no valores por defecto para un deal. El calendario fiscal M2/Florida por padrones no se mezcla con este perfil: su conexión plurianual continúa pendiente. El tope fiscal legal, beneficios condicionales y su orden de aplicación no se infieren de este proxy. La entrada D266 acepta únicamente el esquema técnico v31; extender el horizonte al esquema fiscal v32 y al auditor de datos críticos v33 requiere su conexión y validación específica. Esos perfiles se rechazan con PENDING; no se les atribuye la cobertura de este ensayo.

Permanecen abiertos TEC-02 (orquestador universal y autorización de shocks), TEC-03 (renta regulada), las definiciones de área/materialidad, reglas condicionales y aprobaciones detalladas en D265, además de validación empírica y documentación real. No se reemplazan por nuevas hipótesis sintéticas. La implementación de este horizonte no cambia los umbrales vigentes ni las reglas pendientes, y no activa producción.

### Reproducción

Con las dependencias de `requirements-reference.txt`, Tesseract y el entorno OCR configurado:

```sh
PYTHONPATH=src:tests:tools python -m unittest -v test_worksheet_holding_horizon
PYTHONPATH=src:tests:tools python tools/check_worksheet_holding_horizon_D266.py --output /tmp/miniuw-d266
```

El segundo comando genera fuentes de prueba identificadas como sintéticas, planillas, registro, expediente, cotejo y PDF vigente. No lee documentos de clientes ni exporta una decisión real. La documentación y el manifiesto se actualizan sólo después de comprobar las validaciones del corte publicado.

## 13.16 · D267 · D267 · Horizonte integrado, M2 fiscal y auditor de datos críticos

**Fuente íntegra:** `docs/workbook-horizon-fiscal-audit-D267.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


El contrato optativo `miniuw.synthetic-integrated-fiscal-holding-horizon.v2` conecta los padrones M2 con compra, obra, estabilización, operación, refinanciación y venta. Conserva cuatro historias por USD 10 de equity inicial: Base y Downside, con y sin refi. La decisión real y el retorno personal sin términos de reparto siguen PENDING; no se habilita despliegue ni se adoptan criterios históricos.

### Entrada y alcance

- El esquema fiscal v32 permite comprobar el componente M2. El esquema v33 incorpora también el auditor de datos críticos antes de exponer la caja y entregar el PDF. El fixture principal usa v33.
- `holding_horizon` conserva una duración explícita de 12–60 meses en años completos y el calendario trimestral del primer día. Se prueban cinco años y una duración alternativa de tres años. No hay un default financiero de cinco años.
- `holding_tax_cash` exige perfil, reglas, fuente y declaraciones independientes por escenario. La exclusión de impuestos previos del presupuesto debe estar documentada para agregarlos como usos: no se supone que estén incluidos ni que sean cero.
- `florida_property_tax` necesita padrón inicial, valoración escolar y no escolar, millage separado, tratamiento y fecha de cada evento y fuentes para todos los años utilizados. Los registros del ensayo son pronósticos sintéticos declarados, sin autenticación oficial o legal.
- El perfil proxy y el fiscal no se mezclan. Una fuente fiscal requerida ausente bloquea el cálculo afectado; no se vuelve al proxy ni al perfil anterior.

### Conexiones, fórmulas y evidencia

| Requisito | Definición y conexión | Código | Validación |
|---|---|---|---|
| TEC-01 de D266: horizonte fiscal | M2 calcula cada año operativo, cada trimestre de caja, la tenencia previa y la ventana forward de salida. | `worksheet_horizon_fiscal_D267.window_contract/fiscal_cash`; `worksheet_florida_tax_D203.window_taxes`. | Contraste independiente de 32 ventanas Base y 34 Downside. |
| Impuesto previo a estabilización | Cada trimestre de tenencia genera un uso adicional excluido del presupuesto, con fecha y fuente. Se fondea desde caja o aporte; no aumenta automáticamente la deuda elegible. | `worksheet_construction_financing_D146.staged_construction_financing(additional_uses=...)`. | Cotejo de usos, draws, intereses, comisión, aportes y saldos por fecha. La suma fiscal entra una vez en TDC. |
| Impuesto durante operación | Impuesto escolar = valor imponible escolar × mills / 1000 × meses / 12. El no escolar usa su propia base. Las cuatro cuotas deben sumar exactamente el impuesto anual. | D203 y `worksheet_horizon_fiscal_D267.operation_rows`. | Downside atraviesa enero dentro de su año operativo; se comprueban cuotas distintas, sin sustituirlas por el promedio anual. |
| Base de valoración y salida | Se usa el impuesto de la ventana forward bajo el perfil M2 existente. Si la ventana no alcanza el siguiente reset, no exige un padrón de comprador que no se usa. | D203 `window_taxes`; compilación de NOI D140; valoración/cierre D266 reutilizados. | Salida Base el 1 de enero y Downside en julio; reset del comprador separado de las bases escolares y no escolares. |
| Reglas M2 existentes | Se conserva el perfil sintético D203 de cap no escolar y resets explícitos. No se aplica el cap escolar ni se hereda el cap del vendedor en un reset del comprador. | D203 `assessed_value`, sin cambio de fórmula. | Bordes de cap, cambio de titularidad, mejora declarada y cruce de año. Esto no confirma vigencia o aplicabilidad legal real. |
| Caja y métricas por USD 10 | Factor = 10 / aporte inicial verificado. Aportes posteriores y cobros conservan sus fechas. Reservas y cancelación de deuda ocurren una sola vez. | Adaptador D267 y fuente D266 fijada por SHA-256. | Referencia financiera desde celdas literales: presupuesto, fondeo, seis NOI, 20 cuotas, venta, caja bruta y ambos extremos de TIR para las cuatro rutas. |
| CoC | Primer año completo post-refi: NOI después de reservas e impuesto, menos servicio, dividido por equity remanente. | D266 reutilizado con cuotas M2 fechadas; referencia D267. | Se cotejan numerador, denominador y ventana. El impuesto no se vuelve a restar. |
| Auditor fiscal | Inventario independiente versionado de valores esperados, huellas de las declaraciones fiscales y cobertura de todas las ventanas. Un verde sin respaldo bloquea la caja del escenario. | `audit_worksheet_critical_evidence_D219.audit`; D267 `critical_fiscal_fields/fiscal_source_issues`. | Se comprueban 116 datos críticos; se inyectan detalle fiscal errado, omisión de trimestre y eliminación del inventario de ventanas. |
| Auditor documental | Las citas del plano compartido y del DSCR bancario siguen siendo necesarias. Corregir una sola no habilita la otra rama. | D219/D220 y flujo D140. | Fallos conjuntos, correcciones parciales y restauración completa, con flujos por USD 10 conservados. |
| PDF y revisión | Un PDF de una página muestra los importes y las fechas reales de los trimestres calculados. Sólo se entrega la revisión reproducida vigente. | D267 `render_horizon`; B16 y entrega existente. | Antigüedad de revisión, entrega bloqueada ante falso verde y reproducción del PDF vigente. |
| Vacío y cero | Toda magnitud fiscal o fuente requerida ausente bloquea. Un cero numérico explícito permanece cero. | Guardas M2 y contrato de usos adicionales. | Millage ausente, vacío y sin fuente; millage/tasa/reserva/crecimiento cero y amortización con balloon al cierre. |

La referencia fiscal/financiera es `check_worksheet_horizon_fiscal_D267.independent_taxes/independently_verify`. Lee las declaraciones y celdas fuente; no toma los NOI, saldos o totales del motor como sus entradas. El inventario crítico `templates/synthetic-critical-evidence-D267.json` se construye desde el corpus sintético declarado y esa referencia, antes de observar el resultado del motor. No se genera desde resultados para hacerlos coincidir.

### Preservación de versiones

D266 conserva sus bytes y su perfil v1. D267 reutiliza sus funciones en un espacio aislado, exige la huella `bba535fd748b8f3fb6c982d4e8f9109e1db8dd36d64abce0ffb047a8f3b2c924` y sustituye únicamente el contrato y la liquidación fiscal trimestral. No modifica variables globales del módulo original, sus fórmulas financieras ni el presupuesto aritmético; no redondea los cálculos. Una fuente de algoritmo distinta queda PENDING, sin volver a un motor anterior.

La referencia v33 se selecciona entre rutas conocidas del repositorio. Los perfiles anteriores siguen usando el inventario D219; el corpus D267 tiene su propio inventario. No se aceptan rutas arbitrarias del deal ni se actualiza el inventario automáticamente para aprobar fuentes modificadas. Cambiar el corpus exige otra revisión de evidencia independiente.

El verificador D203 conservaba un cotejo contra el primer PDF archivado D200 (`48427ed9…`). La corrida previa de D267 reprodujo exactamente el PDF de aceptación ya verificado en D265/D266 (`ed0f2ad2…`). Se versiona esa referencia en `templates/expected-D200-pdf-D267.pdf` y se corrige el cotejo del verificador. El PDF original permanece intacto; los cálculos y umbrales no se modifican para resolver esa diferencia de referencia.

### Pendientes que este bloque no cierra

El calendario mensual/irregular, las cotizaciones y reglas de devengo fuera del contrato trimestral, el orquestador de las 15 sensibilidades, la renta regulada, beneficios fiscales condicionales/materialidad y las decisiones de autoridad/criterios conservan sus puertas abiertas. El cierre técnico de este perfil no certifica las 33 políticas, documentos reales, aprobación de inversión, falsos verdes en cualquier PDF ni producción.

### Reproducción

Con las dependencias de referencia y OCR disponibles:

```sh
PYTHONPATH=src:tests:tools python -m unittest -v test_worksheet_horizon_fiscal
PYTHONPATH=src:tests:tools python tools/check_worksheet_horizon_fiscal_D267.py --output /tmp/miniuw-d267
```

La constancia del corte probado y los límites se registran en `docs/review/MiniUW_Validacion_D267.json`. Los logs completos, expedientes generados, runtimes y datos de clientes no se incorporan al hito de GitHub.

## 13.17 · D268 · D268 · Sensibilidades desde fuentes hasta caja por USD 10

**Fuente íntegra:** `docs/workbook-scenario-program-D268.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Se implementa un ejecutor único de variantes con planillas y respaldos propios, sin cambiar los criterios ni el aporte inicial. Cada expediente conserva aportes y cobros brutos fechados, Base/Downside y venta con/sin refi. Los parámetros de este ensayo son sintéticos: no son valores por defecto, propuestas aprobadas ni datos de un proyecto real.

### Cobertura y fórmulas

Fuente de requisitos: matriz D251, p. 1 política 3, p. 2 políticas 18–26 y p. 3 políticas 27–33; cotejo preservado en `worksheet-policy-implementation-audit-D252.md`, tabla «Matriz por política». Código: `worksheet_scenario_program_D268.DRIVERS/driver_terms/transformed/check_variant/run_program`.

| Política | Entrada y transformación explícita | Recálculo y respaldo exigido |
|---|---|---|
| 18 | C8–C11 × (1 + cambio relativo) | Renta residencial, pérdidas, NOI, capacidad y cuatro retornos; rango de mercado vigente del ensayo. |
| 19 | C16–C18 × (1 + cambio relativo) | Ingreso comercial NNN y NOI. No se cambia superficie ni unidades. |
| 20 | C14 + puntos porcentuales / 100 | Pérdida residencial combinada, conforme a la definición de C14. No se infiere vacancia física sin desglose. |
| 21 | C19 + puntos porcentuales / 100 | Vacancia comercial e ingreso reconocido. |
| 22 | C35, C37 y C38 × (1 + cambio relativo) | Obra vertical, parking y sitio; contingencia, soft costs, fondeo e intereses. La nueva cotización GC debe coincidir con C35 y su base documentada. |
| 23 | C46 + meses enteros | TCO, calendario de desembolsos, intereses, impuestos previos, estabilización, venta y ventanas forward. Perfil trimestral explícito. |
| 24 | C47 + meses enteros | Déficit de lease-up, calendario y primer año estabilizado; absorción y fechas respaldadas. |
| 25 | C52 + pb / 10.000 | Interés de obra sobre desembolsos y saldo; nuevos términos bancarios coincidentes. |
| 26 | C69 + pb / 10.000 | Cuotas, saldo, DSCR, capacidad y cobros. El principal solicitado permanece documentado. |
| 27 | C66 + pb / 10.000 | Valoración de refi y límite LTV con su propia base de NOI. |
| 28 | C59 × (1 + cambio relativo) | Prima, gastos, NOI y caja; se exige cotización y población asegurada concordantes. |
| 29 | Impuesto operativo/forward M2 × (1 + cambio relativo) | Ajuste posterior al padrón, una sola vez; no cambia millage, retasación ni impuesto previo a estabilización. Sólo alcance sin beneficios fiscales condicionales. |
| 30 | C71 + puntos porcentuales / 100 | Menor límite bancario aplicable. No se aumenta ni reduce automáticamente el préstamo para producir PASS. |
| 31 | C67 + pb / 10.000 | Venta a partir del NOI forward y costos de cierre; evidencia de cap compatible. |
| 32 | C75 + puntos porcentuales / 100 | Renta por aniversario, NOI, venta y flujos. No se incorpora una tasa de descuento. |

Cada driver declara aplicabilidad, unidad, cambios Base/Downside y fuente. Una excepción necesita fuente y motivo; un valor ausente no se interpreta como cambio cero. El cero explícito se conserva. La variante conjunta se deriva del mismo origen que las individuales, sin acumular involuntariamente los ensayos anteriores. Si el origen ya declara un stress fiscal, el cambio relativo adicional se compone multiplicativamente.

`check_variant` comprueba las 55 celdas, el inventario de ajustes de configuración y las huellas de cada paquete. Rechaza cambios ajenos en criterios, geometría, compromiso bancario, esquema de aportes, bases de costo o supuestos de fondeo. Cada fuente complementaria debe pasar después los lectores y las conciliaciones existentes. Cambiar un hash declarado no autentica un documento.

### Ingreso y auditoría

El perfil optativo v34 agrega `Independent_Reference.json` a las cinco fuentes existentes. Intake registra sus bytes y los liga al caso y a la revisión vigente. La referencia se prepara desde fuentes y fórmulas separadas; el ejecutor no la genera a partir de sus resultados para hacerlos coincidir. Los perfiles históricos conservan sus referencias y contratos.

`worksheet_variant_evidence_D268.reference_issues` exige inventarios completos de escenarios, banco, mercado, planos y M2. D267 coteja las ventanas contra las duraciones literales del Excel. No se puede eliminar un campo crítico del inventario para convertir un faltante en verde. D219/D220 retienen el bloqueo de caja y entrega ante citas faltantes, diferencias o falsos verdes.

Upside es informativo. No sustituye el dictamen de Base/Downside. `cash_deltas` muestra diferencias en aportes brutos, cobros y caja sin recuperar sobre la misma base inicial. Conserva las fechas y no inventa una tasa de descuento ni un ranking económico. Una ruta ausente o con otra base deja su comparación PENDING.

### Prueba ejecutada y límites observados

- 18 expedientes en una corrida: origen, 15 individuales, conjunto y Upside. Cada paquete se reprodujo con B16.
- El OCR rechazó la revisión sintética del conjunto por confianza insuficiente y diferencias de lectura. Sus cuatro rutas quedaron PENDING y el PDF no se entregó. Se preservó ese expediente.
- Una nueva revisión con identificador legible pasó 120 controles críticos. Se volvió a ejecutar únicamente el conjunto, con alcance de ejecución explícito. Downside supera el DSCR: refi PENDING, préstamo sin redimensionar y venta sin refi calculable.
- El cotejo independiente verifica **71 rutas de caja** entre los 19 expedientes y mantiene cinco rutas sin caja por sus bloqueos. Coteja presupuesto, usos, deuda, capacidad LTV/DSCR/debt yield, seis NOI por escenario, venta y movimientos por fecha. Las tres TIR no convencionales que exceden el recurso del aislador actual permanecen PENDING; no se publica una raíz aproximada como certificada.
- Pasaron 11 pruebas unitarias del contrato, vacío/cero, unidades, cambios conjuntos, diferencias de caja, inventarios incompletos, falsos verdes y préstamo por encima de capacidad. La entrega vigente del conjunto corregido se probó; expediente sin respaldo y revisión anterior quedaron bloqueados.
- B16 reprodujo el expediente D267 y su PDF sin cambios. Esta es validación dirigida; no sustituye la próxima batería general de la versión consolidada ni la validación con documentos reales.

La salida de una página usa el renderer fiscal D267 preservado; su encabezado identifica ese productor. Presenta Base refi: USD 5,14 adicionales y USD 27,83 cobrados; Base sin refi: USD 5,14 y USD 28,27. Downside refi queda PENDING por capacidad; sin refi: USD 8,68 adicionales, USD 7,93 cobrados y USD 10,76 sin recuperar. Cada importe se expresa por USD 10 iniciales; el PDF y el JSON conservan fechas y movimientos. Redondeo sólo de presentación. No son retornos históricos ni personales.

### Reproducción

Con el runtime OCR/JPEG y las dependencias del repositorio:

```bash
python3 -m unittest discover -s tests -p test_worksheet_scenario_program.py -v
python3 tools/check_worksheet_scenario_program_D268.py /ruta/a/un/directorio/nuevo
```

Para fuentes ya preparadas, `worksheet_scenario_program_D268.py programa.json --sources directorio --output directorio_nuevo` ejecuta el programa. `--case combined` limita explícitamente la ejecución; los demás casos no se presentan como ejecutados. Intake v34 usa `--include-reference` al registrar y correr las seis fuentes. Los resultados incluyen hashes, cotejo, eventos por USD 10 y diferencias respecto del origen.

Pendientes separados: activar shocks requiere política aprobada; C14 no acredita un desglose físico; el devengo mensual/irregular y los beneficios fiscales condicionales no se deducen del contrato trimestral. Renta regulada, decisiones de autoridad/materialidad y certificación empírica siguen en el registro de pendientes. Dictamen real, histórico y retorno personal sin reparto documentado: **PENDING**. Sin despliegue.

## 13.18 · D269 · D269 · Renta regulada, NOI y retorno por USD 10

**Fuente íntegra:** `docs/workbook-regulated-rent-D269.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


El perfil optativo v35 conecta límites de renta explícitos con las cinco anualidades desde estabilización, el año forward de venta, NOI, capacidad, refi y caja con/sin refi en Base y Downside. No acredita elegibilidad legal ni incorpora un beneficio fiscal. Las 55 celdas nativas conservan su estructura: C8–C11 siguen siendo rentas de mercado; la restricción regulatoria se documenta como fuente suplementaria.

Fuente del requisito: D251 p. 3, observación de renta asequible; `worksheet-policy-implementation-audit-D252.md`, sección «Observación adicional del Input Sheet». Productor: `worksheet_regulated_rent_D269.configuration/project_window`. Conexión: `worksheet_rental_inputs_D140.rental_noi/run_rental_scenario`. Auditoría: `worksheet_regulated_rent_D269.validate_reference/critical_fields` y D219/D220.

### Entradas y fórmulas vigentes del perfil de prueba

Cada escenario aporta distribución de unidades reguladas y de mercado por tipo, conciliada con la población del modelo; referencia al déficit neto de lease-up declarado; y una ventana documentada por anualidad, incluida la de salida. Cada ventana indica vigencia y si sus valores son observaciones o pronósticos sintéticos. No se copian límites al año siguiente por ausencia de datos.

Para cada tipo regulado se declaran: tamaño de hogar imputado y su fuente; ingreso AMI anual; fracción de límite de ingreso; proporción de ingreso aplicable a renta; utility allowance mensual del inquilino; unidades monetarias y fuentes. La moneda es USD y cada magnitud declara unidad. No se incorporan automáticamente una proporción del 30 %, un porcentaje AMI ni una regla de hogar por dormitorio.

| Cálculo | Definición | Control |
|---|---|---|
| Tope bruto mensual | AMI anual × fracción de ingreso × proporción para renta / 12 | Cada operando tiene unidad, valor y fuente. |
| Tope neto al propietario | Tope bruto − utility allowance mensual | Si es negativo, PENDING. No se recorta a cero. |
| Renta regulada cobrada | Menor entre renta de mercado proyectada y tope neto | La selección es una regla explícita del perfil, con su fuente; no una aprobación legal. |
| Renta de mercado proyectada | C8–C11 × factor anual documentado de C75 | El crecimiento se aplica una vez. El tope de cada año es independiente. |
| Ingreso bruto del tipo | 12 × (unidades reguladas × renta regulada + unidades de mercado × renta de mercado) | La suma de unidades coincide con el grupo. |
| Renta efectiva por unidad antes de pérdidas | Ingreso bruto / (12 × unidades totales) | Grupo vacío con cero explícito: N/A documentado, sin dividir por cero. |
| NOI y retorno | El ingreso anterior alimenta pérdidas, concesiones, gestión y el motor financiero existente | Utility allowance no se vuelve a restar de gastos del propietario. M2, reservas y deuda mantienen sus contratos. |

El alcance actual es `PER UNIT`. Un `PER SF` sin conversión regulatoria documentada queda PENDING. Los límites deben cubrir toda la ventana anual; un cambio regulatorio dentro del período requiere un contrato específico y no se aproxima silenciosamente. Exenciones, density bonuses, elegibilidad Live Local y cualquier beneficio condicionado quedan fuera de este cálculo.

### Evidencia de implementación

- Pasaron 10 pruebas unitarias: fórmula conocida, mezcla de unidades, crecimiento por encima del tope, valores vacíos frente a cero explícito, unidad monetaria incorrecta, falta de fuente/vigencia/año forward, población inconsistente, tope negativo, límites de tamaño de fuente y falsos verdes.
- El flujo completo v35 pasó 130 hechos críticos por expediente: los 116 del caso fiscal más fuente y seis ventanas de renta regulada por escenario. Alterar el tope de un grupo retiene la caja de ese escenario. Omitir el cap forward del inventario no produce verde.
- Se corrieron dos controles equivalentes: cuatro unidades reguladas con fuentes sintéticas y cero unidades reguladas con N/A explícito. Se cotejaron ocho rutas de caja, operación, deuda, capacidad, venta, múltiplo y extremos de TIR con fórmulas separadas que leen las fuentes.
- La diferencia de NOI frente al control coincide exactamente con la menor renta × (1 − pérdidas − concesiones) × (1 − gestión). Eso comprueba que no se duplicó la deducción de servicios ni se alteró el impuesto para otorgar un beneficio.
- Los dos expedientes pasaron B16 y la revisión vigente. Se entregó la hoja de una página del ensayo regulado. La ampliación del límite de JSON a 256 KiB pertenece sólo a v35; los límites anteriores permanecen vigentes para sus perfiles.

Por USD 10 iniciales, el ensayo regulado aporta USD 4,78 adicionales en Base y USD 8,13 en Downside. Los cobros Base son USD 28,31 con refi y USD 28,32 sin refi; Downside cobra USD 8,34 y USD 8,35 y deja USD 9,79 y USD 9,78 sin recuperar, respectivamente. Estabilización/refi: 01-01-2028 y 01-07-2028; venta: 01-01-2033 y 01-07-2033. La hoja detalla los aportes y cobros trimestrales. Estos valores provienen de una propuesta bancaria sintética de USD 1 M y supuestos declarados; no son condiciones de Lorena ni datos históricos de un deal.

### Reproducción y transición

```bash
python3 -m unittest discover -s tests -p test_worksheet_regulated_rent.py -v
python3 tools/check_worksheet_regulated_rent_D269.py /ruta/a/un/directorio/nuevo
```

El verificador compara el fixture versionado, arma las seis fuentes, ejecuta ambos controles, coteja los cálculos y entrega el PDF vigente. El productor no lee el template para rellenar datos de un caso. Sin un valor o regla mínimos, se conserva PENDING.

Para un proyecto real hacen falta las fuentes y la aplicabilidad del programa, los hogares/unidades afectados, los límites y deducciones vigentes, y la aprobación del responsable de criterios y supuestos. Un nombre de fuente o un hash no autentica esa aprobación. El dictamen real, el histórico y el retorno personal sin reparto documentado siguen **PENDING**. No hay despliegue ni certificación de las 33 políticas.

## 13.19 · D270 · D270 · TIR con prueba exacta de unicidad, sin cambiar la caja

**Fuente íntegra:** `docs/workbook-irr-certificate-D270.md`. **Estado:** contrato o auditoría de su corte; datos de ejemplo sintéticos. Leer junto al cierre D271.


Se cierran las tres TIR del corpus D268 que quedaban PENDING por el presupuesto del aislador anterior: Downside con refi de los drivers 18, 28 y 29. El método optativo prueba una única raíz admisible y acota la TIR anual. No cambia rentas, costos, impuestos, deuda, criterios, aportes o cobros. El dictamen real y el histórico siguen PENDING.

Fuente del pendiente: `MiniUW_Validacion_D268.json`, `arithmetic_pending_IRR`; registro `MiniUW_Alcance_y_Pendientes_D269.json`, TEC-04. Implementación: `worksheet_irr_certificate_D270.positive_inventory/annual_enclosure/verify_cash`; conexión: callback optativo de `worksheet_integrated_screening_D181.collect_metrics/screen_integrated` y rama sin refi de D140. Los casos que no declaran esta extensión mantienen el método anterior y sus resultados reproducibles.

### Definición matemática

Para flujos netos trimestrales documentados `c[t]`, se busca `z > 0` tal que:

`P(z) = Σ c[t] × z^t = 0`.

La TIR anual efectiva es `z^(-4) − 1`. Es una tasa derivada de los movimientos; no se introduce una tasa de descuento mensual ni un retorno objetivo.

La regla de Descartes se aplica a dos transformaciones exactas:

- `(1+t)^n × P(t/(1+t))` cubre `0 < z < 1`.
- `P(1+t)` cubre `1 < z < infinito`.
- `P(1) = 0` se comprueba por separado.

Cero o una variación certifican el número de raíces del intervalo correspondiente. Si el inventario completo prueba una sola raíz admisible, se construye un intervalo racional y se verifican los signos del VAN en sus extremos. Todos los cálculos usan fracciones exactas. Se conserva la precisión de 68 bisecciones del camino trimestral existente; los presupuestos computacionales son explícitos y acotados.

Si esta condición suficiente no resuelve el inventario, el aislador existente puede aportar su prueba. Un inventario incompleto, varias raíces, un polinomio idénticamente nulo, ausencia de una raíz admisible o agotamiento del recurso deja TIR PENDING. No se selecciona una tasa favorable entre varias. Una TIR exactamente cero puede publicarse sólo cuando está probada; no equivale a un dato vacío.

### Contrato y bloqueos

`rent_inputs.irr_certificate` declara perfil, reglas, referencia de definición y SHA-256 del algoritmo. La extensión pertenece a los perfiles fiscales integrados v34/v35. El código cargado, el archivo y la definición deben coincidir; cambiar el código en disco o los presupuestos en memoria no conserva una aprobación anterior.

Cada fecha de la grilla necesita movimientos observados, incluido el cero explícito. Una fecha omitida, un importe vacío, un tipo de movimiento desconocido, otra moneda o una grilla incompatible deja PENDING. La definición ausente no activa el método viejo como default. Los límites anteriores del lector permanecen vigentes; v34 con esta extensión utiliza el límite existente de 96 KiB, y v35 conserva su límite de 256 KiB.

El verificador no satisface una falta de criterio o evidencia. D219/D220 siguen retirando la caja no respaldada antes de formar el dictamen y entregar el PDF. El retorno personal necesita términos de reparto documentados. No se activa ninguna propuesta de política financiera.

### Validación ejecutada

Se reprodujeron los datos financieros congelados de los tres casos D268, usando las mismas cinco fuentes financieras y de criterios. Cada control conserva la TIR anterior PENDING; su nueva revisión analítica agrega únicamente la definición numérica y la referencia correspondiente. Los doce relatos de caja de esas revisiones coinciden byte por byte con sus controles: cada aporte, cobro, importe, fecha, base y referencia financiera. También coinciden NOI, financiación y capacidad.

| Downside con refi | Antes | Ahora, TIR anual acotada |
|---|---|---|
| Driver 18, renta residencial | PENDING por recurso del aislador | −16,48 % a −16,47 % |
| Driver 28, seguro | PENDING por recurso del aislador | −16,28 % a −16,27 % |
| Driver 29, impuesto operativo | PENDING por recurso del aislador | −16,47 % a −16,46 % |

El cotejo independiente verifica las fórmulas desde celdas y padrones hasta la venta, los movimientos por USD 10 y los extremos de TIR. Una corrida conjunta con AMI/M2 aporta otras cuatro rutas: sus cajas coinciden con las publicadas en D269, con 130 hechos críticos verificados.

Pasaron 13 pruebas unitarias, incluidas tasas negativas, cero exacto, dos/tres raíces admisibles, flujos nulos, movimiento faltante frente a cero, unidades/grilla, definición ausente, límites de tamaño/recurso y cambios de código o reglas. La cadena completa mantiene PENDING al quitar un criterio o el respaldo del DSCR. La entrega se limita al expediente vigente de una página.

### Reproducción

```bash
python3 -m unittest discover -s tests -p test_worksheet_irr_certificate.py -v
python3 tools/check_worksheet_irr_certificate_D270.py /ruta/a/un/directorio/nuevo
```

El fixture numérico versionado se usa sólo para pruebas. El modelo requiere declaración explícita de la extensión; no altera retrospectivamente las revisiones guardadas. La evidencia está en `MiniUW_Validacion_D270.json`. Esta mejora matemática no certifica las 33 políticas, un documento real ni una inversión. Sin despliegue ni decisiones reales.

## 14. Contratos detallados de criterio, reparto, PRELIMINAR y auditoría

Los siguientes documentos se conservan íntegros para revisión de decisiones y versiones. Sus estados de avance y ejemplos son los del corte citado. No sustituyen las confirmaciones pendientes ni actualizan por sí solos el contrato operativo. Las decisiones expresas del usuario resumidas en las secciones 2–5 y los límites actuales D271 tienen precedencia sobre una pregunta histórica ya resuelta.

## 14.1 · workbook-formula-review-D173

**Fuente íntegra:** `docs/workbook-formula-review-D173.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


Con impuestos del comprador y datos sintéticos, Base cobra **USD 18,10** y Downside **USD 6,08**. El aporte inicial de USD 10 es el 30/03/2027. El PDF de una página muestra los aportes y cobros fechados.

| Por USD 10 iniciales de equity del proyecto | Base | Downside |
|---|---:|---:|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Refi neta | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Operación al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Venta neta | USD 13,82 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Cobro total | **USD 18,10** | **USD 6,08** |
| Múltiplo sobre todos los aportes | **1,22x** | **0,33x** |
| Saldo sin recuperar al cierre | USD 0,00 | USD 12,11 |

Las cifras se redondean después del cuadre. El caso conserva FAIL simulado por múltiplo de equity en Downside. Decisión y retorno personal reales PENDING.

### Revisión del catálogo D170

Fuente revisada «MiniUW_Revision_Formulas_D170.pdf», pp. 1–3, SHA-256 `f84794a326bb2c5723dd3178744992ccd476d202e30adb777635d8319bbe6c0a`. La revisión coteja el catálogo. D173 ejecuta el código, el XLSX y la reconstrucción B16.

| Hallazgo y ubicación | Definición del perfil D173 | Validación y pendiente |
|---|---|---|
| CoC posrefi · p. 1, ítem 1 · M7-11 / estándares de la casa, política 12 · diagnóstico D167 | `(NOI del tramo posrefi − servicio programado de deuda del tramo) ÷ capital que sigue invertido al refinanciar`. El NOI y el saldo de capital vienen de fuentes explícitas. En este perfil el servicio es la cuota regular hasta la venta, sin payoff. | Base 11,46 % y Downside 1,79 % en sus respectivos tramos trimestrales, sin anualizar. Faltantes, ventana incompatible o saldo de cero dejan PENDING. D167 es una comparación histórica de cobros operativos sobre aportes brutos. El CoC D173 todavía carece de términos y umbrales reales compatibles, y el ensayo de screening conserva el múltiplo como métrica. |
| Impuesto del comprador en la salida · p. 2, ítem 2 · M7-05 / Inputs!C67 · motor T41 | `NOI forward comprador = ingresos forward − gastos forward sin impuesto − impuesto escolar comprador − impuesto no escolar comprador`. `Precio bruto = NOI forward comprador ÷ cap de salida`. Cada componente fiscal se declara para la misma ventana y con fuente vinculada a la revisión del caso. | Base y Downside concilian exactamente precio, costo variable y venta neta. La operación del vendedor, el NOI bancario y la capacidad de refi conservan sus bases. Si falta evidencia del impuesto del comprador, la venta del escenario queda PENDING. Un cero fiscal explícito se respeta. |
| Lectura del cobro LP/GP · p. 2, «Riesgo de presentación» · D170 | El PDF de ese ejemplo muestra cada cobro junto al múltiplo calculado sobre todos los aportes y al total aportado. Identifica el FAIL simulado del expediente de origen. | En el ejemplo D170, por USD 10 propios de cada rol, Base cobra USD 19,10 sobre USD 14,87 (1,28x) y Downside cobra USD 6,80 sobre USD 18,19 (0,37x). Son flujos archivados del ejemplo original de reparto. |
| Florida · p. 3 · C61–C62 / M2 y M7-05 | Los importes escolares y no escolares se conservan por separado en la interfaz de salida. D173 usa importes sintéticos ya calculados para el comprador. | PENDING para un inmueble real hasta verificar su régimen, jurisdicción, avalúos imponibles, millages, fecha efectiva y prorrateo del período. |
| Interés de obra y preferente · p. 2 | En D146, el interés simple trimestral se aplica al saldo de apertura más los desembolsos del trimestre. El ejemplo D169/D170 devenga el preferente simple sobre el capital LP al inicio del trimestre y el saldo impago no capitaliza. | Convenciones sintéticas declaradas. Queda pendiente cotejar cada una con los términos reales. |
| Ocupación de equilibrio y debt yield · p. 2 | M2-08 conserva el cálculo sintético por componentes. La fórmula simple de ocupación sigue en el conflicto SRC-02. El sizing del piloto usa LTV y DSCR. | PENDING hasta resolver la definición de ocupación y recibir la definición, base y mínimo de debt yield del banco aplicable. |

### Fuentes fiscales

El Department of Revenue de Florida indica que la Enmienda 3 se aplica desde el padrón fiscal 2027. El texto distingue gravámenes escolares y no escolares. La sección 193.1555 describe la retasación tras determinados cambios de propiedad o control al 1 de enero siguiente y contempla excepciones. El cálculo D173 no presupone que la base imponible sea el precio de venta ni adopta automáticamente el tope del 5 % como tasa de impuesto. [Boletín PTO 26-21](https://floridarevenue.com/property/Documents/PTO_BUL_26-21.pdf) · [Texto de la Enmienda 3](https://www.flsenate.gov/Session/Bill/2026F/1F/BillText/er/PDF) · [Florida Statutes §193.1555](https://www.flsenate.gov/Laws/Statutes/2026/193.1555)

### Reproducción

D173 usa el esquema sintético de planilla v25. B16 verifica la salida desde la planilla, el PDF de evidencia y la revisión vigente. Las versiones históricas siguen identificadas por sus propios esquemas y fuentes. Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_formula_review_D173.py --output /tmp/miniuw-d173
```

## 14.2 · workbook-performance-policy-D184

**Fuente íntegra:** `docs/workbook-performance-policy-D184.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


La reproducción del expediente sintético D181 conserva estos importes y fechas. Son flujos de equity agregado del proyecto, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro operativo al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Total cobrado | USD 18,06 | USD 6,08 |
| Sin recuperar al cierre | USD 0,00 | USD 12,11 |

El [PDF de una página](review/MiniUW_Informe_USD10_D181.pdf) se reprodujo byte por byte. El dictamen real, el reparto personal y la aprobación de las definiciones siguen PENDING.

### Bases comparables y ocupación

| Requisito | Fuente exacta | Definición ensayada y parte afectada | Evidencia y estado |
| --- | --- | --- | --- |
| NOI_uw para YoC y CoC | Devolución SRC-02/SRC-03, p. 1, «Reservas de reposición». Confirmación posterior, «YoC con NOI_uw» y mapa de bases | B13 calcula un NOI de underwriting con C60 × unidades elegibles y factores C76 de la ventana. Divide el NOI anual por el TDC conciliado para YoC. Para CoC usa el NOI y las reservas del tramo posrefi, menos servicio del tramo, sobre equity remanente. | JSON, `performance`. Comparación exacta contra el expediente y prorrateo sintético. Adopción PENDING. |
| Spread con la misma base de NOI | Confirmación posterior, «La condición: el spread» | B13/B14 conservan el YoC de underwriting. Si el cap usa NOI antes de reservas, el spread usa el YoC antes de reservas sólo en esa comparación. Una base ausente deja PENDING el spread. | JSON, `performance/*/spread_by_basis`. Se prueban ambas bases y una base ausente, por escenario. |
| NOI bancario y valoraciones | Confirmación posterior, «Las valoraciones no se tocan» | M6 conserva NOI bancario según el término bancario y su tratamiento de H08 y reservas. La refi y la venta usan la base de evidencia de su cap. | El ensayo lee fuentes y reproduce los resultados D181 de caja, deuda y valoración. Registra sus referencias junto a las métricas candidatas. |
| Ocupación económica y física | Devolución, p. 1, «Reservas», «Servicio de deuda» y «Conversión a física». Confirmación posterior, último caso de borde | M2-08 compara NOI después de reservas con servicio amortizante anual. Bajo la base fiscal antes de reservas del ensayo, el objetivo previo a la reserva es deuda más reserva. Conversión física sólo con pérdida de crédito y concesiones separadas. | JSON, `occupancy`. Cinco casos, con piso fiscal, rama proporcional, cero explícito, C14 sin desglose y física superior a 100 %. SRC-02 PENDING. |

El ensayo usa factores mensuales derivados de las ventanas de D181 para aplicar C76. Distribuye la reserva anual entre los meses cubiertos para construir el NOI candidato. Es una convención sintética de medición. La reserva descontada de la métrica y el depósito de caja restringida se registran por separado. Cuando el coeficiente de impuesto opera sobre NOI **antes** de reservas, se usa `X = servicio + reserva` y el impuesto en el cruce es `max(piso, k × X)`. El ensayo coteja el cruce con la solución de NOI y un punto inmediatamente inferior.

| Métrica candidata | Base | Downside |
| --- | ---: | ---: |
| NOI_uw anual | USD 408.737,68 | USD 199.068,85 |
| YoC con NOI_uw | 9,72 % | 3,94 % |
| CoC del tramo posrefi con NOI_uw, sin anualizar | 10,22 % | 0,26 % |
| Spread con cap sintético del 7 % después de reservas | +272,47 pb | −305,92 pb |
| Spread con cap sintético del 7 % antes de reservas | +347,81 pb | −200,66 pb |
| Spread con base del cap ausente | PENDING | PENDING |

El 7 % es un valor de prueba declarado por base. No se aplica como cap de mercado ni como conversión entre bases. En el ensayo separado de ocupación, C14 combinado permite mostrar 48 % de ocupación económica y deja la física PENDING con motivo `C14_sin_desglose`. El cálculo sintético usa servicio amortizante fijo. El tratamiento de interés solo y tasa variable requiere la evidencia anual del préstamo.

### RLV en una grilla sintética con deuda fija

La devolución, pp. 1–2, y la confirmación posterior especifican el criterio conjunto, el cierre de terreno y las fronteras. En la grilla se ajustan TDC y equity por `ΔP × (1 + C33)`. Se comparan simultáneamente YoC o spread, TIR, múltiplo de equity y máximo de equity/TDC. DSCR, debt yield y ocupación permanecen fuera de la búsqueda de precio de este perfil. El valor de Downside es informativo. Es una grilla independiente de los flujos D181 y sus precios son USD sintéticos de terreno.

| Ensayo | Máximo en PASS | Último precio antes de FAIL | Evidencia |
| --- | ---: | ---: | --- |
| Base con C33 = 0 % | USD 200 | USD 266 | Equity/TDC es vinculante. USD 201 queda PENDING en la banda. |
| Base con C33 = 5 % | USD 195 | USD 258 | La deuda queda fija. USD 196 queda PENDING en la banda. |
| Equity/TDC más restrictivo | −USD 37 | −USD 16 | Resultado firmado con bandera. Precio pedido/RLV queda sin valor. |
| Ningún punto cumple | PENDING | PENDING | No alcanzable en la grilla declarada. |
| TIR vinculante | USD 148 | USD 157 | El criterio de TIR deja USD 149 en la banda. |
| Cap después / antes de reservas | USD 133 / USD 166 | USD 171 / USD 207 | Dos casos con spread vinculante y base declarada. |
| Downside informativo con C33 = 5 % | USD 183 | USD 236 | Conserva los criterios del ensayo y usa sus flujos. |

La prueba guarda el punto anterior, el límite y el siguiente punto para cada frontera disponible. Al cruzar el máximo PASS puede aparecer PENDING. Al cruzar el límite previo a FAIL debe fallar al menos una métrica. Se verifica el orden de los estados por métrica en todos los puntos de la grilla. Para TIR se exige un solo cambio de signo de negativo a positivo, con equivalencia trimestral exacta de las tasas anuales del ensayo. Una serie con más de un cambio de signo o un cap sin base bloquean su cálculo de RLV. Un límite en el extremo superior queda sin resolver. Los máximos corresponden a una grilla acotada con paso de USD 1. La aprobación SRC-03 y su activación en el dictamen siguen PENDING.

### Reproducción y fuente

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_performance_policy_D184.py
```

[Resultados exactos y trazabilidad](review/MiniUW_Verificacion_D184.json). Fuente documental «MiniUW_Definiciones_SRC02_SRC03.pdf», pp. 1–2, SHA-256 `1f81b2cf28a81e6e91404e901eec40b7dd6ea1ea63cce7ab7429611345efb931`, y confirmación posterior de la condición de consistencia, las bases y los casos de borde. Ver [pendientes SRC-02 y SRC-03](requirements-conflicts.md) y [política de banda intermedia](pending-band-policy-decision.json).

## 14.3 · workbook-definition-screening-D193

**Fuente íntegra:** `docs/workbook-definition-screening-D193.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El expediente sintético D193 conserva los flujos del equity agregado de D181. El aporte inicial es de USD 10 el 30/03/2027 en ambos escenarios.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, fechados en el PDF | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro de operación | USD 1,43 el 30/12/2028 | USD 0,55 el 30/06/2029 |
| Cobro neto de venta | USD 13,78 el 30/12/2028 | USD 3,08 el 30/06/2029 |
| **Cobro total** | **USD 18,06** | **USD 6,08** |
| **Sin recuperar después de la venta** | **USD 0,00** | **USD 12,11** |

[Informe sintético de una página](review/MiniUW_Informe_USD10_D193.pdf). El retorno personal y la decisión real siguen PENDING.

### Cálculo y dictamen

| Requisito | Definición candidata y origen | Resultado Base | Resultado Downside |
| --- | --- | ---: | ---: |
| SRC-02 · Ocupación de equilibrio | En la ventana estabilizada de 12 meses, B13 encuentra el porcentaje de renta residencial efectiva que cubre el costo operativo, impuesto, reserva de reposición y servicio amortizante anual con tasa fija. Conserva el ingreso comercial y otros ingresos de ese perfil. Reproduce la base de NOI antes de impuestos. | 32,66 % económica | 69,37 % económica |
| SRC-03 · Valor residual del terreno | B13 prueba la grilla de USD −500.000 a USD 9.400.000 en pasos de USD 10.000. Mantiene fija la deuda y ajusta TDC y equity por Δprecio × (1 + C33). Exige en conjunto YoC con reservas o spread de base comparable, TIR, múltiplo y equity/TDC. | USD 3.200.000 | USD 2.720.000 |
| SRC-03 · Último precio antes de FAIL | Máximo punto de la grilla en PASS o banda. Guarda la prueba inmediatamente anterior y posterior a ambos límites. | USD 7.350.000 | USD 4.140.000 |
| B14 · Precio pedido / RLV | Usa el precio pedido y divide por el RLV positivo. La comparación PASS termina en 1×. El límite FAIL se obtiene de la segunda frontera del mismo cálculo. | 0,3438× | 0,4779× |

El fixture tiene umbrales inventados para ejercitar el circuito, identificados como sintéticos. Incluye Downside en la comparación de RLV sólo para probar la ruta. Su aplicabilidad real sigue por confirmar. El PASS de ensayo pertenece a esos umbrales, aun cuando Downside deja parte del capital sin recuperar. El CoC publicado conserva la definición del tramo de D181. Se ajustaron el YoC y el spread que intervienen en el RLV para que sigan las bases de reservas del ensayo D184. Las valoraciones de banco, refi, salida y todos los flujos del caso se reprodujeron íntegros.

### Bloqueos y evidencia

- La ocupación física requiere un desglose con fuente que reproduzca la renta efectiva del expediente. Con C14 combinado se puede calcular la económica si la regla la pide. Una ocupación física solicitada con desglose ausente o incompatible queda PENDING.
- Una frontera de RLV ausente o abierta en la grilla, una regla faltante, una base de cap incompatible o una aplicabilidad sin confirmar dejan el cociente PENDING. Un límite cero o negativo se conserva en la evidencia cuando la grilla lo encuentra. El cociente queda vacío.
- La banda entre las dos fronteras sigue PENDING. Un umbral manual que contradiga la banda calculada deja la fila PENDING tanto en el dictamen como en el cotejo desde el Excel de Lorena.
- La revisión designada vincula las políticas candidatas y las reglas al expediente. El auditor B16 vuelve a generar el resultado desde las planillas y los PDF. El archivo D181 se reproduce con su perfil original.

SRC-02 y SRC-03 se mantienen como definiciones candidatas hasta su confirmación por el responsable de criterios. El piloto real también requiere criterios aplicables de Lorena y respaldos del caso.

### Reproducción

Configurar [el runtime OCR fijado](workbook-plan-scan-D131.md). El perfil v30 y su revisión están en [caso](../templates/synthetic-workbook-definition-screening-D193.json) y [revisión](../templates/synthetic-workbook-current-revision-D193.json).

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_definition_screening_D193.py --output /tmp/miniuw-d193
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d193 \
  --current-revision templates/synthetic-workbook-current-revision-D193.json
```

[Registro de pruebas](review/MiniUW_Verificacion_D193.json) · [Fuente y ensayos de límites D184](workbook-performance-policy-D184.md).

## 14.4 · workbook-lp-gp-D168

**Fuente íntegra:** `docs/workbook-lp-gp-D168.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


D168 · Reparto sintético LP/GP sobre la corrida D166. El aporte inicial del proyecto es USD 10 el 30/03/2027. Bajo los términos del ensayo, LP aporta USD 8 y GP aporta USD 2 en ambos escenarios.

| Por USD 10 iniciales del proyecto | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aportes adicionales | USD 3,89 | USD 0,97 | USD 6,55 | USD 1,64 |
| Cobro neto de refi | USD 2,28 | USD 0,57 | USD 1,96 | USD 0,49 |
| Cobro de operación | USD 1,14 | USD 0,29 | USD 0,44 | USD 0,11 |
| Cobro neto de venta | USD 11,85 | USD 2,96 | USD 3,05 | USD 0,76 |
| **Total cobrado** | **USD 15,28** | **USD 3,82** | **USD 5,44** | **USD 1,36** |
| Ganancia o déficit de caja | +USD 3,38 | +USD 0,85 | −USD 9,11 | −USD 2,28 |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 0,00** | **USD 9,11** | **USD 2,28** |

En Base la refi se cobra el 30/09/2028 y los cobros de operación y venta el 30/12/2028. En Downside la refi se cobra el 30/03/2029 y los cobros de operación y venta el 30/06/2029. El PDF de salida lista cada aporte adicional por fecha. El cotejo se hace con importes exactos antes de redondear.

Por USD 10 iniciales **propios** de cada rol, LP y GP dan el mismo resultado bajo esta regla proporcional. En Base cada uno aporta USD 4,87 adicionales, cobra USD 19,10 y recupera todo su aporte. En Downside cada uno aporta USD 8,19 adicionales, cobra USD 6,80 y queda con USD 11,39 sin recuperar. El múltiplo y el intervalo de TIR anual también se conservan porque cada flujo se multiplica por la misma proporción.

### Términos del ensayo

La [ficha sintética D168](../templates/synthetic-lp-gp-terms-D168.json) declara LP 80 % y GP 20 % para cada aporte y cada cobro bruto de equity del proyecto. Aplica desde el aporte inicial hasta la venta, con los mismos porcentajes en Base y Downside y las fechas de D166. Los términos declaran un reparto proporcional sin comisiones, retorno preferente, promote, impuestos ni prioridades de distribución. Los porcentajes son supuestos de prueba.

La ficha vincula la revisión vigente y las huellas del resultado D166 y de los flujos por escenario. B16 reconstruye D166. D168 usa el asignador proporcional del repositorio y comprueba el cuadre exacto por movimiento, categoría, año y total. Conserva los aportes separados de los cobros, incluidos los movimientos en la misma fecha.

### Bloqueos comprobados

- Ficha de reparto ausente o porcentaje de LP faltante → PENDING para ambos escenarios.
- Porcentajes que suman menos del 100 % → PENDING. El modelo conserva los valores declarados.
- Ficha vinculada a otra revisión → PENDING para ambos escenarios.
- Huella de caja Downside distinta de la declarada → Downside PENDING. Base conserva su asignación sintética.

El retorno personal real y la decisión de inversión siguen PENDING. El reparto por prioridades, las comisiones y el tratamiento fiscal requieren términos y evidencia aplicables.

### Reproducción en el VPS

El script regenera y audita D166 con el [runtime OCR del piloto](workbook-plan-scan-D131.md). Para usar una corrida existente, agregar `--package` con la ruta a su carpeta. La salida guarda la ficha exacta, el cotejo y el resumen de una página.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_lp_gp_D168.py --output /tmp/miniuw-d168
```

## 14.5 · workbook-preferred-lp-gp-D169

**Fuente íntegra:** `docs/workbook-preferred-lp-gp-D169.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


D169 · Ensayo sintético de devolución de capital y retorno preferente LP sobre D166. El LP aporta USD 8 y el GP USD 2 de los USD 10 iniciales del proyecto, el 30/03/2027.

| Por USD 10 iniciales del proyecto | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aportes adicionales | USD 3,89 | USD 0,97 | USD 6,55 | USD 1,64 |
| Refinanciación · Base 30/09/2028 · Downside 30/03/2029 | USD 2,28 | USD 0,57 | USD 1,96 | USD 0,49 |
| Operación · Base 30/12/2028 · Downside 30/06/2029 | USD 1,14 | USD 0,29 | USD 0,44 | USD 0,11 |
| Venta · Base 30/12/2028 · Downside 30/06/2029 | USD 12,15 | USD 2,67 | USD 3,05 | USD 0,76 |
| **Total cobrado** | **USD 15,57** | **USD 3,53** | **USD 5,44** | **USD 1,36** |
| Sin recuperar al cierre | USD 0,00 | USD 0,00 | USD 9,11 | USD 2,28 |

En Base se devuelve todo el capital y el LP cobra USD 1,46 de preferente, incluido en el cobro de venta. En Downside toda la caja distribuible devuelve parte del capital y quedan USD 2,19 de preferente LP impago al cierre, además del capital sin recuperar. El preferente impago se informa por separado del déficit de caja y queda como saldo de la simulación al horizonte de venta.

| Por USD 10 iniciales propios | Aporte adicional | Total cobrado | Sin recuperar al cierre |
|---|---:|---:|---:|
| Base LP | USD 4,87 | USD 19,46 | USD 0,00 |
| Base GP | USD 4,87 | USD 17,64 | USD 0,00 |
| Downside LP | USD 8,19 | USD 6,80 | USD 11,39 |
| Downside GP | USD 8,19 | USD 6,80 | USD 11,39 |

La base por USD 10 propios reexpresa la participación de cada rol con las mismas fechas. El PDF muestra cada aporte y cobro fechado. Los totales se calculan antes de redondear.

### Términos sintéticos

La [ficha D169](../templates/synthetic-preferred-lp-gp-terms-D169.json) conserva el reparto 80 % LP y 20 % GP de los aportes y declara esos mismos porcentajes para el remanente. Usa una preferencia de prueba del 8 % simple anual para el LP, devengada al 2 % por trimestre sobre su capital pendiente al inicio de cada trimestre. El preferente impago se acumula sin capitalizar. Se devenga antes de los movimientos de la fecha y los aportes de ese día entran en la base del trimestre siguiente. Se procesan los aportes antes de los cobros en la misma fecha. Los cobros se procesan en orden de refinanciación, operación y venta.

Cada cobro primero devuelve capital a ambos roles en proporción a sus saldos pendientes. Luego paga al LP el preferente devengado hasta la fecha y distribuye el excedente 80/20. El ensayo excluye comisiones, impuestos y catch-up. Los porcentajes y la prioridad corresponden a esta ficha de prueba.

### Verificación y bloqueos

B16 reproduce D166 y verifica la revisión vigente. La ficha vincula las huellas del resultado, de la revisión y del libro de cada escenario. El cotejo conserva los movimientos brutos, devuelve capital antes de pagar el preferente y verifica que la suma de LP y GP iguale cada movimiento y el total del proyecto. Un cálculo independiente comprueba el devengo del preferente sobre los saldos de apertura.

La ficha ausente, la tasa faltante, las participaciones que no suman 100 % o una revisión distinta dejan el reparto **PENDING**. Una huella de caja distinta bloquea el escenario afectado. Un 0 % explícito reproduce el reparto proporcional bajo los demás términos de esta prueba. El retorno personal real sigue **PENDING** hasta contar con términos de reparto aplicables y verificados.

### Reproducción en el VPS

El script regenera y audita D166 con el [runtime OCR del piloto](workbook-plan-scan-D131.md). Para usar una corrida D166 existente, agregá `--package` con la ruta a su carpeta. La salida guarda la ficha, el cuadre por movimiento y trimestre y el resumen de una página.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_preferred_lp_gp_D169.py --output /tmp/miniuw-d169
```

## 14.6 · workbook-gp-catch-up-D170

**Fuente íntegra:** `docs/workbook-gp-catch-up-D170.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


D170 · Simulación de catch-up del GP sobre D169 y los flujos de D166. Cada columna se normaliza por USD 10 iniciales propios del rol.

| Movimiento | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 | 10,00 | 10,00 |
| Aportes adicionales | 4,87 | 4,87 | 8,19 | 8,19 |
| Refi · Base 30/09/2028 · Downside 30/03/2029 | 2,85 | 2,85 | 2,45 | 2,45 |
| Operación · Base 30/12/2028 · Downside 30/06/2029 | 1,43 | 1,43 | 0,55 | 0,55 |
| Venta · Base 30/12/2028 · Downside 30/06/2029 | 14,82 | 14,82 | 3,81 | 3,81 |
| Múltiplo sobre todos los aportes | **1,28x** | **1,28x** | **0,37x** | **0,37x** |
| **Total cobrado** | **19,10** | **19,10** | **6,80** | **6,80** |
| Sin recuperar al cierre | 0,00 | 0,00 | 11,39 | 11,39 |

El resumen de una página muestra cada aporte adicional por fecha. Las cifras se redondean después del cuadre. En Base, el GP cobra USD 1,82 de catch-up por USD 10 propios, incluido en la venta. Equivale a USD 0,36 por USD 10 iniciales del proyecto. En Downside queda capital sin devolver y el catch-up pagado es cero.

### Términos del ensayo

La [ficha D170](../templates/synthetic-gp-catch-up-terms-D170.json) queda vinculada por huella a los términos D169. D169 conserva aportes y remanente 80 % LP / 20 % GP y preferente LP del 8 % anual simple. D170 inserta un tramo que destina el 100 % de la caja disponible al GP, una vez devuelto el capital y pagado el preferente LP devengado, hasta que el catch-up alcance el 20 % de la suma de preferente LP y catch-up GP. Si P es el preferente acumulado pagado, la meta acumulada es P × 20 % / (1 − 20 %). Cada pago se limita al saldo de esa meta y a la caja disponible. Después se reparte el remanente 80/20.

Con catch-up completo, los porcentajes sobre la ganancia coinciden con las participaciones de aporte de este ensayo. Por eso ambos roles tienen el mismo cobro total por USD 10 propios. Se comprobó un caso adicional con caja que alcanza para pagar el preferente y la mitad del catch-up. El saldo GP queda registrado y el remanente es cero.

### Verificación

B16 reproduce D166. Se concilian todos los movimientos y se comprueba que la devolución de capital y el preferente sean idénticos a D169. Cinco pruebas dejan PENDING ante ficha ausente, porcentaje faltante o inválido, huella D169 distinta u orden incompatible. Un 0 % explícito reproduce D169. El retorno personal real sigue PENDING hasta contar con términos aplicables y verificados.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_gp_catch_up_D170.py --output /tmp/miniuw-d170
```

Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md). Agregá `--package` para auditar un D166 guardado.

El expediente sintético D166 que alimenta este ejemplo tuvo un FAIL simulado. La [revisión D173](workbook-formula-review-D173.md) muestra el múltiplo y el total aportado junto al cobro por rol en el PDF.

## 14.7 · workbook-criteria-intake-D192

**Fuente íntegra:** `docs/workbook-criteria-intake-D192.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El ensayo sintético conserva los flujos conciliados de D191. Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales y cobra USD 6,08 hasta el 30/06/2029. Quedan sin recuperar USD 0,00 y USD 12,11, respectivamente. El [PDF de una página](review/ensayo-D190-D191/MiniUW_Informe_USD10_D191.pdf) detalla las fechas de cada aporte y cobro del equity agregado del proyecto.

### Criterios entregados por Lorena

La [planilla de criterios](../templates/MiniUW_Criterios_PASS_FAIL_Lorena.xlsx) pide operadores y umbrales vigentes. El equipo del proyecto prepara los Inputs y los respaldos. La lectura toma las columnas amarillas E–H y conserva su ubicación, el texto original y la huella del XLSX. Los números de B–D quedan como referencia histórica. Las notas de base, vigencia y política se conservan como declaraciones para revisión.

El cotejo reconstruye primero el expediente de Base y Downside con B16 y comprueba la revisión designada. Así se puede reproducir la comparación desde el XLSX recibido y la corrida financiera. La prueba aplica aritmética exacta a las definiciones del perfil D181, incluida la TIR como intervalo y el aporte de refi en USD del proyecto. La coincidencia de unidad permite comparar. Confirmar que coinciden también definición, denominador y período sigue siendo parte de la revisión.

| Entrada | Efecto de la prueba |
| --- | --- |
| Criterio completo y unidad compatible | Se observa PASS o FAIL en la fila, con el localizador de la regla. |
| Cero explícito | Se coteja como cero. El vacío deja PENDING. |
| Downside con «Sin FAIL» | Se verifica PASS; su incumplimiento queda PENDING. La política vigente queda por confirmar. |
| Banda intermedia, umbrales solapados o TIR que cruza un límite | La fila requiere revisión. |
| Umbral en % cuando el perfil calcula USD | PENDING por unidad, sin conversión del denominador. |
| Fórmula, formato alterado o revisión histórica | Se rechaza la lectura para la revisión vigente. |
| SRC-02, SRC-03 o «No aplica» declarado | PENDING hasta verificar definición o aplicabilidad. |

### Reproducción en el VPS

Usar [el entorno de OCR fijado](workbook-plan-scan-D131.md) y las dependencias de referencia.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_lorena_criteria_D192.py --output /tmp/miniuw-d192
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/preview_lorena_criteria_D192.py /tmp/miniuw-d192/Expediente \
  --current-revision templates/synthetic-workbook-current-revision-D181.json \
  --criteria /tmp/miniuw-d192/Criterios_Sinteticos_D192.xlsx
```

El cotejo se agrega como JSON interno. El estado del piloto y la decisión permanecen PENDING. El perfil D181 mantiene su PDF y dictamen histórico. El primer caso real requiere sus documentos, el cotejo financiero y criterios auténticos y compatibles. SRC-02 y SRC-03 conservan sus definiciones candidatas en [D184](workbook-performance-policy-D184.md).

## 14.8 · lorena-screening-D230

**Fuente íntegra:** `docs/lorena-screening-D230.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


La revisión `SYNTHETIC-Lorena-D230.v1` compila las diez métricas y los 29 umbrales definidos en la sección 2 del DOCX original. La receta fija el SHA-256 del DOCX y conserva su fecha literal. Cada umbral compilado incluye operador, valor racional, unidad, base de cálculo y ubicación exacta de su celda. La corrida exige la revisión y el SHA-256 exactos de la configuración compilada.

Los ensayos aplican las bandas de la Política 17 a observaciones ficticias de Base y Downside. PASS se prueba en la igualdad de cada umbral aplicable. FAIL exige cruzar estrictamente un umbral de Base. El RLV aplica a Base en esta configuración conforme a la Política 13. Se compara la prima sobre un RLV positivo. La prueba deja fuera de dictamen las métricas que la estrategia declara inaplicables y conserva los ceros documentados. Upside queda fuera de la comparación conforme a la Política 33.

| Caso ejecutado en el VPS | Dictamen simulado |
| --- | --- |
| Cumplen las 19 comparaciones aplicables | PASS |
| Downside queda debajo de un umbral de PASS con evidencia completa | HOLD · economía insuficiente |
| Falta una métrica material en Downside | HOLD · requiere diligencia adicional |
| Base cruza un umbral de FAIL con evidencia completa | FAIL |
| Base cruza un umbral de FAIL y falta otra métrica material | PENDING · la precedencia sigue por confirmar |

El dictamen operativo y el retorno histórico del 1101 siguen PENDING. El ensayo recibe métricas declaradas en sus unidades y bases. El motor de caja y el PDF por USD 10 conservan el flujo vigente. La adopción de los criterios y la conexión con métricas calculadas requieren validar sus bases y períodos. Por ejemplo, la Política 10 mide el aporte de refi como porcentaje del equity hasta estabilización y la Política 12 pide CoC anual. El ensayo de FAIL cubre el cruce de umbrales. La evaluación independiente de viabilidad al precio o estructura JV actuales requiere una regla aprobada.

### Reproducción

Desde la raíz del repositorio, compilar la receta versionada y ejecutar la batería de criterios.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/lorena_screening.py prepare --output /tmp/criterios-lorena.v1.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest -v test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
```

El SHA-256 de la configuración compilada en el VPS es `784a7fbde15f4eff7e2c098468422a8b55cda61a9f19651cc46ea50c611544db`. Para probar un caso sintético puntual, pasar la configuración compilada y el caso JSON al subcomando `rehearse`. La función `fixture` de la prueba genera los campos requeridos y fija la huella de la configuración. GitHub conserva la receta y su reproducción. La configuración con los valores compilados y los registros de prueba se guardan en el VPS.

## 14.9 · worksheet-lorena-screening-D231

**Fuente íntegra:** `docs/worksheet-lorena-screening-D231.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


La corrida de planilla sintética conserva los diez movimientos de Base y los trece de Downside, con las mismas fechas, montos exactos y PDF de D229. Base aporta USD 4,87 adicionales y cobra USD 2,85 al refinanciar el 30/09/2028 y USD 16,66 por operación y venta el 30/12/2028. Recupera todo el capital aportado. Downside aporta USD 8,19 adicionales y cobra USD 2,45 el 30/03/2029 y USD 4,68 por operación y venta el 30/06/2029. Quedan USD 11,06 sin recuperar. El PDF conserva el calendario completo. Los montos usan equity agregado del proyecto sintético.

### Conexión y controles

`rehearse-workbook` reproduce el expediente mediante B16, verifica su revisión vigente y aplica el perfil sintético D230 con el SHA-256 exacto de la configuración. El resultado interno vincula las huellas de la caja, el resultado y el PDF. La entrega sigue mostrando el dictamen real PENDING. Se conservan el dictamen y el retorno histórico del 1101 como PENDING.

| Métrica | Base y trazabilidad |
| --- | --- |
| YoC, spread y ocupación de equilibrio | Registros D193 con período y definición compatibles. El spread usa el NOI correspondiente a la base del cap comparable. |
| Recuperación y aporte en refi | Importes del cierre cotejados con el libro de caja y divididos por el equity aportado hasta estabilización. El cero del cierre queda explícito. |
| Equity/TDC | Equity aportado hasta estabilización sobre TDC reconciliado. |
| CoC posrefi | Ventana anual íntegra respaldada, NOI después de reservas, servicio de deuda y equity remanente. |
| Múltiplo y TIR | Distribuciones sobre aportes brutos e intervalo anual verificado de TIR del calendario de tenencia documentado. |
| RLV | Base. Búsqueda a deuda fija con C33 y los umbrales de D230. Exige que el límite cumpla las demás métricas Base y que el vecino superior falle un criterio de precio. Si el intervalo de precio cruza un umbral, la comparación queda pendiente. |

Tres controles en la capa de métricas usan los productores de caja, TIR, CoC, YoC, spread y ocupación del Mini-UW. Los tres conservan el mismo libro de aportes y cobros por fecha. El control de referencia cumple las 19 comparaciones aplicables. Un cap comparable de Downside distinto lleva el spread a la banda de **HOLD** económico. Un cap comparable de Base distinto lleva el spread por debajo del umbral de **FAIL** de Base. Los cambios corresponden al cap de referencia del spread. El precio de salida y la valuación de refi conservan sus propios caps.

El expediente sintético de planilla completa quedó **PENDING** en D230. En ambos escenarios el CoC cubre tres meses y requiere una ventana anual respaldada. El RLV Base también requiere esa métrica y el conjunto de entradas compatibles. El expediente conserva los cruces verificados de FAIL en Base y los faltantes. La adopción de criterios para casos reales y la precedencia entre esos hallazgos siguen pendientes.

### Reproducción

Desde la raíz del repositorio, con el [runtime OCR](workbook-plan-scan-D131.md) configurado, compilar D230 siguiendo [la guía](lorena-screening-D230.md) y ejecutar:

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_lorena_screening test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/lorena_screening.py rehearse-workbook /tmp/criterios-lorena.v1.json ./Expediente --current-revision ./Vigente.json
```

## 14.10 · worksheet-annual-route-lorena-D235

**Fuente íntegra:** `docs/worksheet-annual-route-lorena-D235.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El cotejo toma Base y Downside de `annual_hold_with_refinance` del expediente D234. Verifica la revisión vigente y reproduce el expediente desde sus fuentes. La configuración D230 de Lorena se usa en modo de simulación. El 1101 real y su retorno histórico siguen PENDING.

### Resultados por cada USD 10 iniciales

| Escenario | Aporte adicional | Refi | Cobros de operación | Venta | Cobro total | Sin recuperar |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,03, 30 sep 2028 | USD 1,20, dic 2028 a sep 2029 | USD 13,68, 30 sep 2029 | USD 16,92 | USD 0,00 |
| Downside | USD 8,32 | USD 1,64, 30 mar 2029 | USD 0,21, jun a dic 2029 | USD 3,08, 30 mar 2030 | USD 4,94 | USD 13,38 |

El aporte inicial se registra el 30 de marzo de 2027 en ambos casos. Los aportes adicionales llegan hasta septiembre de 2028 en Base y marzo de 2030 en Downside. Downside aporta USD 0,13 el día de venta para cubrir el déficit operativo del último trimestre. Los totales se redondean después de sumar los movimientos exactos. El cotejo conserva cada fecha, importe y etapa originales.

### Criterios y RLV

- Base cumple las condiciones de YoC, spread, aporte al cierre de refinanciación y cash-on-cash post-refi. Recuperación al refinanciar, equity/TDC, TIR y múltiplo activan su condición FAIL. Ocupación de equilibrio y RLV quedan PENDING. La TIR anual es 6,12 % y el cash-on-cash post-refi es 9,38 %.
- Downside cumple la condición de aporte al cierre de refinanciación. Siete métricas quedan por debajo o fuera de sus condiciones PASS. La ocupación queda PENDING y el RLV figura N/A por la política Base-only de D230. La TIR anual es −43,69 % y el cash-on-cash post-refi es 0,52 %.
- El dictamen simulado queda PENDING por faltantes concurrentes con condiciones FAIL verificadas en Base, cuya precedencia sigue pendiente de confirmación en D230. La ruta original de D234 no tiene un NOI anual que concilie con la curva de ocupación económica. En el control sintético con NOI conciliado se calcula la ocupación en ambos escenarios con la reserva C60 y el servicio de deuda de la ruta anual. La búsqueda del RLV en Base aplica conjuntamente los nueve criterios, mantiene fija la deuda y ajusta el costo total por el movimiento del precio y C33. Ningún precio válido de la grilla ensayada llega a PASS.

El equity acumulado hasta estabilización alimenta los criterios que lo requieren. El equity retenido después del cierre se usa para el cash-on-cash anual. La TIR anual se calcula sobre la caja neta al cierre de cada trimestre. En el control con un solo cambio de signo se comprueba la raíz mediante un intervalo racional.

### Reproducción

```sh
PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_lorena_annual_route
PYTHONPATH=src:tools python3 tools/lorena_screening.py rehearse-workbook \
    criterios-lorena.json expediente --current-revision vigente.json \
    --route annual_hold_with_refinance
```

La prueba compara la caja evento por evento con la salida de D234, verifica el bloqueo de RLV en ambos casos y coteja que el expediente y la revisión designada conserven sus bytes. El comando devuelve el dictamen, las métricas, el saldo y las fechas, junto con los hashes de la caja y del expediente.

## 14.11 · preliminary-pilot-readiness-D189

**Fuente íntegra:** `docs/preliminary-pilot-readiness-D189.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


En el piloto sintético D188, Base aporta USD 6,22 adicionales y cobra USD 31,29 hasta el 30/12/2028. Downside aporta USD 8,01 adicionales, cobra USD 10,15 hasta esa fecha y deja USD 7,86 sin recuperar. El [PDF de una página](review/MiniUW_Preliminar_Obra_Etapas_D188.pdf) desglosa los flujos fechados de equity agregado, antes de impuestos personales.

### Alcance v1 congelado

El Mini-UW v1 cubre el filtro residencial temprano y la evaluación formal del mismo tipo de proyecto. Incluye la planilla Base/Downside, el cotejo de documentos en los formatos ensayados, obra, deuda, refinanciación, operación, venta, retorno por USD 10, dictamen y auditoría. **PRELIMINAR** queda incluido como ruta de LOI para priorizar revisión, con el dictamen formal siempre PENDING. Los ajustes de validación, datos y corrección del piloto están dentro del v1. Nuevos productos, estrategias o módulos se registran para una versión posterior o Full UW. El libro Full UW se incorpora cuando esté disponible para el traspaso.

El corte funcional se apoya en D181–D184 para el expediente integrado y en D185–D188 para PRELIMINAR. El congelamiento deja pendientes las aprobaciones y la aceptación real.

### Mínimos verificados del ranking sintético

Se verifica el perfil residencial financiado con desembolsos por etapas del [caso D188](workbook-preliminary-staged-D188.md). Requiere los dos escenarios del mismo deal y la misma fecha de corte y grilla trimestral. Cada archivo tiene huella declarada. En los ensayos de comparación D185, las oportunidades deben compartir también la ruta de financiación. La convención sintética ordena por múltiplo de equity de Downside y da la misma posición a empates. Su aplicación real sigue pendiente de aprobación.

| Requisito para ingresar | Ubicación | Evidencia y efecto del faltante |
| --- | --- | --- |
| Identidad, fecha y bases | Inputs B3, E3, C7 y C34, y huella de cada XLSX en el caso | Omitir identidad, fecha, base, huella o libro retira la caja del escenario y excluye el deal. |
| Renta y operación | C8–C11, C13–C15, C57–C60, C62, C75 y C76 | Cada celda numérica mínima se probó vacía por separado. Cero numérico válido es una entrada explícita. |
| Adquisición, obra, cronograma y venta | C32–C33, C35, C37–C40, C42, C46–C47 y C67–C68 | Se prueban omisiones una por una. El respaldo aporta alcance, unidades, estacionamientos, absorción y tratamiento de reservas al vender. |
| Financiación | C51–C53 y C66, C69–C74. El complemento incluye principal, compromiso, plazos, H02, H08, debt yield aplicable, fondeo de refi y disposición de reserva permanente. | La ausencia de un mínimo o una solicitud superior al menor límite aplicable deja PENDING. |
| Etapas de obra | `support.financing.construction_stages` por escenario | Cada fila requiere fecha, participación elegible, fracción solicitada, disponibilidad, fuente, fecha de evidencia y responsable. Se bloquean excesos de disponibilidad o compromiso. |
| Trazabilidad de supuestos | `support` de programa, costos, renta/gastos, calendario, financiación y salida | Cada grupo requiere fuente, fecha compatible con el corte, responsable y descripción. La prueba retira grupos y campos por separado. |

Las 212 variantes bloqueadas verifican que se retire la caja afectada, se conserve la del escenario independiente, se excluya el deal del ranking y el PDF mantenga **Dictamen formal PENDING**. Se reproduce el paquete completo tras restituir un cero explícito. Las pruebas se ejecutan en el VPS con datos sintéticos y la salida es de una página. [Matriz de casos y bloqueos](review/MiniUW_Verificacion_D189.json).

### Corrida de referencia

```sh
PYTHONPATH=src:tests python3 tools/check_preliminary_pilot_readiness_D189.py
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_stages_D188.py --output /tmp/miniuw-piloto
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-piloto
```

Para revisar las entradas, usar el [caso JSON](../templates/synthetic-preliminary-staged-D188.json), [Inputs Base](../templates/synthetic-preliminary-staged-base-D188.xlsx) e [Inputs Downside](../templates/synthetic-preliminary-staged-downside-D188.xlsx) de D188. El paquete de salida conserva los dos XLSX, el caso, el PDF, los resultados y el manifiesto de huellas.

### Habilitación del primer piloto real

| Pendiente | Evidencia para cerrar |
| --- | --- |
| Autoridad y roles | Custodio de evidencia oficial, responsable de criterios y revisor financiero designados. |
| Definiciones y criterios | SRC-02 y SRC-03 aprobados, criterios vigentes por escenario y política de ranking para el uso real. |
| Expediente autorizado | Base y Downside de Lorena, supuestos y documentos vigentes del caso, con autorización para procesarlos. |
| Validación de punta a punta | Cotejo independiente de caja y dictamen por escenario, con diferencias resueltas o documentadas y revisión sobre la versión reproducida. |

Un piloto puede completarse con un PENDING o FAIL explicado y reproducible. El paso de un deal a Full UW requiere PASS vigente y aprobación auténtica, conforme al [contrato de decisión](decision-input-contract.md).

## 14.12 · workbook-preliminary-loi-D185

**Fuente íntegra:** `docs/workbook-preliminary-loi-D185.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El ejemplo D185 arranca con USD 10 de equity agregado el 30/03/2027. Los flujos se cargan como estimaciones de prueba en USD del proyecto y se normalizan con el aporte inicial. Las cifras son antes de impuestos personales.

| Caso A · por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional · 30/06/2027 | USD 2,00 | USD 3,00 |
| Cobro operativo · 30/12/2027 | USD 1,00 | USD 0,50 |
| Cobro neto de venta · 30/03/2028 | USD 14,00 | USD 9,50 |
| Cobro total | USD 15,00 | USD 10,00 |
| Resultado neto nominal | +USD 3,00 | −USD 3,00 |
| Sin recuperar al cierre | USD 0,00 | USD 3,00 |

[Informe sintético de una página](review/MiniUW_Preliminar_LOI_D185.pdf). Dictamen formal, retorno personal y valor retenido PENDING. Las cifras son ilustrativas de la ruta sin refi del fixture. La prueba también incluye la ruta con refi.

### Qué hace el ensayo

El perfil `miniuw.synthetic-preliminary-loi.v1` recibe supuestos de programa, adquisición y costos, renta y gastos, calendario, financiación y salida por escenario. Cada grupo tiene fuente, fecha y responsable. Cada evento de caja conserva su propio importe, fecha, fuente y responsable. Se requieren Base y Downside completos. Los importes aplicables de cero se declaran de forma expresa.

La convención de ensayo compara casos en USD de equity agregado con fecha de corte, grilla trimestral y ruta de financiación comunes. Ordena de mayor a menor por el múltiplo de equity estimado de Downside. El múltiplo usa todos los aportes y cobros brutos. Empates comparten posición. Un caso con un faltante o una base de comparación distinta queda fuera del ranking. Un escenario con caja respaldada sigue disponible si el otro está PENDING.

La caja se ingresa como proyección indicativa. El perfil reutiliza el motor de retornos para normalizar los eventos, sumar aportes y cobros, y reproducir el paquete. Los respaldos son declarativos en este ensayo. La derivación de los flujos desde presupuestos, rentas y documentos reales y el uso operativo requieren validación. El ranking sólo prioriza revisión. El resultado formal de esta ruta siempre es PENDING y el expediente conserva la elegibilidad para Full UW en falso.

### Qué se verificó

La prueba corre por el comando habitual y vuelve a leer el paquete y su PDF. Coteja normalización, fechas, orden, exclusión de un caso sin Downside, datos nulos, fuentes con fecha posterior al corte, faltante de responsable, horizonte o financiación incompatibles, empate, refi y aporte/cobro contradictorios de refi. [Resultado de ejecución](review/MiniUW_Verificacion_D185.json).

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_D185.py --output /tmp/miniuw-d185
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d185
```

### Cierre del piloto

La política de mínimos y ranking de D185 es una propuesta sintética para probar el circuito. La base operativa, el uso de datos reales y la aprobación de SRC-02/SRC-03 siguen pendientes. Para la corrida formal se requieren el inventario de criterios vigentes, responsables designados y un expediente Base/Downside con sus fuentes. Un PASS vigente más aprobación auténtica habilita evaluar el paso de ese deal a Full UW.

## 14.13 · workbook-preliminary-calculation-D186

**Fuente íntegra:** `docs/workbook-preliminary-calculation-D186.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El caso sintético aporta USD 10 el 30/03/2027. La [página por USD 10](review/MiniUW_Preliminar_Planilla_D186.pdf) detalla fechas e importes de ambos escenarios. Los flujos corresponden al equity agregado, antes de impuestos personales.

| Resultado por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, de junio a diciembre de 2027 | USD 11,71 | USD 14,25 |
| Cobros operativos trimestrales, de marzo a diciembre de 2028 | USD 3,45 en total | USD 2,35 en total |
| Cobro neto de venta, incluido el saldo de reservas liberado el 30/12/2028 | USD 33,75 | USD 14,45 |
| Total cobrado | USD 37,20 | USD 16,80 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,45 |

El resultado formal sigue **PENDING**, incluso si el caso aparece en el ranking preliminar. Los totales se redondean sobre importes exactos.

### De la planilla a los movimientos fechados

La ruta D186 lee dos copias del formato original `Inputs` de 55 campos, una por escenario. El JSON identifica el caso, la fecha, las huellas de ambos libros y el respaldo con fuente, fecha y responsable. El perfil es una prueba residencial sin deuda, con renta mensual por unidad, obra vertical expresada como total y fechas trimestrales comunes. Una corrida recibe un par de planillas del mismo deal. D185 conserva su entrada histórica de proyecciones para varios deals.

| Celdas mínimas del ensayo | Cálculo y control |
| --- | --- |
| C7–C11, C13–C15 | Unidades por tipo documentadas en el respaldo. Renta efectiva tras vacancia y crédito, más otros ingresos. C15 se declara cero en esta ruta y el costo de absorción se documenta aparte. |
| C32–C35, C37–C40, C42 | Terreno y cierre al comprar. Obra directa, estacionamientos, sitio, contingencia y costo blando. C42 fecha el desembolso temprano de costos blandos. El remanente se aporta al terminar la obra. |
| C46–C47 y C51 | Duración de obra y absorción en trimestres. Costo trimestral de absorción documentado. C51 debe ser cero explícito para el caso sin deuda. |
| C57–C60, C62, C75–C76 | Gastos, administración, seguro, impuesto por comparable, reserva y crecimiento anual de renta y gastos fijos. El saldo de reservas se mantiene separado de la caja de operación. |
| C67–C68 | El NOI proyectado para los cuatro trimestres posteriores al cierre dividido por cap de salida estima el precio. Se descuentan costos de venta y se añade la liberación documentada de reservas al cobro del equity. |

El escenario requiere programa, alcance completo de obra y gastos residenciales, espacios de estacionamiento, costo de absorción y política de liberación de reservas. La prueba deja fuera las celdas comerciales y asignaciones de servicios propias de otros perfiles. El período de deuda, la refinanciación, la obra y comercial con contratos detallados y la aplicación fiscal distinta al comparable requieren otra ruta validada. El cálculo conserva esta convención sintética sin cambiar D181 ni la política candidata de D184.

Si falta un mínimo en un escenario, su caja se retira y el deal queda fuera del ranking. La caja del otro escenario se conserva. El ensayo usa el múltiplo de Downside de D185 como convención para priorizar revisión. Un vacío, fórmula o error carecen de valor operativo. Un cero numérico válido participa en el cálculo.

### Reproducción

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_workbook_D186.py --output /tmp/miniuw-d186
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d186
```

La prueba coteja caja exacta por fecha y saldo sin recuperar con una referencia aritmética. Comprueba una celda vacía, C51 ausente, fórmula con caché, huella incompatible, deuda fuera de perfil y corrección a cero explícito. [Registro de verificación](review/MiniUW_Verificacion_D186.json).

## 14.14 · workbook-preliminary-financing-D187

**Fuente íntegra:** `docs/workbook-preliminary-financing-D187.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El caso sintético aporta USD 10 el 30/03/2027 al equity agregado del proyecto. La [página de PRELIMINAR](review/MiniUW_Preliminar_Refinanciacion_D187.pdf) presenta los movimientos por fecha, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales totales, incluido aporte de refi | USD 6,17 | USD 7,95 |
| Aporte al refinanciar · 30/12/2027 | USD 0,00 | USD 0,17 |
| Cobro neto al refinanciar · 30/12/2027 | USD 2,65 | USD 0,00 |
| Cobro operativo por trimestre · marzo a diciembre de 2028 | USD 0,65 | USD 0,42 |
| Cobro neto de venta · 30/12/2028 | USD 26,05 | USD 8,47 |
| Total cobrado | USD 31,29 | USD 10,15 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,80 |

Se redondea después de calcular con fracciones exactas. El dictamen formal y el retorno personal quedan PENDING.

### Ruta residencial financiada

La entrada común recibe dos XLSX del formato original Inputs, una copia por escenario. Las huellas, datos complementarios y respaldos se declaran en el JSON. El perfil `miniuw.synthetic-preliminary-loi-workbook.v2` conserva la base por USD 10 sobre la compra. D185 y D186 mantienen sus esquemas y salidas.

| Celdas y respaldo | Cálculo |
| --- | --- |
| C51–C53 · LTC, interés nominal anual y comisión | El compromiso es el menor entre el máximo declarado y LTC sobre costo directo elegible. El perfil desembolsa una vez al terminar la obra. Resta ese desembolso del aporte de obra y suma la comisión en la misma fecha. Cobra interés simple al fin de cada trimestre de absorción y cancela el principal al refinanciar. Exige vencimiento de obra explícito. |
| C66, C69–C72 · Cap de refi, tasa fija, amortización, LTV y DSCR | El motor de deuda calcula la cuota trimestral y el servicio anual equivalente. El valor de refi usa NOI estabilizado de valoración y C66. El DSCR usa NOI bancario, con H08 explícito y antes de reservas en este ensayo. Si el respaldo declara debt yield aplicable, se agrega su tope. La solicitud completa debe quedar dentro del menor límite. |
| C73–C74 · Costos y reserva permanente | Al refinanciar, el principal nuevo cubre la cancelación de obra, los costos y la reserva permanente. El remanente es cobro o aporte, según el signo. Un aporte requiere cobertura dentro del monto de equity declarado. |
| H02, C60, C67–C68 y liquidación de reservas | Se descuentan cuotas de la caja operativa trimestral. La venta cancela el saldo después de la última cuota. El cierre añade la reserva de reposición liberada y la fracción explícita liberada de la reserva permanente. Se registra por separado el saldo de reserva permanente transferido. |

El piloto usa calendario trimestral, refi al estabilizar, un desembolso de obra al cierre de construcción y deuda permanente fija con cuota regular hasta venta. El desembolso único es una convención del ensayo y requiere otra ruta para modelar desembolsos progresivos. El primer fixture usa tasa permanente cero explícita para facilitar el cotejo independiente y una variante ejercita la tasa positiva. Los valores no son términos bancarios vigentes.

### Verificación

Se conciliaron todos los aportes y cobros fechados de Base y Downside contra una referencia aritmética independiente. Se probaron faltantes, fórmula con caché, vencimientos, aporte de refi sin fondeo, exceso por LTV, DSCR y debt yield, igualdad en capacidad, no aplicabilidad de debt yield, tasa positiva y venta insuficiente. Un bloqueo en un escenario retira su caja, conserva la caja independiente y excluye el deal del ranking. La comparación de revisión usa el múltiplo de Downside de la política sintética D185.

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_finance_D187.py --output /tmp/miniuw-d187
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d187
```

[Registro de verificación](review/MiniUW_Verificacion_D187.json).

## 14.15 · workbook-preliminary-staged-D188

**Fuente íntegra:** `docs/workbook-preliminary-staged-D188.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El caso sintético aporta USD 10 de equity agregado el 30/03/2027. El [PDF de una página](review/MiniUW_Preliminar_Obra_Etapas_D188.pdf) detalla cada movimiento por fecha, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte de obra · 30/06/2027 | USD 3,44 | USD 4,24 |
| Aporte de obra e interés previo · 30/09/2027 | USD 2,48 | USD 3,28 |
| Absorción e interés final · 30/12/2027 | USD 0,30 | USD 0,32 |
| Movimiento neto al refinanciar · 30/12/2027 | Cobro USD 2,65 | Aporte USD 0,17 |
| Aportes adicionales totales | USD 6,22 | USD 8,01 |
| Cobro operativo por trimestre · marzo a diciembre de 2028 | USD 0,65 | USD 0,42 |
| Cobro neto de venta · 30/12/2028 | USD 26,05 | USD 8,47 |
| Total cobrado | USD 31,29 | USD 10,15 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,86 |

Los totales se calculan con importes exactos y luego se redondean. El dictamen formal y el retorno personal permanecen PENDING.

### Cómo se calculan las etapas

El perfil `miniuw.synthetic-preliminary-loi-workbook.v3` conserva dos XLSX del formato original Inputs y el expediente JSON vinculado por huellas. C34–C40 determinan el presupuesto. C42 asigna el costo blando temprano y C46–C47 delimitan las etapas y la absorción. El expediente complementario declara para cada trimestre de obra su fecha, participación del costo directo elegible, fracción solicitada, disponibilidad, fuente y responsable. Las participaciones deben sumar 100 %. El préstamo de cada etapa se calcula multiplicando el costo directo elegible de la planilla por la participación y la fracción solicitada.

El motor exige que la solicitud por etapa quede dentro del costo elegible y la disponibilidad. El acumulado queda sujeto al menor entre el compromiso declarado y el costo directo por LTC (C51). La comisión C53 se calcula sobre ese compromiso y se paga en la primera etapa según la convención de este ensayo. El interés simple de cada trimestre es el saldo de apertura más el desembolso al inicio del intervalo, por C52 dividido entre cuatro. El aporte de obra cubre los costos y el interés exigible en esa fecha, descontando el desembolso. En refi se cancela el principal efectivamente desembolsado. El expediente guarda el calendario de deuda y sus fuentes junto a las cifras calculadas.

| USD de proyecto | Base | Downside |
| --- | ---: | ---: |
| Primer desembolso · 30/06/2027 | USD 25.000 | USD 30.000 |
| Segundo desembolso · 30/09/2027 | USD 35.000 | USD 40.000 |
| Interés pagado · 30/09/2027 | USD 500 | USD 600 |
| Interés pagado · 30/12/2027 | USD 1.200 | USD 1.400 |
| Interés total | USD 1.700 | USD 2.000 |
| Principal cancelado en refi | USD 60.000 | USD 70.000 |

Los ensayos conservan el calendario trimestral residencial y la refinanciación al estabilizar. Las fracciones de etapa y la disponibilidad pertenecen al expediente complementario sintético. Los términos bancarios reales, otro calendario o una convención distinta de interés o comisiones requieren evidencia y validación propias.

### Bloqueos y reproducción

Una celda mínima ausente, una etapa incompleta, una fecha incompatible o un exceso de disponibilidad, compromiso o capacidad de refi retiran la caja del escenario afectado. Se conserva la caja independiente y el caso queda fuera del ranking. El control de refi sigue usando el menor límite aplicable de LTV, DSCR y debt yield. El dictamen formal sigue PENDING en toda la ruta.

Se cotejaron los aportes y cobros fechados contra aritmética independiente. Las doce variantes incluyen C52 y C72 vacíos, disponibilidad faltante, fecha incorrecta, desembolso superior al costo elegible, participaciones inconsistentes, excesos de disponibilidad, compromiso y refi, cero explícito, reprogramación de un desembolso y recálculo de deuda al modificar C35. El perfil D187 de desembolso único reproduce sus resultados y PDF.

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_stages_D188.py --output /tmp/miniuw-d188
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d188
```

[Registro de verificación](review/MiniUW_Verificacion_D188.json).

## 14.16 · workbook-preliminary-tax-D204

**Fuente íntegra:** `docs/workbook-preliminary-tax-D204.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


PRELIMINAR con M2 estima los flujos de equity agregado del caso sintético residencial con deuda de obra por etapas. Los importes se calculan antes de redondear. [Informe de una página con aportes y cobros fechados](review/MiniUW_Preliminar_Impuesto_D204.pdf)

| Escenario | Aporte adicional total | Refinanciación el 30/12/2027 | Cobro de operación trimestral en 2028 | Cobro neto de venta el 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el total adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

### Integración de M2

El perfil PRELIMINAR v4 usa los mismos padrones, retasaciones y tasas separadas de M2 que D203. C62 queda como dato del perfil histórico. V4 exige evidencia fiscal para valorar la refinanciación, calcular la caja de los trimestres estabilizados y proyectar el NOI de venta. Los períodos usan los meses completos que siguen a cada cierre trimestral. La obra y la absorción conservan los costos del expediente, con el costo de tenencia de absorción declarado en el respaldo de calendario. [Regla fiscal y alcance de D203](workbook-florida-tax-D203.md)

En el ejemplo, el tope deja la tasación no escolar de Base en USD 189.000 en 2028. En Downside, una mejora declarada como calificada produce una retasación a USD 265.000. El impuesto anual del vendedor resulta USD 2.841 y USD 3.445, respectivamente. Para el NOI de salida, el primer padrón del comprador usa la retasación por cambio de titularidad y lleva ese impuesto a USD 4.290 en Base y USD 3.705 en Downside.

La fuente, fecha de corte y responsable fiscal se registran por escenario. El expediente conserva el detalle de cada ventana, los valores escolares y no escolares, el millage, el tratamiento y las citas a los respaldos. La corrida completa entra al ranking sintético con el múltiplo actualizado de Downside. El dictamen formal y el retorno personal quedan PENDING.

Se probaron expediente fiscal ausente, millage faltante, retasación sin fecha, tasación del comprador faltante y evidencia posterior al corte. Se verificó también un aumento del impuesto que reduce la capacidad por debajo del refi solicitado. En esos casos se retira el deal del ranking. Si el faltante afecta a Downside, Base conserva su caja. El millage cero explícito conserva su valor y un blanco en C62 no cambia el flujo v4. [Resultados y motivos](review/MiniUW_Verificacion_D204.json)

### Reproducción en el VPS

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_tax_D204.py
```

[Entrada sintética v4](../templates/synthetic-preliminary-florida-tax-D204.json)

## 14.17 · workbook-preliminary-pilot-D205

**Fuente íntegra:** `docs/workbook-preliminary-pilot-D205.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El primer piloto PRELIMINAR reproduce el caso sintético residencial D204 desde las planillas y los respaldos. [Informe de una página con todos los flujos fechados](review/MiniUW_Preliminar_Piloto_D205.pdf)

| Escenario | Aporte adicional total | Refinanciación el 30/12/2027 | Cobro trimestral en 2028 | Venta neta el 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el total adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

Los importes corresponden a USD 10 iniciales de equity agregado. Los totales se calculan antes de redondear.

### Cómo correrlo

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py run templates/preliminary-pilot-D205 /tmp/miniuw-pilot-D205
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pilot-D205
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_pilot_D205.py
```

El comando de corrida requiere un directorio de salida nuevo. El comando de auditoría recalcula el expediente y compara el contenido archivo por archivo. El paquete de salida incluye el PDF, la caja exacta, el ranking, los motivos de bloqueo y la copia de las fuentes usadas.

### Fuentes y controles

El [inventario del piloto](../templates/preliminary-pilot-D205/pilot.json) fija los dos proyectos de prueba, la fecha de corte, el calendario común y las huellas de las fuentes. Por proyecto y escenario, el ingreso lee un archivo Inputs.xlsx y siete respaldos estructurados de prueba con fuente, fecha y responsable.

| Respaldo | Datos vinculados |
| --- | --- |
| Programa | Unidades y base de renta |
| Adquisición y costos | Terreno, costo de obra, estacionamientos y alcance |
| Renta y gastos | Rentas, pérdidas, gastos y reposición |
| Calendario | Plazos de obra, absorción y costo de tenencia |
| Financiación | Desembolsos de obra, límites, vencimientos y solicitud de refinanciación |
| Salida | Cap, costos de venta y destino de las reservas |
| Fiscal | Padrones, tasación, millage escolar y no escolar y evidencia de retasación de M2 |

Los respaldos JSON contienen datos sintéticos preparados para probar la carga y la conciliación. La corrida coteja sus valores de celda contra las hojas Inputs y aplica los cálculos de D204 con M2. El piloto permite reproducir esta cadena con los respaldos archivados. La extracción desde documentos de un deal real y la validación del ranking real siguen pendientes de la autorización y del expediente correspondiente.

### Resultado de aceptación

El ranking sintético ordena por múltiplo de equity de Downside. El caso de referencia quedó primero con 0,5031×. El comparador quedó segundo con 0,4204× al usar un cap de salida Downside de 18 % en su planilla y respaldo. Las entradas no incluyen un Excel de criterios de Lorena. El dictamen formal y el retorno personal quedan PENDING.

Se verificaron 32 archivos de origen y cinco variantes bloqueadas. Se retiraron los respaldos fiscal y financiero en pruebas separadas. También se alteró un respaldo sin actualizar su huella, se registró una renta discrepante con la planilla y se registró un respaldo fiscal sin tasa no escolar. El caso afectado quedó PENDING y fuera del ranking en cada variante. Base conservó su caja y el comparador permaneció disponible. Al reponer el respaldo fiscal original, se reprodujo el paquete completo byte a byte. [Evidencia de ejecución](review/MiniUW_Verificacion_D205.json)

## 14.18 · workbook-preliminary-pdf-D206

**Fuente íntegra:** `docs/workbook-preliminary-pdf-D206.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


El caso principal del piloto PRELIMINAR reproduce el cálculo D205 desde planillas y respaldos PDF sintéticos. Los importes son de equity agregado y los totales se calculan antes de redondear. [Informe con todos los aportes y cobros por fecha](review/MiniUW_Preliminar_Respaldo_PDF_D206.pdf)

| Escenario | Aporte adicional total | Refi al 30/12/2027 | Cobro trimestral durante 2028 | Venta neta al 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

### Qué lee y coteja el piloto

Cada proyecto y escenario tiene una planilla Inputs y un PDF con nueve páginas rotuladas. Las hojas A101 y A601 cotejan el conteo de unidades del plano y su cuadro. La cotización de obra se coteja con las partidas de la planilla. Las páginas bancarias identifican deuda de obra y deuda permanente por separado, con sus términos y los desembolsos de obra. La página fiscal alimenta M2 con padrones, tasaciones y millage escolar y no escolar. Las otras páginas documentan rentas y gastos, calendario y salida.

El perfil lee tablas de texto diseñadas para este ensayo. Las citas registran PDF, página y línea del campo leído. El ensayo usa el conteo declarado en las hojas del plano. La medición de superficies, el reconocimiento de trazos y la lectura de escaneos quedan fuera de este perfil. Cada bloque estructurado se reconstruye del texto de las páginas. El inventario JSON fija identidad, calendario, huellas y comparabilidad de los dos casos.

Las 36 páginas de respaldo concilian con el cálculo D205. Se conservan el orden del ranking, los aportes y los cobros exactos por fecha. La primera posición corresponde al caso principal, con múltiplo Downside de 0,5031×, seguido del comparador con 0,4204×. Una revisión de prueba del millage no escolar reduce el NOI bancario de Downside, sus cobros y su múltiplo en el ranking.

Se probaron hojas y respaldos faltantes, un duplicado bancario, diferencias de unidades y DSCR, un valor fiscal ausente y un PDF con huella distinta. En cada prueba el caso afectado queda PENDING y sale del ranking. Base y el otro proyecto conservan sus flujos verificados. La auditoría reproduce el paquete desde sus PDF y XLSX archivados. El dictamen formal y el retorno personal quedan PENDING.

### Reproducción

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py run templates/preliminary-pilot-D206 /tmp/miniuw-pdf-D206
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pdf-D206
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_pdf_D206.py
```

[Inventario de fuentes](../templates/preliminary-pilot-D206/pilot.json) · [Pruebas y resultados del VPS](review/MiniUW_Verificacion_D206.json)

## 14.19 · workbook-preliminary-revision-D207

**Fuente íntegra:** `docs/workbook-preliminary-revision-D207.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


Para un expediente nuevo la respuesta se mantiene **PENDING** hasta poder cotejar su evidencia. La referencia sintética D206 permite ensayar la revisión completa. Base aporta USD 6,22 adicionales y cobra USD 29,14 hasta el 30/12/2028. Downside aporta USD 8,01 adicionales y cobra USD 9,06 hasta esa fecha, con USD 8,95 sin recuperar. El informe muestra cada movimiento por fecha. [Ejemplo sintético por USD 10](review/MiniUW_Preliminar_Respaldo_PDF_D206.pdf)

### Cotejo por dato

Cada fila vincula el expediente, la revisión, el escenario y el campo con la planilla y la evidencia aplicable. Conserva la huella y versión de cada archivo, su ubicación exacta, los literales leídos, el valor normalizado, la unidad, la base del cálculo, el período, la fecha de corte y el responsable. La confirmación del respaldo se registra con el rol y la revisión correspondientes. Los datos comunes sólo se comparten si la misma evidencia declara que aplica a ambos escenarios.

| Evidencia | Qué se coteja | Cálculo o salida que depende del dato |
| --- | --- | --- |
| Plano A101 y cuadro A601 | Conteos por tipo, versión y unidades elegibles para renta, gastos y reservas. | Renta potencial, gastos por unidad, NOI, reservas, capacidad y venta. |
| Adquisición y cotización de obra | Precio y cierre, costo base y alcance, estacionamientos, contingencia y costos blandos. | Usos, costo elegible, desembolsos, intereses y aportes. Si cambia el aporte inicial verificado, cambia el factor de todos los flujos por USD 10. |
| Rentas y gastos | Importe por tipo, vacancia, otros ingresos, gastos, seguro, reposición y crecimiento con su período. | NOI operativo, NOI de valoración y banco, capacidad y NOI de salida. |
| Calendario | Compra, desembolsos, fin de obra, estabilización, refinanciación y fecha de venta. | Intereses, vigencia de deuda, padrones fiscales aplicables y fechas de los aportes y cobros. |
| Crédito de obra | Límites, disponibilidad por etapa, tasa, comisión y vencimiento. | Desembolsos y aportes, costo de intereses y saldo que se liquida al refinanciar. |
| Crédito permanente | Principal, LTV, DSCR, debt yield cuando aplica, tasa, amortización, vencimiento, comisiones y reservas. | Capacidad por el menor límite, caja al refinanciar, servicio, saldo al vender y cobros. |
| Respaldo fiscal | Clasificación, padrones, millage escolar y no escolar, tasaciones y fecha de retasación. | M2, NOI por ventana, capacidad y cobros. El NOI de salida usa el padrón del comprador cuando corresponde. |
| Supuesto de salida | Cap y su base de NOI, costos y disposición de reservas. | Precio de venta, costos, cobro neto, múltiplo y saldo sin recuperar. |

El cotejo conserva el blanco como faltante y el cero explícito como valor. Una unidad, base o período incompatible deja la fila sin confirmar. Si dos respaldos vigentes discrepan, se conservan ambas lecturas y se registra el motivo de la resolución, su fuente y quién la confirma. La huella acredita la identidad de los bytes. La publicación, fecha, vigencia y aplicabilidad de la fuente se verifican por separado. [Contrato de evidencias](evidence-locator-contract.md)

### Qué pasa cuando se corrige una fuente

1. **Abrir una revisión.** Guardar la anterior con sus documentos, resultados y huellas. Registrar el campo cambiado, el valor anterior y nuevo, la ubicación en cada respaldo y los escenarios alcanzados.
2. **Volver a cotejar los respaldos.** La planilla y la fuente deben seguir concordando. Registrar por separado las diferencias y los campos requeridos sin respaldo. Cuando el cambio afecta a ambos escenarios, volver a verificar ambos.
3. **Recalcular el expediente.** Repetir la corrida completa por disponibilidad de la implementación actual. Usar las dependencias de la tabla para verificar qué cifras debieron cambiar. Comparar también los importes y fechas independientes del cambio.
4. **Cotejar la caja.** Reconstruir los movimientos en USD del proyecto desde las fuentes. Escalar cada movimiento bruto por `10 ÷ aporte inicial verificado` del escenario. Cotejar fecha, signo y categoría, incluso si coinciden aportes y cobros en un mismo día. Conciliar refi, operación, venta, aportes adicionales, múltiplo y saldo sin recuperar. [Método de conciliación independiente](workbook-independent-reconciliation-D179.md)
5. **Actualizar el ranking.** Si hay un dato obligatorio faltante o discrepante, la caja afectada queda PENDING y el expediente sale del ranking. Los demás expedientes comparables y la caja verificable del escenario independiente siguen visibles. Al resolver la causa y repetir la corrida, el caso puede volver a PRELIMINAR. El dictamen formal permanece PENDING.

### Casos para verificar el diseño

| Cambio | Resultado esperado | Evidencia disponible |
| --- | --- | --- |
| Quitar A601 o el crédito de obra | Downside PENDING, fuera del ranking. Base y el comparador conservan sus flujos. | Verificado con PDF sintéticos en D206. |
| Declarar distinto DSCR en banco y planilla | PENDING con página y celda. Se retira la caja de Downside. | Verificado en D206. |
| Aumentar el millage no escolar Downside en un PDF registrado | Se recalculan el NOI bancario, los cobros y el múltiplo de Downside. | Verificado en D206 con la tasa de prueba. |
| Corregir un aporte inicial en una revisión completa | Volver a conciliar fuentes y usos. Recalcular el factor por USD 10 de todos los eventos del escenario y cotejar montos antes de redondear. | Verificado en D213. Se cambió C32 en Downside, de USD 100.000 a USD 140.000, y el aporte inicial del proyecto pasó de USD 105.000 a USD 147.000. La caja bruta posterior se conservó y los once movimientos se cotejaron por fecha, tipo e importe. |
| Reponer exactamente el respaldo original | El paquete vuelve a reproducirse byte a byte en las mismas condiciones. | Verificado en D205 y D206. |
| Restituir evidencia con valores nuevos | Guardar ambas revisiones, demostrar qué diferencias se explican por el cambio y recalcular el ranking vigente. | Procedimiento definido en D207. D206 prueba un cambio fiscal. D213 vuelve a calcular el ranking ante el nuevo aporte inicial, conserva la revisión anterior y verifica que las discrepancias o un aporte cero dejen el caso fuera del ranking. |

La tabla describe el flujo de revisión diseñado en D207. La corrida D206 acepta los PDF de tablas sintéticas y deja trazas por página y línea. La vinculación de documentos con formatos reales, la revisión de sus términos aplicables y la comparación financiera del primer proyecto se harán cuando exista un expediente autorizado. El PRELIMINAR mantiene el dictamen formal PENDING.

### Vigencia tras una corrección

La auditoría archivada reproduce el expediente con sus propios respaldos y devuelve el resultado de esa revisión. Para consultar el ranking vigente, indicá en `audit` el directorio externo que se designó como revisión vigente. La comparación verifica el inventario completo y las huellas de sus archivos. Un inventario distinto, una fuente ausente o alterada, o un directorio de fuentes dentro del propio expediente deja el cotejo PENDING, con ranking vacío y sin huella de PDF vigente.

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pdf-D206 --current-source templates/preliminary-pilot-D206
```

D214 aplica el cotejo a las dos revisiones sintéticas de C32. La revisión original conserva su ranking histórico. Frente al inventario corregido, el ranking original queda retirado de la consulta vigente. El paquete corregido muestra el orden recalculado y conserva sus flujos por USD 10. La designación es explícita y corresponde al piloto sintético. El dictamen formal sigue PENDING.

### Entrega del PDF vigente

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py deliver /tmp/miniuw-pdf-D206 /tmp/MiniUW_PRELIMINAR_Vigente.pdf --current-source templates/preliminary-pilot-D206
```

`deliver` reproduce el paquete, verifica el inventario designado inmediatamente antes de la entrega y escribe el PDF auditado de una página en un destino nuevo. El destino queda fuera del paquete y de sus fuentes. Si la revisión es anterior, el inventario cambió durante el cotejo o el caso de foco tiene un escenario PENDING, devuelve `delivery=PENDING` con código 2 y el destino no se crea. Un paquete alterado o un destino ocupado genera un error. Una entrega identifica el PDF, el inventario y el ranking de la revisión en ese momento. El archivo histórico sigue disponible mediante `audit`.

D215 coteja los aportes y cobros fechados de Base y Downside antes de redondear y verifica su presentación en el PDF entregado. Con la revisión sintética de C32, Downside aporta USD 5,72 adicionales, cobra USD 6,47 hasta el 30/12/2028 y queda con USD 9,25 sin recuperar por USD 10 iniciales. El dictamen formal sigue PENDING.

## 14.20 · workbook-critical-evidence-audit-D219

**Fuente íntegra:** `docs/workbook-critical-evidence-audit-D219.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


D219 audita el respaldo documental de una corrida sintética archivada. El auditor es de sólo lectura. Los importes y fechas por USD 10 se pueden consultar en el paquete reproducido por B16. El dictamen real y el retorno histórico quedan PENDING.

### Denominador y señal

La unidad de conteo es un **dato crítico por expediente y escenario**. Un dato compartido se cuenta una vez aunque lo lean varios bots o tenga más de una cita. El inventario sintético fija 48 datos:

| Grupo | Datos | Bots en el cotejo |
| --- | ---: | --- |
| GBA conciliada entre A101, A601 y cotización | 1 | B03, B05, B06, B07, B08, B09 |
| Límite de pisos y vigencia de la copia oficial | 1 | B10, B11 |
| Costo vertical de GC en Base y Downside | 2 | B08, B09 |
| Crédito de obra y permanente, siete términos por combinación de crédito y escenario | 28 | B08 |
| Rentas, concesiones, absorción, cap de salida y seguro en ambos escenarios | 16 | B08 |

Un dato con una marca verde incompatible con la referencia independiente se registra como **FALSE_GREEN**. El resultado señala bot, campo, cita, ruta del dato y motivo. Se comprueban el valor y la unidad o convención aplicable, página, localizador, huella y revisión designada. Los datos sin verificación completa quedan PENDING. Un verde válido de un lector puede coexistir con un dato PENDING si la cadena aún debe conciliarlo. La falta de una fuente afecta los datos cuyos verdes dependen de esa fuente.

Los valores y localizadores del inventario se cotejaron contra las líneas originales de las páginas sintéticas D137/D156/D157, los rangos de mercado del caso D200 y las planillas de ensayo. Las huellas fijan los archivos de prueba y permiten detectar si cambian. La auditoría compara el resultado contra ese inventario y comprueba el vínculo con la revisión externa. B16 conserva su función de reproducir la corrida.

### Resultado y reproducción

La corrida vigente sintética produce 48 verdes respaldados y cero falsos verdes. La prueba automatizada altera un respaldo por cada dato y detecta los 48. Los controles adicionales cubren página equivocada, cita ausente, unidad incompatible, lectura omitida, hoja duplicada, huella distinta, PDF ausente y revisión anterior. Se comprueba que un faltante legítimamente pendiente y un dato independiente respaldado conserven sus estados. La cifra 0/48 corresponde a esta muestra y perfil documental sintéticos. El cotejo de falsos verdes sobre documentos reales y otras familias de datos requiere inventarios independientes para esas muestras.

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_critical_evidence_D219

PYTHONPATH=src:tests python3 tools/audit_worksheet_critical_evidence_D219.py /ruta/expediente-sintetico \
  --current-revision /ruta/revision-sintetica-designada.json
```

El comando imprime JSON por dato y devuelve 0 si todos los datos del inventario tienen verde respaldado, o 2 si queda PENDING o detecta un falso verde. El [inventario](../templates/synthetic-critical-evidence-D219.json) se conserva versionado con sus valores, fuentes y alcance.

## 14.21 · workbook-critical-evidence-gate-D220

**Fuente íntegra:** `docs/workbook-critical-evidence-gate-D220.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


En el perfil integral sintético v33, la caja, los escenarios de calendario y el dictamen consumen resultados que pasaron el [cotejo D219](workbook-critical-evidence-audit-D219.md). La revisión registra la huella del inventario independiente de 48 datos. D219 coteja las lecturas de los bots y los vínculos efectivamente usados por cada cálculo candidato antes de que sus resultados pasen a las métricas, el dictamen o el informe.

| Cotejo | Cálculo y entrega |
| --- | --- |
| Los 48 datos tienen respaldo | Base y Downside conservan montos y fechas del perfil fiscal v32. B16 reproduce la corrida y el comando de entrega puede publicar el PDF de una página de la revisión designada. |
| Un falso verde en el DSCR de Downside | Se detecta la cita faltante de B08. Se retiran la capacidad, el NOI, la venta, el retorno por USD 10 y las métricas dependientes de Downside. Base conserva su caja íntegra. El dictamen simulado y la entrega quedan PENDING. |
| Una cita inválida de área compartida entre ambos escenarios | Se retiran los resultados dependientes en ambos escenarios. El auditor conserva los motivos por dato y por bot. |
| Respaldo incompleto o revisión incompatible | Los cálculos afectados quedan PENDING. Cambiar la huella registrada del inventario requiere una nueva revisión. |

El expediente interno conserva el registro critical_evidence_review, con sus hallazgos y escenarios afectados. Si el cálculo queda PENDING, el expediente guarda una página interna de diagnóstico. El comando de entrega vuelve a ejecutar el cotejo con B16 y sólo publica el PDF integral cuando la revisión está vigente, el cotejo documental pasa y ambos flujos por USD 10 están disponibles.

El perfil v33 usa el inventario sintético documentado por D219. Para otras muestras se requiere un inventario de referencia independiente. Los perfiles archivados v31 y v32 conservan su reproducción original. El dictamen real y el retorno histórico siguen PENDING.

### Reproducción

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio:

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_critical_evidence_gate_D220
~~~

Para el ingreso desde archivos, usar la [configuración sintética D203](../templates/synthetic-florida-tax-settings-D203.json) con el esquema miniuw.synthetic-native-rental-inputs.v33. El comando run de worksheet_intake_D198.py registra la huella del inventario D219 al armar el expediente. El uso de audit y deliver con una revisión designada fuera del expediente sigue el [flujo integral](worksheet-technical-acceptance-D200.md#entrega-vigente-del-informe-integral).

## 14.22 · worksheet-technical-acceptance-D200

**Fuente íntegra:** `docs/worksheet-technical-acceptance-D200.md`. **Corte histórico/profile-specific; confirmar alcance vigente antes de uso real.**


Por cada **USD 10 iniciales** de equity agregado, la corrida completa calcula aportes adicionales y cobros fechados en Base y Downside. La decisión real y el retorno personal quedan **PENDING**.

### Evidencia de los cuatro hitos de D197

| Hito | Evidencia ejecutable |
| --- | --- |
| 13 · Expediente desde archivos | D198 lee los dos XLSX de entradas, el XLSX de criterios, el plano y el PDF de respaldos. Separa el registro de huellas del armado. El expediente se deriva sin editar su JSON. Con una revisión anterior, cambiar Downside C70 bloquea la caja de Downside e identifica el archivo y la celda. El mismo conjunto de archivos y registro reproduce el expediente byte a byte. |
| 14 · Deuda, salida y corte fiscal | D199 usa la misma entrada y la caja auditada. Prueba un trimestre de solo intereses, primera amortización y liquidación al vender. También prueba la venta con la deuda de obra vigente hasta su vencimiento. Un ensayo de obra cruza el 1 de enero de 2028: tasación sintética del terreno y de las partes utilizables al corte, con tasas escolares y no escolares declaradas. Una fecha faltante deja la variante PENDING. |
| 15 · Criterios y RLV | El perfil v31 requiere un único umbral de rendimiento para la grilla, YoC o spread, y verifica base y ventana de los criterios que consumen NOI. Quitar un FAIL de equity/TDC en cualquiera de los escenarios bloquea el RLV. Una revisión corregida lo recalcula. Downside puede tener un PASS explícito sin FAIL en una métrica ajena al RLV. |
| 16 · Aceptación de punta a punta | B16 reproduce el expediente completo, adverso, incompleto y corregido. La batería compara las líneas de NOI, deuda, venta y retorno con D179. Comprueba fuentes y usos por fecha y saldo de caja libre y restringida. LP más GP concilian por fecha bajo términos sintéticos de D169. La frontera PASS del RLV y la frontera FAIL tienen vecinos verificados por separado. La ocupación física queda PENDING si C14 carece de desglose. |

[Plan de aceptación D197](review/MiniUW_Cierre_Tecnico_y_Piloto_D197.md) · [Resultado de la batería](review/MiniUW_Verificacion_D200.json)

### Resultado por USD 10 iniciales

| Escenario | Aporte adicional | Refinanciación | Operación y venta | Total cobrado | Sin recuperar |
| --- | ---: | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,85 · 30/09/2028 | USD 15,21 · 30/12/2028 | USD 18,06 | USD 0,00 |
| Downside | USD 8,19 | USD 2,45 · 30/03/2029 | USD 3,63 · 30/06/2029 | USD 6,08 | USD 12,11 |

[Informe de una página, con aportes y cobros por fecha](review/MiniUW_Informe_USD10_D200.pdf)

El caso completo usa criterios sintéticos para ensayar un PASS. El adverso endurece el umbral de ocupación de Downside y da FAIL. En el incompleto faltan umbrales y da PENDING. El corregido los restituye en otra revisión y vuelve a PASS. Los cuatro conservan la misma caja.

### Calendarios sintéticos del mismo expediente

| Escenario y ruta | Aporte adicional | Total cobrado | Último cobro | Sin recuperar |
| --- | ---: | ---: | --- | ---: |
| Base · Solo intereses y después amortización | USD 4,88 | USD 16,64 | 30/03/2029 | USD 0,00 |
| Downside · Solo intereses y después amortización | USD 8,33 | USD 5,01 | 30/09/2029 | USD 13,33 |
| Base · Venta sin refinanciación | USD 4,87 | USD 18,23 | 30/12/2028 | USD 0,00 |
| Downside · Venta sin refinanciación | USD 8,25 | USD 6,47 | 30/06/2029 | USD 11,79 |

La ruta de amortización cuenta el tramo de solo intereses dentro del plazo original, usa el saldo posterior a la primera cuota amortizante y aplica el DSCR al servicio anual amortizante. El préstamo de USD 1,4 millones excede la capacidad en esa variante Downside. Una solicitud alternativa de USD 1,35 millones permite ensayar el cierre. La venta diferida utiliza NOI de salida y caja intermedia explícitos para sus fechas. El impuesto de obra se paga el 30/03/2028 en el ensayo Downside. De USD 1 millón de terreno y tres mejoras de USD 200.000, 300.000 y 400.000, la base sintética es USD 1,5 millones y la salida de caja es USD 15.000. El calendario de aceptación utiliza tasas de prueba. El módulo fiscal real M2 y la aprobación de criterios del piloto siguen PENDING.

Los flujos alternativos y sus conciliaciones quedan en el expediente. Las comparaciones de dictamen corresponden al caso principal. Cada cálculo se realiza con racionales exactos y el informe redondea la presentación a dos decimales.

### Reproducción

Desde una copia limpia con Python 3.12.3, las dependencias de `requirements-reference.txt` y el binario, idioma y biblioteca OCR documentados en [D162](workbook-evidence-progressive-D162.md):

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 tools/check_worksheet_technical_acceptance_D200.py --output /tmp/miniuw-d200
```

La batería prepara las entradas con los respaldos publicados y corre B16 sobre los cuatro expedientes. Si se usa `--output`, elegí un directorio nuevo o vacío. Para el flujo de dos pasos con archivos ya disponibles:

```bash
PYTHONPATH=src python3 tools/worksheet_intake_D198.py register ./fuentes-sinteticas ./registro.json --revision SYNTHETIC-prueba-v1
PYTHONPATH=src python3 tools/worksheet_intake_D198.py run ./fuentes-sinteticas ./registro.json --settings ./templates/synthetic-acceptance-settings-D200.json --output ./Expediente
```

El directorio de prueba contiene `Inputs.xlsx`, `Downside_Inputs.xlsx`, `Criterios_Lorena.xlsx`, `Plan.pdf` y `Evidence.pdf`. El registro conserva hashes de archivo y de celdas para localizar cambios. El archivo de configuración conserva las reglas, las bases de comparación, las confirmaciones y las referencias sintéticas declaradas. La revisión de vigencia del caso se genera al armar el expediente. Las confirmaciones y el registro son evidencias sintéticas locales.

**Alcance de cierre** · D197 mide el checklist técnico v1 con 16 hitos de igual peso. D200 acredita el cierre sintético. El piloto real mantiene sus seis condiciones de cierre y requiere documentos, responsables, criterios y validación del caso.

### Entrega vigente del informe integral

El comando `deliver` vuelve a ejecutar la auditoría B16 desde el expediente, verifica la revisión designada fuera del paquete y coteja su huella justo antes de exportar. Entrega una hoja de los perfiles sintéticos v31, v32 y v33 cuando los flujos por USD 10 de Base y Downside están disponibles. La revisión histórica, una fuente o PDF incompatibles y la caja incompleta bloquean la entrega. La hoja muestra la caja, las métricas calculadas y el dictamen real PENDING. Los umbrales de ensayo y su clasificación se consultan en `results.json`.

Los expedientes nuevos guardan la hoja de entrega auditada. Si un expediente de formato anterior sigue vigente, B16 reproduce su hoja original y `deliver` genera la presentación actual desde sus resultados auditados. La constancia registra las dos huellas para reproducir el expediente y verificar la entrega.

```bash
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py deliver ./Expediente --current-revision ./Vigente.json --output ./MiniUW_Vigente.pdf
```

Designá la revisión verificada en `Vigente.json` y elegí un destino nuevo fuera del expediente. La constancia incluye la huella del PDF y de la revisión. El ensayo automatizado de D216 usa las fuentes sintéticas de D200 y D203. Coteja la salida completa y rechaza el PDF alterado, la revisión anterior, el reemplazo de la revisión durante la entrega y la caja incompleta.

D227 vuelve a comparar los archivos del expediente con la copia auditada antes de publicar. Si algún archivo cambia en ese intervalo, la entrega queda PENDING. El ensayo modifica un respaldo justo después de la auditoría B16, verifica el rechazo y comprueba que al restituir los bytes originales se entrega un solo PDF vigente. Se cotejan las fechas y los importes de los diez movimientos de Base y trece de Downside por USD 10 iniciales.

~~~bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 -m unittest -v test_worksheet_delivery_snapshot_D227
~~~

### Corrección financiera y recálculo para la entrega

D217 corrige el costo porcentual de venta en C68 de 4 % a 5 % en Base y de 7 % a 8 % en Downside, con planillas e inventario sintéticos del perfil v32. El cotejo reconstruye el precio bruto desde NOI de salida y cap, y verifica el efecto exacto `precio bruto × cambio de tasa × 10 ÷ aporte inicial` sobre el cobro de venta. Se cotejan las fechas y los importes de cada aporte y cobro.

| Escenario | Aporte extra por USD 10 | Cobro total anterior | Cobro total corregido | Venta neta corregida | Sin recuperar al cierre |
| --- | ---: | ---: | ---: | --- | ---: |
| Base | USD 4,87 | USD 19,51 | USD 19,30 | USD 14,92 el 30/12/2028 | USD 0,00 |
| Downside | USD 8,19 | USD 7,13 | USD 7,03 | USD 4,01 el 30/06/2029 | USD 11,16 |

La prueba coteja ambas planillas antes y después, verifica el bloqueo por C68 al usar el registro anterior y confirma que el comando `deliver` sólo entrega el PDF auditado de la revisión nueva. La decisión real permanece PENDING.

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 -m unittest discover -s tests -p test_worksheet_cash_revision_D217.py -v
```

## 15. Ejemplo vigente de caja: cada aporte y cobro por USD 10

Ejemplo estrictamente sintético de la integración M2/AMI/TIR D270, con fuentes y términos bancarios ficticios; no es un resultado del 1101 ni de One Hollywood ni un valor aportado por Lorena. El relato corresponde al equity agregado del proyecto. El retorno personal sigue PENDING sin términos reales. Las tasas de TIR se derivan de flujos; no se impone un objetivo del 2 % mensual.

| Ruta | Inicial | Adicional | Cobro total | Sin recuperar | EM |
| --- | --- | --- | --- | --- | --- |
| Base Con refi | 10,00 | 4,78 | 28,31 | 0,00 | 1,92 x |
| Base Sin refi | 10,00 | 4,78 | 28,32 | 0,00 | 1,92 x |
| Downside Con refi | 10,00 | 8,13 | 8,34 | 9,79 | 0,46 x |
| Downside Sin refi | 10,00 | 8,13 | 8,35 | 9,78 | 0,46 x |

Todos los importes siguientes son USD por USD 10 iniciales. Se mantienen ceros explícitos de los eventos presentes. Los totales se calculan con fracciones exactas antes de redondear; sumas de importes ya redondeados pueden diferir por centavos. Una ausencia no se publica como 0.

| Ruta | Fecha | Categoría | Tipo | USD por 10 |
| --- | --- | --- | --- | --- |
| Base Con refi | 2027-04-01 | initial_capital | Aporte | 10,00 |
| Base Con refi | 2027-04-01 | other_distribution | Cobro | 0,00 |
| Base Con refi | 2027-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2027-07-01 | other_distribution | Cobro | 0,00 |
| Base Con refi | 2027-10-01 | additional_capital | Aporte | 4,70 |
| Base Con refi | 2027-10-01 | other_distribution | Cobro | 0,00 |
| Base Con refi | 2028-01-01 | additional_capital | Aporte | 0,08 |
| Base Con refi | 2028-01-01 | other_distribution | Cobro | 0,00 |
| Base Con refi | 2028-01-01 | refinance_cash_in | Aporte | 0,00 |
| Base Con refi | 2028-01-01 | net_refinance_distribution | Cobro | 1,22 |
| Base Con refi | 2028-04-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2028-04-01 | operating_distribution | Cobro | 0,34 |
| Base Con refi | 2028-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2028-07-01 | operating_distribution | Cobro | 0,34 |
| Base Con refi | 2028-10-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2028-10-01 | operating_distribution | Cobro | 0,34 |
| Base Con refi | 2029-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2029-01-01 | operating_distribution | Cobro | 0,34 |
| Base Con refi | 2029-04-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2029-04-01 | operating_distribution | Cobro | 0,35 |
| Base Con refi | 2029-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2029-07-01 | operating_distribution | Cobro | 0,35 |
| Base Con refi | 2029-10-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2029-10-01 | operating_distribution | Cobro | 0,35 |
| Base Con refi | 2030-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2030-01-01 | operating_distribution | Cobro | 0,35 |
| Base Con refi | 2030-04-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2030-04-01 | operating_distribution | Cobro | 0,36 |
| Base Con refi | 2030-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2030-07-01 | operating_distribution | Cobro | 0,36 |
| Base Con refi | 2030-10-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2030-10-01 | operating_distribution | Cobro | 0,36 |
| Base Con refi | 2031-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2031-01-01 | operating_distribution | Cobro | 0,36 |
| Base Con refi | 2031-04-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2031-04-01 | operating_distribution | Cobro | 0,37 |
| Base Con refi | 2031-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2031-07-01 | operating_distribution | Cobro | 0,37 |
| Base Con refi | 2031-10-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2031-10-01 | operating_distribution | Cobro | 0,37 |
| Base Con refi | 2032-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2032-01-01 | operating_distribution | Cobro | 0,37 |
| Base Con refi | 2032-04-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2032-04-01 | operating_distribution | Cobro | 0,39 |
| Base Con refi | 2032-07-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2032-07-01 | operating_distribution | Cobro | 0,39 |
| Base Con refi | 2032-10-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2032-10-01 | operating_distribution | Cobro | 0,39 |
| Base Con refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2033-01-01 | operating_distribution | Cobro | 0,39 |
| Base Con refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Base Con refi | 2033-01-01 | net_sale_distribution | Cobro | 19,83 |
| Base Sin refi | 2027-04-01 | initial_capital | Aporte | 10,00 |
| Base Sin refi | 2027-04-01 | other_distribution | Cobro | 0,00 |
| Base Sin refi | 2027-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2027-07-01 | other_distribution | Cobro | 0,00 |
| Base Sin refi | 2027-10-01 | additional_capital | Aporte | 4,70 |
| Base Sin refi | 2027-10-01 | other_distribution | Cobro | 0,00 |
| Base Sin refi | 2028-01-01 | additional_capital | Aporte | 0,08 |
| Base Sin refi | 2028-01-01 | other_distribution | Cobro | 0,00 |
| Base Sin refi | 2028-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2028-01-01 | other_distribution | Cobro | 0,00 |
| Base Sin refi | 2028-04-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2028-04-01 | operating_distribution | Cobro | 0,37 |
| Base Sin refi | 2028-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2028-07-01 | operating_distribution | Cobro | 0,37 |
| Base Sin refi | 2028-10-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2028-10-01 | operating_distribution | Cobro | 0,37 |
| Base Sin refi | 2029-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2029-01-01 | operating_distribution | Cobro | 0,37 |
| Base Sin refi | 2029-04-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2029-04-01 | operating_distribution | Cobro | 0,38 |
| Base Sin refi | 2029-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2029-07-01 | operating_distribution | Cobro | 0,38 |
| Base Sin refi | 2029-10-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2029-10-01 | operating_distribution | Cobro | 0,38 |
| Base Sin refi | 2030-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2030-01-01 | operating_distribution | Cobro | 0,38 |
| Base Sin refi | 2030-04-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2030-04-01 | operating_distribution | Cobro | 0,39 |
| Base Sin refi | 2030-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2030-07-01 | operating_distribution | Cobro | 0,39 |
| Base Sin refi | 2030-10-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2030-10-01 | operating_distribution | Cobro | 0,39 |
| Base Sin refi | 2031-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2031-01-01 | operating_distribution | Cobro | 0,39 |
| Base Sin refi | 2031-04-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2031-04-01 | operating_distribution | Cobro | 0,40 |
| Base Sin refi | 2031-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2031-07-01 | operating_distribution | Cobro | 0,40 |
| Base Sin refi | 2031-10-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2031-10-01 | operating_distribution | Cobro | 0,40 |
| Base Sin refi | 2032-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2032-01-01 | operating_distribution | Cobro | 0,40 |
| Base Sin refi | 2032-04-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2032-04-01 | operating_distribution | Cobro | 0,42 |
| Base Sin refi | 2032-07-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2032-07-01 | operating_distribution | Cobro | 0,42 |
| Base Sin refi | 2032-10-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2032-10-01 | operating_distribution | Cobro | 0,42 |
| Base Sin refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2033-01-01 | operating_distribution | Cobro | 0,42 |
| Base Sin refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Base Sin refi | 2033-01-01 | net_sale_distribution | Cobro | 20,47 |
| Downside Con refi | 2027-04-01 | initial_capital | Aporte | 10,00 |
| Downside Con refi | 2027-04-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2027-07-01 | additional_capital | Aporte | 0,79 |
| Downside Con refi | 2027-07-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2027-10-01 | additional_capital | Aporte | 0,06 |
| Downside Con refi | 2027-10-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2028-01-01 | additional_capital | Aporte | 7,06 |
| Downside Con refi | 2028-01-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2028-04-01 | additional_capital | Aporte | 0,11 |
| Downside Con refi | 2028-04-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2028-07-01 | additional_capital | Aporte | 0,11 |
| Downside Con refi | 2028-07-01 | other_distribution | Cobro | 0,00 |
| Downside Con refi | 2028-07-01 | refinance_cash_in | Aporte | 0,00 |
| Downside Con refi | 2028-07-01 | net_refinance_distribution | Cobro | 0,84 |
| Downside Con refi | 2028-10-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2028-10-01 | operating_distribution | Cobro | 0,09 |
| Downside Con refi | 2029-01-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2029-01-01 | operating_distribution | Cobro | 0,09 |
| Downside Con refi | 2029-04-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2029-04-01 | operating_distribution | Cobro | 0,08 |
| Downside Con refi | 2029-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2029-07-01 | operating_distribution | Cobro | 0,08 |
| Downside Con refi | 2029-10-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2029-10-01 | operating_distribution | Cobro | 0,08 |
| Downside Con refi | 2030-01-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2030-01-01 | operating_distribution | Cobro | 0,08 |
| Downside Con refi | 2030-04-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2030-04-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2030-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2030-07-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2030-10-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2030-10-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2031-01-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2031-01-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2031-04-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2031-04-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2031-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2031-07-01 | operating_distribution | Cobro | 0,07 |
| Downside Con refi | 2031-10-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2031-10-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2032-01-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2032-01-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2032-04-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2032-04-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2032-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2032-07-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2032-10-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2032-10-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2033-01-01 | operating_distribution | Cobro | 0,06 |
| Downside Con refi | 2033-04-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2033-04-01 | operating_distribution | Cobro | 0,05 |
| Downside Con refi | 2033-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2033-07-01 | operating_distribution | Cobro | 0,05 |
| Downside Con refi | 2033-07-01 | additional_capital | Aporte | 0,00 |
| Downside Con refi | 2033-07-01 | net_sale_distribution | Cobro | 6,14 |
| Downside Sin refi | 2027-04-01 | initial_capital | Aporte | 10,00 |
| Downside Sin refi | 2027-04-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2027-07-01 | additional_capital | Aporte | 0,79 |
| Downside Sin refi | 2027-07-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2027-10-01 | additional_capital | Aporte | 0,06 |
| Downside Sin refi | 2027-10-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2028-01-01 | additional_capital | Aporte | 7,06 |
| Downside Sin refi | 2028-01-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2028-04-01 | additional_capital | Aporte | 0,11 |
| Downside Sin refi | 2028-04-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2028-07-01 | additional_capital | Aporte | 0,11 |
| Downside Sin refi | 2028-07-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2028-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2028-07-01 | other_distribution | Cobro | 0,00 |
| Downside Sin refi | 2028-10-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2028-10-01 | operating_distribution | Cobro | 0,15 |
| Downside Sin refi | 2029-01-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2029-01-01 | operating_distribution | Cobro | 0,15 |
| Downside Sin refi | 2029-04-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2029-04-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2029-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2029-07-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2029-10-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2029-10-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2030-01-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2030-01-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2030-04-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2030-04-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2030-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2030-07-01 | operating_distribution | Cobro | 0,14 |
| Downside Sin refi | 2030-10-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2030-10-01 | operating_distribution | Cobro | 0,13 |
| Downside Sin refi | 2031-01-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2031-01-01 | operating_distribution | Cobro | 0,13 |
| Downside Sin refi | 2031-04-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2031-04-01 | operating_distribution | Cobro | 0,13 |
| Downside Sin refi | 2031-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2031-07-01 | operating_distribution | Cobro | 0,13 |
| Downside Sin refi | 2031-10-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2031-10-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2032-01-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2032-01-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2032-04-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2032-04-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2032-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2032-07-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2032-10-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2032-10-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2033-01-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2033-01-01 | operating_distribution | Cobro | 0,12 |
| Downside Sin refi | 2033-04-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2033-04-01 | operating_distribution | Cobro | 0,11 |
| Downside Sin refi | 2033-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2033-07-01 | operating_distribution | Cobro | 0,11 |
| Downside Sin refi | 2033-07-01 | additional_capital | Aporte | 0,00 |
| Downside Sin refi | 2033-07-01 | net_sale_distribution | Cobro | 5,75 |

## 16. Evidencia de pruebas y límites de lo aprobado

| Actividad | Resultado observado |
| --- | --- |
| Código probado | da4358d594b4717db78a9ab68c1cdaca4de5b70e; los 681 archivos Python coinciden con el corte documentado. |
| Unitarias | 1.766 OK, sin fallos, errores u omisiones; no equivale a 1.766 deals ni certifica todo documento real. |
| 55 campos | 440 vacíos nulos (436 PENDING y 4 N/A declarados); 98 ceros numéricos preservados; 12 ceros rechazados en campos no numéricos. |
| Referencias | 26 suites, 2.087 archivos en el corte de la batería, originales preservados. |
| Aceptación | 16/16: completo PASS, adverso FAIL, incompleto PENDING y corregido PASS, todos simulados. |
| Integridad | Fuente y copia limpia coinciden. Prueba adicional: trimestre omitido tanto en eventos como en fechas deja TIR PENDING. |
| Fiscal / AMI | 116 datos críticos fiscales; 120 en programa de variantes; 130 en AMI. Inventarios del perfil correspondiente, no un único conteo universal. |
| TIR optativa | 16 rutas actuales con certificado; tres TIR D268 antes incompletas resueltas sin alterar caja. Raíz no probada o múltiple: PENDING. |
| Tiempo | Batería D271: 9.413 s; unitarias 8.808 s. No es el tiempo de una corrida de deal. |
| GitHub Actions | Pruebas ejecutadas en VPS; no se afirma aprobación de Actions ni se altera presupuesto. |

El código usa una referencia de cálculo separada desde celdas y padrones. Esto es cotejo de software; la revisión financiera profesional y la validación con evidencia real son carriles distintos. Los corpus D268, D269 y D270 se relacionan y no se suman como proyectos independientes. Los resultados y comandos exactos están en la constancia D271 adjunta. El índice de pruebas permite localizar escenarios, módulos y casos límite.

## 17. Todo lo que sigue pendiente y qué se necesita para cerrarlo

| ID | Requisito | Estado actual / efecto |
| --- | --- | --- |
| TEC-01 | Calendario integrado general de cinco años desde estabilización y duración documentada | implemented_and_validated_for_quarterly_v31_v32_v33; A missing fiscal value/source or false green blocks affected cash and delivery. No proxy fallback, inherited criterion, loan extension or blank-as-zero.; Monthly/irregular schedules and financial conventions outside the explicitly supported quarterly contract |
| TEC-02 | Un orquestador para todos los drivers, excepciones y Upside | implemented_and_validated_for_explicit_synthetic_v34; Orquestador explícito de 15 drivers implementado y cotejado; los defaults históricos siguen sin activar por CUR-01/REQ-06.; No historical shock defaults activated; source authority and exceptions await approved policy; C14 is stressed as documented combined loss; physical vacancy is not inferred from an undocumented decomposition; Conditional tax-benefit ordering remains POL-02; Monthly construction accrual is outside the explicitly supported quarterly contract |
| TEC-03 | Renta asequible regulada con AMI, tope y utility allowance | implemented_and_validated_for_annual_per_unit_v35; No deducir renta asequible de los gastos de servicios ni calcular un beneficio sin regla acreditada; Real program applicability and current official source authentication; PER_SF or changes within an annual window require an explicit separate contract; no silent conversion or averaging; Conditional tax benefits remain POL-02; no eligibility, exemption or density bonus is inferred |
| POL-01 | GBA derivado, materialidad y autoridad de fuente | decision_then_implementation; El área no respaldada bloquea los cálculos dependientes;  |
| POL-02 | Beneficios fiscales condicionales y stress de incertidumbre/orden de reglas | evidence_policy_then_implementation; El perfil actual no acredita un beneficio o excepción fiscal real;  |
| POL-03 | Criterios por versión, RLV por estrategia, equity bajo y precedencia con faltantes | approval_and_scoped_implementation_pending; Conservar banda PENDING y no adoptar propuestas ni umbrales históricos sin alcance confirmado;  |
| PIL-01 | Fuentes y términos reales, roles y cotejo independiente del caso | await_real_case_and_confirmations; Datos no documentados quedan vacíos/PENDING; retorno personal requiere reparto real;  |
| VAL-01 | Validación empírica del OCR, backtest y corridas en paralelo | real_validation_pending; Las pruebas sintéticas no certifican cero falsos verdes en documentos reales;  |
| TEC-04 | Improve complete IRR certification for high-complexity nonconventional cash polynomials | implemented_and_validated_for_opt_in_quarterly_certificate; The three known incomplete Downside refi IRRs now have a complete unique-root certificate with identical financial cash. No root chosen from multiple/unknown cases.; Mathematically unproved, multiple, missing or out-of-budget cases remain explicitly PENDING; no financial root-selection policy is invented |

**Alcance que no debe declararse terminado universalmente.** Los contratos integrados probados son trimestrales, con horizonte de años completos, y la renta regulada opera por unidad con límites que cubren toda la ventana anual. Calendarios mensuales/irregulares, devengo diferente, PER SF regulatorio o cambios dentro del año requieren definición, implementación y validación separadas. No se aproximan silenciosamente para presentar un resultado.

**Para la aceptación real:** obtener documentos y autorizaciones del primer caso; criterios confirmados; roles e identidad/alcance acreditados; términos de reparto si se quiere retorno personal; medir falsos verdes por dato crítico con documentos reales; backtest de 3–5 proyectos cerrados y 2–3 corridas en paralelo. Los objetivos de validación no se presentan como ya logrados. El aporte de Lorena no sustituye ninguno de esos respaldos.

**Full UW.** Nuevos productos, estrategias de venta por unidades/presales y ampliaciones se mantienen para v2/Full UW. El libro Full UW y su conciliación no se reconstruyen ni se simulan como recibidos.

## 18. Guía para la devolución profesional

| ID | Área | Cotejo solicitado |
| --- | --- | --- |
| R01 | Bases de NOI | ¿YoC, spread, CoC y equilibrio usan las bases y ventanas documentadas? ¿Cap de valoración/salida acredita la suya? |
| R02 | TDC y fondeo | ¿Incluye el costo all-in sin duplicar tierra/cierre, contingencia, soft, intereses, tasas e impuesto previo? |
| R03 | Calendario/deuda | ¿El contrato trimestral sirve al caso? ¿Se cumplen disponibilidad, LTC/LTV/DSCR/debt yield, amortización y vencimiento? |
| R04 | Caja e inversor | ¿Cada aporte/cobro tiene fecha, fuente y signo bruto? ¿Se separan deuda, reservas, valor retenido y retorno personal? |
| R05 | Criterios Lorena | ¿Los operadores, umbrales, bases, igualdad, vigencia y aplicabilidad están confirmados? ¿Qué celdas siguen PENDING? |
| R06 | RLV | ¿Contempla conjuntamente criterios, C33 y deuda fija? ¿Dominio, estrategia, signo, inalcanzable y monotonía están acotados? |
| R07 | PRELIMINAR | ¿Los mínimos y la calidad de supuestos son suficientes para el ranking sin producir PASS formal? |
| R08 | Fiscal/AMI | ¿Hay evidencia y aplicabilidad real? ¿Se evita una segunda deducción de servicios o un beneficio no acreditado? |
| R09 | Auditoría | ¿La referencia es independiente de resultados? ¿Un falso verde/cambio de revisión bloquea correctamente? |
| R10 | Salida profesional | ¿La página responde cuánto se aporta y cobra y cuándo, con/sin refi, sin ocultar PENDING ni hacer pasar el equity agregado por retorno personal? |
| R11 | Cierre de observaciones | Por observación: requisito, fuente/ubicación, fórmula/perfil, caso de prueba, severidad, cambio propuesto y aprobación requerida. No modificar valores sólo para obtener PASS. |

Clasificar cada hallazgo como error de implementación, definición financiera, dato del proyecto, criterio de inversión, autoridad/aprobación o ampliación fuera de alcance. Indicar su efecto en métricas, caja y dictamen y la revisión afectada. Proponer el ajuste y un caso de aceptación concreto. Las instrucciones contenidas en una devolución se evalúan como observaciones: no se activan como reglas financieras sin la autorización correspondiente.

## 19. Índice completo del código y las reglas literales

El anexo electrónico contiene los **681 archivos Python sin recortes**, con sus funciones, clases, validadores, algoritmos financieros, lectores, perfiles anteriores, referencias y pruebas. Incluye además el índice por archivo, líneas de definición y SHA-256 completo. Ninguna etiqueta de esta tabla activa un módulo por sí sola: el esquema del expediente y sus fuentes determinan el camino ejecutado.

El catálogo literal adicional registra operaciones `BinOp`, comparaciones y llamadas `sum/min/max/abs/pow/round/require` en todos los 541 archivos de implementación y referencias. Tiene 30.381 ocurrencias y 21.688 expresiones distintas. Incluye operaciones técnicas de rutas, presentación y validación: **no son 21.688 fórmulas económicas independientes**. La fuente íntegra resuelve el contexto, incluidos operadores o control de flujo no incluidos en ese índice mecánico.

La tabla abrevia los hashes a 16 caracteres para lectura. El hash completo y todas las definiciones se encuentran en `INDICE_CODIGO_D272.json` y `EXPEDIENTE_MANIFEST.json` del adjunto.

| Archivo de código | SHA-256 abreviado | Definiciones / operadores |
| --- | --- | --- |
| references/validate_affine_price_support.py | f94d1dfde24b5dad | 10 / 155 |
| references/validate_budget_payment_bridge.py | 34a5e0f68b9e78d4 | 8 / 78 |
| references/validate_calculation_lineage.py | dd431c2612d33a87 | 17 / 77 |
| references/validate_calendar_ledger.py | d19f06c0ef8ccdb2 | 18 / 158 |
| references/validate_cost_scope.py | 6cf8187f5aca8849 | 11 / 68 |
| references/validate_evidence_locators.py | 482b8c3fa0c61dbb | 6 / 52 |
| references/validate_financing_timeline.py | 5582d96704f29509 | 9 / 159 |
| references/validate_integrated_bridge.py | 0b1a665d1466bc61 | 1 / 65 |
| references/validate_interface_contracts.py | 51200cff4f04dab3 | 19 / 79 |
| references/validate_investor_return_bridge.py | 0535e95918f042f9 | 6 / 80 |
| references/validate_m2_algebra.py | 6b82cea9197fd977 | 0 / 28 |
| references/validate_m34_allocation.py | 8d62db30ba2d7526 | 1 / 17 |
| references/validate_m5_algebra.py | 6999083a40fab8ad | 0 / 39 |
| references/validate_m6_refinance.py | eaac79d9e23aec13 | 1 / 61 |
| references/validate_m7_returns.py | 92a813e8a92060a9 | 2 / 59 |
| references/validate_m8_scenarios_price.py | 4f10701c26e776df | 1 / 76 |
| references/validate_m9_comparisons.py | a47d50c320558cbc | 3 / 26 |
| references/validate_operating_cash_bridge.py | b995ec196b580d03 | 7 / 86 |
| references/validate_periodic_irr_isolation.py | b7f62f866581f25b | 18 / 120 |
| references/validate_price_grid_catalogue.py | 21966585f42ad73d | 9 / 120 |
| references/validate_refinance_capacity_bridge.py | c140509d924229b6 | 9 / 160 |
| references/validate_return_metric_bridge.py | 74090ec3723b8f21 | 7 / 116 |
| references/validate_revision_integrity.py | b723c19f2d5fff5f | 9 / 43 |
| references/validate_sensitivity_ranking.py | 72056c5fea476746 | 8 / 64 |
| references/validate_settlement_bridge.py | 9130a7575205b2cd | 6 / 146 |
| references/validate_structure_closeout.py | 384455bd2742a64e | 4 / 115 |
| src/miniuw_foundation/__init__.py | fd28e9e74d4ed9b6 | 0 / 0 |
| src/miniuw_foundation/archive.py | 54bf3b65c28a784d | 227 / 302 |
| src/miniuw_foundation/bounded_exit_sale.py | eb0e65a57c98d373 | 6 / 34 |
| src/miniuw_foundation/bounded_sale_costs.py | 1bf80e111a2dfbea | 4 / 60 |
| src/miniuw_foundation/bounded_sale_recovery.py | d7308d51262d2e68 | 9 / 87 |
| src/miniuw_foundation/calculations.py | ee79e0683eb9c5c5 | 16 / 58 |
| src/miniuw_foundation/capacity_project_returns.py | 6004b8146431c235 | 9 / 32 |
| src/miniuw_foundation/capital_checked_output.py | cd34fc11cb06b39f | 16 / 72 |
| src/miniuw_foundation/cash_participation.py | f2e1e28c4b37032f | 7 / 73 |
| src/miniuw_foundation/cash_participation_artifacts.py | 544fb52918bebc6e | 11 / 26 |
| src/miniuw_foundation/cash_risk.py | 570785ab8fa2547d | 4 / 21 |
| src/miniuw_foundation/closing_cash.py | 7053bbdba91ad38d | 7 / 98 |
| src/miniuw_foundation/closing_returns.py | 59c090460087d46f | 7 / 39 |
| src/miniuw_foundation/construction_bundle.py | a5e0d80508276538 | 4 / 9 |
| src/miniuw_foundation/construction_cash.py | b8a6967217927895 | 8 / 62 |
| src/miniuw_foundation/construction_draws.py | 623c2892168854d3 | 6 / 71 |
| src/miniuw_foundation/costed_exit_sale.py | 0281d9221745ad3e | 6 / 34 |
| src/miniuw_foundation/current_bounded_exit_output.py | ca7a01d43867430a | 5 / 18 |
| src/miniuw_foundation/current_bounded_recovery.py | a668e00153ea3888 | 5 / 14 |
| src/miniuw_foundation/current_construction_cash.py | 50d1798ac8619eaa | 4 / 39 |
| src/miniuw_foundation/current_exit_output.py | 1bdd108274fe9022 | 6 / 32 |
| src/miniuw_foundation/current_expense_lifecycle.py | 82fee3c9344127fd | 5 / 28 |
| src/miniuw_foundation/current_hold_sale.py | b04420d84aa41fbf | 5 / 22 |
| src/miniuw_foundation/current_lifecycle.py | a0efea0a9520bc5a | 7 / 36 |
| src/miniuw_foundation/current_phased_rental.py | 0ff27b2e2ebe1785 | 5 / 33 |
| src/miniuw_foundation/current_recovery_case.py | f4db6a03b8910bed | 4 / 12 |
| src/miniuw_foundation/current_rental_lifecycle.py | de9a1d79706be3ec | 5 / 27 |
| src/miniuw_foundation/current_settled_case.py | 68afc9c3ca4d30b3 | 6 / 42 |
| src/miniuw_foundation/debt_closing.py | 1cba940c460b0481 | 8 / 83 |
| src/miniuw_foundation/debt_closing_returns.py | e1468355b29c00f7 | 9 / 18 |
| src/miniuw_foundation/debt_dscr.py | 5a6557352fa2871a | 5 / 33 |
| src/miniuw_foundation/debt_service.py | 04d34f9479ebc802 | 12 / 88 |
| src/miniuw_foundation/deferred_insurance_artifacts.py | 90e9e0c5f0cd2bac | 7 / 22 |
| src/miniuw_foundation/deferred_insurance_settlement.py | 8cc1980e490bfcc8 | 7 / 96 |
| src/miniuw_foundation/drafts.py | babe6de12ad98ecb | 16 / 36 |
| src/miniuw_foundation/evidence_currency.py | 50f72838cdd9df15 | 6 / 48 |
| src/miniuw_foundation/execution.py | 575513986a934e1d | 14 / 57 |
| src/miniuw_foundation/exit_sale_bridge.py | 2e1095bf115f923b | 6 / 46 |
| src/miniuw_foundation/exit_value.py | 4885e792dc30dc28 | 4 / 40 |
| src/miniuw_foundation/expense_cash_detail.py | 78bf5aaafcf20c25 | 10 / 89 |
| src/miniuw_foundation/expense_checked_lifecycle.py | 3f81f3b297968910 | 11 / 61 |
| src/miniuw_foundation/expense_schedule.py | 0ccb1428ab2cfac6 | 4 / 50 |
| src/miniuw_foundation/hold_sale_bundle.py | f56db8b5a008c35d | 4 / 9 |
| src/miniuw_foundation/hold_sale_cash.py | d49f94f77edceef7 | 3 / 56 |
| src/miniuw_foundation/hold_sale_opening.py | e5df87d2709d8eb5 | 4 / 56 |
| src/miniuw_foundation/hold_sale_returns.py | bea9889b68c9b5b7 | 6 / 52 |
| src/miniuw_foundation/holding_cash.py | d7f427eeb3e24cb0 | 8 / 84 |
| src/miniuw_foundation/holding_returns.py | 79b682587ff90501 | 10 / 54 |
| src/miniuw_foundation/inputsheet.py | 7009c2c07573741e | 4 / 84 |
| src/miniuw_foundation/insurance_renewals.py | f30e1c1746e16eb3 | 4 / 94 |
| src/miniuw_foundation/insurance_terminal_artifacts.py | 32ac0f0646e9da63 | 7 / 22 |
| src/miniuw_foundation/insurance_terminal_closing.py | 37ce6d1f9503873b | 5 / 55 |
| src/miniuw_foundation/intake.py | 65c81e7916f28d2c | 4 / 13 |
| src/miniuw_foundation/investor_onepage.py | 9166655c5ad08802 | 2 / 58 |
| src/miniuw_foundation/investor_output_artifacts.py | e0125f13036f1a49 | 10 / 31 |
| src/miniuw_foundation/investor_returns.py | b64f5bae914ce97e | 7 / 147 |
| src/miniuw_foundation/investor_review.py | 49b4be61631ce86e | 6 / 92 |
| src/miniuw_foundation/irr_checked_artifacts.py | d3e599692b0c6eb1 | 10 / 35 |
| src/miniuw_foundation/irr_checked_output.py | 1e48f07bc41a7abe | 10 / 36 |
| src/miniuw_foundation/irr_interval_artifacts.py | 72968aa9fa2220da | 10 / 34 |
| src/miniuw_foundation/irr_interval_output.py | c3f9dfb600ebe749 | 10 / 79 |
| src/miniuw_foundation/irr_review_artifacts.py | 31b3fe387d177601 | 11 / 26 |
| src/miniuw_foundation/irr_revision_review.py | 049c7e89830f41f8 | 11 / 69 |
| src/miniuw_foundation/lifecycle_bundle.py | 68abecf3a0dc8701 | 9 / 16 |
| src/miniuw_foundation/lifecycle_returns.py | 2a981d5e4da67fff | 5 / 57 |
| src/miniuw_foundation/lifecycle_review.py | 617a42d0e4cb865b | 3 / 13 |
| src/miniuw_foundation/long_horizon_artifacts.py | 2acc493c8bb3f8ca | 10 / 35 |
| src/miniuw_foundation/long_horizon_report.py | 13553de154016edc | 5 / 130 |
| src/miniuw_foundation/lorena_screening.py | f17dd86ac508e397 | 6 / 58 |
| src/miniuw_foundation/nominal_policy_book.py | 49d040eb1192d73a | 4 / 95 |
| src/miniuw_foundation/normalization.py | 582f318182971e79 | 8 / 45 |
| src/miniuw_foundation/opening_debt.py | 601f9e8a9ff6d48d | 3 / 61 |
| src/miniuw_foundation/operating_cash.py | 1c23d1c6d629e98e | 7 / 108 |
| src/miniuw_foundation/operating_debt_phase.py | 7f875a0f0fbe3ffe | 4 / 46 |
| src/miniuw_foundation/operating_dscr.py | a3df43cf92b8a3fa | 5 / 29 |
| src/miniuw_foundation/operating_noi.py | 034fda6791ce3386 | 8 / 72 |
| src/miniuw_foundation/operating_returns.py | c0e62855b6bbcf91 | 7 / 37 |
| src/miniuw_foundation/participant_cash_risk.py | 3f40895c2270d555 | 7 / 46 |
| src/miniuw_foundation/participant_cash_risk_artifacts.py | 64800ce38a27c53a | 7 / 20 |
| src/miniuw_foundation/periodic_returns.py | eac518ac1fe44b19 | 19 / 66 |
| src/miniuw_foundation/phased_rental.py | 3fba8e990dc417dd | 5 / 80 |
| src/miniuw_foundation/phased_rental_lifecycle.py | f46dde3d968f2cb7 | 10 / 48 |
| src/miniuw_foundation/phased_settled_artifacts.py | 9cde0cba7f725f05 | 8 / 27 |
| src/miniuw_foundation/phased_settled_output.py | 1f0c1bfad58d4b7a | 8 / 66 |
| src/miniuw_foundation/phased_settled_report.py | af66217fbe213931 | 4 / 150 |
| src/miniuw_foundation/policy_renewal_artifacts.py | c3f6ef1b9de08e68 | 9 / 44 |
| src/miniuw_foundation/policy_renewal_case.py | 7f1bf0c2fcd861f8 | 5 / 27 |
| src/miniuw_foundation/preopening_cash.py | c49e83c2bdabcbb4 | 11 / 114 |
| src/miniuw_foundation/primitive_periodic_returns.py | 2f01214d43bd4e92 | 20 / 71 |
| src/miniuw_foundation/project_cash.py | ed906e56cb9a59fb | 10 / 137 |
| src/miniuw_foundation/project_returns.py | 761a34c27c3b7b79 | 10 / 75 |
| src/miniuw_foundation/project_sale_comparison.py | 9c609ab47f466124 | 6 / 38 |
| src/miniuw_foundation/project_sale_revision.py | 087ed71dd0217cde | 11 / 47 |
| src/miniuw_foundation/proposal_queue.py | 3a0af7fd5b74f887 | 25 / 24 |
| src/miniuw_foundation/recovery_case_check.py | 6a95ac57f16bfadd | 6 / 29 |
| src/miniuw_foundation/recovery_case_inventory.py | 4ce1e377d42dfa84 | 7 / 41 |
| src/miniuw_foundation/refinance_capacity.py | b3250d05ecf4af5c | 10 / 135 |
| src/miniuw_foundation/rental_calendar.py | 0339c2d4fb3e223e | 7 / 42 |
| src/miniuw_foundation/rental_checked_lifecycle.py | 39ff3281768799af | 10 / 60 |
| src/miniuw_foundation/rental_noi.py | 873f0687ab622d3a | 7 / 33 |
| src/miniuw_foundation/rental_operations.py | b1df13991edfe8a3 | 5 / 100 |
| src/miniuw_foundation/review_proposals.py | b232c7caa62aaf1b | 7 / 42 |
| src/miniuw_foundation/sale_costs.py | 5da82d3838b56b86 | 4 / 52 |
| src/miniuw_foundation/sale_recovery.py | ccc13f85c216874e | 8 / 70 |
| src/miniuw_foundation/sale_sensitivity.py | 3f92ce8af5f3722a | 5 / 52 |
| src/miniuw_foundation/scenario_review.py | dbb6054b1e4d9e13 | 7 / 29 |
| src/miniuw_foundation/scenario_threshold_rehearsal.py | 0f0e4fee3d0d6c34 | 4 / 17 |
| src/miniuw_foundation/scheduled_expense_artifacts.py | 21c085adba184f90 | 10 / 49 |
| src/miniuw_foundation/scheduled_expense_case.py | 39d1130aa1b424c7 | 9 / 81 |
| src/miniuw_foundation/scoped_profiles.py | 09ae05bd0ed27649 | 6 / 28 |
| src/miniuw_foundation/screening.py | 52701de576e82c52 | 10 / 84 |
| src/miniuw_foundation/settled_case.py | cd4d346dbb6af1c9 | 6 / 28 |
| src/miniuw_foundation/settled_case_artifacts.py | 50c4d3ee7ce2d48c | 7 / 25 |
| src/miniuw_foundation/settled_expense_boundary.py | 126aa3cd82a4e164 | 3 / 84 |
| src/miniuw_foundation/settled_hold_sale.py | 95cce059bd65fd0a | 3 / 55 |
| src/miniuw_foundation/settled_lifecycle_returns.py | 3130b3102dcac1f8 | 5 / 47 |
| src/miniuw_foundation/settled_operating_window.py | 268ca9c625220152 | 3 / 30 |
| src/miniuw_foundation/settled_output_artifacts.py | e82d006c4c0380db | 8 / 27 |
| src/miniuw_foundation/settled_output_report.py | 919b2f2d0f049e90 | 4 / 145 |
| src/miniuw_foundation/sheets.py | b3ef61d0bbef3365 | 2 / 10 |
| src/miniuw_foundation/sources.py | 4a9747a6623f20b5 | 2 / 2 |
| src/miniuw_foundation/staged_lifecycle_bundle.py | 49b658b5cc7de1c1 | 10 / 46 |
| src/miniuw_foundation/staged_lifecycle_returns.py | 2dd366642eb025e3 | 5 / 47 |
| src/miniuw_foundation/staged_operating_window.py | 20b394cc8dab2d4c | 3 / 30 |
| src/miniuw_foundation/store.py | b054aaef2c69e9b4 | 20 / 28 |
| src/miniuw_foundation/synthetic_onepager.py | d1e388ffc7c84815 | 9 / 72 |
| src/miniuw_foundation/threshold_rehearsal.py | a3de520e268867e0 | 6 / 39 |
| src/miniuw_foundation/v1_artifacts.py | 65f375bbfe450e6f | 6 / 33 |
| src/miniuw_foundation/v1_case.py | 490add260ae8d231 | 8 / 73 |
| src/miniuw_foundation/v1_contracts.py | cbd584f93bef7222 | 2 / 21 |
| src/miniuw_foundation/v1_projection.py | 16e4574b1c18feb1 | 7 / 22 |
| src/miniuw_foundation/v1_report.py | 3b63ad76e5c7f818 | 9 / 126 |
| src/miniuw_foundation/v1_revision.py | 7aade287213b6a0e | 10 / 51 |
| src/miniuw_foundation/v1_revision_bundle.py | 8f89820de2818944 | 9 / 55 |
| src/miniuw_foundation/workbooks.py | cd301d7b4758b5c8 | 10 / 150 |
| src/miniuw_foundation/worksheet_case_artifacts.py | f1cd5033ea1771b9 | 11 / 36 |
| src/miniuw_foundation/worksheet_case_output.py | 0f04f9a0ce17e8d2 | 9 / 60 |
| src/miniuw_foundation/worksheet_settled_artifacts.py | efb23a6f99d3d08f | 8 / 28 |
| src/miniuw_foundation/worksheet_settled_output.py | f004532782ea335d | 9 / 72 |
| src/miniuw_foundation/worksheet_settled_report.py | 897572db03f685e0 | 2 / 25 |
| tests/bounded_cost_test_support.py | 2be8659ca6ab6954 | 3 / 6 |
| tests/capacity_test_support.py | 95059aeec17193e7 | 5 / 4 |
| tests/debt_closing_test_support.py | a16dac035959a383 | 5 / 4 |
| tests/evidence_currency_test_support.py | 751e8b1b69088086 | 3 / 1 |
| tests/holding_test_support.py | 88448d26f461a19f | 4 / 5 |
| tests/inputsheet_fixture.py | d441222d44195c13 | 1 / 26 |
| tests/loan_fixture.py | 7e566a56a690f98f | 1 / 0 |
| tests/piecewise_recovery_test_support.py | 82395913370c3d05 | 2 / 3 |
| tests/project_test_support.py | 692dd62ff7a14027 | 5 / 8 |
| tests/recovery_case_test_support.py | 26dc2502f2260700 | 1 / 5 |
| tests/sale_cost_test_support.py | c2da593c481e89ff | 4 / 5 |
| tests/sale_revision_test_support.py | f8ac660428694de9 | 3 / 6 |
| tests/test_archive.py | eae6a3f355fbe3e3 | 30 / 13 |
| tests/test_bounded_exit_sale.py | a5722c961f943d6f | 17 / 3 |
| tests/test_bounded_sale_costs.py | ed3be8189e0328b2 | 22 / 5 |
| tests/test_bounded_sale_recovery.py | d51a30eb52b9c9be | 26 / 21 |
| tests/test_calculations.py | 7e93ec2a88323ef8 | 34 / 17 |
| tests/test_capacity_project_returns.py | d3ccb8bddc43faaf | 20 / 5 |
| tests/test_capital_checked_output.py | 3e663823f0af6139 | 14 / 27 |
| tests/test_cash_participation.py | d5877430c508caa3 | 21 / 38 |
| tests/test_cash_risk.py | 9c9486607bd7a40f | 28 / 6 |
| tests/test_closing_cash.py | 3f0da1b4435f3986 | 28 / 33 |
| tests/test_closing_returns.py | c728ffb018bd7477 | 23 / 14 |
| tests/test_construction_draws.py | ac6da97bba012a63 | 47 / 42 |
| tests/test_costed_exit_sale.py | a137ac9b78eb2f59 | 19 / 3 |
| tests/test_current_bounded_exit_output.py | 5386e7daaefed9a9 | 16 / 7 |
| tests/test_current_bounded_recovery.py | 08ccc55f9e23cb17 | 17 / 6 |
| tests/test_current_exit_output.py | cb66b80b35609628 | 18 / 6 |
| tests/test_current_lifecycle.py | 5174a43d8591c810 | 22 / 6 |
| tests/test_current_recovery_case.py | 5b9f30be3c6f8cd2 | 14 / 6 |
| tests/test_current_settled_output.py | 89cdd54523e67500 | 29 / 36 |
| tests/test_debt_closing.py | 9194a7ab39b4ec19 | 27 / 23 |
| tests/test_debt_closing_returns.py | 6cccc875bd66d839 | 21 / 10 |
| tests/test_debt_service.py | a0072fda153fe3b3 | 29 / 28 |
| tests/test_deferred_insurance_settlement.py | 2fcaa95f7c711fa5 | 22 / 37 |
| tests/test_evidence_currency.py | 0e8de89dc0dacec7 | 20 / 7 |
| tests/test_execution.py | 13011978322ec05b | 25 / 10 |
| tests/test_exit_sale_bridge.py | 7305bb17f8c87044 | 21 / 13 |
| tests/test_exit_value.py | 4dde5e9e9866364a | 19 / 6 |
| tests/test_expense_cash_detail.py | d74ccce48c2792ee | 25 / 30 |
| tests/test_expense_checked_lifecycle.py | f599cfe1312dc5e7 | 29 / 32 |
| tests/test_foundation.py | 52c74047a9f6f18a | 29 / 10 |
| tests/test_hold_sale.py | 386ff28c79a32eb6 | 59 / 29 |
| tests/test_holding_cash.py | 8fac7145a77a36ac | 26 / 58 |
| tests/test_holding_returns.py | 36e815fca125c57b | 23 / 20 |
| tests/test_inputsheet.py | fc68be29bf98bec0 | 28 / 28 |
| tests/test_insurance_terminal_closing.py | 00647a9c18a5d343 | 24 / 33 |
| tests/test_intake.py | fe18fefdc9a9002f | 12 / 7 |
| tests/test_investor_onepage.py | 3349d7133565183d | 6 / 13 |
| tests/test_investor_output_artifacts.py | 5954f50dce320c8a | 11 / 28 |
| tests/test_investor_returns.py | 7e92a428575c7fe4 | 30 / 17 |
| tests/test_investor_review.py | a984c2aa9a92d9c2 | 8 / 3 |
| tests/test_irr_checked_output.py | 4ec628763ee5006c | 19 / 34 |
| tests/test_irr_interval_logic.py | c56a8d21c95432b2 | 13 / 14 |
| tests/test_irr_interval_output.py | 1b4f8cecd2c1f162 | 16 / 39 |
| tests/test_irr_revision_review.py | 2fda2fcdced9ec68 | 20 / 41 |
| tests/test_lifecycle_returns.py | 4273e2f1ef2e5d88 | 51 / 27 |
| tests/test_long_horizon_output.py | 030a7e51814a9cb8 | 15 / 39 |
| tests/test_lorena_screening.py | 847d3fa90ad545af | 16 / 15 |
| tests/test_miniuw_v1.py | 0b0c17a06418d971 | 30 / 31 |
| tests/test_normalization.py | 1131920b5d665b32 | 33 / 7 |
| tests/test_operating_cash.py | 618061c38e48c912 | 30 / 34 |
| tests/test_operating_debt_phase.py | 22f34b418a1cc500 | 48 / 38 |
| tests/test_operating_dscr.py | 333814f8fe5ba2a1 | 21 / 14 |
| tests/test_operating_noi.py | 31d4122c43a2369f | 27 / 16 |
| tests/test_operating_returns.py | dec2f648b906c1c8 | 26 / 19 |
| tests/test_participant_cash_risk.py | 025fb14c96b5cfc1 | 21 / 36 |
| tests/test_periodic_returns.py | 9cab563a872fc9ad | 21 / 13 |
| tests/test_phased_rental.py | f9093b00f63650b6 | 18 / 12 |
| tests/test_phased_rental_lifecycle.py | 955498af879b5dcf | 24 / 33 |
| tests/test_phased_settled_output.py | 33eb564ec864245e | 27 / 56 |
| tests/test_policy_renewals.py | 029778e66241fa71 | 37 / 44 |
| tests/test_preliminary_initial_equity_D213.py | 4e49190d8e653a0a | 8 / 47 |
| tests/test_preopening_cash.py | 1c45e0db2e8f835b | 33 / 29 |
| tests/test_primitive_periodic_returns.py | 03231092fd359058 | 15 / 33 |
| tests/test_project_cash.py | 02d48c610e87b2a3 | 26 / 49 |
| tests/test_project_returns.py | bcc11ddcc31ebac9 | 23 / 29 |
| tests/test_project_sale_comparison.py | 1ef3245d385c7458 | 16 / 9 |
| tests/test_project_sale_revision.py | 2624c73a35bc8049 | 24 / 7 |
| tests/test_proposal_queue.py | 0dfb5476aec14c09 | 25 / 8 |
| tests/test_recovery_case_check.py | 9ba31e0d73bcaf44 | 16 / 1 |
| tests/test_recovery_case_inventory.py | a8a885fe33638763 | 12 / 4 |
| tests/test_refinance_capacity.py | 5acd331f7670def3 | 28 / 15 |
| tests/test_rental_calendar.py | 8cb6d2ee3bf36967 | 16 / 12 |
| tests/test_rental_checked_lifecycle.py | 42ef7040904a5d44 | 25 / 30 |
| tests/test_rental_noi.py | 5823473d6e76f26f | 19 / 11 |
| tests/test_rental_operations.py | 292d01bcd6701034 | 21 / 8 |
| tests/test_review_proposals.py | 4be12acde9cd49db | 24 / 6 |
| tests/test_sale_costs.py | 8ecda618799d6f64 | 21 / 3 |
| tests/test_sale_recovery.py | a2e122a30e5c8ae3 | 21 / 16 |
| tests/test_sale_sensitivity.py | 89834ad70c5f84e2 | 29 / 18 |
| tests/test_scenario_review.py | 1ef74bb631489321 | 25 / 9 |
| tests/test_scenario_threshold_rehearsal.py | 365c9350ffec9e39 | 25 / 19 |
| tests/test_scheduled_expenses.py | b27600cb8d7a3189 | 41 / 42 |
| tests/test_scoped_profiles.py | 74239a326ae849be | 23 / 14 |
| tests/test_screening.py | a8217759cb0ad477 | 29 / 7 |
| tests/test_settled_lifecycle.py | 092abb59c1e12709 | 35 / 38 |
| tests/test_sheets.py | 272634c6f8e9cbe2 | 27 / 11 |
| tests/test_synthetic_onepager.py | 98a9625007bbe67e | 16 / 3 |
| tests/test_threshold_rehearsal.py | 30884ff04769ba5c | 23 / 16 |
| tests/test_v1_revision.py | 6da4b42fcbd048a5 | 28 / 46 |
| tests/test_verdict_matrix_D212.py | 2bbdafc693e58954 | 8 / 39 |
| tests/test_workbooks.py | 58efdeb4e8f3535f | 33 / 23 |
| tests/test_worksheet_annual_coc.py | a7d42c682351d6a7 | 7 / 2 |
| tests/test_worksheet_annual_comparison.py | a7efa70b94795e75 | 5 / 73 |
| tests/test_worksheet_annual_holding.py | 78b3ae90c71d5d1a | 5 / 49 |
| tests/test_worksheet_annual_sale_without_refi.py | 8a805f8bd3a9686a | 4 / 63 |
| tests/test_worksheet_budget_sensitivities.py | 5f33f83b25f66737 | 10 / 51 |
| tests/test_worksheet_calendar_sensitivities.py | 31eef8c1203cfaf6 | 8 / 31 |
| tests/test_worksheet_case.py | 9e1699e417b87698 | 20 / 41 |
| tests/test_worksheet_cash_revision_D217.py | 194a29053a36b09b | 5 / 63 |
| tests/test_worksheet_combined_citation_orders_D225.py | 42b386fc1069593d | 3 / 18 |
| tests/test_worksheet_construction_sensitivities.py | 652919fe6367dd33 | 10 / 39 |
| tests/test_worksheet_critical_evidence_D219.py | 8a0ba2365e8ea050 | 12 / 30 |
| tests/test_worksheet_critical_evidence_gate_D220.py | df6031db8c25fd54 | 13 / 21 |
| tests/test_worksheet_delivery_D216.py | 35cf78d0235c2c67 | 4 / 16 |
| tests/test_worksheet_delivery_snapshot_D227.py | 8f775a6468a4bc85 | 4 / 23 |
| tests/test_worksheet_dscr_citation_recovery_D221.py | 5a9a9dc8ccbe83b4 | 15 / 62 |
| tests/test_worksheet_exact_cash.py | a0acf2d0583319b4 | 10 / 38 |
| tests/test_worksheet_expense_sensitivities.py | ac660b2ca18a8fee | 9 / 46 |
| tests/test_worksheet_holding_horizon.py | b46b8f57b24c976c | 10 / 43 |
| tests/test_worksheet_horizon_fiscal.py | db319ba71ea9ff43 | 19 / 36 |
| tests/test_worksheet_integrated_transport.py | 5e8dcce11eaf8b36 | 5 / 22 |
| tests/test_worksheet_irr_certificate.py | b8f5b64c0a37045c | 20 / 21 |
| tests/test_worksheet_lorena_annual_route.py | 548c6112aff8b11b | 3 / 10 |
| tests/test_worksheet_lorena_screening.py | a3f7abf534da0f0b | 11 / 8 |
| tests/test_worksheet_operating_sensitivities.py | 97574df9c0b897f6 | 5 / 17 |
| tests/test_worksheet_permanent_sensitivities.py | 43b584c26b0e8762 | 12 / 86 |
| tests/test_worksheet_plan_citation_recovery_D222.py | d198876cdc282c2f | 5 / 9 |
| tests/test_worksheet_pricing_sensitivities.py | 12e845272e1016e0 | 11 / 36 |
| tests/test_worksheet_professional_proposals_D218.py | 4d42633cca92dd0f | 17 / 24 |
| tests/test_worksheet_regulated_rent.py | 253fe2c50a0b7962 | 15 / 20 |
| tests/test_worksheet_reserve_sensitivities.py | ff354dac13e6d164 | 8 / 32 |
| tests/test_worksheet_reverse_citation_recovery_D224.py | 991d7482cf910e3a | 1 / 1 |
| tests/test_worksheet_scenario_program.py | 94780b9242a2a279 | 21 / 17 |
| tests/test_worksheet_sensitivities.py | 642872e3597f0c2a | 5 / 18 |
| tests/test_worksheet_sequential_citation_recovery_D223.py | 08655f570cd1f0e3 | 3 / 1 |
| tests/test_worksheet_settled_output.py | 4613a7a695290e80 | 26 / 43 |
| tests/test_worksheet_tax_sensitivities.py | 43e9f42a982f209f | 11 / 36 |
| tests/xlsx_fixture.py | 2b1c6449a1d5cfc2 | 1 / 71 |
| tools/audit_worksheet_critical_evidence_D219.py | 1e658efb5d9be137 | 13 / 75 |
| tools/capital_miniuw_v1.py | 89f6d470e0ef44d4 | 1 / 3 |
| tools/cash_participation_miniuw_v1.py | 8323c8222c77898a | 1 / 3 |
| tools/check_IRR_interval_T101.py | 3b022072719929ba | 2 / 53 |
| tools/check_IRR_output_T100.py | 0b5ec2f2b507f0ea | 1 / 60 |
| tools/check_IRR_revision_review_T102.py | f11242c6b76b0c55 | 2 / 57 |
| tools/check_annual_return_replay_D24.py | 6a78dec6d4a3dad4 | 2 / 17 |
| tools/check_bank_noi_capacity_order_D36.py | bf1e7f8d31f565f0 | 7 / 35 |
| tools/check_blocking_structure_D06.py | 8491f2d033854b38 | 15 / 57 |
| tools/check_breakeven_occupancy_D72.py | babe1ca8ec3098d1 | 3 / 33 |
| tools/check_capital_coc_replay_D27.py | ddee687a55f72d41 | 3 / 55 |
| tools/check_capital_output_T98.py | 26d7ac7a620e2f05 | 1 / 26 |
| tools/check_cash_participation_T104.py | 03712ab2f3ea26d0 | 3 / 80 |
| tools/check_costed_sale_diagnostics_D67.py | d7f07a3ee1143c37 | 1 / 23 |
| tools/check_cotejo_corrections_D56.py | 1a4cab293540924a | 2 / 41 |
| tools/check_cotejo_diagnostics_D55.py | 26ee62957467200f | 2 / 15 |
| tools/check_cotejo_review_D53.py | 8762791b8ad88e58 | 11 / 103 |
| tools/check_cotejo_revision_D57.py | a9a6dcb7f35436cb | 3 / 42 |
| tools/check_current_cotejo_D59.py | 63e1e6fe470d20f2 | 2 / 17 |
| tools/check_current_publication_D60.py | 5f5485b06b398735 | 3 / 25 |
| tools/check_current_settled_T109.py | 0f0397a047be9da5 | 2 / 57 |
| tools/check_current_structure_D04.py | 308c4553f8e582f3 | 2 / 84 |
| tools/check_debt_sale_replay_D21.py | a29632510918c5a0 | 12 / 214 |
| tools/check_deferred_insurance_T106.py | 411e80d6cd756249 | 2 / 47 |
| tools/check_dependency_structure_D05.py | b7d7abf6e6cc6ea1 | 22 / 119 |
| tools/check_discount_rate_crossover_D35.py | 564a2f5d34eef7bf | 6 / 50 |
| tools/check_discounted_sale_recovery_D34.py | 8a5beb549f4702a2 | 7 / 35 |
| tools/check_discounted_scenario_recovery_D83.py | a3a7e12b8d33819b | 1 / 45 |
| tools/check_discounted_worksheet_sale_D64.py | c984530bd2df49ac | 2 / 7 |
| tools/check_dots_bots_onepage_ROLES01.py | 20f049ab0b80207e | 1 / 27 |
| tools/check_downside_threshold_revision_D58.py | ce5e01a93a77a5ec | 3 / 52 |
| tools/check_equity_tdc_D71.py | 0682a31c66211b8f | 3 / 30 |
| tools/check_first_pilot_D49.py | 3d26c7a3bc1db250 | 3 / 36 |
| tools/check_historical_cotejo_D61.py | 7bbb20a09d575885 | 3 / 29 |
| tools/check_initial_equity_basis_D80.py | 4595fbfeadd074cf | 6 / 46 |
| tools/check_insurance_terminal_T107.py | adf1d58313f0b02c | 2 / 40 |
| tools/check_integral_miniuw_D102.py | f54803a5f73ef328 | 6 / 87 |
| tools/check_integrated_participation_D28.py | 604f99b2eb31ad33 | 8 / 51 |
| tools/check_integrated_replay_D22.py | 9c2e19f95c98ed7f | 1 / 2 |
| tools/check_investor_answers_D77.py | 9cccd50f464bd633 | 6 / 40 |
| tools/check_investor_output_D07.py | 7215b12dbd2535d4 | 12 / 121 |
| tools/check_investor_package_T97.py | 2479187cbdfa0f2b | 1 / 12 |
| tools/check_investor_scenarios_D75.py | 2d2f236c22797323 | 1 / 32 |
| tools/check_joint_noi_capacity_D38.py | 8b8ad2db3673617b | 5 / 25 |
| tools/check_joint_noi_discounted_returns_D41.py | 6e116c23e30a30c0 | 4 / 34 |
| tools/check_joint_noi_investor_returns_D39.py | d49508c20413797b | 5 / 16 |
| tools/check_joint_noi_recovery_prices_D42.py | 67b875542ee40b74 | 4 / 32 |
| tools/check_joint_noi_sale_returns_D40.py | dcf4dbfb5c451c90 | 6 / 22 |
| tools/check_linked_cotejo_D54.py | dfb7ad12e0fea533 | 2 / 29 |
| tools/check_long_output_T99.py | c625d27511050a74 | 1 / 37 |
| tools/check_lorena_criteria_D192.py | c895cde5465da4ea | 2 / 29 |
| tools/check_ltv_capacity_order_D37.py | 252a624b5a03d291 | 4 / 55 |
| tools/check_operating_replay_D20.py | 77cbbb721e9abcf2 | 6 / 67 |
| tools/check_participant_cash_risk_T105.py | 7069fe773a19253e | 3 / 49 |
| tools/check_participant_funding_risk_D29.py | c42b8f6859ff1c84 | 6 / 27 |
| tools/check_participant_joint_exit_D32.py | 3812645d8bff22ec | 5 / 37 |
| tools/check_participant_refinance_variants_D31.py | 17268649b9d3445a | 10 / 38 |
| tools/check_participant_sale_revisions_D30.py | 2508e5dcb9317f51 | 6 / 31 |
| tools/check_pending_investor_answers_D78.py | d94c183266cd6093 | 3 / 27 |
| tools/check_phased_settled_T110.py | 6e635103a011cdf8 | 2 / 54 |
| tools/check_pilot_intake_D191.py | 6ac7f653ec014365 | 17 / 122 |
| tools/check_plan_discount_D112.py | c5d7ca47037ded0f | 4 / 63 |
| tools/check_plan_refinance_request_D109.py | 98ee7ad09b8da0a7 | 3 / 61 |
| tools/check_plan_sale_recovery_D113.py | 048269eca243fd85 | 3 / 50 |
| tools/check_preliminary_pilot_readiness_D189.py | c0d03f8513da6040 | 4 / 33 |
| tools/check_reference_package.py | 85fa024e6718f2ad | 7 / 47 |
| tools/check_refinance_pilot_D50.py | 947f90b4224005b9 | 2 / 26 |
| tools/check_refinance_return_replay_D26.py | 74e734a226302c52 | 4 / 68 |
| tools/check_return_handoff_faults_D25.py | 24b856bdc4f59751 | 3 / 14 |
| tools/check_return_replay_D23.py | 72d61804c742ad9b | 9 / 71 |
| tools/check_sale_cash_recovery_D33.py | e3d170e566cbf8e4 | 7 / 33 |
| tools/check_sale_gap_D85.py | 6d3b43f6a4b07988 | 1 / 14 |
| tools/check_sale_rate_grid_D84.py | bdd692fbab6418f5 | 1 / 34 |
| tools/check_scenario_availability_D104.py | 9fa8e713d3ed5e34 | 3 / 42 |
| tools/check_scenario_package_D52.py | bdac59ddf72f4b7d | 4 / 28 |
| tools/check_scenario_pilot_D51.py | 8511b26d0729f082 | 5 / 38 |
| tools/check_scenario_recovery_D82.py | b22b57d09ff469db | 1 / 18 |
| tools/check_settled_lifecycle_T108.py | acc98d25cdf327c8 | 4 / 94 |
| tools/check_structure_faults.py | ef657ee6d978353d | 0 / 6 |
| tools/check_unified_costed_sale_D65.py | dd4546e3d1714b18 | 1 / 21 |
| tools/check_unified_worksheet_D48.py | 67260d28fd328719 | 12 / 121 |
| tools/check_worksheet_alternatives_D155.py | d4ae23cc0220a0b3 | 8 / 70 |
| tools/check_worksheet_blanks_and_zero_D171.py | c0b4ac28fa2e9459 | 9 / 50 |
| tools/check_worksheet_capacity_case_D118.py | aee7c93999f86441 | 2 / 45 |
| tools/check_worksheet_case_T103.py | f9d408ad9371cc68 | 2 / 60 |
| tools/check_worksheet_commercial_inputs_D141.py | 11994779fd9b173a | 7 / 48 |
| tools/check_worksheet_complete_pilot_D126.py | b1bafd06a0508520 | 3 / 58 |
| tools/check_worksheet_construction_budget_D144.py | 079f3bd848ab0eb8 | 8 / 55 |
| tools/check_worksheet_construction_financing_D146.py | e985e95db46b3988 | 7 / 76 |
| tools/check_worksheet_construction_pdf_D157.py | 25edea1b5d554a20 | 8 / 39 |
| tools/check_worksheet_current_chain_D128.py | c0009bc3ec30a103 | 4 / 58 |
| tools/check_worksheet_debt_yield_D178.py | 633b5e1505e93ab8 | 6 / 57 |
| tools/check_worksheet_definition_screening_D193.py | 220dcb3f775e689d | 19 / 76 |
| tools/check_worksheet_development_inputs_D143.py | fce5f963375f1b2e | 8 / 42 |
| tools/check_worksheet_document_currency_D201.py | 84fcd6762d31f9f4 | 2 / 26 |
| tools/check_worksheet_document_pages_D202.py | a0ae520b27df2db7 | 2 / 20 |
| tools/check_worksheet_documentary_intake.py | 27cc2c663ec74b64 | 2 / 38 |
| tools/check_worksheet_documented_finance_D147.py | c810ffdeefa93a97 | 10 / 55 |
| tools/check_worksheet_downside_pass_only_D196.py | 3c018ac9fac003a1 | 4 / 32 |
| tools/check_worksheet_equity_limit_revision_D129.py | 185ac802bbd0a5c3 | 3 / 37 |
| tools/check_worksheet_equity_tdc_D124.py | 8b0432a664da6512 | 3 / 48 |
| tools/check_worksheet_evidence_color_D160.py | 15af6a3df31c8758 | 6 / 84 |
| tools/check_worksheet_evidence_jpeg_D161.py | 4a562157a9aae80e | 5 / 60 |
| tools/check_worksheet_evidence_oriented_D159.py | 87a31b60622ffcba | 6 / 69 |
| tools/check_worksheet_evidence_pdf_D156.py | 7ff48ff8c81389c8 | 8 / 54 |
| tools/check_worksheet_evidence_progressive_D162.py | 00a6fd949ea37a38 | 4 / 46 |
| tools/check_worksheet_evidence_progressive_crop_D163.py | 8d621d938e0d8dba | 6 / 56 |
| tools/check_worksheet_evidence_progressive_order_D164.py | 57bc2689a91c760a | 5 / 50 |
| tools/check_worksheet_evidence_scan_D158.py | cac1963eacef5d6e | 7 / 68 |
| tools/check_worksheet_exit_D62.py | b108560e49ab3ec4 | 5 / 34 |
| tools/check_worksheet_exit_pricing_D151.py | 82b302e246a25587 | 7 / 69 |
| tools/check_worksheet_florida_tax_D203.py | 27359339841a5147 | 7 / 87 |
| tools/check_worksheet_formula_review_D173.py | a1ad4d69f31c2007 | 7 / 71 |
| tools/check_worksheet_gp_catch_up_D170.py | 8290b78af277ce11 | 4 / 63 |
| tools/check_worksheet_growth_D154.py | e346272bf97d0276 | 9 / 106 |
| tools/check_worksheet_holding_horizon_D266.py | 784817a8c7f76584 | 7 / 162 |
| tools/check_worksheet_horizon_fiscal_D267.py | 5e05145cc1bdbe5b | 11 / 274 |
| tools/check_worksheet_intake_case_D117.py | 0a64eee4c8966978 | 5 / 51 |
| tools/check_worksheet_integrated_screening_D181.py | 9a8c8219ccee713a | 16 / 81 |
| tools/check_worksheet_investor_D74.py | 9003942b4836c68e | 1 / 25 |
| tools/check_worksheet_irr_D122.py | 0eda837dff49c228 | 5 / 49 |
| tools/check_worksheet_irr_certificate_D270.py | 4769f47fe0174391 | 8 / 56 |
| tools/check_worksheet_local_chain_D127.py | d18ee80ecf0c2a84 | 3 / 42 |
| tools/check_worksheet_lorena_screening_D194.py | ccd055462482f15d | 6 / 58 |
| tools/check_worksheet_lp_gp_D168.py | 5841b45fd8f8d7e9 | 8 / 55 |
| tools/check_worksheet_ltv_case_D119.py | ebffd4ced5f99fda | 3 / 52 |
| tools/check_worksheet_market_evidence_D166.py | 31c9cd64f19236cc | 7 / 41 |
| tools/check_worksheet_native_mapping_D139.py | 46e2a672fc1317cc | 8 / 55 |
| tools/check_worksheet_occupancy_D125.py | 079ea5dd60690875 | 3 / 40 |
| tools/check_worksheet_operating_costs_D148.py | b4abfeaed1a54145 | 6 / 54 |
| tools/check_worksheet_participation_D68.py | 8f31ec3d22d30b9b | 1 / 29 |
| tools/check_worksheet_performance_policy_D184.py | b8fcad2b3813f021 | 6 / 104 |
| tools/check_worksheet_permanent_loan_D152.py | 283b1ad4633cfab0 | 7 / 94 |
| tools/check_worksheet_plan_cropped_set_D138.py | 0b5938d3beeeb693 | 8 / 58 |
| tools/check_worksheet_plan_dual_rotation_D137.py | 6321ad469aecfb7f | 9 / 57 |
| tools/check_worksheet_plan_mixed_D132.py | fd2f8f3e2f4c469b | 4 / 42 |
| tools/check_worksheet_plan_overlay_D133.py | 806f4347dc6823bb | 5 / 44 |
| tools/check_worksheet_plan_pdf_D130.py | 2c481c0c4db24a25 | 6 / 55 |
| tools/check_worksheet_plan_rotated_set_D136.py | d4fb521056abd99b | 7 / 56 |
| tools/check_worksheet_plan_rotation_D134.py | 7064ffb86230b157 | 7 / 48 |
| tools/check_worksheet_plan_scan_D131.py | 02b082b637fe53f7 | 3 / 44 |
| tools/check_worksheet_plan_set_D135.py | eda12a0c55417d60 | 5 / 54 |
| tools/check_worksheet_preferred_lp_gp_D169.py | 231591539e120602 | 7 / 109 |
| tools/check_worksheet_preflight_D116.py | cca61135c39f867d | 1 / 20 |
| tools/check_worksheet_preliminary_D185.py | 7f032e193b8aac2a | 9 / 34 |
| tools/check_worksheet_preliminary_finance_D187.py | 93b606ab44e44f28 | 4 / 54 |
| tools/check_worksheet_preliminary_pdf_D206.py | 6deed4797209fab0 | 7 / 67 |
| tools/check_worksheet_preliminary_pilot_D205.py | f6b57a601f467af9 | 3 / 47 |
| tools/check_worksheet_preliminary_stages_D188.py | 47d2ca06a3e9e436 | 5 / 46 |
| tools/check_worksheet_preliminary_tax_D204.py | 97e7e3e4377bb025 | 5 / 70 |
| tools/check_worksheet_preliminary_workbook_D186.py | 689fc1f1c58e7ee2 | 4 / 48 |
| tools/check_worksheet_project_calendar_D145.py | b598eeb09401e223 | 7 / 61 |
| tools/check_worksheet_property_tax_D150.py | 40df7e95708f6241 | 7 / 59 |
| tools/check_worksheet_reconciliation_D179.py | 9b6683fa69cf0800 | 8 / 47 |
| tools/check_worksheet_recovery_page_D44.py | 3f230b9ad7ab3de0 | 4 / 33 |
| tools/check_worksheet_reference_metrics_D121.py | 0205031ca3e7b0dd | 3 / 36 |
| tools/check_worksheet_refinance_D45.py | e74e6be863d1ccdc | 9 / 79 |
| tools/check_worksheet_refinance_costs_D153.py | 8d2a899239fa457a | 7 / 84 |
| tools/check_worksheet_refinance_recovery_D46.py | 3e2f7a4a27761674 | 1 / 13 |
| tools/check_worksheet_regulated_rent_D269.py | d59e353add46eef1 | 7 / 298 |
| tools/check_worksheet_rental_inputs_D140.py | 499375a77a63db51 | 8 / 62 |
| tools/check_worksheet_replacement_reserve_D149.py | 94373750964c1711 | 8 / 66 |
| tools/check_worksheet_return_metrics_D167.py | f49bf7cb694cbc0b | 9 / 86 |
| tools/check_worksheet_revision_audit_D195.py | 8123d4fae9eaed28 | 4 / 27 |
| tools/check_worksheet_sale_costs_D63.py | b45116c41e4b1871 | 3 / 42 |
| tools/check_worksheet_sale_recovery_D43.py | 17623ba29030161d | 8 / 46 |
| tools/check_worksheet_scenario_program_D268.py | 29c4eb434877abe0 | 12 / 337 |
| tools/check_worksheet_scope_D174.py | b610479ef62e7701 | 6 / 41 |
| tools/check_worksheet_screening_pilot_D120.py | 46af4d86b84a5027 | 6 / 64 |
| tools/check_worksheet_settled_T111.py | bf4446c454d18e29 | 2 / 74 |
| tools/check_worksheet_technical_acceptance_D200.py | c260d8f6847ecac4 | 11 / 128 |
| tools/check_worksheet_template_version_D176.py | 0d36527a64e2bce1 | 5 / 38 |
| tools/check_worksheet_utility_inputs_D142.py | 487f6e91fd0ae439 | 7 / 45 |
| tools/check_worksheet_verdict_options_D211.py | 5e6cc37205f504c8 | 5 / 51 |
| tools/check_worksheet_yoc_spread_D123.py | 3728fe15f0a5d1a4 | 2 / 40 |
| tools/check_yoc_spread_D70.py | adced9ccd22f034f | 4 / 48 |
| tools/compare_miniuw_v1.py | 38ba3e3d9b91d27b | 1 / 3 |
| tools/compare_refinance_discount_D111.py | eb9f4b3d5212cd11 | 10 / 67 |
| tools/compare_revised_plan_D110.py | 13d3a20b74bf3a08 | 7 / 54 |
| tools/compare_sale_to_minimum_D114.py | 25676022736434d8 | 6 / 24 |
| tools/compare_sale_uplift_D115.py | 294472fbd214bf33 | 6 / 22 |
| tools/construction_demo_support.py | d6ee1826357d7af1 | 6 / 9 |
| tools/current_settled_miniuw_v1.py | 196fe13712941772 | 1 / 3 |
| tools/deferred_insurance_miniuw_v1.py | 50c7f57d091bde2c | 1 / 3 |
| tools/delayed_exit_combinations_D96.py | bf850bf51b207a16 | 3 / 73 |
| tools/delayed_sale_carry_D93.py | 5604af9eb886382e | 5 / 74 |
| tools/delayed_sale_recovery_D94.py | 327c43df19499fad | 3 / 57 |
| tools/delayed_sale_refinance_reduction_D95.py | 18ec86b2da7b64fa | 3 / 57 |
| tools/demo_bounded_exit_sale.py | 26fced7d10849c07 | 6 / 13 |
| tools/demo_bounded_sale_recovery.py | d4e6fba3792ffb7d | 5 / 11 |
| tools/demo_cash_risk.py | 6628c465f38e4cdb | 1 / 3 |
| tools/demo_closing_cash_returns.py | 6c05e40a69734e3c | 1 / 11 |
| tools/demo_computed_noi_dscr.py | 21edb66a306f7427 | 1 / 6 |
| tools/demo_construction_draws.py | f55013a36a07a411 | 2 / 16 |
| tools/demo_costed_exit_sale.py | 03cadcaa98605fe4 | 4 / 11 |
| tools/demo_current_lifecycle.py | ff9db3a0195918ee | 5 / 9 |
| tools/demo_current_recovery_case.py | 7a400ce3be554426 | 2 / 9 |
| tools/demo_debt_checked_closing_returns.py | 100da551b4da9271 | 1 / 13 |
| tools/demo_documented_threshold_rehearsal.py | 903ced684c4276ca | 1 / 8 |
| tools/demo_evidence_currency.py | affe8305f5aef7f2 | 5 / 17 |
| tools/demo_exit_value_to_sale.py | 597f9ee5eac2026b | 3 / 20 |
| tools/demo_expense_cash_detail.py | efb642ebe7dcdf29 | 2 / 12 |
| tools/demo_expense_checked_lifecycle.py | 50b88392a016eb60 | 2 / 14 |
| tools/demo_hold_sale.py | f8cf43e34a27b5ad | 3 / 39 |
| tools/demo_holding_cash_returns.py | 341167c3380e3de1 | 1 / 12 |
| tools/demo_integrated_project_cash_returns.py | 8e009c77a2b43c46 | 1 / 16 |
| tools/demo_integrated_synthetic_review.py | 6df552431042f73a | 2 / 16 |
| tools/demo_investor_review.py | f93675e3701e14b6 | 3 / 3 |
| tools/demo_lifecycle_returns.py | 023a49e94298bab2 | 5 / 64 |
| tools/demo_operating_cash_returns.py | a474026134e8b372 | 1 / 11 |
| tools/demo_phased_rental.py | 7136f74465959eea | 1 / 17 |
| tools/demo_preopening_cash.py | d8dfd9ca01f991ab | 7 / 13 |
| tools/demo_project_sale_revisions.py | c8fa6a89420a186d | 6 / 28 |
| tools/demo_recovery_case_check.py | 4c9b446a12e7b337 | 4 / 6 |
| tools/demo_recovery_case_inventory.py | 045541b5439c26df | 3 / 5 |
| tools/demo_refinance_capacity.py | f20060a436cefe18 | 2 / 16 |
| tools/demo_rental_checked_lifecycle.py | cdee15ab83cb108c | 1 / 14 |
| tools/demo_residential_noi_chain.py | 57ea254f74e7c132 | 1 / 10 |
| tools/demo_sale_recovery.py | 47a9e47ca4fe4279 | 2 / 5 |
| tools/demo_sale_sensitivity.py | 3a912940fb317217 | 1 / 3 |
| tools/demo_scenario_threshold_rehearsal.py | ecddcb31a5484762 | 1 / 8 |
| tools/demo_staged_operating_debt.py | ab266e3ad81f702a | 3 / 41 |
| tools/demo_synthetic_archive.py | 54347de7ff5f45a7 | 1 / 6 |
| tools/demo_synthetic_calculation.py | 985c9a43baa162d4 | 1 / 5 |
| tools/demo_synthetic_debt_service.py | f558539c73a04ac8 | 1 / 6 |
| tools/demo_synthetic_dependencies.py | 17160f5baaf301f7 | 2 / 3 |
| tools/demo_synthetic_dscr.py | 7074c4a6ca4bd453 | 1 / 7 |
| tools/demo_synthetic_input_sheet.py | a25606d618c18f31 | 1 / 3 |
| tools/demo_synthetic_investor_returns.py | a39f803f84fb7b28 | 3 / 52 |
| tools/demo_synthetic_normalization.py | dca23d87027854ed | 1 / 4 |
| tools/demo_synthetic_operating_noi.py | 058c1ca2d60666ad | 1 / 4 |
| tools/demo_synthetic_review_proposals.py | f1d31e2c1d68c02b | 1 / 9 |
| tools/demo_synthetic_screening.py | 7413f781453c5dfc | 1 / 3 |
| tools/demo_synthetic_sheet.py | 5fc5901fd26deaf8 | 1 / 3 |
| tools/demo_synthetic_workbook.py | 531bfdab248c6ac8 | 1 / 4 |
| tools/discounted_costed_sale_D64.py | 81f7f057af537083 | 2 / 30 |
| tools/expense_lifecycle_demo_support.py | 01b458d45c7a778d | 5 / 22 |
| tools/extended_holding_sale_D99.py | 80b308480e7d754e | 3 / 77 |
| tools/fixed_extended_sale_D100.py | e167c762d495ba5c | 2 / 4 |
| tools/fixed_sale_cash_D90.py | b99d3413c1e46f04 | 4 / 49 |
| tools/fixed_sale_delay_D92.py | a0bd73aaaf4a332a | 7 / 54 |
| tools/fixed_sale_holding_grid_D98.py | a942877ea74e61a8 | 5 / 47 |
| tools/fixed_sale_refinance_limit_D91.py | 643321fa94dd24b2 | 3 / 57 |
| tools/hold_sale_demo_support.py | c9f0f618a169d63c | 7 / 34 |
| tools/holding_cash_funding_boundary_D101.py | 658a9c6dc8a2b0f3 | 3 / 67 |
| tools/holding_cost_sale_recovery_D97.py | 2f605dec0f7a98f0 | 3 / 67 |
| tools/insurance_terminal_miniuw_v1.py | 5d6290f6444c84dd | 1 / 3 |
| tools/investor_miniuw_v1.py | 832bd29520d603c5 | 1 / 3 |
| tools/irr_interval_miniuw_v1.py | 8b4b1edfcccdad63 | 1 / 3 |
| tools/irr_miniuw_v1.py | 719177712b1c0e46 | 1 / 3 |
| tools/irr_review_miniuw_v1.py | 9b01905a43684a97 | 1 / 3 |
| tools/lifecycle_demo_support.py | 36072b52ab4a8f98 | 8 / 21 |
| tools/long_miniuw_v1.py | c586b45088b13de2 | 1 / 3 |
| tools/lorena_screening.py | 01b1ec06309ff8e1 | 2 / 4 |
| tools/miniuw_current_cotejo_D59.py | ce716c0c6c8214fe | 12 / 43 |
| tools/miniuw_linked_cotejo_D54.py | 5e965df4b3061d87 | 3 / 8 |
| tools/miniuw_scenario_package_D52.py | 2ca5758046b66f78 | 10 / 38 |
| tools/miniuw_v1.py | 0fbb233d20194063 | 1 / 3 |
| tools/miniuw_worksheet_v1.py | 9af08fadebd4c23b | 19 / 206 |
| tools/onepage_pending_cases_D79.py | a0615d683cad0ff8 | 8 / 32 |
| tools/participant_cash_risk_miniuw_v1.py | a750601ccddc6f14 | 1 / 3 |
| tools/phased_rental_demo_support.py | b8a5dcab0c7756c3 | 6 / 22 |
| tools/phased_settled_miniuw_v1.py | 4c1dea3147ca47bd | 1 / 3 |
| tools/pilot_workbook_D49.py | f64321df776f6402 | 7 / 49 |
| tools/plan_impact_D106.py | d4ff4236e22ce5f7 | 8 / 40 |
| tools/plan_refinance_D108.py | 3a789dbd81a52221 | 10 / 141 |
| tools/plan_return_D107.py | acda5f1b863c9538 | 18 / 109 |
| tools/plan_schedule_D105.py | 6aa0db2696f9f12f | 5 / 56 |
| tools/preview_lorena_criteria_D192.py | cc31219dd8535a2b | 8 / 66 |
| tools/price_linked_sale_cost_D88.py | ecd723594df9e991 | 3 / 12 |
| tools/reconcile_worksheet_D179.py | 17b2fa388ea75976 | 9 / 183 |
| tools/refinance_cost_recovery_D86.py | 19c72b44c5b51055 | 7 / 51 |
| tools/refinance_sale_combinations_D87.py | 42551e089997af0f | 5 / 82 |
| tools/reissue_investor_reports_D76.py | 7ab7c352c3bb852e | 6 / 47 |
| tools/renewal_miniuw_v1.py | 5f0a13cd90bcba42 | 1 / 3 |
| tools/rental_lifecycle_demo_support.py | bd5cde6a714adffa | 6 / 27 |
| tools/revise_pending_investor_reports_D81.py | 19c9e02c32cef745 | 3 / 19 |
| tools/sale_cost_rate_grid_D89.py | 66e5e946c6e46728 | 2 / 13 |
| tools/scheduled_miniuw_v1.py | 57f00bf482afbce4 | 1 / 3 |
| tools/settled_miniuw_v1.py | cd92f3684d7ac2e8 | 1 / 3 |
| tools/staged_phase_demo_support.py | 98f46cf846638a53 | 3 / 10 |
| tools/worksheet_alternatives_D155.py | 0c9c9c8f4c166471 | 2 / 24 |
| tools/worksheet_annual_coc.py | c00e7e9a293eb77a | 4 / 57 |
| tools/worksheet_annual_comparison.py | 59aa9daecd46e8a1 | 6 / 20 |
| tools/worksheet_annual_crossover_construction.py | fa4f1fdba304a850 | 9 / 49 |
| tools/worksheet_annual_crossover_sale_price.py | 7898d4eabcd98f76 | 6 / 52 |
| tools/worksheet_annual_discount_crossover.py | 83f62b1e960a1f12 | 9 / 33 |
| tools/worksheet_annual_route_report.py | 1e17717daee413aa | 6 / 18 |
| tools/worksheet_calendar_routes_D199.py | b3eaad8f9cedc220 | 8 / 168 |
| tools/worksheet_calendar_support_D256.py | 78ce188364564487 | 2 / 16 |
| tools/worksheet_case_miniuw_v1.py | 92f47b8bded9fd15 | 1 / 3 |
| tools/worksheet_commercial_inputs_D141.py | 0e0587e9be4e25d8 | 3 / 37 |
| tools/worksheet_construction_budget_D144.py | 648bd56ea1715853 | 2 / 40 |
| tools/worksheet_construction_financing_D146.py | e74f512975130719 | 3 / 60 |
| tools/worksheet_construction_support_D257.py | 438ad254c8c17e0d | 2 / 19 |
| tools/worksheet_costed_case_D65.py | ae8273021f01e6c6 | 1 / 3 |
| tools/worksheet_criteria_intake_D194.py | fb0bba7692befc92 | 2 / 27 |
| tools/worksheet_critical_evidence_D220.py | 1852622bba71c2d5 | 1 / 8 |
| tools/worksheet_debt_yield_D178.py | b40ce242d3f8f5a4 | 2 / 20 |
| tools/worksheet_definition_screening_D193.py | 567479d913f01140 | 8 / 91 |
| tools/worksheet_development_inputs_D143.py | ed41ecdc80246c4d | 3 / 33 |
| tools/worksheet_discounted_recovery_D83.py | ec83895f19d169b8 | 3 / 38 |
| tools/worksheet_documentary_intake.py | c87668ba70e5d5b9 | 7 / 31 |
| tools/worksheet_documented_finance_D147.py | 2b69cf6dc95f4a9f | 3 / 18 |
| tools/worksheet_downside_construction_sale.py | 1e2e023f284bb09b | 3 / 12 |
| tools/worksheet_downside_fixed_sale_balance.py | 02edf6bc0bbef120 | 6 / 18 |
| tools/worksheet_downside_fixed_sale_construction.py | f27775e852d9386b | 6 / 32 |
| tools/worksheet_equity_tdc_D124.py | df733f88b3942fb0 | 2 / 12 |
| tools/worksheet_evidence_jpeg_D161.py | 186864aa21aeaf50 | 2 / 4 |
| tools/worksheet_evidence_pdf_D156.py | 79e4a7b0d8bf66c7 | 9 / 51 |
| tools/worksheet_evidence_scan_D158.py | 9307bc14f2f93600 | 5 / 39 |
| tools/worksheet_exact_cash_D263.py | 75f6f011cc5b6165 | 3 / 9 |
| tools/worksheet_exit_pricing_D151.py | f913c36e717bb110 | 2 / 11 |
| tools/worksheet_expense_support_D258.py | 2829ee1bcf01f3b2 | 2 / 14 |
| tools/worksheet_final_metrics_D126.py | a39cabeaa4f9ebbe | 5 / 83 |
| tools/worksheet_florida_tax_D203.py | ec46c12c9acf3067 | 7 / 51 |
| tools/worksheet_formula_review_D173.py | 5ce4434b2f89fad0 | 2 / 32 |
| tools/worksheet_growth_D154.py | debd49bfd36fb616 | 3 / 33 |
| tools/worksheet_holding_horizon_D266.py | bba535fd748b8f3f | 23 / 227 |
| tools/worksheet_horizon_fiscal_D267.py | 9fa14e91ea7bbe67 | 14 / 149 |
| tools/worksheet_intake_D198.py | 4f172e20a26b9d69 | 9 / 24 |
| tools/worksheet_intake_case_D117.py | d2f6cae11ea8f85b | 3 / 30 |
| tools/worksheet_integrated_screening_D181.py | f979fd927f9fe79e | 11 / 132 |
| tools/worksheet_integrated_transport_D264.py | 78f244cfa3a15264 | 1 / 5 |
| tools/worksheet_investor_D74.py | c54dd07e75ecd10c | 3 / 21 |
| tools/worksheet_investor_scenarios_D75.py | 032d657a1b59825a | 5 / 28 |
| tools/worksheet_irr_D122.py | ad52af9c2ccc2727 | 3 / 33 |
| tools/worksheet_irr_certificate_D270.py | 6ca6d34c726d36be | 11 / 89 |
| tools/worksheet_local_sources_D127.py | 793ecd91b9fcc37a | 13 / 46 |
| tools/worksheet_lorena_annual_route.py | 58c05a9e7397281e | 4 / 50 |
| tools/worksheet_lorena_screening.py | 41d23fda702591d2 | 8 / 93 |
| tools/worksheet_market_evidence_D166.py | c50f55d531123aa5 | 4 / 38 |
| tools/worksheet_native_mapping_D139.py | 5c98b6504883a5b4 | 8 / 32 |
| tools/worksheet_occupancy_D125.py | 70d918b6c0cf69d8 | 3 / 24 |
| tools/worksheet_operating_costs_D148.py | 6b9a562b49dbf5f7 | 3 / 18 |
| tools/worksheet_participation_D68.py | 04c7677bc76c8cf3 | 1 / 6 |
| tools/worksheet_performance_policy_D184.py | ed7f7ee000517986 | 6 / 156 |
| tools/worksheet_permanent_loan_D152.py | 9bc7118e687b8e23 | 1 / 22 |
| tools/worksheet_permanent_support_D262.py | c83cf5b5758d2809 | 2 / 23 |
| tools/worksheet_plan_checklist.py | 6cf8d97aa9c1c0af | 4 / 7 |
| tools/worksheet_plan_crop_D138.py | 15fcfd4022c30b71 | 2 / 37 |
| tools/worksheet_plan_discount_D112.py | 40bdf31a4db62424 | 3 / 30 |
| tools/worksheet_plan_mixed_D132.py | e9d23531e368e63f | 5 / 28 |
| tools/worksheet_plan_overlay_D133.py | d5024b835ea9b5b4 | 5 / 24 |
| tools/worksheet_plan_pdf_D130.py | 8a746b7a7d4d4d21 | 3 / 12 |
| tools/worksheet_plan_refinance_D109.py | 4a811ed32f854584 | 2 / 16 |
| tools/worksheet_plan_sale_recovery_D113.py | 3c8e4b4d2f88f082 | 6 / 32 |
| tools/worksheet_plan_scan_D131.py | 5fcf1a3e1f3bdfb7 | 7 / 62 |
| tools/worksheet_plan_set_D135.py | e77d28496955b1e8 | 4 / 48 |
| tools/worksheet_preflight_D116.py | 8574a388bd4c02bc | 1 / 13 |
| tools/worksheet_preliminary_D185.py | 70736bf3d14a1bd8 | 5 / 55 |
| tools/worksheet_preliminary_finance_D187.py | 2787f39c1db37393 | 1 / 66 |
| tools/worksheet_preliminary_pdf_D206.py | bc41348e20f28e3b | 6 / 25 |
| tools/worksheet_preliminary_pilot_D205.py | 514e17cacc1b3dda | 13 / 74 |
| tools/worksheet_preliminary_stages_D188.py | 5121a25b9f891455 | 1 / 17 |
| tools/worksheet_preliminary_workbook_D186.py | 556bb974979e2bc7 | 6 / 125 |
| tools/worksheet_project_calendar_D145.py | 71ad22d26f58aafc | 3 / 35 |
| tools/worksheet_property_tax_D150.py | c8dee78c87a19339 | 1 / 22 |
| tools/worksheet_reference_metrics_D121.py | 893f4dc62baca359 | 1 / 14 |
| tools/worksheet_refinance_costs_D153.py | 92517532c67d1d5d | 2 / 20 |
| tools/worksheet_regulated_rent_D269.py | 9748669a2be3db27 | 6 / 87 |
| tools/worksheet_rental_inputs_D140.py | 94c4b22263e0159e | 9 / 258 |
| tools/worksheet_replacement_reserve_D149.py | c840f5b1c75ec583 | 1 / 12 |
| tools/worksheet_revision_D128.py | 3f390abf5d5afaed | 6 / 28 |
| tools/worksheet_sale_gap_D85.py | 8e447f14535036ec | 3 / 23 |
| tools/worksheet_sale_rate_grid_D84.py | 7e776d236d50ac8c | 4 / 31 |
| tools/worksheet_scenario_program_D268.py | 136333a838f1348c | 13 / 109 |
| tools/worksheet_scenario_recovery_D82.py | c013e3f869931bad | 2 / 25 |
| tools/worksheet_scope_D174.py | b8c469f7684adae4 | 1 / 18 |
| tools/worksheet_screening_pilot_D120.py | f38f16ed6bf3ecae | 7 / 115 |
| tools/worksheet_sensitivities_D253.py | b52e07ef39a42ae5 | 5 / 92 |
| tools/worksheet_settled_miniuw_v1.py | 95ea004ccbff0790 | 1 / 3 |
| tools/worksheet_utility_inputs_D142.py | 6a6ad8794d63f39f | 1 / 14 |
| tools/worksheet_variant_evidence_D268.py | 55c54843a898de3b | 7 / 60 |
| tools/worksheet_yoc_spread_D123.py | 003f1ae5ef18ed87 | 4 / 27 |
