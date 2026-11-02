# Entrada de métricas criterios y conciliación

Lorena entregará una hoja con valores de las métricas para analizar cada deal. Mini-UW conservará esos valores como aportados, con fuente y contexto, y los contrastará con criterios expresos. Un valor aportado, un umbral de inversión, una condición del banco y un resultado calculado por el modelo son registros diferentes, aunque aparezcan juntos en una hoja.

Este diseño desarrolla la entrada M1 y su conexión con M9 después de D02. Define contratos y aceptación futura; no incorpora un nuevo lector operativo ni acredita el formato de una hoja real completada. El catálogo de diez métricas y el Input Sheet original de 55 campos permanecen intactos.

## Recorrido de una hoja hasta la comparación

1. Conservar el archivo original y calcular su hash, sin modificar celdas ni ejecutar contenido.
2. Identificar deal, revisión, formato y perfil explícito de mapeo. El nombre del archivo o del autor no decide autoridad.
3. Registrar cada afirmación con literal, ubicación exacta, rol y metadatos. Conservar duplicados y alternativas hasta conciliarlos.
4. Interpretar números sólo con un perfil explícito de escala, separadores y unidad, manteniendo el literal original.
5. Comprobar definición, período, base, moneda cuando aplique, escenario y aplicabilidad frente al criterio correspondiente.
6. Conciliar afirmaciones y cálculos propios si existen y el alcance lo requiere. Un cálculo propio no se simula atribuyendo autoría al valor recibido.
7. Revisar el inventario requerido completo y generar bloqueos localizados. Sólo después evaluar las condiciones y la regla de agregación aplicable.

La carga de una hoja no es autorización de decisión real. Revisión, vigencia y publicación conservan los controles separados de [D02](review-lifecycle-design.md).

## Cuatro clases de información

| Clase | Qué representa | Qué no permite inferir |
|---|---|---|
| Métrica aportada | Valor que una fuente entrega para un deal y escenario. | Que Mini-UW ejecutó su productor financiero o validó su verdad. |
| Criterio de inversión | Condición expresa de comparación, con umbral, operador e igualdad. | Que el valor de la métrica sea también su umbral. |
| Condición bancaria | Restricción de financiación, como mínimo DSCR o máximo LTV. | Que sea otro criterio de inversión o una aprobación del banco. |
| Entrada subyacente | Renta, costo, fecha u otra afirmación que necesita un productor para generar una métrica. | Que el dato sea ya YoC, IRR o retorno del inversor. |

Los resultados propios se registran aparte con productor, definición, ejecución y dependencias. T13 compara cambios propuestos de métricas y criterios; aún no recalcula el grafo financiero completo desde estas entradas subyacentes.

## Ubicación y mapeo explícitos

Cada afirmación conserva archivo/hash y revisión, hoja/celda o ubicación equivalente, literal original y tipo de celda. El perfil de mapeo vincula esas ubicaciones y etiquetas a un rol e identificador de métrica. No se selecciona una abreviatura por parecido textual ni se interpreta el papel del número por su tamaño.

El perfil debe estar versionado y vinculado al layout que realmente describe. Un cambio de columna, encabezado, fórmula o estructura que afecte la interpretación requiere revalidar ese vínculo. La nueva versión conserva la anterior; no reinterpreta retroactivamente una afirmación sin registrar el cambio.

Una celda puede ser número literal, texto, vacío, fórmula o error. Fórmulas y cachés se conservan como evidencia sin ejecutarlas ni usar el caché como literal. Tampoco se accede a vínculos externos ni se ejecutan macros. No se reconstruye una entrada faltante desde una celda oculta o vecina por intuición.

El XLSX original conserva 55 campos vacíos y no contiene por sí mismo una tabla completa de valores y criterios para este flujo. La plantilla nueva [de entrada vacía](../templates/metric-intake-draft-empty.json) es un contrato interno de diseño; no sustituye el documento de Lorena ni implica que deba cambiar su formato.

## Compatibilidad necesaria

| Dimensión | Comprobación candidata |
|---|---|
| Identidad | Mismo deal, métrica y escenario; revisión y contexto enlazados. |
| Definición | Mismo significado económico y versión aplicable. Un nombre idéntico no basta. |
| Unidad y escala | Fracción, porcentaje, puntos porcentuales, bps y múltiplo se interpretan expresamente. |
| Moneda | Requerida cuando la cantidad sea monetaria; el símbolo $ no elige moneda. |
| Tiempo | Período, fechas, regularidad y cutoff compatibles; mensual no se anualiza tácitamente. |
| Base y alcance | Denominador, capital, TDC, nivel proyecto o LP y alcance financiero compatibles. |
| Aplicabilidad | Exclusión sustentada por regla y evidencia; N/A sin justificación no elimina una obligación. |
| Comparación | Operador, umbral, igualdad y regla de agregación expresos; no inferidos del nombre de la métrica. |

Un literal `5` no se convierte en `0.05` porque parezca un porcentaje habitual. `1,250` necesita convención decimal y de millares. Un spread en bps exige conversión documentada; no es intercambiable con un cambio relativo. La precisión de presentación no define una tolerancia para aceptar discrepancias ni altera una comparación en la frontera.

## Catálogo de métricas y cuestiones de definición

| Identificador conservado | Base de compatibilidad que debe quedar resuelta |
|---|---|
| YoC | NOI estabilizado y TDC all-in, estabilización, alcance y período. |
| spread | YoC y cap de referencia, con distinción entre fracción y bps. |
| equity_recovered | Proceeds distribuibles y base/cutoff de equity. |
| equity_cash_in | Aporte adicional del refi y base/cutoff de equity. |
| breakeven_occupancy | Función de ocupación, ingresos, costos, impuesto y servicio; conflicto bruto/efectivo pendiente. |
| post_refi_CoC | Caja anual disponible y capital remanente definido; denominador cero no produce infinito. |
| equity_TDC | Capital requerido al cutoff y TDC compatibles; distinguir monto y ratio. |
| equity_multiple | Distribuciones/proceeds y aportes brutos, sin perderlos al netear flujos. |
| IRR | Serie de flujos, fechas, dominio, raíces y nivel de retorno; IRR regular y XIRR no se intercambian. |
| asking_relative_to_supported_price | Definición de precio soportado/RLV, objetivos, dominio y comparación con asking; Q3 sigue pendiente. |

El catálogo no es automáticamente el inventario requerido de un deal. Las métricas y escenarios exigibles se declaran expresamente, junto con la aplicabilidad. La plantilla no carga escenarios, definiciones aprobadas, unidades activas, valores ni umbrales por defecto.

## Conciliación sin preferencia automática

Dos afirmaciones para la misma métrica y escenario se conservan con sus ubicaciones y roles. Si difieren, no gana automáticamente la última fila, el archivo más reciente ni el nombre del profesional. La resolución necesita evidencia aplicable, motivo, alcance y una nueva revisión; si afecta un requisito, la comparación permanece PENDIENTE hasta resolverla.

Si además hay un resultado propio, primero se comprueba que ambas cifras representen la misma definición, base y período. Sólo entonces se registra una diferencia exacta. No se adopta una tolerancia por redondeo visual, tamaño del importe o ejemplos anteriores. Una política de tolerancia futura debe quedar identificada y sustentada antes de usarse.

La igualdad bajo un perfil exacto permite registrar concordancia, pero no acredita fuentes independientes ni auditoría financiera. Dos celdas iguales pueden proceder de la misma fórmula o copia. La selección de un valor no borra las afirmaciones alternativas ni vuelve auténtica una fuente declarada.

## Completitud y estados

La plantilla comienza sin inventario requerido definido. Tener diez filas o leer un archivo sin error no prueba completitud. El conjunto se determina por métricas, escenarios, reglas y evidencia de aplicabilidad, no por el número de celdas ocupadas.

Se conserva cero como dato distinto de vacío; su admisión económica sigue dependiendo del dominio de la métrica. Inválido, conflicto, indefinido y no aplicable justificado también son estados distintos. Un escenario requerido sin dato no copia Base; un criterio de otro deal no se hereda.

Ante un dato o regla requerida ausente, discrepancia requerida no resuelta o banda intermedia, el resultado global permanece PENDIENTE. Un incumplimiento conocido conserva su causa individual pero no elimina los otros bloqueos ni produce un dictamen completo. La banda intermedia sigue la decisión del usuario de esperar revisión profesional, sin ajustar variables para forzar PASS.

Cada bloqueo debe identificar afirmación y celda, causa concreta, dependencias afectadas y evidencia que permitiría resolverlo. Por ejemplo, “falta período de CoC en esta fila” es distinto de “CoC incumple”: el primero todavía no permite comparar.

## Correcciones e integración con la revisión

Corregir valor, perfil, criterio, aplicabilidad o definición crea otra revisión y conserva el original. La invalidación sigue las dependencias afectadas; las comparaciones y los precios que usaron un criterio modificado deben recalcularse. El manifiesto del candidato enlaza las versiones exactas utilizadas, conforme a D02.

La completitud de la hoja, la concordancia de cifras y una simulación PASS no autentican revisión ni habilitan publicación. El estado operativo actual continúa PENDIENTE, sin despliegue ni decisiones reales. La puerta final a Full UW y su entrega diferida no cambian.

## Entregables y evidencia de este bloque

El [contrato estructurado](metric-intake-design.json) especifica registros, diez métricas y 14 reglas con documento, línea o campo y hash. [Los 28 casos futuros](metric-intake-acceptance-cases.json) cubren separación de roles, duplicados, escala ambigua, fórmulas/cachés, incompatibilidad temporal, faltantes, aplicabilidad, conciliación y revisiones.

Esos casos están especificados y no ejecutados contra un producto. No se suman a las 273 pruebas técnicas ni reemplazan los 36 casos de aceptación financiera originales. D02 conserva sus 28 casos propios: ambos bloques suman 56 casos de diseño pendientes de implementación. El [estado del diseño](design-evolution-status.json) conserva esta separación.

Este bloque no modifica los documentos originales, las fuentes de definición enlazadas a T13 o la matriz histórica de 398 filas. La interpretación histórica de la hoja como sólo criterios y la antigua cuestión abierta de bandas se leen junto con las instrucciones posteriores del usuario, T12 y este contrato: habrá valores aportados, y las bandas intermedias permanecen PENDIENTES.
