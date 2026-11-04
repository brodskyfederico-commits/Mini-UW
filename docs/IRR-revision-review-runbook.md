# Revisión de versiones sintéticas T102

Reproduce dos versiones completas, muestra qué cambió en las fuentes y los criterios y cuánto cambiaron los aportes, cobros y retornos calculados. Conserva ambos resultados y los localizadores exactos. No genera ni adopta una nueva versión activa. El resultado global sigue PENDING.

Desde la raíz del repositorio, con Python y las dependencias de `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/irr_review_miniuw_v1.py compare \
  templates/miniuw-v1-IRR-condition-band-case.json \
  templates/miniuw-v1-review-criteria-candidate.json \
  --spec templates/IRR-review-criteria-T102.json \
  --output /tmp/miniuw-T102-review
PYTHONDONTWRITEBYTECODE=1 python tools/irr_review_miniuw_v1.py audit /tmp/miniuw-T102-review
PYTHONDONTWRITEBYTECODE=1 python tools/check_IRR_revision_review_T102.py
```

El directorio nuevo contiene siete archivos: especificación, evidencia completa de referencia, evidencia completa candidata, JSON y texto de revisión, un PDF del candidato y manifiesto. El ejemplo guardado está en `docs/review/miniuw-v1-IRR-revision-review-example/`. La lectura/auditoría es local; el comando no publica en GitHub ni despliega servicios. Un reintento idéntico se verifica; una salida distinta exige otro directorio.

Los hashes exactos y la base de comparación son entradas explícitas. Para restar importes exige caso/contexto/escenario/fecha, moneda, ventana e inventario de movimientos compatibles y revisión candidata posterior. No cambia fechas ni fuentes para hacerlas coincidir. Diferencias son candidato menos referencia, racionales exactos. Bases de normalización distintas o ausentes no producen deltas normalizados. Las TIR conservan todas sus raíces/intervalos, sin punto elegido ni resta de tasas.

Tres ensayos declarados prueban comportamientos distintos. En el primero cambia la regla IRR y su fila pasa de BAND a PASS_CONDITION, con caja y retornos idénticos; ambos deals siguen pendientes. Sus umbrales son controles sintéticos de software. También cambian revisiones y evidencia declarada: no se atribuye causalidad exclusiva a una variable. El segundo reproduce cobros778→776, neto−622→−624 y diferencia EM−1/700 por fuentes suministradas. El tercero vence la evidencia candidata: retira sus cifras actuales y diferencias, conservando la referencia sólo como otro snapshot.

El paquete y la API portable reconstruyen ambas cadenas desde sus fuentes antes de aceptar resultados o PDF. Rehashear una alteración no la convierte en evidencia válida. Es una prueba técnica con versiones compatibles, no autenticación de fuentes ni auditoría financiera independiente. No implementa publicación concurrente productiva o recuperación del VPS.

Las54 correspondencias semánticas originales, datos reales, criterios aprobados, bases de capital/CoC y términos personales conservan sus pendientes. No se solicita nueva información para ejecutar estos ensayos sintéticos. [Definición T102](technical-implementation-T102.md).
