# Entradas de sensibilidad y ranking con signo — contrato candidato

`schemas/sensitivity-ranking.schema.json` y `references/validate_sensitivity_ranking.py` estructuran ensayos numéricos declarados y sus resultados medidos. Esta referencia no genera perturbaciones ni reejecuta las fórmulas financieras: los valores de cada ensayo son afirmaciones recibidas que requieren evidencia y validación posteriores.

## Comparabilidad de ensayos

El paquete identifica métrica/definición, contexto de análisis, entradas de referencia, drivers permitidos y ensayos esperados. Cada ensayo tiene un contexto de escenario propio dentro del mismo contexto/revisiones del paquete; otros esquemas de reutilización entre corridas requieren su contrato de vigencia. No se acepta sustituir el contexto de un ensayo por Base.

Los campos de cada ensayo se dividen explícitamente en objetivos de la perturbación y campos conservados. El inventario completo debe coincidir con el de referencia. Los objetivos deben pertenecer a los campos permitidos por los drivers declarados; un single-driver admite exactamente un driver, mientras un ensayo conjunto declara varios. Un driver puede alcanzar varios campos, por ejemplo varios tipos de renta: no se equipara driver con una sola celda.

Los campos conservados mantienen cantidad y procedencia exactas. La ausencia de un binding no hereda un valor. Un objetivo cero puede conservar el valor de referencia; no se obliga a producir un efecto para poder registrar el ensayo. Una cantidad con unidad/base/período diferente exige un contrato de conversión separado, no una reinterpretación silenciosa.

Esta partición verifica el paquete recibido; no descubre todas las dependencias económicas de un driver ni prueba que las fórmulas se hayan recalculado. Un resultado conocido no elimina el bloqueo de una entrada requerida sin resolver. El perfil cubre bindings numéricos del vocabulario existente, no todos los datos categóricos de un proyecto.

## Diferencias y ranking

La diferencia es valor del ensayo menos valor de referencia, con signo y sin redondeo. Se exige misma definición de métrica, dimensión, unidad, moneda, rol, base y período. La dirección del ranking se recibe expresamente: mayor diferencia primero o menor diferencia primero. Ninguna se instala como política de la casa; no se utiliza valor absoluto ni se cambia la métrica cuando discrimina poco.

El perfil declara empates con rango denso compartido: los ensayos empatados aparecen en el mismo grupo, sin elegir un ganador por posición. Si todos los deltas son cero, se conserva un único grupo empatado y la métrica original. Un dato faltante o conflicto mantiene sus causas; no se omite el ensayo para obtener un ranking aparentemente completo. Los diagnósticos parciales permanecen separados de un ranking completo.

Los ensayos conjuntos se muestran aparte y no se rankean como drivers individuales. Su resultado procede de su propia afirmación medida, nunca de sumar deltas individuales. No se deducen probabilidades, causalidad o interacciones económicas a partir de esos registros. Una comparación de interacciones requeriría además comprobar que las perturbaciones sean compatibles y equivalentes, fuera de esta referencia.

## Ejemplo y evidencia

El ejemplo sintético usa métrica de referencia 100; ensayos individuales 110, 90 y 100; y un ensayo conjunto 120. El ranking descendente usa deltas +10, 0 y −10. El delta conjunto +20 se conserva aparte: no se reconstruye como suma de los individuales. Estos importes no representan un deal ni un criterio de Lorena.

Se retienen 33 controles sobre signos, dirección, empates, campos conservados, inventarios, métricas comparables, faltantes y separación de ensayos conjuntos. Todas las salidas conservan PENDING y publicación desautorizada, con `financial_reexecution_verified=false`. No acredita ranking aprobado, ejecución del modelo, escenarios requeridos auténticos, riesgo probabilístico o auditoría independiente.
