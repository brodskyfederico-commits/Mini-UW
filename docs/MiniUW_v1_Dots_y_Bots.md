# Dots y bots — contratos Mini-UW v1

Definicion funcional para integracion sintetica local. Ningun agente externo esta desplegado. Los estados parciales no equivalen a cierre financiero ni auditoria independiente.

Fuentes preservadas: Feedback_Dots_Mini_UW, pagina fisica 1; Framework Roadmap 3.1, pagina fisica 4. La asignacion funcional es nueva; no adopta recomendaciones historicas de modelos, umbrales o plataformas.

| Dot | Entradas | Salidas | Bloqueos | Estado |
|---|---|---|---|---|
| D01 Recepcion y coordinacion | Caso/archivos declarados/revision | Inventario de fuentes y plan de ejecucion | Formato/contexto ambiguo; Fuente o revision incompatible | partial_synthetic_runtime |
| D02 Validacion de entrada | 55 campos originales; Criterios por deal; Fuentes complementarias | Valores/index y pendientes por campo | Faltante o conflicto; Unidad/base/mapeo sin definir | partial_synthetic_runtime |
| D03 Planos y conciliacion | Planos originales; Dos lecturas independientes; Fuentes GC y politica de tolerancia | Lecturas citadas; Discrepancias sin sobrescribir | Sin planos o lectura independiente; Sin tolerancia aplicable | contract_only_pending |
| D04 Datos oficiales | Pregunta/documento/allowlist aprobada | Copia y cita con fecha; Valor verificado en copia | Dominio no autorizado; Sin copia/cita vigente | contract_only_pending |
| D05 Calculo y screening | Fuentes financieras declaradas; Calendarios/deuda/renta/gastos; Criterios | Resultados reproducibles; Retorno y matriz de comparacion | Fuente/fecha incompatible; Regla o criterio faltante; Perfil no soportado | partial_synthetic_runtime |
| D06 Informe | Resultados actuales y snapshot de fuente | PDF de una pagina; Manifiesto de cifras | Datos vencidos retiran cifras; Desborde o glifo no representable impide PDF | synthetic_callable |
| D07 Comprobacion y pruebas | Entrada/resultados/PDF/huellas; Casos de prueba de version | Audit tecnico; Evidencia de pruebas y pendientes independientes | Diferencia de archivo/cifra/pagina; Falta auditoria financiera independiente | deterministic_check_only |

| Bot / Dot | Entrada | Salida | Bloqueo | Estado |
|---|---|---|---|---|
| B01 Orquestador / D01 | case.json | stages/results/package | Perfil/contexto no soportado; dependencia bloqueada | synthetic_callable |
| B02 Recepcion / D01 | case.json y fuentes declarativas | Inventario SHA/revision | JSON invalido o fuente duplicada/inventario incompleto | synthetic_callable |
| B03 Clasificador / D01 | Archivos originales ambiguos | Tipo y confianza con evidencia | Ambiguedad conserva sin tipo; sin extractor implementado | contract_only_pending |
| B04 Validador Input Sheet / D02 | Catalogo 55; criterios; mapas | Estado por campo y discrepancias | Null/valor contradictorio/mapeo o semantica pendiente | partial_synthetic_callable |
| B05 Lector A / D03 | Planos originales | Lectura A con citas | Sin planos; prohibido takeoff o inferir medidas | contract_only_pending |
| B06 Lector B / D03 | Planos originales aislados de A | Lectura B con citas | Sin originales/independencia; no ve A | contract_only_pending |
| B07 Conciliador / D03 | Lecturas A; B y fuentes | Ambos valores y conflicto | Falta lectura o autoridad para resolver diferencia | contract_only_pending |
| B08 Lector financiero / D05 | Documentos financieros originales | Afirmaciones con pagina/celda | No extraer o estimar ausencia; v1 recibe fuentes ya estructuradas | contract_only_pending |
| B09 Control cruzado GC / D03 | Lecturas conciliadas; GC y regla | Conciliacion y diferencias | Sin tolerancia aprobada o fuente independiente | contract_only_pending |
| B10 Investigador oficial / D04 | Pregunta y dominios aprobados | Copia/URL/fecha/publicador | Sin allowlist o permiso; ninguna consulta externa en v1 | contract_only_pending |
| B11 Verificador oficial / D04 | Copia y cita de bot 10 | Valor exacto verificado | Sin copia/ubicacion o evidencia vencida | contract_only_pending |
| B12 Guardian / D05 | Inventarios; estado de entrada; cadena | Gates de calculo y decision separados | Faltantes/conflictos/reglas: PENDING; nunca arreglar para PASS | partial_synthetic_callable |
| B13 Motor / D05 | Fuentes tipadas; calendarios; definiciones | NOI/caja/deuda/retorno con hashes | Solo perfil suministrado; presupuesto/exactitud/continuidad incompatibles | synthetic_callable |
| B14 Juez / D05 | Metricas propias y criterios explicitos | Comparaciones y PENDING operacional | Faltantes/banda: PENDING; sin umbrales historicos por defecto | partial_synthetic_callable |
| B15 Redactor y maquetador / D06 | results.json reproducido | Resumen PDF/manifest de una pagina | Sin cifras manuales; sin clipping/seleccion conveniente de IRR | synthetic_callable |
| B16 Auditor / D07 | Entrada; results; PDF manifiestos | audit.json tecnico | Una diferencia bloquea artefacto; no certifica auditoria independiente | deterministic_check_only |
| B17 Pruebas de version / D07 | Casos y codigo versionado | Logs y CI del commit exacto | Sin expected financiero independiente no cerrar aceptacion; no corre en cada deal | release_test_contract |

El ejecutor puede calcular el perfil sintetico desde fuentes complementarias completas sin considerar validado el formulario original. El guardian de decision conserva todos los pendientes del expediente completo. Los lectores y la investigacion oficial no corren en esta version.

El auditor local reproduce cifras y archivos; su salida no acredita independencia financiera o profesional. La evidencia de CI corresponde a la version, no al estado de cada deal. No hay mensajes, busquedas, aprobaciones, publicacion o despliegue externos.

[Contrato ejecutable](miniuw-v1-dot-bot-contracts.json) · [Alcance tecnico](technical-implementation-T85-T87.md).

D127 prueba estos contratos en la cadena local con copias sintéticas estructuradas. [Alcance, casos y reproducción](workbook-local-chain-D127.md).

D130 prueba B05, B06, B07 y B09 con un plano PDF de texto sintético vinculado al expediente. [Lecturas, conciliación y reproducción](workbook-plan-pdf-D130.md).

D131 prueba esos contratos con OCR sobre un PDF escaneado sintético y conserva la región y la confianza de cada cita. [Lecturas y bloqueos](workbook-plan-scan-D131.md).

D132 prueba ambos métodos en hojas separadas de un mismo PDF. [Alcance y resultados](workbook-plan-mixed-D132.md).

D133 compara texto y OCR de la misma hoja en B06. B07 y B09 continúan la conciliación sólo cuando ambas lecturas están completas y coinciden. [Alcance y resultados](workbook-plan-overlay-D133.md).

D134 conserva ese cotejo para una hoja escaneada con un giro declarado de 90°, 180° o 270°. El expediente guarda la orientación, el hash del escaneo extraído y el de la imagen que recibe el OCR. [Alcance y resultados](workbook-plan-rotation-D134.md).

D135 inventaría las páginas antes de conciliar A101 y A601. Registra la ubicación de cada hoja y conserva PENDING ante faltantes, duplicados o identidades en conflicto. [Alcance y resultados](workbook-plan-set-D135.md).
