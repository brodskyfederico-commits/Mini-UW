# Mini-UW: faltantes, bloqueos y retiro de cifras D06

Este documento distingue tres resultados del recorrido actual: entrada rechazada, proyección sintética retirada y proyección sintética calculada con decisión PENDING. Usa doce comprobaciones sobre copias en memoria del expediente T95. No introduce fórmulas, umbrales, parámetros financieros ni agentes nuevos.

Complementa el [mapa de dependencias D05](MiniUW_Dependencias_D05.md) y el [cruce de los 55 campos D04](MiniUW_55_campos_D04.csv). Cada comprobación conserva el localizador exacto del cambio, los bloqueos obtenidos y la huella del resultado en el [JSON D06](MiniUW_Bloqueos_D06.json); el [CSV](MiniUW_Bloqueos_D06.csv) permite revisar las doce filas juntas.

## Tres puertas distintas

| Puerta | Qué comprueba | Qué puede salir | Qué sigue pendiente |
| --- | --- | --- | --- |
| A. Admisión técnica de la entrada | Esquema, identidad sintética, inventarios, tipos y duplicados | Entrada aceptada para validación o error de contrato sin corrida financiera | La admisión no valida fuentes ni reglas financieras |
| B. Proyección actual | Fuentes complementarias, vínculos, cálculo, continuidad y vigencia de todo el recorrido T94 | Proyección condicional completa o retiro conjunto de historia de retorno actual, totales actuales y puntos métricos | Los cálculos de ramas y su evidencia pueden conservarse para diagnóstico; no sustituyen la vista actual |
| C. Decisión y entrega autorizada | Campos originales, métricas/criterios aplicables, revisión auténtica y autorizaciones | En este entorno, siempre PENDING y sin publicación financiera autorizada | Datos reales, definiciones, mapeos, revisión y aceptación financiera siguen abiertos |

El caso base puede calcular desde fuentes complementarias sintéticas completas aunque 54 campos originales y los diez criterios conserven sus pendientes. Esto permite comprobar el mecanismo sin certificar que la hoja de Lorena ya esté adaptada. El conflicto entre un campo original y su fuente vinculada bloquea la proyección antes de ejecutar cálculos. Un dato requerido ausente dentro del recorrido detiene ese recorrido en el productor afectado.

Un PDF de diagnóstico de una página puede mostrar PENDING y cifras retiradas. Generarlo no equivale a entregar un dictamen real ni autorizar inversión, publicación o Full UW. La entrada inválida de D06-11 se rechaza sin producir una corrida ni PDF.

## Matriz de comportamiento observado

Las operaciones se aplican al [expediente sintético base preservado](../../templates/miniuw-v1-policy-renewal-case.json). Ninguna prueba renueva registros de evidencia, arregla importes o escribe la entrada original.

| Caso | Cambio o situación comprobada | Puerta y resultado | Qué exige revisar para una nueva corrida |
| --- | --- | --- | --- |
| D06-01 | Base original: una vinculación sintética de 55 campos, 54 pendientes y diez criterios sin fuente | B calcula; C conserva PENDING. Un punto métrico calculado: EM; TIR conserva intervalos, sin punto elegido | Completar mapeos, datos y reglas aplicables sin convertir el cálculo de prueba en aprobación |
| D06-02 | `INPUT_C7` contradice la base de renta vinculada | B bloquea antes del primer productor; no elige una de las dos versiones | Resolver la discrepancia con evidencia y revisión explícita; conservar ambas afirmaciones |
| D06-03 | Principal pagado del primer período operativo pasa a `null` | El productor de caja queda `blocked`; el recorrido no llega a tenencia. La vista completa queda PENDING | Aportar el valor requerido y sus vínculos; ausencia no es pago cero |
| D06-04 | La evidencia de póliza vence exactamente en el instante UTC de evaluación | B retira cifras actuales aunque la póliza todavía pueda calcularse | Evidencia vigente aplicable al corte; no prolongar fechas automáticamente |
| D06-05 | La revisión declarada de esa evidencia está `pending` | B retira cifras actuales; una declaración sintética pendiente no es aceptación | Resolver el estado con evidencia. `accepted_synthetic` tampoco acredita aprobación profesional real |
| D06-06 | La evidencia declara otra fuente como sustituta | B retira cifras actuales; no mantiene una fuente sustituida como actual | Aportar y vincular la nueva revisión aplicable; no seleccionar una fuente por conveniencia |
| D06-07 | Una prima pasa a `null` | T93 no exporta totales calculados de pólizas; T94 retira cifras actuales | Aportar prima y fuente; no convertir ausencia en cero ni tomar la prima de otro período |
| D06-08 | Cuotas de la primera póliza cambian de 5/5 a 6/4, con el mismo total 10 | T93 bloquea por diferencias en ambos grupos agregados; T94 retira cifras | Conciliar cada cuota, fecha y grupo. El total general no compensa diferencias entre grupos |
| D06-09 | Se agrega un salto de línea a los bytes de la póliza sin cambiar sus valores JSON | El cálculo diagnóstico de pólizas conserva totales; B retira la vista actual por inventario de huellas incompatible | Revisar el binding de la fuente exacta y aportar una revisión explícita; dinero idéntico no autentica bytes nuevos |
| D06-10 | Vence evidencia del calendario del padre T91, conservando el registro exterior | T91 bloquea; T94 retira todas las cifras actuales | Resolver la evidencia del padre y los vínculos que correspondan; el registro exterior no suple esa vigencia |
| D06-11 | Clave `schema` duplicada en el JSON exterior | A rechaza el contrato; sin resultado financiero ni PDF | Entregar una entrada no ambigua; no escoger automáticamente la primera o última clave |
| D06-12 | Se solicita otro escenario sin un recorrido configurado compatible | B bloquea antes del primer productor | Declarar fuentes y configuración compatibles; no copiar Base a Downside automáticamente |

El resultado es una proyección condicional con decisión pendiente, diez retiros de cifras actuales y un rechazo de entrada. Cada retiro comprobado conserva nulos los totales actuales de calendarios y pólizas y los valores puntuales de las métricas; las comparaciones y la decisión operacional continúan PENDING.

Las pruebas de cambio no actualizan hashes ni registros de los padres. Por eso algunas filas producen, además del bloqueo primario exigido, incidencias de bindings o inventarios desactualizados. Se conservan todas en `observations/i/blockers`. La matriz demuestra contención y detección del motivo indicado; no pretende aislar un único error ni probar todos los fallos financieros posibles.

## Qué verá el informe y qué conservará la evidencia

Se reproducen tres PDFs en memoria: caso base, fuente de póliza vencida y cambio de bytes con dinero idéntico. Se comprueban una página, el texto PENDIENTE, todas las frases del manifiesto y cuatro cifras de caja del caso base: aportes 1.400, cobros 778, resultado −622 y venta 578. Las cuatro aparecen en el PDF base y están ausentes en los dos PDFs bloqueados. No se crea otro entregable externo.

El JSON interno conserva bloqueos, etapas con su estado, huellas de fuentes/resultados y evidencia de calendarios/pólizas. Una etapa registrada puede ser la etapa que falló; su presencia no acredita que terminó correctamente. En D06-03 se verifica expresamente que la última etapa es caja operativa bloqueada y que tenencia no se ejecutó.

En D06-09 los totales diagnósticos de pólizas pueden calcularse, pero los totales actuales siguen retirados. En D06-07 el cálculo diagnóstico de pólizas tampoco tiene totales exportables. Esta distinción evita publicar una rama calculada como si fuera el resultado actual del proyecto.

Después de las pruebas se reproduce el caso base sin cambios y se exige el mismo resultado y PDF. Esta comprobación demuestra que las pruebas no alteraron ese expediente; no es una restauración de servicios, una base de datos o una aplicación histórica.

## Responsabilidad funcional para los Dots y bots

Estas responsabilidades se enlazan con los [contratos vigentes](../MiniUW_v1_Dots_y_Bots.md). Los nombres son roles funcionales del diseño; D06 no instancia agentes ni conecta servicios.

| Rol | Entrada que revisa | Salida/bloqueo que debe respetar |
| --- | --- | --- |
| B01/B02, coordinación y recepción | Caso exacto, versión y esquema | Error de entrada no se transforma en un caso calculado; conservar identificación y origen |
| B04, Input Sheet | Catálogo, valor, localizador y base de mapeo | Campo pendiente separado de conflicto; no declarar cubiertos los 54 mapeos pendientes |
| B12, guardián | Fuentes, vínculos, vigencia y estado de la cadena | Puertas A/B/C separadas; retirar la vista actual completa ante un bloqueo del recorrido |
| B13, motor | Fuentes tipadas y entradas de cada productor | Ausencia y conflicto detienen el cálculo afectado; nunca completar para obtener PASS |
| B14, juez | Métrica, regla, escenario y evidencia aplicable | PENDING ante faltantes/bandas; cálculo compatible no es autorización de inversión |
| B15, informe | Resultado actual reproducido y manifiesto | Mostrar pendientes; no sustituir cifras retiradas por históricos o ceros |
| B16/B17, comprobación y pruebas | Entrada, resultado, PDF y versión de código | Verificación técnica reproducible; no presentarla como auditoría financiera independiente |

## Requisitos, evidencia y límites

| Requisito vigente y ubicación | Definición aplicada | Evidencia de esta ampliación | Estado y pendiente |
| --- | --- | --- | --- |
| [REQ-04](../requirements-conflicts.md), fila de requisitos actuales | Faltantes/conflictos bloquean lo afectado; cero y ausencia se distinguen | D06-02/03/07, bloqueo primario y estado de caja/póliza | Comprobado en estos casos; no completa los mapeos originales ni todas las fórmulas |
| REQ-05 y REQ-07, mismas filas | Preservar fuentes, dependencia de versiones y snapshot de entrada | D06-09 y reproducción final del base; SHA de cada entrada de prueba | Comprobado en memoria; concurrencia y publicación de producción no se validan aquí |
| REQ-06, misma tabla | Escenarios explícitos, sin copia automática de Base | D06-12, sin etapa financiera ejecutada | Escenario adicional pendiente de configuración compatible; no se adopta un shock |
| REQ-08, misma tabla | Separar evidencia, cálculo, comparación y PDF | Tres puertas, estados métricos, bloqueos y tres PDFs reproducidos | Comprobado técnicamente para el perfil T95; no autentica originales |
| [T46–T47](../technical-implementation-T46-T47.md), vigencia | Corte expreso; `valid_until` excluyente, revisión y sustitución explícitas | D06-04/05/06/10; funciones y líneas en `function_locations` | Declaraciones sintéticas; autoridad y revisión real pendientes |
| [REQ-02 y REQ-09](../requirements-conflicts.md), filas de requisitos | Una página externa; PASS no autoriza por sí solo inversión o Full UW | PDFs de una página; puertas de publicación/despliegue/decisión en falso | No hay aprobación o entrega financiera real |

El [registro D06](D06-structural-validation.json) distingue doce comprobaciones de comportamiento y cinco intentos de alterar su evidencia —PASS inventado, cifras bloqueadas expuestas, fila ausente, localizador falso y despliegue indebidamente habilitado—. No se suman al registro de 1.351 pruebas unitarias ni se confunden con los siete controles D05 o los ocho defectos I01.

Continúan abiertos los 54 mapeos semánticos runtime, la hoja real completa de Lorena, las definiciones/reglas aplicables, ocho métricas sin punto calculado, los datos de capital/equity/CoC, la asignación personal y la aceptación financiera. Las bandas conservan PENDING por decisión del usuario. La refinanciación intermedia conserva su ruta separada. No hay despliegue, decisiones reales, contacto externo o ampliación a Full UW.

## Reproducir

Con las dependencias de `requirements-reference.txt` ya instaladas, desde la raíz del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/check_blocking_structure_D06.py
```

El control lee el caso, aplica las operaciones declaradas en memoria y reproduce las salidas. No escribe archivos ni consulta servicios. `--emit-snapshot` y `--emit-record` imprimen candidatos a stdout para una revisión explícita. El comando normal exige coincidencia exacta con JSON, CSV y registro conservados; fija quince hashes de archivos, incluida la fuente del caso.
