# T04 — Hojas CSV sintéticas con procedencia exacta

T04 agrega lectura de hojas CSV de prueba y su conexión con T01/T02/T03, sin ejecutar fórmulas ni decidir sobre inversiones. No presupone que Lorena deba cambiar el formato de su hoja: el lector de Excel/XLSX real sigue pendiente. Los originales entregados no se modifican.

## Contrato explícito del formato de prueba

Los bytes deben ser UTF-8 sin BOM, con separador coma y comillas dobles según el lector CSV estándar de Python. No se infieren separador, columnas, configuración regional, moneda ni unidad. La primera fila lógica contiene únicamente `miniuw.synthetic-sheet.v1`. La segunda fila contiene exactamente estas ocho columnas, en este orden:

```text
claim_id,slot_kind,slot_id,literal,unit_literal,currency_literal,period_literal,definition_ref
```

Las siguientes filas contienen declaraciones explícitas. `slot_kind` es `input` o `criterion`; `slot_id` debe existir en la plantilla de 55 campos/diez criterios para que la importación tenga éxito. No se crean campos por aproximación de nombres. El archivo de ejemplo es `templates/synthetic-sheet-example.csv`; contiene solo texto de demostración, sin umbrales activos.

Cada celda conserva su texto. `0` permanece texto cero, una celda vacía permanece cadena vacía y `\N` representa nulo explícito (una sola barra invertida seguida de N en el archivo). Para expresar una barra inicial literal se duplica: `\\N` en el archivo produce texto `\N`, no nulo. Cualquier otra barra inicial sin duplicar se rechaza para evitar interpretar escapes ambiguos. Las barras internas se conservan sin cambios. Identidades nulas o vacías no son válidas.

No se convierten decimales, porcentajes, fechas, monedas o unidades, ni se ejecuta texto que empiece por `=`, `+`, `-` o `@`. Los espacios se conservan. Las filas vacías o con columnas faltantes/extra se rechazan, sin saltarlas silenciosamente. Una hoja sin declaraciones también se rechaza. Límites técnicos: 1 MiB de fuente, 10.000 declaraciones y 65.536 caracteres por celda; no son límites financieros ni tolerancias del modelo.

## Evidencia e integración

Cada declaración recibe el SHA-256 de todos los bytes originales y un localizador como `csv:record:3:column:D`. El número identifica el registro lógico CSV, incluyendo marcador y encabezado; no es necesariamente el número de línea física, porque las celdas entrecomilladas pueden contener saltos de línea. D es la columna literal. Esta definición permite recuperar sin ambigüedad la celda con el mismo parser.

`sources.parse_source_claims` e `import_synthetic_source` admiten los dos formatos sintéticos explícitos: JSON de T01 y CSV de T04. No existe fallback de un esquema rechazado a otro: las fuentes que empiezan por objeto JSON se validan como JSON; las demás deben presentar el marcador CSV válido. La API JSON anterior permanece disponible sin cambios.

`archive_and_import` ahora admite ambos formatos. T03 conserva los bytes CSV exactos y verifica que las declaraciones/localizadores del snapshot correspondan a esos bytes, tanto al capturar como al recuperar la ejecución. Un mismo snapshot puede contener fuentes JSON y CSV. La tabla de objetos no cambia ni requiere migración. Los paquetes JSON anteriores siguen pasando las pruebas de recuperación.

Se conserva la semántica transaccional anterior: primero fuente, después borrador. Si falla un lote por slot desconocido, revisión obsoleta o identidad duplicada, el borrador no cambia; puede conservarse una fuente sin referencias. Los reintentos exactos no duplican declaraciones. Un cambio de bytes bajo la misma operación se rechaza, incluso si solo cambian los finales de línea. No se elige la última fila como ganadora ante valores contradictorios.

## Reproducir y validar

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_sheet.py
```

La demostración lee el ejemplo, importa una declaración, ejecuta longitud de texto 3, archiva y recupera sus bytes y resultado. Usa bases en memoria; no genera archivos runtime ni produce una decisión real.

Las 22 pruebas nuevas cubren ceros/vacíos/nulos, comillas y multilinea, Unicode, fórmulas literales, escapes, metadatos sin defaults, marcador/esquema, columnas/filas inválidas, UTF-8/BOM, límites, IDs duplicados, campos desconocidos, conflictos, reintentos, criterios vacíos por deal, recuperación CSV, mezcla JSON/CSV y la API directa. Total técnico: 96 pruebas; las 26 suites de referencia y los ocho controles estructurales siguen separados. No se ejecutaron los 36 casos de aceptación financiera contra un producto integrado.

## Pendientes

Lector XLSX con referencias de celdas y manejo expreso de fórmulas/cachés, normalización de unidades y períodos, perfiles financieros definidos, grabación atómica de vigencia y publicación, revisión auténtica y habilitación operativa. T04 cubre parcialmente IMP-01/IMP-06. No activa parámetros históricos, tolerancias, escenarios o políticas no resueltas. Todos los casos siguen PENDING, sin despliegue ni decisiones reales. Las bases runtime siguen excluidas de GitHub y del ZIP documental.
