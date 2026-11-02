# T43–T44 — costos explícitos de venta dependientes del precio

Se implementan perfiles sintéticos acotados para M7-06 (docs/model-hold-exit-returns.md): inventario de cargos y conexión con el cierre. No se adoptan comisiones, tasas fiscales, mínimos históricos o reglas legales por defecto.

## T43: inventario y cálculo

La fuente declara contexto sintético, moneda/fecha, precio bruto proyectado con metadatos y un inventario de hasta 64 cargos. Necesita declaración de completitud, base del inventario y referencia de no superposición. La declaración no verifica que se hayan identificado todos los cargos reales ni que no se dupliquen conceptos económicos; esos controles siguen pendientes de evidencia.

Cada cargo tiene ID único, clasificación (costo de transacción, impuesto u otro), perfil (fijo o fracción del precio bruto), aplicabilidad, justificación, unidad/moneda/fecha/fuente y valor racional explícito. El costo fijo es su valor; el porcentual es precio bruto × fracción declarada. No se interpretan números como porcentajes enteros, no se aplican porcentajes a precio neto ni a otros cargos, y no se inventan mínimos, máximos, tramos, redondeo monetario o conversión de moneda. Una fracción mayor de 1 no se recorta por una política no declarada; puede generar déficit de cierre.

Un cargo incluido requiere valor no negativo y metadatos completos, incluido cero. Un cargo no aplicable exige justificación/fuente y valor ausente; no se descarta silenciosamente un monto suministrado. Aplicabilidad sin resolver, valor requerido ausente, incompatibilidad de moneda/fecha/unidad/fuente o inventario incompleto bloquea el total, aunque se conserven filas calculables para auditoría. No se publica un subtotal parcial como costo completo. Un inventario vacío solo produce cero si se declara completo y con sus bases explícitas; no es un valor por defecto para un deal real.

Los impuestos pueden representarse únicamente como hipótesis explícitas dentro del perfil fijo/fracción. Un impuesto sin regla/aplicabilidad definida queda pendiente y bloquea el total. El perfil no verifica ley fiscal, exenciones, jurisdicción ni base imponible; no sustituye reglas fiscales no lineales o contratos. La aritmética exacta acotada bloquea al excederse.

## T44: costo calculado al cierre guardado

Se reproducen T41 y todo el inventario T43, junto con la evidencia base T36. Los hashes de fuente/resultado, contexto, moneda, fecha y precio deben coincidir. El precio de costos debe referenciar exactamente el resultado de valoración usado; no se admite un costo calculado con otro precio o corrida aunque parezca compatible.

Solo con total completo se genera la declaración de costos para el T42 existente. T42 sigue requiriendo hipótesis explícita de venta a valor y otras fuentes fijas, preserva conflictos de valoración y recorre cierre/deuda/caja/capacidad. El total calculado reemplaza, bajo la revisión explícita, el claim de costos de cierre; no se añade además del costo anterior. No se compensan automáticamente cargos contra proceeds brutos. Cada costo y el precio mantienen su procedencia; no se transforma el valor del activo en cobro real verificado.

Se conservan el bloqueo bancario original, aporte adicional bruto con su target/hipótesis, criterios vacíos y estados PENDING. Retorno personal, impuestos/pagos reales, disponibilidad de fondos y aprobación no se infieren. El inventario de cargos de cierre es distinto de principal/intereses/fees bancarios presentes en el payoff: su no duplicación necesita clasificación explícita; no se verifica por nombres similares.

## Validación y límites

Pruebas independientes de fijo + fracción × precio, cargos múltiples, cero/ausente/no aplicable/no resuelto, inventario, metadatos, linaje de precio/corrida, costo repetido y retorno recalculado. Replay rechaza resultados alterados aun con hashes actualizados; agotamiento de presupuesto se comprueba por inyección. El demo conserva fuentes originales y muestra hipótesis sintéticas separadas, sin adoptar tasas o reparar el proyecto previo.

Sin nuevas reglas fiscales, escenarios de mercado completos, fechas alternativas, precio/exit cap de equilibrio global, reparto LP/JV, despliegue o decisiones reales. No hay bundle SQLite runtime nuevo ni cierre de casos financieros originales. Las evidencias compactas se regeneran desde fuentes/especificaciones conservadas.
