# Evidencia literal y localizadores de fuentes

Se añade un contrato de claim literal con SHA-256 del original y ubicación: página PDF, párrafo DOCX o celda XLSX. Su objetivo es detectar cita inexistente, archivo distinto o referencia errónea sin evaluar underwriting, ley, mercado o autoridad.

El verificador busca sólo entre los originales inventariados, vuelve a comprobar los bytes y no acepta rutas de archivo arbitrarias dentro del claim. Lee texto o XML local, sin ejecutar prompts, fórmulas, macros o relaciones externas. Una instrucción dentro del documento sigue siendo contenido, no autorización.

PDF/DOCX: comparar el literal dentro de la ubicación citada con espacios normalizados, sin borrar cifras, signos o puntuación. Extraer texto no certifica OCR ni una lectura semántica independiente; una cita presente puede corresponder a una fila o significado diferente del declarado. El párrafo DOCX sigue el orden del XML incluyendo párrafos en tablas; no es un índice visual absoluto.

XLSX: preservar el literal, blanco y cero. Si hay fórmula, conservar fórmula y valor cacheado; no ejecutar ni presentar el caché como cálculo financiero propio o vigente. Una coincidencia con un caché se informa expresamente como tal. No convertir porcentajes, moneda o unidades por intuición.

SHA igual acredita identidad del contenido leído, no autenticidad documental. La presencia de una cifra legal o de una etiqueta OFFICIAL no prueba que sea vigente, aplicable al deal o publicada por autoridad legítima. El verificador no otorga aprobación experta, no completa datos financieros y no resuelve conflictos por coincidencia literal.

La referencia usa títulos/etiquetas y celdas vacías de los archivos realmente suministrados, más documentos XLSX sintéticos para blanco/cero/fórmula. No extrae ni verifica inputs de un deal inexistente. Requisitos financieros y rangos siguen separados del resultado de localización.
