# Presupuesto, períodos y pagos — contrato candidato

Este puente vincula tres estructuras existentes: el alcance económico conciliado de M3, las asignaciones temporales explícitas de M4 y los movimientos de caja de M5. Se define en `schemas/budget-payment-bridge.schema.json`; la referencia aislada es `references/validate_budget_payment_bridge.py`. No se elige curva de obra, convención bancaria, reconocimiento contable o plazo de pago.

## Entradas y vínculos

El paquete incorpora los registros originales de alcance y ledger, con sus contextos completos. Cada asignación temporal identifica un alcance requerido, un período existente, un importe monetario exacto y evidencia de su distribución. No se reparte un residual automáticamente, ni por partes iguales ni según una curva histórica. Una partida de costo cero necesita una asignación explícita de cero.

Cada vínculo de pago identifica un evento de caja de desarrollo y una asignación temporal, con importe y evidencia. Un pago puede cubrir varios alcances y una asignación puede pagarse en varios movimientos. Se rechazan IDs duplicados, vínculos huérfanos y pares pago/asignación duplicados. Los abonos de principal, aportes y transferencias a reservas no son pagos de obra. La clasificación de un evento es una afirmación documental pendiente de validación semántica, no una detección automática de su naturaleza.

Los pagos pueden tener un período diferente de la asignación que cubren cuando el vínculo es explícito. Esto permite representar un anticipo o un pago posterior, sin afirmar que cumpla un contrato o que determine cuándo se devenga el costo. La referencia limita el importe agregado vinculado a cada asignación a su importe programado; excedentes quedan pendientes de tratamiento explícito. No convierte esa limitación del ejemplo en una prohibición general de anticipos.

## Conciliaciones conservadas

| Nivel | Comparación | Tratamiento de diferencias |
|---|---|---|
| Alcance económico | Costo conciliado menos suma programada | Conservar ambos importes y residual; bloquear el puente |
| Movimiento de desarrollo | Caja registrada menos suma de vínculos | Exigir cobertura explícita de todos los movimientos clasificados de desarrollo |
| Asignación temporal | Importe programado menos caja vinculada | Mostrar saldo sin vínculo de caja; no llamarlo cuenta por pagar ni devengado |
| Paquetes de origen | Conciliaciones de alcance y ledger | Mantener sus afirmaciones, causas y discrepancias sin reemplazarlas |

No se suman otra vez representaciones documentales del mismo alcance. Las monedas, bases y unidades de presupuesto, asignaciones y caja deben concordar. Los períodos de cada cantidad tienen un rol explícito: presupuesto como stock en su corte; asignación/pago como total del período declarado. La vinculación entre esos roles es el contrato explícito del puente, no una conversión implícita de unidades.

Los valores faltantes o contradictorios mantienen sus causas y afirmaciones originales; no se transforman en cero. Los créditos documentados conservan su signo en el presupuesto y bloquean este puente reducido hasta especificar su tratamiento temporal/de caja. No se netean contra pagos positivos. Retenciones, facturas, IVA, elegibilidad bancaria y costos financiados requieren contratos adicionales; un saldo sin vínculo no los resuelve.

## Evidencia y límites

El ejemplo declarado usa las referencias sintéticas existentes bajo un contexto común: presupuesto único 37, asignaciones 37 y un pago de desarrollo 25, distribuido en tres alcances. La representación auxiliar de parking 5 no aumenta el presupuesto a 42. Quedan 12 programados sin vínculo de caja; esto no demuestra que sean exigibles, que exista financiación suficiente o que el presupuesto sea completo.

La referencia comprueba relaciones explícitas y conservación racional exacta. No valida un calendario real, integración financiera completa, solver circular, fuente auténtica, auditoría independiente ni producción. La decisión de deal permanece PENDING y la publicación desautorizada incluso cuando el ejemplo concilia. Todos los criterios reales siguen vacíos; R02 y los documentos originales permanecen intactos.
