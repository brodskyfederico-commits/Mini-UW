# T76 — gastos devengados, pagos y saldos por concepto

## Perfil reducido y fuentes

El detalle sintético reproduce el NOI T19 y la conciliación de caja T25 desde sus bytes exactos. Exige el inventario completo de cada fila de gasto del NOI y exactamente una fila para su impuesto calculado. Seguros y otros gastos se identifican por concepto; el impuesto sólo puede apuntar a `/property_tax`. El modelo fiscal condicional anterior se conserva, sin adoptar una ley, exención o calendario fiscal. Los importes de gasto, saldos y pagos son datos expresamente suministrados, no inferidos de fechas de cobertura o de una cuota anual.

## Identidad por concepto

Para cada concepto: `pago = gasto devengado + payable inicial − payable final + prepago final − prepago inicial`. Los saldos y pagos brutos son no negativos. Deben suministrarse los cuatro saldos, incluidos los ceros, inventarios declarados completos, clasificación sin solapamiento y referencias. No hay movimientos no monetarios, reembolsos, compensaciones ni traslados entre conceptos en este perfil. Un pago vacío explícitamente declarado completo equivale a ningún pago planificado; un inventario incompleto nunca equivale a cero.

Los pagos tienen fecha dentro del período semiabierto T25, ID y referencia únicos en todo el detalle. La suma de pagos concilia por concepto y también contra los pagos operativos T25. Las sumas de payables y prepagos iniciales/finales deben coincidir con los saldos agregados T25. No basta con que el total global cuadre: una diferencia de seguro no puede compensarse con una diferencia de impuesto. Cada gasto coincide con su fila original y el impuesto con el resultado reproducido T19. Se requieren contexto, moneda, período, fechas y hashes exactos. Los ajustes no monetarios de gasto T25 deben ser cero.

## Alcance y recuperación

El resultado compatible expone por separado gasto, pagos, saldos y residual por concepto. No añade un gasto al NOI ni vuelve a restar pagos de la caja T25; sólo comprueba el puente ya declarado. El reparto sigue siendo la propuesta T25, sin redistribución automática. Un fallo T19/T25, un saldo faltante o una diferencia por concepto bloquea el detalle y retira sus totales exportables; la decisión permanece PENDING.

El transporte JSON acotado incluye las tres fuentes UTF-8 exactas y el resultado. La recuperación valida versiones, hashes y reproducción integral; resultados o fuentes alterados no se autentican por recalcular su hash. No ejecuta código ni busca fuentes externas. Puede recuperar tanto casos compatibles como bloqueados.

La fecha es de pago planificado, no evidencia bancaria o vencimiento contractual. No se comprueban devengos intraperíodo, disponibilidad intradía, cobertura del seguro, base imponible, autoridad real, vencimientos, vigencia actual, clasificación contable independiente o exhaustividad económica. No hay entrada real de Lorena, revisión profesional autenticada, despliegue ni decisiones reales. Los paquetes anteriores permanecen intactos.
