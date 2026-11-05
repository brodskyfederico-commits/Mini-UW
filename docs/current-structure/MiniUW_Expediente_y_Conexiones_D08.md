# Expediente del proyecto y conexiones del Mini UW

El expediente de cada proyecto reúne la hoja de valores, el programa físico, los calendarios, los costos, las condiciones financieras y las reglas aplicables. La hoja original aporta 55 campos; su coincidencia con otra declaración permite cotejar representaciones. Para usar un valor en un cálculo también deben quedar definidos su fuente, unidad, moneda, período, base, aplicabilidad y vínculo con ese cálculo.

El resultado debe explicar cuánto se aporta, cuándo se aporta y qué efectivo se recibe durante operación, refinanciación y venta. El dictamen permanece PENDING cuando falta un dato o una definición del alcance requerido. Una proyección sintética independiente, sustentada por sus propias fuentes completas, puede conservarse como proyección condicional del proyecto.

## Familias de la hoja y cálculos que necesitan sus datos

Se conservan las etiquetas, unidades, notas y condiciones REQUIRED, IF APPLIES y OPTIONAL del original. Una condición IF APPLIES necesita evidencia de aplicabilidad; el cero de una tarifa no prueba ausencia del uso. Un dato OPTIONAL puede seguir siendo necesario para una comparación específica, como asking frente a precio soportado.

| Familia | Celdas originales | Conexión por definir y validar |
|---|---|---|
| Renta residencial y comparables | C7 a C15 | Base de renta, grupos de unidades, disponibilidad, ingresos y pérdidas por período. C12 aporta evidencia de comparables. |
| Ingresos comerciales | C16 a C21 | Uso, áreas, renta NNN, vacancia, no recuperable y fechas de inicio. |
| Utility allowance | C25 a C28 | Grupo y programa aplicables, período y tratamiento documentado. |
| Compra y presupuesto | C32 a C42 | Asking, compra evaluada, bases de costos, cantidades e inclusiones exclusivas. |
| Duraciones | C46 y C47 | Hitos, origen del calendario y curvas de pagos/disponibilidad. |
| Deuda de obra | C51 a C53 | Base elegible, compromiso, draws, interés, fees y aportes por fecha. |
| Gastos, seguros y reservas | C57 a C60 | Unidades/base, gasto devengado, pago, reserva y saldos contables. |
| Impuesto a la propiedad | C61 y C62 | Valoración, comparables, reglas y períodos aplicables al NOI. |
| Refinanciación y venta | C66 a C74 | NOI/valor de sizing y salida, préstamo seleccionado, costos, reservas y liquidación. |
| Crecimientos | C75 y C76 | Base, conceptos afectados, calendario y horizonte. |
| Alternativas solicitadas | C80 a C82 | Escenarios separados con datos y reglas explícitas; el texto se conserva como solicitud. |

La [matriz de 55 conexiones](MiniUW_Conexiones_55_campos_D08.csv) identifica para cada campo su ubicación original, consumidores documentados, contratos candidatos, fuentes complementarias y preguntas de retorno relacionadas. Es un mapa conservador de conexiones propuestas; no constituye un grafo de ejecución o invalidación automática. Sus 55 vínculos financieros permanecen sin activar en este refinamiento. Los 54 mapeos globales abiertos del expediente anterior conservan su estado.

## Información complementaria para cada proyecto

Los 15 conjuntos siguientes describen registros que deben estar disponibles cuando el cálculo o comparación los requiere. Un conjunto puede apoyarse en varios documentos, y un documento puede sustentar varios conjuntos; no son 15 archivos obligatorios ni 15 nuevas variables económicas.

| Conjuntos | Información que resuelven | Consecuencia si falta o contradice otra fuente |
|---|---|---|
| S01 Programa físico y S02 calendario | Unit types, conteos, áreas, parking, disponibilidad y fechas de compra, obra, TCO, estabilización, refi y venta. | Una tarifa o duración aislada no permite construir cantidades, hitos o flujos. |
| S03 presupuesto y S04 deuda de obra | Partidas, inclusiones, compra evaluada, base elegible, draws, fees, capitalización, pagos y deuda heredada. | Impedir costos duplicados, draws supuestos o deuda contada como nuevo equity al cambiar de fase. |
| S05 operación y S11 reglas oficiales | Devengo, cobros, pagos, pólizas, saldos, reservas e información oficial aplicable. | Mantener pendientes las reglas o importes dependientes; conservar evidencia de cada afirmación. |
| S06 refinanciación y S07 venta | Condiciones, capacidad, préstamo seleccionado, financiación efectiva, payoffs, costos y caja del cierre. | Una capacidad bancaria o precio bruto no acredita dinero distribuible al inversor. |
| S08 atribución y S09 capital | Aportes/cobros por participante, términos de reparto, capital con fecha, equity retenido y base anual de CoC. | Retorno personal, capital o CoC permanecen pendientes según el dato o definición ausente. |
| S10 criterios y S12 escenarios | Métricas, operadores, límites, aplicabilidad, hipótesis y objetivos de precio expresos. | No completar umbrales desde condiciones bancarias, copiar Base o ajustar variables para lograr PASS. |
| S13 procedencia y S14 normalización | Originales, localizadores, hashes, revisión, vigencia, moneda, unidades, períodos y bases. | Una coincidencia no resuelve fuente vencida, versión incompatible o significado financiero ambiguo. |
| S15 aceptación | Casos y resultados esperados independientes, conciliaciones, informe y revisión pertinente. | Las pruebas técnicas conservan su alcance; la aceptación financiera exige evidencia propia. |

El [registro de fuentes complementarias](MiniUW_Fuentes_Complementarias_D08.csv) detalla los datos, módulos afectados y responsabilidades funcionales de Dots y bots. Los contratos originales de [entradas](../model-input-evidence.md), [presupuesto y calendario](../model-budget-schedule.md), [financiación](../model-construction-finance.md), [refinanciación](../model-refinance-contract.md) y [tenencia y retornos](../model-hold-exit-returns.md) conservan sus definiciones y pendientes.

## Condiciones para usar un dato y emitir una comparación

La recepción conserva original e identidad. El cotejo verifica la representación de la hoja y la declaración. La normalización y el vínculo financiero requieren evidencia de unidad, moneda, período, base y aplicabilidad. La proyección exige un perfil soportado y sus fuentes actuales y conciliadas. La comparación requiere además métricas propias y criterios aplicables expresos; la revisión y autorización de un uso real tienen una puerta separada.

Los límites LTC, LTV y DSCR de la financiación permanecen separados de los diez criterios de inversión que se inicializan vacíos por deal. Una fuente o regla ausente, un conflicto o una banda intermedia conserva PENDING. Un PASS de comparación tampoco autoriza por sí solo una inversión o el pase al Full UW. Se mantienen los [contratos de decisión](../model-decision-audit.md) y las [responsabilidades de Dots y bots](../MiniUW_v1_Dots_y_Bots.md).

Cuando una fuente cambia, la revisión debe identificar los cálculos y comparaciones dependientes y conservar las versiones anteriores. Una cifra anterior sólo puede mostrarse con su alcance y versión históricos. La coincidencia de la hoja no restaura una cifra retirada por una fuente vencida.

## Historia de retorno que debe recibir el inversor

La salida relaciona aportes iniciales y adicionales con fechas; cobros de operación y refinanciación; cash-in requerido; cobro neto de venta; aportes y cobros brutos; resultado neto de caja; Equity Multiple; intervalos y condiciones de TIR; caja anual y riesgos. Explica por separado el capital aún invertido, el valor de equity retenido y la base de CoC cuando estén documentados.

La [matriz de 23 preguntas de retorno](MiniUW_Entradas_a_Retornos_D08.csv) conecta cada salida con sus registros de soporte y la ubicación observada en la evidencia sintética T111. Los movimientos se mantienen brutos y fechados. El déficit de caja al horizonte se distingue del stock de capital y de una pérdida económica final. Una referencia por 10 aportados al proyecto conserva su base explícita; el retorno personal requiere términos de atribución aplicables.

El informe de decisión conserva una sola página. Los registros completos de fuentes, cálculos y pendientes permanecen en la evidencia interna. El [ejemplo sintético existente](../review/miniuw-v1-worksheet-settled-matched-example/MiniUW_Resumen.pdf) mantiene su condición PENDING y sus límites.

## Alcance del refinamiento y aceptación pendiente

Este contrato detalla conexiones del diseño estructural I01, cuyos ocho entregables conservan su cierre definido. Añade un inventario de información por deal y ocho situaciones de aceptación especificadas en el [registro completo](MiniUW_Expediente_y_Conexiones_D08.json). Esas situaciones nuevas todavía no son pruebas de aceptación financiera ejecutadas.

Se conservan la implementación T111, sus casos y las 1.619 pruebas técnicas existentes. Este refinamiento documental incorpora cero componentes de producto, cero criterios y cero vínculos financieros activos nuevos. Las fuentes y definiciones que faltan continúan pendientes; no se solicita ahora información a Lorena ni se habilitan decisiones reales o despliegue. La ampliación de condominios y presale permanece para Full UW.
