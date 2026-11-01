# Conciliaciones de operación, refinanciación y venta — contratos candidatos

Se añaden referencias aisladas de intercambio M2/M5/M6/M7, sin adoptar políticas bancarias, fiscales, contables o de distribución. Los schemas `operating-cash-bridge` y `settlement-bridge` componen los contratos existentes de cantidades, módulos y ledger. Las fuentes originales y R02 no se modifican.

## Operación devengada y caja

El perfil explícito `explicit_accrual_cash_reconciliation` recibe, por cada período del calendario, la salida candidata M2, saldos inicial/final de cuentas por cobrar, ingresos anticipados, cuentas por pagar y gastos anticipados, más ingresos/gastos sin caja expresos. No se presupone que esas categorías estén completas o correctamente clasificadas por introducirlas en el paquete.

Con Δ como saldo final menos inicial, las identidades declaradas son:

- Cobros = ingreso efectivo − ingreso sin caja − Δcuentas por cobrar + Δingresos anticipados.
- Pagos = gasto operativo + impuesto − gasto sin caja − Δcuentas por pagar + Δgastos anticipados.
- NOI candidato = ingreso efectivo − gasto operativo − impuesto.

Los ajustes sin caja son importes explícitos con signo, período y evidencia; no se infieren por diferencia. Los saldos de estas categorías brutas no admiten valores negativos en esta referencia reducida; créditos/reclasificaciones requieren tratamiento separado. Los cortes de apertura/cierre deben coincidir entre períodos; no se reinician saldos en cero cada mes. Todos los períodos necesitan registros, aun cuando los flujos sean cero.

Se comparan estas identidades con los eventos `operating_receipt` y `operating_payment` del ledger conciliado. Banco, principal, reservas, aportes y distribuciones no se agregan a esos cobros/pagos por su signo. La aplicabilidad e inclusión real de cada partida en NOI siguen pendientes de definición y validación: la igualdad aritmética no resuelve una clasificación incorrecta de origen.

Ejemplo sintético: ingreso 50, gasto 20 e impuesto 5 producen NOI 25; los saldos y ajustes declarados producen cobros 46 y pagos 20, por tanto caja operativa 26. Se distribuyen 10, se restringen 5 y quedan 11 libres. Ninguno de esos tres montos se sustituye automáticamente por NOI. Un bloqueo de M2 o una diferencia conserva sus causas y las cifras originales.

## Estado de cierre y ledger

El segundo perfil compara un estado de cierre explícito con los eventos del último período de un ledger. En este submodelo, todos los eventos de caja de ese período deben tener la fecha del cierre y una única clasificación. Si existen operaciones en otras fechas dentro del período, se necesita otro contrato de orden/corte; no se atribuyen al cierre silenciosamente. Los períodos previos se conservan para derivar la caja libre de entrada.

Se exigen afirmaciones expresas, incluidos ceros, para proceeds, principal, interés, fees, costos, liberación/nueva reserva, aportes/distribuciones y otras fuentes/usos. Se verifica tipo de evento, dirección, préstamo y correspondencia de importes. No se infiere una fuente de capital para cubrir diferencias ni se ajusta una distribución para que el estado cuadre.

Caja libre previa + proceeds + liberación + aportes + otras fuentes = principal + interés + fees + costos + nueva reserva + distribuciones + otros usos + caja libre retenida.

La liberación de reservas y su depósito nuevo se mantienen como transferencias separadas. Los fondos restringidos no son distribución y la caja libre retenida no se considera automáticamente distribuible. La autorización de usar o distribuir fondos requiere evidencia aplicable, no una identidad de conservación.

## Deuda, valorización y representación

El perfil de payoff completo es una hipótesis explícita del ejercicio: enumera todas las deudas preexistentes y exige principal/obligaciones registrados en cero tras el cierre. No es una obligación de cancelar toda deuda en cualquier refinanciación real. Payoffs parciales quedan pendientes de un contrato específico. La completitud del inventario de obligaciones es una afirmación documentada, no una auditoría del banco.

El interés capitalizado con contrapartida conserva su transferencia a principal; al pagarse como principal no se suma otra vez como interés en caja. Un ajuste documental de principal u obligaciones no se trata como prueba de pago o liberación: necesita una justificación específica fuera de este perfil. Principal cero con un fee pendiente sigue bloqueado.

En refinanciación, el préstamo nuevo debe estar identificado y ser distinto de los anteriores; proceeds de deuda no son recuperación de equity ni aprobación crediticia. Un aumento no monetario del principal nuevo se conserva pendiente de su tratamiento. En venta, se utiliza el cobro registrado, separado del valor estimado del inmueble. La referencia no calcula ni aprueba la valoración.

Sólo se concilian movimientos brutos de caja expresamente registrados. Un cobro neto con costos retenidos, una cancelación directa por escrow o una liquidación consolidada necesitan contrapartidas documentadas y otro contrato; el perfil actual los bloquea sin fabricar cobros/pagos brutos. No se certifica que un movimiento intermedio exista en un extracto por poder representarlo aritméticamente.

Ejemplo sintético de cierre: proceeds 100, caja libre previa 2 y liberación 4; se pagan principal 70, interés 2, fee 1 y costos 3, se restringen 5 y se distribuyen 20; quedan 5 libres y 5 restringidos. El valor estimado 120 no altera ninguno de esos movimientos. En refinanciación, además queda principal nuevo 100; en venta el ejemplo no incorpora deuda nueva. Ambos conservan PENDING, sin aprobación de inversión o publicación.

## Evidencia y límites

`operating-cash-bridge-validation.json` retiene 26 controles sintéticos; `settlement-bridge-validation.json` retiene 43. Comprueban discrepancias, faltantes, continuidad, clasificación, capitalización, caja retenida y obligaciones abiertas. No demuestran completitud económica de los documentos, legalidad fiscal, sizing aprobado, orden intradía, términos de banco, derecho a distribución, auditoría independiente o producción. Las elecciones e inputs reales permanecen vacíos.
