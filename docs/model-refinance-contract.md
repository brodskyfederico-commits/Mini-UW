# M6 — Financiación permanente y refinanciación

Estado: contratos candidatos y referencia matemática aislada; no motor productivo, aprobación bancaria ni revisión financiera independiente. Las fuentes originales se conservan sin activar sus parámetros históricos. Los criterios numéricos de Lorena permanecen vacíos por deal; datos/reglas faltantes dejan PENDIENTE sin PASS/FAIL. Full UW diferido hasta el final.

## Contratos, fuentes exactas y pendientes

| ID | Salida | Fuente / definición pendiente |
|---|---|---|
| M6-01 | Estrategia y fecha del refi | Master §3 Timing/Refinance; Manual p.20 y Q12 p.24. La aplicabilidad y el calendario son entradas expresas. Si la estrategia no requiere refi, justificar no aplicable; no inventar un préstamo. |
| M6-02 | NOI y valor para sizing | Master §3, Value = NOI / refi cap; Inputs C66. Usar NOI admisible y cap de mismo período/alcance; definir si difiere del NOI del inversor. Cap cero o dato faltante bloquea; NOI negativo no produce por sí solo un préstamo negativo. |
| M6-03 | Límite bancario por LTV | Master §3; Inputs C71. Valor admisible × LTV explícito. No confundir con LTC ni tratar límite como desembolso aprobado. |
| M6-04 | Constante de deuda y servicio | Master §3 annual constant; Inputs C69/C70. Especificar tasa periódica, capitalización, pagos/año, amortización, pagos vencidos/anticipados e interest-only si existe. No inferir términos del dato tasa. |
| M6-05 | Límite bancario por DSCR | Master §3, min DSCR; Inputs C72. NOI bancario / (DSCR mínimo × constante anual) bajo denominadores positivos. No confundir DSCR bancario con criterio de inversión de Lorena. |
| M6-06 | Préstamo seleccionado y restricciones activas | Master §3 MIN LTV/DSCR; Estándares políticas 26/30. Menor capacidad de restricciones aplicables y documentadas. Empate conserva ambas como vinculantes; otras restricciones contractuales pueden limitar. Capacidad no equivale a aprobación. |
| M6-07 | Amortización, vencimiento y balloon | Inputs C70; traspaso §5 distinciones de préstamo. Saldo posterior a pagos depende del calendario. Vencimiento menor a amortización exige saldo residual exigible; no inventar refinanciación futura ni extensión. |
| M6-08 | Liquidación de construcción y otras deudas | Master §3 net cash-out; M5-10; Q13 Manual p.24. Payoff = obligaciones expresas a fecha: principal, interés pendiente, fees y otras partidas aplicables, sin duplicar capitalización. Ausencia de campo otra deuda no demuestra monto cero. |
| M6-09 | Costos y reservas de refinanciación | Inputs C73/C74; Estándares políticas 9/10. Costo porcentual requiere base y fecha. Reservas nuevas y liberación de reservas previas se registran por separado; fondos restringidos no son distribución. |
| M6-10 | Caja neta, cash-out/cash-in y estado para M7 | Master §3; Estándares políticas 9/10/12; Q7/Q8. Distribución posible y aporte adicional se determinan después de liquidación, costos y fondos restringidos. Equity recuperado, equity remanente y valor patrimonial son conceptos distintos; bases pendientes. |

La referencia principal es Reglas de la casa v5.1 (SHA-256 95a304fd3e535f16ebd5eb6abf0b223c211f9f596727c878de720779f7ceb701), §3 Refinance and metrics. Los campos del workbook original Inputs!C66, C69:C74 están vacíos (b433468ec6cb2ebf6b9950325fef212dc9df365ac9adbca4895ca1df39234600). Manual físico pp.11/13/20 y Q7/Q8/Q12/Q13 pp.23–24. No se ha recuperado term sheet real para validar estas convenciones.

## Contrato de pago amortizante: hipótesis explícitas

Sólo para préstamo con principal L, tasa efectiva por período i≥0 constante, n pagos vencidos iguales, períodos regulares, sin nuevos draws, fees capitalizados, interest-only, moras ni cambios de tasa. El pago por unidad de principal es:

- si i>0: a = i / [1 − (1+i) elevado a −n];
- si i=0 documentado: a = 1/n, para n entero positivo.

Con m pagos por año explícitamente definidos y régimen uniforme, constante anual K=m×a y servicio anual regular DS=K×L. El período inicial/final fraccionario, pagos adelantados, tasa flotante o período interest-only requieren contrato distinto. No dividir automáticamente una tasa anual por m: la conversión depende de su convención. El servicio de un primer año incompleto tampoco es siempre K×L.

Saldo después de k pagos: principal inicial capitalizado k períodos menos pagos acumulados a la fecha, para 0≤k≤n bajo las mismas hipótesis. Si el vencimiento ocurre antes de n pagos, ese saldo es un balloon; amortizar a n no extiende el maturity. Incluir intereses/fees no pagados en el payoff separado, no agregar otra vez interés ya capitalizado.

Este contrato no incluye una estrategia de cálculo numérico estable para tasas diminutas, n enorme o redondeo contractual de cuotas. Esas condiciones, residuales y precisión deben validarse antes de producción.

## Sizing y restricción vinculante

Con valor V admisible, máximo LTV l, NOI bancario anual N, DSCR mínimo d>0 y K>0 compatibles:

Capacidad LTV = l×V; capacidad DSCR = N/(d×K). Selección candidata L = menor(capacidad LTV, capacidad DSCR), siempre que ambas sean válidas/no negativas y no existan otros límites omitidos.

Si una capacidad es estrictamente menor, se identifica como vinculante; si son iguales se conservan ambas. Una capacidad explícita cero puede producir L=0 dentro de este submodelo, pero DSCR=N/DS con DS=0 es indefinido: no presentarlo como infinito ni 0. Una capacidad negativa no es deuda negativa; clasificar la rama incompatible o pendiente de política. La factibilidad de financiación y el FAIL de inversión no son estados intercambiables.

El límite bancario no aprueba crédito ni prueba que la caja necesaria esté disponible. Comparar el préstamo seleccionado con el payoff y los usos reales; no aumentar el préstamo por necesidad de caja si supera su capacidad.

## Puente de caja del evento de refinanciación

En un evento con todos los conceptos conciliados:

Z = proceeds de deuda recibidos + caja previa libre autorizada + liberación efectiva de reservas − payoff de construcción/otras deudas − costos de cierre pagados − reservas nuevas/restringidas − otros usos expresos.

Si toda la caja residual está permitida para distribución y no existen otras restricciones: distribución D=max(Z,0); aporte adicional A=max(−Z,0). Identidad de control: fuentes + A = usos + D, y D−A=Z. Esto es un caso condicionado; restricciones contractuales o necesidades de liquidez pueden impedir distribuir un Z positivo y requieren separar caja retenida, no forzar D=Z.

Un fee retenido de proceeds brutos se concilia como costo o reducción de proceeds, nunca ambas sin contrapartida. Si el escrow paga el payoff directamente, conservar la liquidación y sus fuentes sin duplicar el pago. Una reserva ya liberada no se suma de nuevo como caja libre previa. Las reservas restringidas no son recuperación de equity.

Ejemplo algebraico de reserva: aumentar un uso restringido en Δ, manteniendo el resto fijo, reduce Z en Δ; puede disminuir distribución o aumentar aporte, pero no altera automáticamente la capacidad del préstamo si las restricciones de sizing son independientes. Si la reserva modifica el préstamo admisible, reejecutar esas dependencias en vez de usar esta propiedad.

## Salida y límites de métricas

Entregar a M7: fecha, deuda permanente y restricciones activas, calendario/convención de pagos y maturity, saldos y ballon si aplica, costos/fees/reservas, payoff cerrado, caja retenida, aporte y distribución brutos, evidencia y versión de cálculo.

El valor patrimonial V−deudas no es capital aún invertido. El denominador de recuperación/cash-in y el capital remanente requieren cierre de Q7/Q8; no restar automáticamente distribuciones de un monto arbitrario para definir el indicador. Si la estrategia no refinancia, registrar aplicabilidad antes de ejecutar o comparar estas métricas.

## Evidencia actual y aceptación pendiente

Referencia propia `references/validate_m6_refinance.py`; resultado `m6-validation.json`. Con fracciones exactas y datos sintéticos: pago contra valor presente de cuotas; saldo por recurrencia contra expresión cerrada; balloon distinto de amortización completa; capacidad y ties LTV/DSCR; conservación de caja y cambios de reservas; rechazo de datos ausentes/dominios inválidos. Es validación algebraica condicionada, no auditoría independiente, préstamo real, implementación productiva ni referencia histórica recuperada.

Pendientes de cierre: contraste con un modelo independiente, tasas/frecuencias y reglas bancarias aprobadas, term sheet con costos/reservas y límites, fechas y aplicaciones de payoff, no-aplicabilidad, pruebas de integración M2/M5/M7, casos con service parcial/interest-only/tasa flotante y reglas de decisión. M6 permanece abierto.

El PDF profesional R01 es un corte anterior a este contrato detallado: se conserva intacto para trazabilidad. Este documento amplía su sección preliminar M6 sin atribuir aprobación al profesional.
