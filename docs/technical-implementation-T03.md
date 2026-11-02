# T03 — Archivo durable de evidencia sintética

T03 agrega `miniuw_foundation.archive`, un archivo SQLite local separado de la base de borradores T01. El alcance sigue siendo desarrollo con datos sintéticos, sin despliegue ni decisiones reales. Es infraestructura parcial de IMP-01/IMP-06, no cierre del motor financiero.

## Qué conserva y comprueba

Las fuentes se guardan como bytes originales, identificadas por SHA-256, sin convertir espacios, números, fórmulas o unidades. Solo se admiten sobres JSON con el esquema sintético explícito de T01. Esta marca delimita la interfaz; no es un detector de datos reales, un filtro de privacidad ni autenticación de autoría. Los hashes identifican contenido y detectan cambios; no prueban aprobación profesional.

Cada paquete de ejecución incorpora el snapshot completo de inputs, su identidad y hash, el grafo con sus definiciones, el código de ejecutor requerido, el resultado sintético y el inventario de fuentes. Antes de guardar se reproduce la ejecución y se comprueba que todas las declaraciones del snapshot completo, incluidas las no usadas por el grafo, coincidan con los bytes archivados y sus localizadores. Un hash declarado sin fuente disponible no basta.

La recuperación comprueba hashes, inventario, grafo, fuentes y reproducción del resultado. Las declaraciones falsas o localizadores que no existan en la fuente bloquean el paquete. Una modificación accidental de los objetos no se repara ni sobrescribe silenciosamente. Los paquetes se identifican por contenido y los reintentos idénticos conservan un solo objeto. Las revisiones antiguas siguen disponibles aunque avance el borrador.

`load_execution` requiere el código de ejecutor correspondiente a la versión archivada. Si cambia, no reinterpreta el paquete como si fuera equivalente: exige la versión compatible. `read_bundle_bytes` permite recuperar los bytes comprobando únicamente su hash; no certifica reproducción ni vigencia. No se ha construido migración entre versiones de código/esquema.

## Integración y límites transaccionales

`archive_and_import` guarda primero la fuente y después usa la importación transaccional de T01. Son dos bases y no existe transacción distribuida: si falla el borrador, puede quedar una fuente sin referencias. Esta fuente se conserva para recuperación; no representa importación exitosa ni se elimina automáticamente. Si falla guardar la fuente, no se intenta importar.

La inserción de cada fuente y la captura de cada paquete tienen rollback local. La captura comprueba fuentes e inserta el paquete en una transacción del archivo. Los argumentos snapshot/grafo/ejecución son inmutables; guardar un paquete histórico no afirma que el borrador siga en esa revisión. La recuperación tampoco declara vigente una ejecución frente a la cabecera actual. Para observar cambios se usa T02; la publicación atómica sigue pendiente.

El archivo no es autenticación, almacenamiento cifrado, servicio remoto, respaldo completo del VPS ni aplicación histórica restaurada. No se prueban aquí cortes eléctricos o fallos de disco. No existe API de modificación/borrado de objetos ni recolección automática de fuentes sin referencias. Las bases runtime siguen excluidas de GitHub y del ZIP documental; quien use archivos persistentes debe respaldarlos por separado con una copia consistente de SQLite. Todas las pruebas y demostraciones actuales usan ubicaciones temporales y las eliminan al terminar.

## Ejecución y evidencia

Desde la raíz del repositorio, con Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_archive.py
```

La demostración importa un fixture, archiva su ejecución, obtiene una copia consistente de SQLite, cierra las conexiones originales y recupera desde otro archivo. Comprueba los bytes originales, snapshot y ejecución, y reproduce longitud de texto 3. Mantiene PENDING y producción desautorizada; no evalúa una inversión.

Las 22 pruebas T03 cubren preservación exacta de bytes, idempotencia, reapertura, copia/restauración, avance de borrador, evidencia ausente, datos/localizadores falsos, resultados adulterados aun con hash actualizado, corrupción, cambios de versión, rollback, dos escritores, fuentes sin referencias, importación reintentada, paquetes pendientes vacíos, bases incompatibles y copias inmutables. Total técnico: 74 pruebas (31 T01 + 21 T02 + 22 T03). No sustituyen las 26 suites de referencias ni los 36 casos de aceptación financiera todavía no ejecutados contra producto completo.

## Próximo trabajo independiente

Adaptadores sintéticos adicionales de hojas y conexión de perfiles de cálculo definidos, con tratamiento explícito de unidades y calendarios. Permanecen abiertas las políticas/reglas sin evidencia, revisión auténtica, integración de todos los contratos, publicación atómica, PDF externo y habilitación operativa. No se adoptan datos ni criterios de Lorena por defecto.
