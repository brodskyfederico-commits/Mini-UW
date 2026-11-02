# Ensayo del comparador con la tabla documentada de Lorena

T14 lee la tabla de umbrales del DOCX original de estándares de Lorena y compara observaciones ficticias de sus diez métricas. Es una prueba de integración del comparador con una fuente documental preservada; no es un Mini-UW completo ni una evaluación real. Los umbrales se cargan sólo para este experimento, sin convertirse en valores por defecto de un deal nuevo.

## Fuente e interpretación controladas

Fuente exacta: `sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx`, SHA-256 `38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9`. El lector rechaza cualquier archivo con bytes diferentes, incluso si conserva el nombre. Verifica la tabla única, sus encabezados, las diez etiquetas y la convención documentada de PASS inclusivo y FAIL estrictamente peor que su nivel.

Cada umbral conserva literal, fracción exacta y ubicación de tabla/fila/celda en `word/document.xml`, con índices desde cero. La convención de operadores conserva su ubicación de párrafo. Porcentajes se dividen por 100 y bps por 10000; los múltiplos mantienen su cantidad. La raya permanece sin valor. Esta comprobación identifica el documento, sin autenticar a su autor ni acreditar vigencia financiera.

## Dos alcances diferentes

El ensayo Base compara las diez métricas contra PASS Base y FAIL Base documentados. Las métricas ficticias vienen de un fixture explícito; no se generan ajustando un deal para hacerlo pasar. Los metadatos compatibles se declaran sólo dentro del perfil sintético y no acreditan definiciones, períodos o cantidades de un proyecto real.

El ensayo conjunto declara Base y Downside y conserva los vacíos documentales. La tabla no tiene columna FAIL Downside y contiene una raya en PASS Downside para asking frente a RLV. El comparador canónico actual requiere condiciones PASS y FAIL en cada fila aplicable. Por eso el ensayo conjunto produce PENDIENTE con diez bloqueos de FAIL Downside y otro de PASS Downside para asking/RLV. No se copia FAIL Base, no se inventa un umbral y no se interpreta la raya como exclusión aprobada.

Esto identifica una limitación de integración del motor actual, no una necesidad de pedir a Lorena que invente una columna FAIL Downside. La evolución debe distinguir condiciones por escenario y completitud de las reglas realmente requeridas. El tratamiento de asking/RLV Downside necesita aplicabilidad explícita antes de excluirlo de un dictamen conjunto. Este bloque conserva el comparador anterior para mostrar la limitación sin adoptar una política nueva.

## Resultados reproducidos

| Ensayo | Resultado simulado | Alcance o causa |
|---|---|---|
| Base con métricas ficticias que cumplen | PASS | Sólo Base; no cubre Downside ni Full UW. |
| Base con YoC ficticio de 5% | FAIL | Menor al FAIL Base documentado de 5,25%. |
| Base con YoC ficticio de 6% | PENDIENTE | Banda entre PASS Base 6,50% y FAIL Base 5,25%. |
| Base con YoC exactamente 5,25% | PENDIENTE | FAIL es estricto; la igualdad no lo cruza. |
| Base con incumplimiento y métrica requerida ausente | PENDIENTE | La ausencia impide el dictamen completo. |
| Base y Downside con métricas ficticias | PENDIENTE | Once bloqueos de condiciones no representadas por el contrato actual. |

En todos los ensayos, la decisión operacional permanece PENDIENTE. No se ejecuta el productor de NOI, TDC, IRR o retornos; se reciben números ficticios expresos. No hay aprobación profesional, publicación de un deal ni despliegue.

## Ejecución y evidencia

Desde la raíz del repositorio:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_documented_threshold_rehearsal.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Fixtures: `templates/synthetic-documented-threshold-base.json` y `templates/synthetic-documented-threshold-full.json`. Ambos exigen identidad SYNTHETIC, escenarios expresos y valores racionales, sin floats. Duplicados, métricas desconocidas, escenarios fuera del inventario, campos adicionales y fuentes sustituidas se rechazan.

El resultado registra hashes de fuente, fixture, caso compilado, ejecución, código experimental, comparador, documentos de definición y política de bandas. El caso compilado puede conservarse y recuperarse con el archivo de screening existente; ese paquete no incorpora automáticamente el DOCX ni constituye un archivo tipado nuevo de todo el experimento. Para reproducir el origen documental hay que conservar también la fuente exacta y el código compatible del ensayo.

Son 17 pruebas técnicas nuevas, 290 en total. Cubren los 30 umbrales/celdas, ubicaciones, escala, fronteras min/max, vacíos, fuente modificada, aislamiento sintético, bloqueos e integración con recuperación. Los seis ensayos son ejemplos ejecutados por el mismo sistema, sin validación financiera independiente. No se cierran módulos o paquetes del plan ni se ejecutan los 36 casos de aceptación financiera originales. D02/D03 conservan por separado sus 56 casos de diseño especificados, aún no certificados contra un producto.
