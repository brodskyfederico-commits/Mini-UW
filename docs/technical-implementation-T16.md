# Propuestas sobre el comparador por escenario

T16 conecta los candidatos de revisión con el experimento T15. Cada propuesta modifica únicamente valores de métricas ficticias existentes. Conserva el DOCX original, caso base, resultado base, propuesta, candidato y ejecución nueva sin alterar los anteriores. Una etiqueta de autor o referencia declarada no acredita identidad, revisión ni aceptación.

El contrato `miniuw.synthetic-scenario-metric-proposal.v1` exige hashes del documento, caso y ejecución base, identidad SYNTHETIC de propuesta, nuevos identificadores de caso/ejecución, motivo, evidencia declarada y cambios explícitos. Antes de aplicar, reproduce la base y comprueba el valor anterior exacto. Fracciones equivalentes con distinta representación no sustituyen silenciosamente la evidencia original. Un cambio vacío, duplicado, sobre una fila ausente o con base obsoleta se rechaza.

Este perfil mantiene protegidos criterios, reglas, escenarios y aplicabilidad. No adapta el DOCX para hacer pasar un deal. La revisión de un criterio necesita evidencia y un contrato apropiado; no se disfraza como corrección de métrica. Una propuesta que cambia YoC puede pasar de banda a PASS o FAIL simulado en alcance Base. En Base/Downside sigue pendiente asking/RLV Downside si su aplicabilidad no está resuelta. Una corrección no elimina ese bloqueo.

El archivo `miniuw.synthetic-scenario-review-bundle.v1` captura atómicamente cuatro fuentes —DOCX, base, propuesta y candidato— y el paquete de resultados. La recuperación reproduce ambas ejecuciones y los cambios contra versiones compatibles de código, documentos y política de bandas. Las fuentes faltantes y resultados alterados bloquean la recuperación; actualizar el hash del resultado falso no evita el cotejo. No se modifica el esquema de la tabla existente.

Son 17 pruebas nuevas: candidatos PASS/FAIL/PENDIENTE, conservación de original, Downside sin FAIL inventado, base falsificada u obsoleta, comparación literal, nulos, campos protegidos, lotes fallidos, cadenas de candidatos, etiquetas sin autenticación, reapertura, falsificación, rollback y versiones/evidencia ausentes. El componente reejecuta comparaciones de métricas aportadas; no recalcula todo M2–M8 ni valida la economía de un proyecto.

API: `evaluate_scenario_proposal(document_raw, base_raw, base_run, proposal_raw)`. Devuelve un resultado inmutable `ScenarioReviewRun`. Captura y recuperación: `save_scenario_review` y `load_scenario_review`. La demostración integrada se describe en T18. Ninguna propuesta queda aceptada ni habilita decisiones reales.
