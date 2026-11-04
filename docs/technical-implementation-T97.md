# T97: paquete y recuperación de la página del inversor

T97 conecta la página T96 con ejecución local, ocho artefactos, auditoría por reproducción y recuperación portable. Recibe el mismo expediente sintético T94/T95. Conserva sin cambios las fuentes, resultados, políticas, criterios y renderers anteriores.

La ejecución produce exactamente `case.json`, `results.json`, `execution-evidence.json`, `MiniUW_v1_Resumen.pdf`, `report-manifest.json`, `audit.json`, `schedule-review.txt` y `package.json`. Hay un solo PDF de una página. Los otros archivos son evidencia interna. El PDF incluye aportes, cobros, caja neta y cobros operativos por año de la ventana suministrada; CoC/capital/retorno personal siguen pendientes cuando faltan sus bases.

El bundle T97 encapsula el bundle T95 íntegro y agrega el manifiesto T96 y la huella del PDF. Fija las versiones de transportador, renderer, definiciones y lector de inventario. Recuperar exige primero reproducir el resultado padre desde sus bytes exactos y después regenerar la página desde ese resultado. No basta con recalcular hashes después de alterar una cifra o un manifiesto. No se interpretan fechas o etiquetas de revisión como autenticación financiera.

El contenedor completo y cada artefacto están limitados a96MiB; fuentes y formatos internos conservan también sus límites anteriores. El contenedor T97 no es un bundle T95 intercambiable: cada API exige su esquema. La recuperación devuelve bytes del caso, resultado T94 y reporte T96; no restaura servicios, sistema operativo, aplicación histórica o bases de datos. Requiere código y dependencias compatibles.

La auditoría de carpeta exige ocho archivos regulares, nombres exactos, siete entradas únicas en el manifiesto del paquete y coincidencia de bytes/longitudes/hashes. Luego reproduce todo el paquete y lo compara. Rechaza archivos faltantes, adicionales, enlaces simbólicos, rutas ajenas y contenido adulterado incluso si el inventario fue rehasheado. Una coincidencia técnica no equivale a auditoría financiera independiente.

La escritura se prepara en un directorio temporal hermano y se entrega con rename tras escribir y sincronizar cada archivo. Un reintento idéntico verifica los ocho bytes; una carpeta diferente o incompleta se conserva y se rechaza. Si falla el rename se limpia sólo el temporal propio. Este comportamiento está acotado a escritura local sin concurrencia productiva; no es una transacción entre servicios.

El comando nuevo `tools/investor_miniuw_v1.py` ofrece `run` y `audit`. El comando anterior de renovaciones conserva T95; los hitos y snapshots D04–D07 permanecen intactos. T97 no modifica cálculos, adopta bases de capital ni selecciona una TIR puntual. Decisión PENDING, sin despliegue ni uso real. Los54 mapeos semánticos, datos de Lorena y aceptación financiera mantienen sus pendientes.
