# T41–T42 — NOI forward y exit cap hasta venta hipotética y retorno guardado

Requisitos de origen: docs/model-hold-exit-returns.md, fila M7-05 y sección de salida, distinguen NOI forward, precio candidato, cobro de venta, liquidación de deuda y proceeds al inversor. Se implementa un perfil sintético acotado, sin adoptar modelo de valoración, fuentes reales o reglas fiscales.

## T41: valoración condicionada

Entrada: fuente/resultado NOI T19 reproducidos exactamente y especificación que liga ambos hashes, contexto, moneda, fecha de valoración, período forward y cap con unidad/período/fuente. La ventana suministrada debe comenzar en la fecha de valoración y terminar en la misma fecha del año siguiente. No se anualiza automáticamente un NOI trimestral ni se altera un calendario de fin de mes/bisiesto: el 29 de febrero sin fecha aniversario válida requiere otro perfil explícito. La comprobación de fechas no verifica que el NOI declarado cubra realmente esos doce meses; eso requiere fuente y revisión de alcance.

Valor candidato = NOI forward / exit cap, con NOI no negativo y cap estrictamente positivo. El NOI cero puede producir valoración matemática cero dentro de esta hipótesis, no evidencia de un precio comercial. No se recorta NOI negativo ni se usa un cap cero para fabricar valor. Se conservan impuestos/costos condicionales del productor NOI T19 sin atribuirles validez legal. Períodos, moneda, hipótesis, unidades o fuentes faltantes/incompatibles bloquean. La aritmética exacta tiene límite y bloquea al excederse.

El valor no es caja: T41 no produce proceeds, distribución, tasación autenticada ni precio de mercado. La procedencia de NOI, la base de valoración y la compatibilidad temporal se conservan; ningún forecast se agrega a las distribuciones del período operativo.

## T42: hipótesis explícita de venta a ese valor

Se exige evidencia completa T36, fuente/resultado T41 reproducidos, hashes ligados y referencia explícita de la hipótesis sintética de venta a valor. Deben coincidir contexto/moneda y fecha de valoración/venta. Sin esa hipótesis no se convierte una valoración en proceeds, aunque el valor sea calculable.

Si el cierre ya contiene una declaración de valoración, debe estar completa, ser compatible y coincidir con el valor calculado. Una diferencia bloquea antes de compilar; no se borra ni se reemplaza por preferencia del cálculo nuevo. Un cierre sin declaración de valoración puede recibir la hipótesis nueva sin inventar una declaración histórica. El demo compatible usa expresamente otra fuente sintética de cierre sin esa declaración; el original con valor declarado 500 permanece intacto y conserva sus conflictos/bloqueos.

Bajo esa hipótesis solamente, se genera una declaración de proceeds brutos proyectados con referencia al resultado T41 y a la hipótesis. Se recibe por separado una declaración completa de costos de cierre y otra referencia que mantiene las demás fuentes fijas; costos faltantes no se convierten en cero ni se deducen de un porcentaje histórico. La hipótesis de financiación sigue explícita o ausente.

La fuente generada recorre T39: cierre, deuda fechada, continuidad de caja, capacidad de refinanciación y targets vacíos del inversor. No se suma el valor por segunda vez como receipt del inversor ni se distribuye el NOI forward como si fuera caja cobrada después de vender. Las reservas/caja previa se concilian una vez. Si el préstamo original sigue superando capacidad, el valor puede mostrarse pero no se publica un retorno nuevo.

Se preservan la fecha de cierre, obligaciones, operación y refi; no se modelan respuestas del precio en impuestos/fees, demoras, planes alternativos de financiación o construcción histórica. El perfil no calcula un exit cap/precio de equilibrio completo ni un escenario Downside aprobado. Retorno personal, pérdida económica definitiva, aprobación y fondos reales siguen pendientes. Condominios/Full UW permanecen fuera de esta ampliación.

## Validación y recuperación

Las pruebas verifican división exacta e independiente, cero/negativo/cap indefinido, límites de calendario, unidades/períodos/fuentes, hipótesis de venta obligatoria, costo ausente, bloqueo bancario preservado, ausencia de doble cuenta y replay de reportes adulterados incluso con hash actualizado. Las pruebas de agotamiento T41 inyectan una falla del presupuesto; no certifican escenarios financieros reales. Se conservan hashes/definiciones y evidencia compacta regenerable desde fuentes y especificaciones. No se agrega un bundle SQLite runtime ni se cierran los casos de aceptación financieros originales.
