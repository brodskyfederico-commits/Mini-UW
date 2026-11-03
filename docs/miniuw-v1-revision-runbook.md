# Comparar revisiones sintéticas del Mini-UW v1

El comparador conserva dos expedientes completos y muestra sus cambios junto con el efecto condicionado en aportes, cobros, resultado de caja y EM. La candidata se suministra explícitamente; el sistema no la inventa, renueva sus fuentes o selecciona una ganadora. El [contrato](technical-implementation-T88-T89.md) define alcance y bloqueos.

Desde la raíz del repositorio, con Python 3.11 o posterior y las dependencias de `requirements-reference.txt` instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/compare_miniuw_v1.py compare --reference templates/miniuw-v1-synthetic-case.json --candidate templates/miniuw-v1-sale-500-candidate.json --spec templates/miniuw-v1-revision-comparison.json --output /tmp/miniuw-v1-revision-demo
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/compare_miniuw_v1.py audit /tmp/miniuw-v1-revision-demo
```

La especificación usa `miniuw.synthetic-v1-revision-comparison.v1`, un `comparison_id` sintético, hashes SHA256 exactos `reference_case_sha256` y `candidate_case_sha256`, y `comparison_basis_ref` explícito. Cambiar bytes exige nuevas huellas en esa especificación; la evidencia financiera de cada expediente también debe concordar por separado. Whitespace distinto cambia la huella de bytes. La revisión candidata debe ser posterior al mismo caso, con contexto económico, escenarios e instante UTC compatibles.

La carpeta contiene exactamente `comparison.json`, `comparison-evidence.json`, `review.txt` y `package.json`. El texto es un registro interno; cada expediente puede producir su propio PDF de una página con el comando v1 original. No se concatena una segunda página de decisión. Usar una carpeta nueva por comparación; repetir una entrada idéntica sólo verifica bytes, y una salida diferente/incompleta no se sobrescribe.

Una corrida válida pero bloqueada produce el registro con decisión PENDIENTE y código 0: revisar `comparison_blockers` y los bloqueos de ambos expedientes. Estructura inválida, tamaño/profundidad/inventario excedidos o alteraciones devuelven código 2. El audit no se limita a hashes: reconstruye ambas corridas y los cuatro archivos con las versiones compatibles.

El [ejemplo](review/miniuw-v1-revision-example/review.txt) pasa de proceeds de venta 400 a 500 con evidencia sintética revisada expresamente. Los cobros pasan de 778 a 878 y el resultado de caja de −622 a −522, sin variar aportes de 1.400. Si falta vigencia o conciliación en cualquiera, se retiran todos los deltas. Cambios de horizonte o identidad de eventos también requieren conciliación fuera de este perfil. Las normalizaciones con bases distintas se muestran por separado; IRR conserva todas las raíces e intervalos sin calcular una tasa elegida o una diferencia puntual.

El mapeo completo de los 55 campos, ocho métricas pendientes, bases de capital/CoC/retorno personal, fuentes auténticas y validación financiera permanecen abiertos. El comparador no adopta criterios históricos, reglas profesionales o precios de mercado; no despliega servicios ni habilita decisiones reales.
