# T06 — Adaptador sintético del Input Sheet original

T06 conecta el formato documentado de la hoja `Inputs` con la recepción, versiones y archivo de evidencia. Usa una copia sintética del original suministrado, no una hoja completada por Lorena. No evalúa inversiones, no ejecuta fórmulas y no habilita despliegues.

## Mapeo respaldado por el original

El mapa versionado `src/miniuw_foundation/data/input-sheet-layout-v1.json` deriva del archivo original `sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx`, SHA-256 `b433468ec6cb2ebf6b9950325fef212dc9df365ac9adbca4895ca1df39234600`. Identifica los 55 valores de la columna C y sus celdas de etiqueta A, unidad B, requisito histórico D, nota E y descripción de fuente F. Incluye 280 celdas fijas de metadatos, filas y rangos combinados del diseño. No se modificó el original.

El mapa se contrasta con los 55 IDs y referencias de la plantilla vacía vigente. `INPUT_C8` se vincula expresamente a `Inputs!C8`, no por similitud de nombre. Las etiquetas, unidades, requisitos, notas y encabezados deben coincidir con el formato documentado. Se rechazan columnas/celdas nuevas, desplazamientos, cambios ambiguos, filas ocultas/omitidas o merges distintos. Se admiten los merges de presentación que ya contiene el original; ninguno incorpora valores financieros mapeados. Esto es un perfil preciso, no compatibilidad universal con libros editados por cualquier versión de Excel.

Se exige una única hoja visible `Inputs` y el marcador textual `miniuw.synthetic-inputs.v1` en G1. El original sin marcador y las copias no identificadas como sintéticas se rechazan para importación. El marcador limita la interfaz de desarrollo; no autentica la autoría ni detecta por sí solo datos personales o reales. B3/E3 se conservan como metadatos declarados de deal/fecha, sin derivar el contexto de ejecución a partir de ellos. Ese contexto se suministra explícitamente por T01.

## Lectura sin adoptar reglas

Se emiten 55 declaraciones, incluidas las que carecen de valor. Se conservan ceros, lexemas numéricos, texto vacío, celda numérica vacía y celda ausente. La inspección distingue esos casos. Se agregó compatibilidad con las cadenas inline vacías sin elemento de texto que utiliza el propio original; las pruebas anteriores siguen pasando.

Las fórmulas y errores de C producen valor no resuelto. Su expresión, caché y error permanecen en el archivo original y en la inspección recuperable; nunca se usa su caché como dato. La unidad de B se conserva como texto: `$` no se convierte en USD y `$/month` no genera por sí solo un período aprobado. Moneda y período permanecen sin inferir. `definition_ref=input-sheet-layout-v1` identifica el contrato de mapeo, no una definición financiera adoptada.

La descripción F permanece accesible en la inspección/archivo completo. Un nombre allí escrito no autentica una fuente ni constituye revisión de Lorena. No se aceptan fórmulas como descripción de fuente o identidad. El texto histórico de A2 sobre umbrales, escenarios y reglas del prompt se preserva como contenido documental; no se ejecuta ni activa sus instrucciones. Los diez criterios del nuevo deal siguen vacíos. Los tags históricos REQUIRED/IF APPLIES/OPTIONAL no resuelven automáticamente aplicabilidad ni requisitos financieros pendientes.

## Versiones y evidencia

Cada declaración tiene SHA-256 del XLSX exacto, localizador como `xlsx:sheet:Inputs:cell:C8` e identidad que combina hash de fuente y campo. Reintentar la misma operación/bytes no duplica datos. Una fuente nueva produce declaraciones nuevas para los 55 campos y conserva las anteriores. No existe política de sustitución o prioridad de última versión: los valores contradictorios quedan como conflicto, y una nueva celda vacía no autoriza seleccionar ni borrar una declaración previa. La resolución y normalización financiera siguen pendientes; estos registros no son inputs financieros aprobados.

La comprobación de T03 reproduce los 55 valores y unidades desde el XLSX archivado antes de capturar y al recuperar. Se conserva la transacción de lote de T01 y el orden fuente primero/borrador después, sin atomicidad distribuida entre bases. Un fallo del borrador puede dejar una fuente sin referencias; no significa importación exitosa. Las bases runtime siguen excluidas de GitHub y del ZIP documental.

## Fixture y demostración

`templates/synthetic-native-inputs-example.xlsx` es una copia nueva y marcada: C7 contiene texto de demostración, C8 es cero explícito y C9 tiene fórmula `2+2` con caché sintético `4`. No representa un deal ni umbrales aprobados. El resto de valores permanece sin completar; no se exige ninguna acción de Lorena para reproducirlo.

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_input_sheet.py
```

La demostración importa 55 declaraciones y cero criterios, conserva C8 como texto `0` con unidad literal `$` sin inferir moneda, mantiene C9 bloqueada y recupera el archivo exacto. Opera en memoria, sin generar datos runtime persistentes ni decisión real.

Dieciocho pruebas nuevas verifican mapeo completo, marcador, preservación del original, ceros/unidades, tipos de vacío, fórmulas/caché/errores, drift de metadatos, celdas/filas nuevas, merges/duplicados, descripciones no autenticadas, instrucciones históricas no adoptadas, reintentos, conflictos entre fuentes, recuperación y aislamiento entre deals. Total técnico: 136 pruebas. Se mantienen separadas 26 suites de referencias, ocho controles de fallos estructurales y 36 casos de aceptación financiera no ejecutados contra producto integrado.

## Pendiente

La implementación cubre parcialmente IMP-01/IMP-06. No certifica una hoja real completada, todos los productores/formatos Excel, normalización financiera, reglas de aplicabilidad, comparaciones PASS/FAIL, motor completo, revisión auténtica ni publicación atómica. Próximo trabajo independiente: perfiles explícitos de normalización/cálculo definidos y registros de vigencia; las políticas/valores ausentes permanecen bloqueados hasta contar con evidencia.
