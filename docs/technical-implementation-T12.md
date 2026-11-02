# T12 — Banda intermedia PENDIENTE por decisión del usuario

El usuario resolvió M9-04: «marcarlos como pendiente porque el profesional puede llegar a modificar una variable y convertirlo en pass o fail». La regla se registra en `pending-band-policy-decision.json` con estado selected_by_user y opción retain_pending_in_band. El nombre del archivo se conserva por continuidad de referencias; la decisión ya no está esperando respuesta.

## Comportamiento aplicado

El camino canónico `simulate_screening` mantiene PENDING en una banda intermedia, incluso con valores y criterios completos y aunque una fuente antigua solicite la alternativa hipotética FAIL. Conserva el detalle BAND y registra causa de pendiente por revisión profesional, las métricas/escenarios afectados, sus localizadores y el hash de la instrucción del usuario. Faltantes/conflictos siguen bloqueando como antes.

Los casos completos que satisfacen condiciones PASS o cruzan condiciones FAIL pueden seguir produciendo esas clasificaciones en simulación, sin emitir decisiones reales. La elección del usuario es una regla de diseño; no adopta los números ficticios, no autentica una revisión ni habilita producción. Los diez criterios de cada nuevo deal continúan vacíos.

La antigua alternativa se mantiene únicamente como investigación explícita `simulate_policy_whatif`, con marca what_if_only=true y sin admisión como evidencia canónica por `save_screening`. No es un selector de la clasificación normal ni cambia la instrucción del usuario. La demostración principal usa exclusivamente el camino canónico: las tres solicitudes antiguas de banda (sin regla, pending o fail) resultan PENDING.

## Revisión de variables y versiones

No se ajustan automáticamente variables para llegar a PASS. Una propuesta de revisión debe conservar fuente, autoría declarada y contexto, crear nueva versión/evidencia y volver a calcular/comparar las dependencias afectadas. Si solo cambia un valor, se conserva el criterio aplicable y se versiona la corrida; si cambia un criterio, también su revisión. Las versiones anteriores permanecen disponibles. El componente no implementa todavía autenticación del profesional ni la ejecución completa de todos los cálculos financieros.

Las pruebas preparan revisiones sintéticas que llevan un valor de banda a PASS o FAIL y comprueban que el registro original siga PENDING y sus bytes permanezcan intactos. Otra revisión cambia el umbral explícito, sin tocar el valor: genera resultado distinto y nueva evidencia, pero sigue sin representar criterios auténticos aprobados. Estos son controles de trazabilidad, no recomendaciones de modificar supuestos económicos.

## Evidencia y verificación

El paquete canónico pasa a `miniuw.synthetic-screening-bundle.v2` y queda ligado al hash del documento con la elección del usuario. La recuperación exige código, documentos y política compatibles; no reinterpreta un archivo antiguo con una política nueva. Los bytes históricos permanecen recuperables por hash y las versiones de código/documentos se conservan en GitHub. No se afirma publicación atómica, revisión autenticada ni disponibilidad actual de un deal.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_screening.py
```

Cuatro pruebas nuevas (254 técnicas totales) cubren la regla canónica frente a solicitudes contradictorias, aislamiento del what-if, revisiones que cambian resultados sin borrar historia y cambios de criterio sin ajuste automático del dato. Los controles anteriores también pasan: 26 suites de referencia y ocho fallos estructurales. Los 36 casos de aceptación financiera del producto completo siguen sin ejecutarse; las puertas financieras, revisión y despliegue siguen abiertas/no autorizadas.

Esta decisión ya no requiere confirmación repetida. El trabajo técnico independiente puede continuar con el mismo alcance sintético; no se solicita de nuevo elegir entre banda PENDING y FAIL.
