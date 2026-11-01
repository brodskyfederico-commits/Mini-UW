# Integridad de revisiones y escenarios — referencia de diseño

Base: traspaso §§6–7; M8-02/07/12 y M9-05/06/09. Se fortalece la estructura mientras llega la revisión, sin elegir umbrales, reglas financieras o términos bancarios.

## Modelo acotado de dependencias

La referencia distingue hechos compartidos expresamente, inputs/banco/criterios de cada escenario, operación, presupuesto, calendario, bloque de cierre financiero, refi, retornos, precio objetivo, comparaciones, decisión y PDF candidato. Los hechos compartidos apuntan a la misma fuente/versionado de manera explícita; no se usa un fallback de Base para completar Downside.

El ciclo TDC/interés se representa como un bloque cuya resolución sigue pendiente. Un grafo acíclico de dependencias no demuestra convergencia del cálculo contenido en ese bloque. Las dependencias de la referencia son propuestas explícitas, no descubiertas de un motor real.

## Reglas verificadas en la referencia sintética

- Un cambio de criterio de Base invalida comparaciones/precio objetivo de Base y el documento dependiente. Preserva caja que es independiente de ese criterio bajo este grafo.
- Cambios de input o banco invalidan sus dependientes por escenario; fuentes compartidas pueden invalidar ambos escenarios por su relación expresa.
- La instantánea conserva deal, contexto de escenario, corrida y revisiones de todas las dependencias transitivas; no basta comprobar sólo el nodo hijo.
- Reutilizar con otro deal, corrida, escenario, revisión ausente o ancestro cambiado se rechaza.
- Un slot de Downside no puede completarse con un slot de Base; cero explícito es distinto de dato ausente.
- Dependencia desconocida y ciclo sin bloque resuelto son errores, no cálculos válidos.

Si un criterio afecta realmente la operación o el sizing, el grafo deberá incluir esa dependencia. El ejemplo no acredita que todas las relaciones del producto estén completas. La reutilización de caja exige comprobar independencia en el contrato real, no una etiqueta arbitraria.

## Lo que no está probado

La referencia es en memoria, inmutable en sus registros y sin servicios externos. No implementa transacciones de base de datos, autenticación, persistencia, aprobación experta ni publicación. Un chequeo correcto seguido de una edición puede quedar obsoleto; sigue siendo indispensable un registro atómico de vigencia en el producto futuro. No se denomina a estas pruebas “aprobación autenticada” ni prueba de carreras reales.

Evidencia: `references/validate_revision_integrity.py`, `revision-integrity-validation.json` y `dependency-graph-reference.json`. Es un refuerzo de diseño y prueba sintética, no producción. El PDF profesional R02 se mantiene idéntico; las observaciones se referirán a ese corte y después se evaluará su impacto en documentos/cálculos posteriores.
