# T93 a T95 Renovaciones de seguros y retorno del Mini-UW

## T93 Pólizas sucesivas y cuotas agrupadas

El perfil recibe un calendario agregado T90 y un libro sintético de pólizas para ese mismo concepto, contexto y moneda. Las pólizas se suministran en orden, con ventanas sucesivas, sin gaps o solapamientos, que particionan toda la ventana operativa. Este perfil de sucesión temporal no valida suficiencia de cobertura, riesgos, deducibles o condiciones contractuales; pólizas simultáneas/complementarias y cobertura fuera de tenencia requieren otro alcance.

Cada prima bruta no negativa tiene fuente y fracciones explícitas por intersección con los períodos operativos. Las intersecciones y su inventario son exactos; las fracciones de cada póliza suman uno y no se deducen de días. Se calcula prima por fracción y se exige que la suma por período coincida con el gasto agregado T90 que T91 ya liga al NOI/T76. Un costo cero conserva inventarios y fracciones explícitos. Una prima o fracción faltante bloquea todos los importes exportables; no se toma como cero.

Las cuotas de cada póliza se suministran por separado, con importe, fecha y fuente. Pueden vencer después del fin de esa póliza si siguen dentro de la ventana de caja operativa suministrada; la fecha no se interpreta como mora, financiación o penalidad. Todas las cuotas liquidan la prima completa en esa ventana. Los grupos explícitos asignan cada cuota exactamente una vez a una cuota agregada T90 de la misma fecha. Su suma debe coincidir con el importe agregado; no se infiere la partición de un pago ni se permite compensar diferencias entre grupos. T91 conserva el mapa agregado → pago planificado T76. No se genera otro gasto o pago.

## T94 Ejecución completa y vigencia

La entrada única contiene el expediente con calendarios T91, libros de todas sus filas de seguro, registro de fuentes y UTC. Se reconstruyen T91 y T93; todo seguro debe tener exactamente un libro compatible con el hash de su fuente T90. Contexto, moneda, concepto, inventarios, ventanas y cuotas deben coincidir. El retorno se conserva únicamente si toda la cadena concilia; falta o diferencia en una renovación retira retorno y métricas actuales. Los insumos y pruebas históricas permanecen recuperables.

La vigencia exige todos los requisitos del padre, el expediente T91 completo y cada libro. El ejemplo conserva 43 vínculos de fuente al mismo UTC explícito. Una fuente cambiada, vencida, pendiente o sustituida en cualquier nivel retira las cifras actuales. No se renueva autoridad o vigencia por modificar el libro o el calendario agregado. Los criterios del deal conservan su propia evidencia y sus pendientes.

## T95 Una página y recuperación

El paquete portable conserva bytes exactos de entrada, resultado y versiones de motor/definición; recuperar requiere reproducción completa. Cambiar un resultado y actualizar su hash no sustituye el replay. Casos compatibles y bloqueados se conservan. El renderer público reproduce T94 antes de usar la utilidad de página T86; el manifiesto identifica el nuevo control, la entrada y sus cifras. El resumen tiene una página y muestra el retorno condicionado o PENDIENTE con cifras retiradas.

Una orden local produce ocho archivos: case.json, results.json, execution-evidence.json, MiniUW_v1_Resumen.pdf, report-manifest.json, audit.json, schedule-review.txt y package.json. Se verifican inventario regular, hashes, una página/texto y reconstrucción integral. La salida se materializa completa desde un temporal hermano; repetición idéntica verifica bytes y una salida diferente/incompleta no se sobrescribe. Los límites de datos/aritmética/tamaño/layout rechazan sin truncar. Es comprobación técnica determinista; auditoría financiera y publicación productiva concurrente siguen pendientes.

## Ejemplos y pendientes

Dos pólizas de prima10 cubren enero–abril y abril–julio. La primera declara cuotas5 en marzo y5 en junio; la segunda10 en junio. El grupo de junio suma15 y coincide con el pago agregado existente. Gasto10/10, pagos5/15 y retorno778 sobre aportes1.400 se conservan; no hay doble gasto o pago. El vencimiento posterior a cobertura es un dato sintético suministrado, sin afirmar cobertura legal o permiso contractual.

Una revisión independiente declara prima de renovación12, gasto10/12, cuotas agregadas5/17 y fuentes completas de NOI/caja/venta/evidencia compatibles. Los cobros pasan a776 y el resultado a−624, contando el costo adicional2 una vez. No es una predicción de prima ni una optimización para conseguir PASS.

Pólizas superpuestas, créditos/cancelaciones/reembolsos, obligaciones/prepagos fuera de ventana, autoridad real, cláusulas, impuestos/contabilidad aplicables, capital/equity/CoC/retorno personal y validación financiera permanecen pendientes. Los 55 campos no quedan completamente conectados por este bloque. PENDING, sin despliegue ni decisiones reales; originales/I01 y rutas anteriores preservados.
