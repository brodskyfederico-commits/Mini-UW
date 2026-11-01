# Trazabilidad de contenido y dependencias — contrato candidato

Se amplía la referencia de revisiones con `schemas/calculation-lineage.schema.json` y `references/validate_calculation_lineage.py`. El contrato enlaza artefactos de evidencia literal, entradas normalizadas, definiciones, criterios, reglas y resultados candidatos. La referencia no ejecuta sus fórmulas financieras.

## Registro explícito

Cada artefacto tiene ID, revisión, tipo, ámbito de escenario, estado de disponibilidad, contenido y digest SHA-256. El digest cubre todos esos campos excepto el propio digest. Un resultado declara la definición que utiliza y cada slot de dependencia con su artefacto, tipo y permiso de uso compartido. Las entradas normalizadas y los criterios son específicos del escenario; las fuentes literales y definiciones pueden compartirse mediante vínculos expresos. Compartir una definición no acredita que sea aplicable o aprobada.

Se comprueba la existencia de los vínculos, sus tipos y escenarios, la unicidad de IDs/slots y que cada resultado tenga un contrato. No se resuelven dependencias por nombre, posición, fecha o “último disponible”. Un ciclo se rechaza: el bloque financiero circular requiere una definición y un método separados; cambiar un grafo no demuestra que converja.

El registro de slots es declarado, no descubierto del futuro motor. Si el autor omite una dependencia económica desde el inicio, este contrato no puede deducirla. La revisión de completitud de fórmulas y dependencias reales sigue abierta.

## Captura y vigencia

La captura conserva el contexto de deal, escenario de captura, corrida y revisiones; incluye el cierre transitivo de dependencias. Por artefacto guarda revisión y digest de contenido; por cálculo, también digest de su contrato. Por eso cambiar el contenido sin cambiar la etiqueta de revisión, quitar un slot o modificar una definición vuelve obsoleta una captura anterior.

La referencia usa una serialización JSON local determinista: claves ordenadas, UTF-8, enteros/booleanos/textos/null y orden de arrays conservado. Rechaza floats y valores no finitos; no introduce redondeo financiero. Esta serialización no se presenta como un estándar de canonicalización interoperable. Su uso futuro entre lenguajes requiere un contrato y casos de compatibilidad específicos.

Un digest prueba correspondencia de contenido dentro de esta referencia, no identidad, autoridad o autenticidad del documento. Si un payload contiene un hash o una cita de un archivo externo, sigue siendo una afirmación: su cotejo requiere el lector de evidencia correspondiente. Rehacer un digest no hace auténtica una revisión humana. Tampoco se comprueba que un resultado numérico sea correcto sólo porque tenga procedencia.

## Bloqueos y resultados

Faltantes, conflictos, inválidos, indefinidos y no aplicables sin tratamiento del cálculo conservan su estado y payload original. Una salida declarada conocida no elimina el bloqueo de un ancestro. Un cambio de criterio invalida las comparaciones dependientes; puede conservar una caja cuyo contrato explícito sea independiente. Cambios de una fuente compartida afectan a los escenarios que la referencian; no a cualquier escenario por parecido de nombres.

Los estados son `current_reference`, `stale_reference` o `blocked`. Incluso el primero conserva decisión PENDING y publicación desautorizada. No implica completitud del deal, validación económica, persistencia inmutable o aprobación experta. Los controles son en memoria: la vigencia puede cambiar después de comprobarla; autenticación y registro atómico siguen siendo requisitos del futuro producto.

La evidencia retenida contiene 48 controles sintéticos, incluidos cambios de contenido con igual revisión, fuentes compartidas, criterios aislados, bloqueos transitivos, contexto, digest alterado, ciclos y referencias cruzadas de escenario. No modifica los valores reales pendientes ni el PDF profesional R02.
