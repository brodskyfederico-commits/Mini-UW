# Secuencia, disponibilidad de deuda y vencimiento — contrato candidato

`schemas/financing-timeline.schema.json` amplía el ledger periódico con un orden explícito de acciones. La referencia es `references/validate_financing_timeline.py`. No descubre términos bancarios, no interpreta contratos ni convierte una referencia conciliada en aprobación de financiación.

## Orden y contrapartidas

Cada acción tiene fecha, secuencia consecutiva desde cero, IDs de registros y referencia de evidencia de su agrupación. Todos los eventos de caja, principal y obligaciones del ledger deben aparecer exactamente una vez. Las contrapartidas de un draw, repago, liquidación o capitalización permanecen en la misma acción. Se admite como máximo un movimiento de caja por acción para evitar que un cobro y un pago separados oculten un déficit intermedio mediante neteo.

Se reconstruyen caja por cuenta, principal por préstamo y obligaciones por tipo después de cada acción. Un saldo negativo queda registrado como incidencia, aunque movimientos posteriores dejen positivo el cierre del período. No se añade un aporte o draw para corregirlo. El estado final debe coincidir con el ledger periódico original; ambas evidencias se conservan.

Esta secuencia es una afirmación expresa de los datos del ejemplo. Un orden declarado o una referencia de evidencia no acredita ejecución bancaria intradía. Las acciones agrupan contrapartidas contables; sus detalles internos no simulan un sistema transaccional ni timestamps certificados. Con cronología ausente o contradictoria, el control queda bloqueado sin ordenar por conveniencia.

## Términos y límites

Cada préstamo necesita un registro explícito, con estado de evidencia, inicio/fin de disponibilidad, inclusión/exclusión de sus extremos, vencimiento/corte y límite monetario con base definida. Fechas o elecciones ausentes admiten null y conservan sus causas; no se completan desde el calendario, el nombre del préstamo o un criterio de Lorena.

Dos bases reducidas, elegidas expresamente en los datos, se comprueban por separado:

- Máximo principal pendiente: incluye el principal registrado, también sus aumentos por capitalización/ajustes. Un saldo final inferior al límite no borra un exceso transitorio.
- Desembolsos de caja acumulados: exige el acumulado anterior documentado y suma nuevos cash draws. Los repagos no restauran automáticamente disponibilidad en esta base. No se infiere el acumulado inicial del saldo de principal.

El límite cero es un valor conocido; no significa “sin restricción”. El exceso se conserva con importe y fecha/acción. Estas dos bases no cubren todos los compromisos bancarios: bases elegibles, LTC/LTV, borrowing base, covenants, condiciones precedentes y gastos exceptuados requieren contratos adicionales. No se presupone que el límite excluya interés capitalizado ni que el préstamo sea revolving.

## Corte de vencimiento

El registro distingue vencimiento al final de la fecha y al inicio exclusivo de la fecha. La evaluación se declara al final de la fecha de assessment. Se revisa la posición al corte aun cuando no exista un movimiento ese día; pagar después no borra la incidencia anterior. El principal y todas las obligaciones registradas del préstamo se conservan por separado. Una posición positiva registrada después del vencimiento también queda señalada.

Si el vencimiento cae fuera del horizonte evaluado, la salida indica que todavía no se alcanzó: no certifica el payoff futuro, una extensión o una refinanciación que no esté documentada. Cero registrado al corte tampoco prueba liberación jurídica ni completitud del inventario de obligaciones.

## Fondos restringidos

Cada transferencia hacia reserva y cada liberación necesita su propio registro de regla/evidencia, además del vínculo en el evento de caja. La coincidencia de esas referencias sólo comprueba consistencia del paquete; `contract_authority_verified=false` se conserva siempre.

Este perfil reducido no permite justificar el uso directo de caja restringida por tener saldo suficiente. Casos como una distribución directa desde reserva quedan pendientes de tratamiento específico. Una liberación registrada y su posterior uso se conservan como dos acciones, sin sumar la liberación a deuda o aportes del inversor.

## Evidencia y límites

Se retienen 50 controles sintéticos: secuencia que revela déficit pese a cierre conciliado; extremos de disponibilidad; corte inclusivo/exclusivo; vencimiento sin movimiento en su fecha; capitalización que supera un tope; repago/redraw bajo distintas bases; obligaciones pagadas antes de devengarse; fondos restringidos y datos ausentes. El fixture enlaza el cierre bruto existente, con préstamo anterior cancelado y préstamo nuevo cuyo vencimiento queda fuera del horizonte.

La estructura no adopta una convención real por probar estas alternativas. No acredita términos auténticos, disponibilidad de fondos, viabilidad de un deal, permisos legales, todos los covenants, aceptación independiente o producción. Todas las salidas mantienen PENDING a nivel deal y publicación desautorizada. R02, originales, inputs reales y criterios pendientes se mantienen intactos.
