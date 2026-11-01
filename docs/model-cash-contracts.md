# Modelo: contratos de datos, caja y capital — propuesta de revisión

Estado: diseño documentado, no implementación ni modelo certificado. Fuentes: traspaso actual §§3, 5–7; Master v5.1 §3; Estándares políticas 9–16; Manual físico pp. 7–14 y 50–53; D1 p. 2. Cada contrato se enlaza a filas DAT-01, CASH-01/02, DEBT-01, RETURN-01 y PRICE-01 de la matriz. Reglas no resueltas permanecen sin valor.

## 1. Contrato de cantidad y dimensión (DAT-01)

Cada dato necesita identificador estable, valor literal, valor normalizado si existe, estado, unidad, moneda, base física, período/fecha, aplicabilidad, documento/hash y localizador, transformación y versión. Una cifra derivada conserva todas sus dependencias. La versión aprobada de cada definición se distingue de la versión de fuente y de la revisión de datos del deal.

| Dimensión | Distinciones obligatorias | Pendiente |
|---|---|---|
| Superficie | GSF edificio, NRSF residencial y SF comercial por uso; SF por unit type frente a dormitorio | Mapeo de programa original y reconciliación de sumas |
| Renta | moneda/unidad/mes frente a moneda/SF/mes; comercial moneda/SF/año | Q11 y períodos exactos de ingreso |
| Ratio | fracción dimensional versus presentación porcentual; diferencia en puntos porcentuales versus cambio relativo | PAR-02 y rango de cada variable |
| Tasa | nominal/efectiva, frecuencia de capitalización, día-base y frecuencia de pagos | PAR-03, term sheet y convención de conversión |
| Tiempo | índice mensual, fecha efectiva del evento, TCO, estabilización, refi, maturity y salida | PAR-04; definición de inicio/fin de período |
| Capital | requerido, comprometido, disponible, aportado y aún invertido | Q7/Q8 y reglas de financiación |
| Precio | asking, compra evaluada, soporte bajo objetivos y RLV aprobado | Q3, dominio y restricciones |

Un dato vacío sigue faltante. Un cero explícito se conserva si su fuente lo respalda; no implica validez de dominio por sí mismo. Una métrica no aplicable requiere razón y regla. Conflicto conserva las alternativas. Resultado indefinido conserva causa; no se muestra como cero o infinito.

## 2. Contrato de eventos brutos y cuentas (CASH-01)

El modelo se diseña con eventos brutos, no sólo un neto mensual. Campos propuestos de evento: ID inmutable, deal/run/revisión, fecha y período, tipo, cuenta origen/destino, monto y moneda, liquidación versus devengo, evidencia y clasificación, fórmula si derivado, y relación con deuda/reserva/etapa. Los nombres definitivos del esquema son una tarea posterior; esto no es una migración de datos aprobada.

| Evento/cuenta | Significado | No confundir con |
|---|---|---|
| Aporte de equity | Caja realmente aportada; registrar aportante, monto y momento | Capital prometido o simplemente requerido |
| Distribución a equity | Caja disponible efectivamente entregada | Repago al banco o transferencia a reserva |
| Draw de deuda | Financiación recibida por cuenta/deuda | Ingreso operativo o distribución automática |
| Principal pagado | Reducción de saldo de deuda | Gasto de interés o rentabilidad del inversor |
| Interés pagado/capitalizado | Caja por interés versus incremento documentado de deuda | Una misma erogación contada dos veces |
| Caja restringida | Fondos con uso contractual limitado y su liberación | Caja libre para distribuir |
| Caja operativa | Cobros y pagos del proyecto por período | NOI devengado automáticamente disponible |
| Venta y costo de salida | Cobro del activo y costos separados, con deuda liquidada aparte | Valoración no realizada o proceeds netos duplicados |

La prioridad del waterfall —por ejemplo uso de NOI de lease-up sobrante— sigue pendiente de Q6. El requisito de equity-first histórico no autoriza inventar el orden de todos los usos o reservar caja por intuición. Ausencia de un evento en una lista incompleta no demuestra monto cero.

## 3. Identidades de control propuestas (CASH-02 / DEBT-01)

Estas son identidades contables de conciliación, no políticas de underwriting ni resultados probados sobre un deal.

Sea K la caja total del proyecto, incluyendo libre y restringida. Para cada período documentado:

`K_final = K_inicial + aportes_equity + draws_deuda + cobros_operativos + cobros_venta + otros_cobros_documentados − pagos_desarrollo − pagos_operativos − intereses_pagados − principal_pagado − costos_financiacion_pagados − costos_venta_pagados − distribuciones_equity − otros_pagos_documentados`

Toda partida debe tener clasificación mutuamente excluyente para evitar duplicados. Devengos sin caja no entran como cobros/pagos. Transferencias libre↔restringida se concilian en cada cuenta y se cancelan en la suma total, sin crear retorno del inversor. El detalle de impuestos, fees, reservas y costos capitalizados necesita cierre de inclusiones. No se presupone que la caja final deba ser cero: el residual debe estar explicado y clasificado.

Por cada préstamo:

`saldo_final = saldo_inicial + principal_desembolsado + interes_capitalizado_documentado + otros_incrementos_documentados − principal_repagado − otras_reducciones_documentadas`

Interés pagado no reduce principal salvo aplicación contractual explícita. Una misma capitalización no aparece también como pago de caja sin contrapartida. Amortización determina el patrón de principal; vencimiento determina exigibilidad y posibles balloons. No se inventa refinancing para cubrir un vencimiento.

Fuentes y usos deben conciliar sin ocultar saldos de caja o reservas. La tolerancia de comparación no se fija aquí. Debe ser explícita y aprobada antes de certificar C2.

## 4. Contrato de equity y retornos (RETURN-01)

Mantener por período `aporte_bruto` y `distribucion_bruta`; sólo después derivar `flujo_neto_inversor = distribucion_bruta − aporte_bruto`. Si ambos ocurren en un mes, conservar ambos aunque el neto sea cero. EM usa series brutas bajo definición aprobada; no puede reconstruirse de la parte positiva/negativa del neto. Un valor terminal sólo es distribución realizada si la estrategia/definición lo establece y la salida es consistente.

| Salida | Dependencias y bloqueo |
|---|---|
| Equity hasta estabilización | Cutoff TCO/estabilización/refi y contribuciones incluidas pendientes de Q7 |
| Equity aún invertido | Aportes y recuperación bajo definición aprobada; no equiparar sin más con equity de mercado |
| Equity de mercado retenido | Valor del activo menos deudas aplicables; no es automáticamente capital aún invertido |
| Cash-in refi | Faltante de caja de refinanciación que exige aporte; no inflar distribución con proceeds brutos |
| CoC | Flujo disponible de período definido / capital remanente definido; denominador cero o no aplicable se clasifica |
| EM | Distribuciones/proceeds realizados divididos por contribuciones incluidas; denominador y estrategia explícitos |
| IRR | Serie neta, calendario y dominio explícitos; raíces inexistentes/múltiples/indeterminadas o no aisladas se informan |

La anualización de una IRR mensual y una XIRR sobre fechas irregulares son contratos distintos. No se selecciona una raíz conveniente ni se atribuye unicidad por el mero número de cambios de signo. No se presentan métricas al nivel LP sin estructura JV documentada; nivel proyecto y LP requieren ledgers separados y conciliables.

## 5. Contrato de precio soportado (PRICE-01)

La variable de búsqueda es un precio de compra evaluado, separado del asking. Cada punto del dominio requiere una corrida válida con costos/financiación/refi/operación/retornos dependientes recalculados. El conjunto de objetivos incluye sólo criterios explícitos aplicables: Q3 decide el alcance de RLV, todavía abierto.

El resultado debe separar dominio admitido, conjunto factible, extremos incluidos/excluidos, objetivo(s) y restricciones activas, máximo realmente alcanzado o sólo supremo/límite, falta de solución, indeterminación y evidencia de verificación. Un límite superior no certifica que ese precio pueda pagarse. La monotonía condicionada de referencias anteriores no está reproducida: no hay código de recuperación disponible.

El texto de Q8 opción A usa `(1−LTC)×TDC` aunque solicita Equity/TDC: la expresión es un monto, no un ratio. Se registra la inconsistencia; no se corrige ni aprueba silenciosamente como si el documento hubiera dicho otra cosa.

## 6. Siguiente cierre del modelo

Completar un catálogo por evento/cuenta y una fórmula por salida, con unidad, período, fuente, dominio, precondiciones, dependencias, estado indefinido, reglas de invalidación y caso independiente esperado. Primera secuencia: programa y rentas → operación/impuestos → costos/calendario → deuda/caja → refi → hold/venta → retornos → escenarios/precio → comparación/PDF. La iteración TDC/interés y las valoraciones dependientes de criterios se mantienen como ciclos explícitos, no se esconden con un cálculo lineal.

Faltan decisiones expertas, convenciones y originales. Esta documentación permite avanzar en especificación; no habilita producción ni evaluación de deals reales.
