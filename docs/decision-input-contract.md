# Entrada de Lorena y clasificación del Mini-UW

## Confirmado por el usuario

Lorena entregará una hoja con valores para analizar cada deal, con referencia a los documentos suministrados. El usuario confirmó expresamente: ante faltantes de datos o reglas, dejar el deal pendiente sin PASS/FAIL. Full UW se entregará al final. No se requiere ahora para desarrollar el Mini-UW.

## Interpretación de trabajo y evidencia

La referencia documental para criterios es Estándares §2 (tabla PASS Base / PASS Downside / FAIL Base) y Master v5.1 §5. Se interpreta la hoja de Lorena como criterios de comparación, separados de los resultados que el modelo calcula. El usuario no ha adjuntado aún una hoja nueva completada ni confirmado expresamente si contendrá también resultados calculados; si los incluye, conservarlos como valores aportados, con procedencia y conciliación, separados de resultados propios. No confundir esta interpretación con una aprobación de los umbrales históricos.

El Input Sheet original de 55 campos está vacío y no contiene esas columnas de criterios: Inputs!A2 remite al prompt. Por ello no se puede afirmar que el workbook original ya implementa el contrato de criterios por deal. Diseñar una entrada separada de criterios hasta disponer del documento real; no modificar el original.

## Contrato candidato de criterio

Cada fila debe identificar deal, revisión, métrica/definición, escenario, aplicabilidad, valor explícito y unidad, dirección de comparación y trato de igualdad, período/base, fuente y celda de Lorena, vigencia y alcance de revisión. Los criterios comienzan vacíos por deal; no heredar otro deal ni números del archivo histórico. Un cero explícito es un valor y no equivale a celda vacía. Las condiciones bancarias siguen siendo entradas distintas.

Antes de clasificar, se exige completitud de criterios y escenarios aplicables, cálculos válidos y reglas de agregación definidas. Si falta algo: estado PENDIENTE con dependencias y causa; no convertir en FAIL ni producir un PASS parcial.

## Cuestión abierta: dos estados versus bandas históricas

La intención del usuario es que el modelo determine PASS o FAIL. Los documentos originales describen además HOLD–MORE DD y HOLD–ECONOMICS y tienen una banda entre PASS y FAIL. No hay una regla expresamente aprobada que convierta toda esa banda en FAIL. Mantener pendiente la regla de agregación binaria para ese intervalo; no confundir este pendiente normativo con un FAIL económico demostrado. Tampoco resolver por intuición el caso Base que cumple PASS pero Downside no, sin incumplir una línea FAIL.

PASS/FAIL del screening no es aprobación final de inversión. El avance a Full UW sigue requiriendo PASS vigente y revisión final auténtica. Una hoja con nombre o casilla de aprobación no autentica por sí sola a un aprobador.
