# Implementación técnica T01 — datos sintéticos

Autorización vigente del usuario: construir sin despliegue ni decisiones reales, sin esperar inputs de Lorena ni revisión profesional para tareas independientes. Este componente nuevo no es la recuperación de una aplicación histórica.

## Comportamiento implementado

`src/miniuw_foundation` recibe declaraciones sintéticas explícitas y las conserva en SQLite local con historial de revisiones. Cada borrador nuevo inicia sus 55 campos y diez criterios sin declaraciones ni umbrales heredados. No rellena valores, unidades, períodos, monedas ni definiciones.

Una declaración conserva su texto literal, localizador y SHA-256 declarado de la fuente. El hash declarado no prueba que exista el archivo ni autentica la fuente. El prefijo de contexto `SYNTHETIC-` delimita el desarrollo; no es un control de acceso ni un detector de datos personales.

Cero, nulo y texto vacío conservan sus diferencias. Los valores incompatibles se mantienen juntos sin seleccionar un ganador. Las representaciones `5%` y `0.05` se consideran declaraciones diferentes hasta que exista normalización explícita. Una declaración única o coincidente sigue sin verificar; no equivale a un dato financiero validado.

Cada escritura exige revisión esperada e identidad de operación. La transacción registra revisión, cabecera y operación conjuntamente. Un reintento idéntico devuelve la revisión original; si entretanto avanzó la cabecera, devuelve también la revisión actual observada. Reutilizar la operación con otro contenido falla. Las revisiones anteriores no se sobrescriben y el consumidor recibe copias JSON. La integridad por hash detecta alteraciones accidentales, no protege frente a un administrador que reescriba contenido y hash.

## Ejecutar pruebas

Desde la raíz del repositorio, con Python 3.11 o posterior y biblioteca estándar:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
```

Las 23 pruebas de persistencia usan bases temporales: criterios nuevos vacíos, literales y procedencia, conflictos, copia e historia inmutables, reintentos exactos e históricos, revisiones obsoletas, dos conexiones concurrentes, fallo inyectado antes del commit, reapertura, corrupción y rechazo de bases ajenas/incompatibles. La prueba de rollback no simula pérdida eléctrica ni certifica durabilidad del sistema operativo. Se usa un archivo nuevo o `:memory:`; no se ofrece migración de bases preexistentes.

La prueba de concurrencia cubre actualizaciones de un borrador ya creado mediante dos conexiones locales. No certifica creación simultánea de esquema, servidores distribuidos, autorizaciones, publicación o invalidación de todo el grafo financiero.

## Estado y límites

T01 implementa parcialmente recepción y persistencia del plan técnico; no cierra módulos financieros ni casos de aceptación del producto. Todos los snapshots mantienen `PENDING`, `run_ready=false` y autorización operativa no otorgada. La autorización para escribir código es distinta de la autorización para usar el modelo en producción.

Pendiente: lectura de hojas reales y adaptación controlada de sus formatos, normalización explícita, motor de dependencias, cálculos integrados, comparación contra criterios suministrados, revisión autenticada y PDF externo de una página. Las tareas técnicas independientes pueden continuar; las reglas sin definición o evidencia permanecen bloqueadas. No hay servicio, API, despliegue, evaluación de inversiones ni conexión a datos reales.

Los originales, R01/R02, plantilla vacía y fotografía I01 se conservan intactos. El informe `backup-restoration-I01.json` documenta restauración temporal de los 208 archivos del commit I01 y sus 26 suites usando las dependencias Python de este entorno; no certifica instalación desde un sistema limpio ni recuperación histórica.

## Adaptador de archivos sintéticos

`miniuw_foundation.intake` recibe bytes UTF-8 con sobre JSON `schema=miniuw.synthetic-claims.v1` y una lista `claims`. Cada declaración exige exactamente `claim_id`, `slot_kind`, `slot_id`, `literal`, `unit_literal`, `currency_literal`, `period_literal` y `definition_ref`; los valores ausentes se expresan como null, no se omiten. El adaptador deriva SHA-256 de los bytes y localizadores JSON Pointer `/claims/N/literal`. No conserva una copia duradera de los bytes: el llamador debe preservar su fixture si quiere reproducirlo después. El hash verifica identidad de contenido recibido, no autoría ni validez financiera.

Ocho pruebas adicionales cubren el hash y localizador reales, texto de fórmula sin ejecutarlo, reintentos idénticos frente a contenido diferente, claves JSON duplicadas, UTF-8 inválido, NaN, límite técnico de 1 MiB, campos ausentes, procedencia inyectada y rechazo de lotes completos ante un campo desconocido. Total técnico: 31 pruebas. No acepta hojas de Lorena ni declara completo IMP-01.

Importación: `import_synthetic_claims(store, draft_id, expected_revision=0, operation_id="fixture-1", raw=bytes_del_fixture)`. El borrador se crea previamente con `ContextSeed` explícito. El adaptador no modifica contexto, criterios heredados, reglas o permisos. Una fórmula permanece texto literal, nunca se evalúa.
