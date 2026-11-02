# Condiciones documentadas por escenario y recuperación del ensayo

T15 incorpora un perfil experimental que evalúa PASS Base, PASS Downside y FAIL Base como condiciones distintas. Usa el DOCX original de Lorena y métricas ficticias; no activa sus umbrales como política de inversión. El comparador canónico anterior y los resultados T14 permanecen intactos para conservar su reproducción histórica.

## Qué cambia respecto a T14

T14 mostró once bloqueos de compatibilidad porque el comparador anterior exigía FAIL en cada escenario. El perfil T15 utiliza el comparador exacto existente para Base y evalúa en Downside sólo las condiciones PASS que sí están documentadas. No crea una columna FAIL Downside ni copia el nivel de Base.

La fuente exacta es `sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx`, SHA-256 `38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9`. Además de la tabla, el perfil comprueba y localiza las reglas documentadas “Any Base metric is worse than its FAIL level.” y “Every Base and Downside metric meets its PASS level.” Las ubicaciones XML tienen índices desde cero. La identificación del archivo no autentica su autor ni acredita adopción para un deal real.

## Estados y agregación del experimento

| Situación | Resultado de comparación |
|---|---|
| Base cumple PASS | PASS_CONDITION, usando frontera inclusiva. |
| Base cruza su FAIL | FAIL_CONDITION, usando frontera estricta. |
| Base queda entre ambas líneas | BAND; el conjunto permanece PENDIENTE para revisión. |
| Downside cumple PASS | PASS_CONDITION; no necesita un FAIL inexistente. |
| Downside no alcanza PASS | PASS_MISS_PENDING; no se transforma en FAIL Downside. |
| Valor requerido ausente | PENDIENTE, con distinción entre registro ausente y valor vacío. |
| Asking/RLV Downside sin umbral o aplicabilidad resuelta | PENDIENTE; no se excluye automáticamente por la raya. |

Los bloqueos requeridos y las bandas tienen prioridad sobre un incumplimiento Base conocido. Sin bloqueos, el perfil conserva la agregación experimental explícita de FAIL si existe un incumplimiento Base y PASS si todas las condiciones requeridas se satisfacen. La decisión operacional sigue PENDIENTE en todos los casos.

Con los fixtures actuales, Base/Downside tiene diez comparaciones Base, nueve condiciones Downside evaluables y una condición asking/RLV Downside pendiente. Ningún fixture actual demuestra PASS o FAIL conjunto porque esa última aplicabilidad sigue abierta. La funcionalidad probada no permite omitirla mediante una casilla o un campo adicional.

## Resultados reproducidos

| Fixture | Resultado simulado | Evidencia |
|---|---|---|
| Base y Downside con cifras ficticias de T14 | PENDIENTE | Nueve condiciones Downside PASS; queda un bloqueo de asking/RLV Downside. |
| El anterior con YoC Downside ficticio de 1% | PENDIENTE | PASS_MISS_PENDING más el bloqueo de asking/RLV; no hay FAIL Downside. |
| Sólo Base con cifras ficticias que cumplen | PASS | Alcance parcial, sin cubrir Downside ni completar Mini-UW. |

Los metadatos compatibles y las cifras son declaraciones del experimento. No se producen NOI, TDC, IRR o retornos desde entradas reales; no se valida una hoja completada de Lorena ni la economía de un proyecto.

## Archivo y reproducción

El nuevo paquete `miniuw.synthetic-scenario-threshold-bundle.v1` conserva atómicamente el DOCX exacto, el JSON de cifras ficticias y el resultado completo. La captura reproduce el resultado antes de guardarlo. La recuperación comprueba hashes, versiones de los tres componentes de cálculo, documentos de definición, política de bandas y reproducción completa desde ambas fuentes. El paquete conserva también la ejecución Base utilizada.

Una alteración del resultado se rechaza aunque se actualice su hash. Una versión incompatible se informa como tal; no se migra silenciosamente. Si falta evidencia, se bloquea la recuperación. Un fallo antes del commit revierte fuentes y paquete juntos en esta base local; no se afirma atomicidad con otros sistemas ni publicación de decisiones.

No cambia la tabla de almacenamiento existente ni se modifica una ejecución previa. Las bases runtime quedan excluidas de GitHub y del ZIP documental; los originales y el código del experimento permiten reproducir las pruebas, no recuperar una operación real inexistente.

## Uso y pruebas

Desde la raíz del repositorio:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_scenario_threshold_rehearsal.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

API del experimento: `simulate_scenario_thresholds(source_raw, case_raw)`. Consume los mismos fixtures explícitos de T14 y devuelve un resultado inmutable `ScenarioThresholdRun`. Archivo: `save_scenario_thresholds`, `load_scenario_thresholds`, `get_documented_threshold_source` y `get_scenario_threshold_case`. No es un adaptador general de criterios o una vía de decisión real.

Son 18 pruebas técnicas nuevas y 308 en total: límites min/max de Downside, incumplimiento de PASS sin FAIL inventado, fronteras Base, faltantes, bloqueo conjunto, identidad sintética, fuente exacta, vínculos de política, inmutabilidad, recuperación tras reapertura, idempotencia exacta de captura, falsificación, rollback, versiones incompatibles y evidencia ausente. T14 conserva sus once bloqueos históricos; T15 reduce esa incompatibilidad a la aplicabilidad pendiente de asking/RLV en el fixture sin otros faltantes.

No se cierran módulos financieros o paquetes del plan. Los 36 casos originales de aceptación financiera y los 56 casos de diseño D02/D03 mantienen su estado separado. Sigue pendiente integrar definiciones y aplicabilidad reales, productores financieros, revisión auténtica y publicación operativa. No se pide inventar FAIL Downside para continuar el desarrollo.
