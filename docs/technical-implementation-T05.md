# T05 — Lector XLSX sintético sin ejecución de fórmulas

T05 agrega un lector OOXML/ZIP con biblioteca estándar para un perfil de prueba explícito. No necesita Excel, no evalúa fórmulas, no recalcula libros y no convierte resultados almacenados en inputs verificados. Sigue el alcance autorizado: datos sintéticos, sin despliegue ni decisiones reales.

## Perfil de entrada implementado

Se requiere un libro XLSX con una sola hoja visible llamada `Synthetic`. A1 contiene texto `miniuw.synthetic-xlsx.v1`; A2:H2 contiene las ocho columnas del contrato CSV T04 en el mismo orden. Desde la fila 3, los registros son contiguos y A/B/C/E/F/G/H contienen metadatos como texto explícito. No se infieren IDs a partir de etiquetas aproximadas. La semántica de nulos y escapes en texto es la misma del formato sintético CSV.

Se leen cadenas inline y cadenas de la tabla compartida, incluidos fragmentos de texto enriquecido compatibles. En D se admiten texto, lexemas numéricos, vacío, celda ausente, fórmula o error Excel. Una celda numérica conserva el texto XML del número, por ejemplo `0`, `001.2500` o `1E-3`; no se redondea, normaliza ni aplica formato de moneda/fecha/porcentaje. El ID de estilo se conserva en la inspección, pero no se interpreta. Esto no permite afirmar que un serial numérico sea una fecha. El texto XML se decodifica conforme al parser XML; los bytes originales completos se preservan por separado.

Las fórmulas en columnas de identidad/metadatos se rechazan: su caché nunca decide a qué campo corresponde un valor. Tipos no soportados, como booleanos, no se convierten por inferencia. Este es un perfil sintético limitado, no un lector universal ni la adaptación final de la hoja real de Lorena. No requiere que ella cambie su formato.

## Fórmulas, cachés y bloqueos

`inspect_synthetic_xlsx` distingue texto, número literal, celda vacía, celda ausente, fórmula y error Excel. Conserva expresión, atributos de fórmula (incluida una fórmula compartida sin expresión local), caché si existe, tipo de celda, estilo y ruta de la parte XML. No reconstruye fórmulas compartidas ni consume el caché como una fórmula propia.

En D, una fórmula o error produce una declaración con `literal=null`, manteniendo SHA y referencia de celda. La ejecución queda bloqueada por valor no resuelto; no reemplaza el dato por cero ni emite FAIL. La inspección recuperable del archivo explica si ese nulo corresponde a fórmula, error, celda vacía o ausente. Una cadena de texto `=1+1` permanece texto; no se interpreta como fórmula XML.

El ejemplo `templates/synthetic-workbook-example.xlsx` contiene texto `abc` en D3 y fórmula `2+2` con caché sintético suministrado `4` en D4. Ese caché es parte del fixture; no se afirma que Excel lo haya recalculado. La demostración recupera el archivo exacto y muestra D4 bloqueada, con input nulo y decisión PENDING.

## Procedencia y archivo

Cada declaración incorpora SHA-256 de los bytes ZIP originales y localizador como `xlsx:sheet:Synthetic:cell:D3`. La inspección retiene además la parte XML correspondiente. El despachador de fuentes y el archivo T03 admiten XLSX junto con JSON/CSV, sin cambiar la base de datos de objetos. Antes de capturar y al recuperar una ejecución se vuelven a leer las celdas del archivo archivado y se comprueba su coincidencia con las declaraciones. Se conservan las APIs y pruebas anteriores.

La importación sigue siendo un lote transaccional T01 y el orden sigue siendo fuente primero, borrador después, sin transacción distribuida entre las dos bases. Puede conservarse una fuente sin referencias si falla la importación; no hay éxito ficticio ni sobrescritura de revisiones. El archivo de evidencia no certifica autoría, revisión profesional, vigencia frente a la cabecera actual ni permiso de publicar.

## Límites técnicos del lector

Máximo 1 MiB de archivo comprimido, 64 entradas ZIP, 1 MiB por parte, 4 MiB expandidos, 10.000 filas de datos y 65.536 caracteres de texto por celda. Se rechazan entradas duplicadas, rutas de escape/absolutas en ZIP, enlaces simbólicos, cifrado y compresión no admitida. No se extrae el ZIP al filesystem. Se rechazan relaciones externas, marcadores conocidos de macros/embebidos, DTD/entidades XML, celdas ambiguas, filas/celdas duplicadas, merges y estructuras ocultas soportadas por el control. No se siguen enlaces ni se ejecuta contenido.

Solo se interpreta XML UTF-8 y los namespaces OOXML transicionales usados por el fixture. Las fórmulas matriciales, cachés, vínculos y estructuras fuera del perfil no se convierten en cálculos del modelo. Estos controles acotan la interfaz de prueba; no constituyen certificación de seguridad para archivos arbitrarios o compatibilidad con todas las variantes de Excel.

## Reproducir

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_workbook.py
```

Las 22 pruebas T05 cubren inline/shared strings, Unicode, números sin formato, distinción entre blancos/ausentes/texto vacío, fórmulas con/sin caché, fórmulas compartidas, errores, metadatos inválidos, esquema/headers, duplicados, filas dispersas, estructuras ocultas/merged, relaciones externas, macros, XML/ZIP inválidos, límites, tipos no soportados, celdas ambiguas, fixture entregado y recuperación de evidencia con caché inactivo. Total técnico: 118 pruebas (96 previas + 22 T05). Se mantienen aparte 26 suites de referencias, ocho fallos estructurales y 36 casos de aceptación financiera sin ejecución contra producto completo.

## Pendiente

Adaptación expresa del formato real de inputs, normalización trazable de unidades/períodos, integración de perfiles de cálculo definidos, vigencia/publicación atómica y revisión auténtica. T05 sigue cubriendo parcialmente IMP-01/IMP-06. No se cierra el motor financiero, no se adoptan criterios ni políticas sin evidencia y no se despliega ningún servicio. Las bases runtime siguen excluidas de GitHub y del ZIP documental; la demostración trabaja en memoria.
