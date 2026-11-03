# T88 y T89 Comparación de revisiones del Mini-UW v1

## T88 Dos expedientes completos y cambios explícitos

El comparador recibe referencia, candidata y una especificación con ID sintético, hashes exactos de ambas entradas y base explícita de comparación. Cada expediente se reconstruye con T85. No crea la candidata, copia parámetros o criterios, renueva evidencia ni modifica las fuentes. Los documentos adjuntos siguen siendo evidencia; ninguna instrucción histórica activa reglas o proveedores.

Exige mismo caso, revisión candidata posterior, mismo perfil, contexto económico (deal, escenario y versión de definiciones), mismo instante UTC y escenarios requeridos. Cada run_id puede identificar una ejecución diferente; el motor anterior también exige concordancia interna de cada expediente. Un hash distinto o base ausente bloquea la comparación cuantitativa. Los expedientes y sus bloqueos se conservan.

Enumera diferencias exactas mediante JSON Pointer, separando presencia de null, cero, texto y número; los racionales se conservan como declaraciones completas. Incluye cambios en fuentes, criterios, vigencia y metadatos. Los cambios de arreglos conservan sus posiciones, sin adivinar equivalencias por nombres. El inventario tiene límite explícito de 4.096 diferencias y 128 niveles; nunca se trunca. No atribuye causalidad a una variable cuando cambian varias.

Sólo compara cifras si las dos proyecciones están actuales bajo sus registros declarados y coinciden moneda, horizonte de caja e inventario/identidad/fecha/tipo de eventos. Calcula candidata menos referencia para aportes brutos, cobros, resultado de caja, EM y cada evento. Si cambia la fecha o clasificación de un evento, retira todas las diferencias numéricas y conserva ambas historias. Una revisión vencida no aporta cifras históricas como actuales. La incompletitud financiera y del formulario conserva la decisión PENDING aunque exista comparación matemática condicionada.

Cada historia conserva su normalización y su base. Las diferencias normalizadas sólo se calculan cuando coinciden base, referencia, eventos/base declarada y factor; dos bases diferentes no se presentan como la misma inversión. Conserva todas las raíces e intervalos IRR de ambos casos, sin elegir punto, restar intervalos o afirmar mejora porcentual. Capital, CoC, equity retenido y retorno personal mantienen los pendientes del productor.

## T89 Recuperación y registro interno

El paquete portable contiene los bytes UTF-8 exactos de ambas entradas y especificación, versiones del motor/definición, resultado y hash. Recuperar exige inventario/esquema exactos, máximo de 48 MiB por paquete y reproducción completa con las mismas versiones. Recalcular hashes de un resultado alterado no sustituye la reproducción. Whitespace diferente conserva identidad de bytes distinta aunque la economía sea igual.

Una orden local genera cuatro archivos: comparison.json, comparison-evidence.json, review.txt y package.json. El texto interno muestra las cifras comparables o su retiro, ambos conjuntos de bloqueos y todas las diferencias de entrada. No agrega un PDF externo; el comando v1 original sigue produciendo una página por expediente. El registro no escoge un caso ganador, no recomienda invertir y no autoriza publicar o admitir a Full UW.

Cada artefacto tiene un límite de 64 MiB. La carpeta se materializa completa desde un temporal hermano. Reintentos idénticos verifican bytes e inventario; salidas distintas/incompletas, enlaces simbólicos y artefactos alterados se rechazan. El audit reejecuta fuentes y vuelve a construir los cuatro archivos. Este mecanismo local no es publicación concurrente productiva, autenticación, auditoría financiera independiente o recuperación de toda la VPS.

## Alcance pendiente

El ejemplo de revisión suministrada cambia proceeds de venta de 400 a 500 y declara nuevas huellas sintéticas de evidencia compatibles: cobros 778 a 878, resultado −622 a −522 y EM 389/700 a 439/700. No se modifica el aporte 1.400 ni se presupone que ese precio sea alcanzable; la candidata es un experimento explícito. Sin nuevos hashes de evidencia, su proyección actual y todos los deltas permanecen pendientes.

Comparaciones entre escenarios/horizontes diferentes, autoridad real de fuentes, variaciones de mercado, condiciones personales de reparto, integración de refi en esta ruta y validación financiera completa siguen pendientes. Los 55 campos, diez criterios vacíos y reglas de bandas permanecen sin cambios. Sin despliegue, agentes externos o decisiones reales.
