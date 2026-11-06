# Mini-UW — conexiones complementarias y catálogo de 55 campos D10

D10 especifica las conexiones documentales de los **36 campos originales restantes**, mediante doce fichas F09–F20. Junto con las ocho fichas y 19 campos de [D09](MiniUW_Contratos_Financieros_Prioritarios_D09.md), el catálogo reúne **55 campos y 20 fichas**. Esto completa esta descripción de conexiones; no significa que los 55 campos produzcan cálculos integrados ni que el modelo esté financieramente validado.

Se conserva la implementación sintética T111, sus 1.619 pruebas existentes y todos los resultados anteriores. Este hito no añade código, valores, criterios o conexiones financieras activas. Los 54 mapeos semánticos del registro original continúan pendientes. Tampoco sustituye los requerimientos adicionales de [D08](MiniUW_Expediente_y_Conexiones_D08.md): programa, calendario, fuentes GC/banco, caja, contabilidad, reparto personal y aceptación independiente siguen siendo necesarios cuando correspondan.

## Qué conecta cada ficha

| Ficha y celdas originales | Relación que deberá quedar sustentada | Definición o evidencia pendiente |
| --- | --- | --- |
| F09 · C12:C13 | Comparables como evidencia; otros ingresos desde tarifa, cantidad elegible y período. | Fecha y alcance del comparable; unidades, disponibilidad y cobro de otros ingresos. C12 es referencia, no flujo monetario. |
| F10 · C14:C15 | Renta bruta o neta, vacancia/pérdida crediticia y concesiones sin descuentos repetidos. | Bases y orden de cada fracción; qué reducciones incluye ya una renta neta. |
| F11 · C16:C21 | Áreas y rentas comerciales anuales por SF, vacancia, gastos no recuperables e inicio. | Uso real por planos, superficie elegible, alcance NNN, fecha TCO y convención de comienzo. No se presupone que una superficie ausente sea cero. |
| F12 · C25:C28 | Utility allowance por grupo, programa y período, bajo una regla aplicable. | Programa, elegibilidad, fuente vigente y relación entre límite, renta publicada y renta neta. No se adopta una regla legal por aparecer en un documento histórico. |
| F13 · C32:C33 | Asking, precio evaluado y precio soportado separados; costos de compra con base y fecha. | Precio de compra efectivamente evaluado, alcance del porcentaje, objetivos y dominio de precio soportado. La nota histórica de RLV no certifica un RLV ni convierte asking ausente en cero. |
| F14 · C37:C38 | Parking por espacios documentados; site work por monto y alcance declarado. | Conteo, moneda, inclusiones del GC y exclusividad frente al costo vertical. No se deducen espacios desde unidades o superficie. |
| F15 · C39:C41 | Contingencia, soft costs y TI/LC con bases elegibles e identidad de partidas. | Alcance de hard y contingencia, inclusión del developer fee y área comercial. Presupuesto reservado no equivale a pago realizado. |
| F16 · C42, C46:C47 | Soft upfront con ventana y pesos suministrados; duraciones vinculadas a hitos. | Origen de meses 1–3, remanente, calendario y curva de pagos. TCO, fin de obra, estabilización y refi permanecen separados. |
| F17 · C51:C53 | LTC sobre costo elegible, interés por saldo/intervalo y fee sobre una base definida. | Compromiso, draw, tasa, convención, originación, pagos y orden de fondos. No se inventa financiación para cerrar una diferencia. |
| F18 · C61:C62 | Assessment y comparable fiscal con alcance; hipótesis matemática separada de regla fiscal. | Unidades, período, valoración, millage/exenciones si aplican, devengo y pago. Assessment/market no determina por sí solo el coeficiente fiscal. |
| F19 · C73:C74 | Costo de refi sobre la base de préstamo documentada; reserva por unidades elegibles. | Préstamo base, fecha, conteo y representación bruta/neta. Reserva restringida, costo pagado y gasto anual de reposición son conceptos distintos. |
| F20 · C75:C76, C80:C82 | Crecimiento con base y calendario; alternativas como solicitudes de escenarios. | Regla de actualización, drivers, alcance, fuentes y objetivos. El texto de una alternativa no se ejecuta ni genera automáticamente Downside. |

## Qué permiten hoy las interfaces y qué falta

Las interfaces existentes muestran cómo reciben datos algunos perfiles sintéticos. Cada ficha del [registro estructurado](MiniUW_Contratos_Financieros_Complementarios_D10.json) conserva contratos y documentos originales, hash, ubicación, símbolo del código y, cuando existe, un puntero al ejemplo nativo. Esa evidencia delimita el perfil disponible; no activa una traducción desde la hoja.

El productor residencial T21 excluye otros ingresos e ingresos comerciales. T111 exige cero explícito en los ingresos ajenos a la renta objetivo de su perfil actual. Por eso C13 o C16:C21 no se pueden añadir a la salida actual mediante un cambio de etiqueta. Hace falta una conexión compatible y una conciliación de ingresos, gastos y bases de administración. Las bases de vacancia y concesiones también deben ser explícitas: aplicar un segundo descuento a una renta ya neta duplicaría la reducción.

Los pagos de compra, obra y soft de T57 se reciben como eventos fechados. No son un presupuesto generado desde C32:C42. Las referencias algebraicas de asignación no certifican cantidades, inclusiones de GC ni curvas reales de gasto. C46/C47 tampoco producen fechas de apertura o estabilización por sí solos. El comparador T88 exige conservar el horizonte y el inventario fechado de su perfil; no valida cualquier retraso que cambie las fechas.

La deuda de obra T68 recibe el compromiso, los draws y el interés simple por intervalo. Su fee es una fracción del draw bruto; no equivale automáticamente al fee de originación C53. No convierte una tasa anual, capitaliza interés ni calcula el compromiso desde LTC. Esos enlaces necesitan convenciones y fuentes antes de implementarse.

El NOI T20 recibe un piso fiscal F y un coeficiente k para la hipótesis N = A − max(F, kN). Resolver esa ecuación no demuestra que la hipótesis fiscal corresponda al deal, ni obtiene k desde C61. Los costos y reservas de refi tienen un ejemplo independiente en T29; T111 no contiene un refi activo. Las proyecciones por período de T111 son fuentes suministradas, no resultados de aplicar C75/C76 o ejecutar C80:C82.

## Cómo revisar y activar una conexión futura

El [catálogo consolidado](MiniUW_Catalogo_55_Conexiones_D10.csv) conserva los 55 IDs, etiquetas, unidades, celdas y referencias a las fichas D09/D10. La [matriz de este bloque](MiniUW_Conexiones_Complementarias_D10.csv) detalla sus 36 campos. Ninguna de las dos tablas sustituye la matriz original de requisitos.

La [plantilla de revisión](../../templates/financial-link-review-D10-empty.json) contiene doce filas vacías, una por ficha. No es una entrada ejecutable. Para una futura activación deberá identificarse la fuente/version/localización, cantidad elegible, unidad y período, definición financiera, aplicabilidad, clasificación, perfil compatible, caso esperado independiente y autoridad cuando corresponda. No se impone un responsable ficticio ni se rellena un criterio de inversión con un límite bancario.

Cada ficha propone dos comprobaciones condicionales: **24 comprobaciones futuras especificadas, cero ejecutadas como aceptación financiera**. La [verificación documental D10](D10-design-validation.json) comprueba referencias, metadatos, partición de campos, punteros y plantilla vacía. Las comprobaciones técnicas existentes verifican el software sintético, sin acreditar esas decisiones financieras.

Si falta información, una definición contradice su fuente o el perfil no admite la relación, el resultado afectado permanece **PENDING**. Cero explícito se conserva separado de ausencia. No se transforma una banda intermedia en PASS/FAIL ni se modifica una variable para conseguirlo. El retorno agregado del proyecto tampoco se presenta como retorno personal: aún requiere términos y asignaciones del inversor. Datos reales, revisión profesional, criterios y aceptación financiera permanecen pendientes; sin despliegue, decisiones reales ni ampliación a Full UW.
