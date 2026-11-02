# T13 — propuestas sintéticas de revisión

Cada propuesta conserva el caso original y genera una versión candidata. Solo admite cambios explícitos de valores de métricas o condiciones de criterios existentes; registra localizador exacto, valor anterior, valor propuesto, motivo y referencias de evidencia declaradas. No modifica automáticamente variables para conseguir PASS.

El contrato `miniuw.synthetic-screening-review-proposal.v1` exige los hashes del archivo y ejecución base y coincidencia literal del valor anterior. Rechaza propuestas obsoletas, cambios duplicados o vacíos y campos protegidos. Cada candidato necesita nuevos identificadores de caso y ejecución; modificar un criterio exige también una nueva revisión de criterios. Unidades, alcance, inventarios, aplicabilidad y regla de bandas permanecen protegidos. Las bandas intermedias siguen PENDING para revisión profesional según la decisión del usuario.

Se vuelve a ejecutar la comparación de métricas y criterios. Esto no recalcula el grafo financiero completo desde costos, rentas u otras variables de origen: los productores restantes siguen pendientes. Los resultados PASS/FAIL son simulaciones; la decisión operacional permanece PENDING. No se acepta ninguna propuesta ni se sustituye un caso activo. Propuestas independientes pueden partir de la misma base sin que una invalide o apruebe otra.

El nombre del autor y las referencias de evidencia son declaraciones sin autenticación. Los hashes permiten comprobar bytes y reproducción, pero no acreditan identidad, autoridad ni aprobación profesional. No hay interfaz de revisión profesional autenticada, despliegue o evaluación de deals reales.

El archivo local conserva atómicamente fuente base, propuesta, candidato y paquete de resultados. Al recuperar verifica fuentes, versiones de código, documentos, política vigente y reproducción completa. Una versión incompatible requiere el código/documentos compatibles; no se migra silenciosamente. Las bases runtime están excluidas de Git y del respaldo documental.

La plantilla `templates/synthetic-screening-review-proposal.json` está vinculada por hashes al ejemplo de banda y a su ejecución actual. Si cambia esa base o su versión, la propuesta debe renovarse explícitamente. No se actualizan sus hashes silenciosamente.

Desde la raíz del repositorio:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_synthetic_review_proposals.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

La demostración conserva la base PENDING y archiva/recupera tres propuestas explícitas: simulación PASS, FAIL y PENDING. Son 19 pruebas nuevas, 273 técnicas en total: versiones obsoletas, cambios incompatibles, conservación del original, ausencia de autenticación, recuperación, falsificación y rollback, entre otras. Esto no cierra módulos financieros, paquetes del plan ni revisión profesional.
