# Vigencia de evidencia — prueba interna sintética

Se verifica cada una de las 21 fuentes técnicas/bindings del ejemplo al instante UTC explícito. No se autentican documentos originales o revisión profesional. El estado decisorio permanece PENDING incluso cuando se muestra una cifra sintética.

| Caso | Instante UTC evaluado | Resultado de caja del proyecto expuesto | Estado técnico |
|---|---|---:|---|
| current | 2027-07-01T12:00:00Z | 288.9197 | current_synthetic_output_at_declared_time |
| expired | 2027-08-01T00:00:00Z | Pendiente | PENDING |
| pending-review | 2027-07-01T12:00:00Z | Pendiente | PENDING |
| estimated-value | 2027-07-01T12:00:00Z | Pendiente | PENDING |
| superseded | 2027-07-01T12:00:00Z | Pendiente | PENDING |
| explicit-renewed-test | 2027-08-01T00:00:00Z | 288.9197 | current_synthetic_output_at_declared_time |
| known-bank-blocker | 2027-07-01T12:00:00Z | Pendiente | PENDING |

La misma operación conserva sus cifras históricas al vencer la evidencia. El nuevo resultado deja de exponer el resumen como vigente. Una renovación de prueba necesita otra versión explícita del registro y su reproducción; no adopta plazos reales ni autentica una aprobación. El bloqueo bancario original continúa aunque sus anotaciones de evidencia estén vigentes.

Sin reloj/monitor automático: otra fecha exige reevaluación. Estimaciones, registros sustituidos o sin revisar y conflictos permanecen pendientes. Los APIs históricos siguen como cálculos aislados sin esta validación optativa. Sin retorno personal, despliegue o decisiones reales.
