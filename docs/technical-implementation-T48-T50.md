# T48–T50 — mínimos y topes explícitos por cargo de venta

Extiende M7-06 dentro del Mini-UW de renta/refinanciación/venta. Son reglas sintéticas suministradas, no comisiones, contratos o leyes adoptados. Se conservan T43–T47 y sus ejemplos; no cambia una política existente.

## T48: cargo calculado y límites monetarios por ítem

Se reproduce exactamente la fuente/resultado completo de cargos T43. Una especificación liga ambos hashes y declara inventario/bases de reglas para cada cargo incluido. No se aplica un mínimo a la suma de todos los cargos ni se convierte un tope monetario en porcentaje. Los cargos expresamente no aplicables se conservan fuera del cálculo; un impuesto no resuelto en T43 sigue bloqueando el total.

Cada mínimo y máximo declara si está habilitado, deshabilitado o sin resolver. Habilitado requiere valor monetario no negativo, moneda/fecha/fuente; deshabilitado exige ausencia de monto y fuente explícita de esa condición. Un estado o valor requerido ausente no equivale a límite ilimitado o cero. El mínimo no puede superar el máximo; el conflicto bloquea sin reordenar cifras. La base de la regla y metadatos son obligatorios.

Para cada cargo, se calcula primero su fórmula original y luego se aplica mínimo, si está habilitado, y máximo, si está habilitado: min(max(cargo, mínimo), máximo). Con mínimo ≤ máximo, ese clamp no altera el orden de otros cargos ni supone condiciones contractuales adicionales. Se conservan monto original, monto limitado y todos los límites empatados, incluido empate con la fórmula original. Un tope de cero explícito es conocido. No se redondean centavos ni se inventan tramos, condiciones de pago o jurisdicción.

El total solo se entrega si la fuente base y todas las reglas necesarias son compatibles/completas. Filas calculables pueden mostrarse para auditoría con bloqueos, pero no se publica un subtotal como total. La aritmética racional acotada bloquea al excederse. La clasificación/no superposición con payoff bancario sigue siendo una hipótesis suministrada, no un control económico autenticado.

## T49: costo limitado al cierre y retorno

Se reproducen NOI/valor T41, costos T43, reglas/resultado T48 y evidencia de proyecto T36. Se verifican siete bindings, precio de la misma corrida, contexto, moneda, fecha y linaje. Solo con total completo se genera una declaración de costo para el T42 existente. Este conserva hipótesis de venta a valor, valoración previa, deuda fechada, continuidad de caja, capacidad de refinanciación, targets de aporte y demás bloqueos.

El total limitado reemplaza el costo anterior una vez; no se suma además de él ni se netea contra el precio bruto. Precio, cargo original, límites y resultado conservan sus fuentes. Un mayor precio puede activar otro tramo del mínimo/tope; debe recalcularse toda la cadena con los inputs de ese punto.

No se traduce este perfil a cargos fijos T43 para presentarlos como una función afín global. T49 tiene un tipo distinto de T44, y el análisis afín T45 no lo acepta. Un cálculo en un precio no prueba el rango de recuperación con mínimos/topes; ese análisis por tramos queda pendiente. La compuerta de vigencia T47 sigue limitada a su perfil T44: el cálculo T49 declara que no comprobó vigencia; su salida actual usa la nueva conexión T50. Ninguna ruta autentica documentos o revisión profesional.

## T50: vigencia de la nueva salida

Se reproduce T49 y el registro T46 al instante UTC explícito. Se exigen todos los bindings técnicos del nuevo perfil, incluyendo la fuente de mínimos/topes y la especificación T49; son 22 en el ejemplo. Cambios de regla, hash, localizador o contexto, evidencia vencida/estimada/sustituida/sin revisar e inventarios incompletos dejan la salida pendiente. La vigencia de los demás 21 bindings no permite omitir las reglas nuevas.

Cuando la evidencia sintética y el cálculo son compatibles se expone la historia del equity del proyecto, con fechas/aportes/cobros, IRR, stocks declarados, riesgos y detalle de cargos/límites. Ante vencimiento el nuevo resumen se omite sin cambiar la matemática histórica ni sus fallos conocidos. No se verifican originales externos ni contratos; el estado decisorio sigue PENDING. No hay reloj implícito, monitor o publicación financiera autorizada.

## Validación y límites

Se verifican mínimos/topes deshabilitados, activos, cero y empates, conflictos/ausencias/metadatos/inventarios, fuente/corrida de precio y cambio de costos por precio. También se comprueba el binding adicional de reglas, su vigencia y la conservación del cálculo histórico. Reproducción completa rechaza resultados adulterados con hashes actualizados. Las pruebas de presupuesto inyectan agotamiento; no validan contratos reales. El demo usa cifras sintéticas explícitas y conserva los fallos del proyecto original.

Sin tasas por defecto, ley fiscal o contrato validado, nueva financiación, reparto LP/JV, escenario de mercado completo, bundle SQLite runtime, despliegue o decisión real. El retorno personal y el cierre financiero permanecen pendientes.
