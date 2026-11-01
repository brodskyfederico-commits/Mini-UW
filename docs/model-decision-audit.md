# M9 — Comparación, decisión, auditoría y revisión

Estado: especificación candidata. No implementa autenticación, publicación financiera ni aprobación real. La revisión del profesional y el ingreso de valores de Lorena no se simulan. Producción continúa pausada.

## Contratos

Fuentes: Master §§5–7; Estándares §2 y política 17; Manual físico pp.17–18/28–29/39/50–53; D1 p.1; instrucciones actuales sobre hoja de Lorena, PDF único y estado PENDIENTE. La autoridad actual se distingue de las transcripciones históricas.

| ID | Salida | Fuente y pendiente |
|---|---|---|
| M9-01 | Paquete vigente y completo | Traspaso §§6–7; C1/C2 Manual pp.17–18. Datos, aplicabilidad, fuentes, reglas y escenarios requeridos deben estar completos; sin dictamen parcial ante bloqueos. |
| M9-02 | Criterios de Lorena por deal | Master §5/Estándares §2; instrucción actual. Valores expresos, definición/unidad/período/escenario, operador, igualdad y revisión separados de términos bancarios. No heredar umbrales. |
| M9-03 | Comparación de cada métrica | Estándares §2; traspaso §3. Comparar valor válido sin redondeo decisorio; preservar no aplicable justificado, indefinido, faltante y conflicto como estados diferentes. |
| M9-04 | Bandas y agregación | Master §6/política 17; confirmaciones del usuario. El objetivo binario no resuelve la banda entre PASS y FAIL histórica. Agregación y prioridades requieren regla explícita; si falta, PENDIENTE. |
| M9-05 | Invalidación y reutilización | Traspaso §§6–7; Manual prueba 14 p.29. Cambios de fuentes/datos/fórmulas invalidan descendientes; criterio solo permite conservar caja independiente pero recalcula comparaciones y precio objetivo. |
| M9-06 | Instantánea y concurrencia | Traspaso §7. Resultados y decisión vinculados a una revisión inmutable, con registro atómico de vigencia; evitar mezcla entre corridas, reintentos y guardados interrumpidos. |
| M9-07 | Hoja externa de una página | Traspaso §2; D1 p.1; Master §7. Render desde resultados enlazados; cifras, unidades, limitaciones y criterios legibles; exactamente una página PDF por deal. |
| M9-08 | Auditoría y discrepancias | C4 Manual p.18/pp.39/50; PAR-08. Independencia de revisión y diferencias persistentes requieren evidencia; corregir render o escalar sin publicar; no afirmar auditoría sólo por cotejo de texto. |
| M9-09 | Revisión humana auténtica | Traspaso §§2/3/7. Identidad acreditada, alcance, versión, vigencia, decisión y revocación; nombre/casilla/approved:true insuficientes. |
| M9-10 | Puerta al Full UW | Traspaso §2; política 17. PASS aplicable y vigente más aprobación final auténtica. No significa aprobación final de inversión; Full UW diferido al final. |
| M9-11 | Registros internos separados | Traspaso §7. Preservar originales/lecturas, entradas/supuestos, cálculo, comparaciones, revisión y PDF con relaciones claras; hash no prueba autenticidad. |
| M9-12 | Hito/release y límites | Traspaso §§8/10/11. Versionar, verificar SHA remoto completo y exclusiones; no liberar producción por conteo de pruebas, prototipo o referencias sintéticas. |

## Estados que deben conservarse

Una comparación individual necesita valor/criterio definidos, misma unidad/base/período, escenario, definición versionada y operador explícito. La presentación redondeada no determina el resultado. Un cero válido participa normalmente; valor o criterio ausente no se convierte en cero.

Resultados de comparación candidatos: satisface la condición de PASS; cruza condición de FAIL; banda intermedia; conflicto entre criterios; no aplicable acreditado; o no evaluable por causa. Debe conservarse el detalle; un booleano único ocultaría información material. Las líneas PASS/FAIL, sus sentidos y reglas de igualdad deben venir de criterios/reglas expresos; no inferirlas del nombre de la métrica.

La confirmación del usuario impone PENDIENTE sin PASS/FAIL si faltan datos/reglas requeridos. Un incumplimiento conocido no elimina ese bloqueo de completitud. “No evaluable” no es “FAIL económico probado”. La no aplicabilidad no puede elegirse para eludir una métrica o escenario requerido: necesita regla y evidencia vigentes.

Cuando el conjunto está completo, aún se requiere regla de agregación de métricas y escenarios, prioridades de DD/condicionales y resolución de bandas históricas. La regla binaria para HOLD no está aprobada. Un escenario Upside fuerte no rescata Base bajo las fuentes; tampoco se excluye Downside silenciosamente. No se declara PASS por comparar sólo métricas disponibles.

## Criterios, cálculos y versiones

Cada comparación vincula deal, escenario, ejecución/revisión, versión de métrica, valor con procedencia, umbral y su fuente/celda, operador y unidad/período, aplicabilidad, resultado y causa. Una modificación de criterio puede conservar cálculos de caja independientes; invalida siempre comparaciones y decisiones afectadas, y también búsquedas de precio que usaron ese objetivo.

Las revisiones de fuentes/fórmulas/datos invalidan resultados descendientes según grafo. Una decisión actual no se construye con cálculos “últimos” seleccionados de corridas distintas. El contenido de cada ejecución debe ser inmutable y su actualización producir otra revisión.

## Concurrencia y publicación: contrato por implementar

Preparar resultados, comparaciones y PDF sobre una única instantánea; antes de registrar una decisión actual o publicar, comprobar y registrar de forma atómica que las revisiones relevantes siguen vigentes. Un chequeo de versión seguido de una escritura separada no elimina una carrera concurrente. Si cambia la revisión, conservar el artefacto como histórico/desactualizado y exigir la revalidación pertinente.

Reintentos necesitan una identidad de operación y reglas de idempotencia para no duplicar decisión, aprobación o publicación. Un guardado incompleto no debe aparecer como decisión completa. La expiración/revocación y ámbito de una revisión humana invalidan su uso posterior. No hay aún un almacén transaccional/autenticado implementado ni pruebas de carreras reales: son criterios de aceptación pendientes, no capacidades existentes.

## Revisión y Full UW

Cotejar cifras y etiquetas no es auditoría financiera independiente. Separar autoría, relectura documental, control de render y revisión del modelo. La revisión debe acreditar identidad, alcance, versión revisada y decisión, con timestamp/validez/revocación; no basta un nombre, rol, casilla o bandera.

Un PASS válido es un resultado de screening, no aprobación de inversión. El paso a Full UW requiere revisión final auténtica aplicable al PASS y versión vigentes. Su entrega se difiere al final, sin exigir ahora su workbook para la especificación independiente.

## Página por deal y evidencias internas

Contenido propuesto: identidad/estado/motivo; capital y plazos; cifras clave; scorecard y criterios; sensibilidades/soporte de precio; riesgos/materialidad; trazabilidad/condicionales/desviaciones. El detalle debe caber en una página legible; si no, revisar diseño sin reducir a letra ilegible ni añadir anexos externos no autorizados. Los registros internos pueden ser extensos.

Verificar el PDF real, no una maqueta: página única, cifras/unidades/fechas/signos/escenarios correctos y legibles, vínculos a ejecución vigente y auditoría. El PDF profesional R01 de 26 páginas es revisión interna del diseño, no salida de un deal ni evidencia de C4 financiero completo.

## Validación actual limitada

`references/validate_m9_comparisons.py` prueba comparadores expresamente suministrados, fronteras sin redondeo, preservación de faltantes/bandas/conflictos y un caso hipotético de agregación declarada sólo en la referencia. Esa regla de ejemplo no se activa para deals ni resuelve Q1/Q3 o las bandas históricas. No valida identidad, persistencia, carrera de publicación, PDF decisorio real, producto ni revisión independiente.

M9 y todos los módulos siguen abiertos para revisión de política, integración y aceptación real. El paquete de especificación puede prepararse sin valores de Lorena; su aplicación financiera y cierre profesional requieren las decisiones/entradas pertinentes.
