# T11 — Simulador de comparación de métricas y criterios por caso

Implementa la parte del objetivo de Mini-UW de recibir valores y compararlos con criterios expresos. Es una simulación: `simulation_result` puede ser PASS/FAIL/PENDING, pero `decision` operacional siempre permanece PENDING, revisión no autenticada y producción false. No se adoptan umbrales históricos ni respuestas de Lorena.

## Entrada explícita e independiente por deal

`miniuw.synthetic-screening-case.v1` exige contexto sintético, identidad de caso/revisión de criterios, marcador `synthetic_fixture_only`, inventarios no vacíos de métricas y escenarios, tablas separadas de valores/criterios y selección explícita de agregación/política hipotética de banda. Se admiten los diez IDs de inversión de la plantilla vigente; condiciones bancarias como DSCR no se introducen como criterios de inversión por aproximación. La interfaz estructurada JSON no afirma que ya se conozca el formato final de la hoja de Lorena.

Se compara todo el producto métrica×escenario declarado. Filas ausentes generan PENDING, duplicadas/fuera de inventario se rechazan y escenarios adicionales no se omiten silenciosamente. El inventario declarado no constituye prueba de completitud financiera: queda sin verificar. Cada ejecución nace desde su fuente completa; no hay herencia de otro deal o criterios por defecto.

Cada valor/criterio declara definición, unidad, tipo de cantidad, moneda, período/base y aplicabilidad. Se conservan números racionales exactos, sin redondeo decisorio. Definición/unidad/período/tipo faltantes o incompatibles bloquean; cantidades monetarias exigen moneda explícita. La comparación no verifica por sí sola el cálculo financiero del valor aportado. La no aplicabilidad necesita declaraciones coincidentes y referencias de evidencia en ambas tablas; las referencias no autentican una exención real. Un conjunto totalmente no aplicable no produce PASS vacío.

## Condiciones, bandas y completitud

Cada criterio requiere dos condiciones expresas (PASS y FAIL), con operador >, >=, < o <= y umbral. Cero es valor, no ausencia. No se infiere dirección por el nombre de la métrica ni se decide igualdad desde el render. Regiones PASS/FAIL que se solapan generan CONFLICT aunque el valor observado esté fuera del solapamiento.

Estados detallados: PASS_CONDITION, FAIL_CONDITION, BAND, CONFLICT, NOT_APPLICABLE_DECLARED y PENDING. Ningún incumplimiento conocido elimina faltantes de datos/reglas requeridos: la simulación global queda PENDING, como confirmó el usuario. La agregación usada por un fixture debe declararse: todas las comparaciones aplicables en PASS permiten simular PASS; alguna FAIL con todo completo permite simular FAIL. Conflictos/incompletitud bloquean. No se activa esta política para deals reales.

La banda no se convierte por intuición: `hypothetical_band_policy=null` conserva el bloqueo por regla ausente; `pending` conserva PENDING por política hipotética explícita; `fail` permite probar FAIL en el simulador sin cambiar el detalle BAND ni adoptar una política real. El contrato M9-04 deja pendiente la regla binaria para la banda histórica.

## Primera decisión solicitada al usuario

Con valores y criterios completos, un ejemplo ficticio PASS>=5%, FAIL<4% y valor 4,5% queda entre líneas. Las dos alternativas preparadas son mantener PENDIENTE o tratar el no cumplimiento de PASS como FAIL en la banda. Los faltantes permanecen PENDING bajo ambas. Esta elección es una regla de diseño del screening, no aprobación de un deal, adopción de esos números ni autorización de despliegue. No se ha elegido una opción mientras falta respuesta. Ver `pending-band-policy-decision.json`.

## Evidencia y archivo

El resultado conserva fuente exacta/contexto/revisión, inventarios, metadatos, condiciones, valores, JSON Pointers de cada valor/criterio y causas. Incluye versión del simulador y ubicaciones/hash de los contratos de comparación/completitud. El archivo tipado captura fuente y paquete en una transacción local y reproduce la simulación al recuperar; un resultado falso con hash actualizado no supera la reproducción. Código/documentos distintos requieren la versión compatible. No implementa vigencia/publicación atómica, revisión auténtica, PDF externo o puerta de Full UW. Runtime sigue excluido de GitHub/ZIP.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_screening.py
```

El fixture `synthetic-screening-band-case.json` usa solo dos métricas y dos escenarios ficticios; no representa el inventario completo aprobado de un deal. La demostración archiva/recupera cinco casos: banda sin regla, banda pendiente, banda como FAIL hipotético, caso completo PASS y FAIL conocido con otro valor ausente (PENDING).

21 pruebas nuevas (250 técnicas totales) cubren completitud, igualdad/operadores, precisión, conflictos globales, band policies, cantidades/monedas/bases, no aplicabilidad, inventarios, aislamiento, revisión no simulada, procedencia, replay/rollback/falsificación/versiones. Permanecen aparte 26 suites de referencia, ocho fallos estructurales y 36 casos de aceptación financiera no ejecutados contra producto completo. M9/IMP-05 permanecen parciales; aún faltan criterios/valores auténticos, reglas de aplicación adoptadas, integración financiera, revisión y publicación.
