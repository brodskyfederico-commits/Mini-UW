# Alcance económico del presupuesto y representaciones documentales

Base: M3-01:06, ficha GC Manual físico pp.58–61 (R1–R4/R7) e instrucciones de conservar conflictos. Se desarrolla estructura contable con asignaciones declaradas, no una decisión experta sobre C35, contingencia o contratos reales.

## Alcance versus documento

Cada presupuesto/contrato/factura se representa con ID, fuente, total citado y mapeo explícito a alcances económicos. Un alcance debe identificar una obligación económica concreta; dos edificios o partes distintas no se colapsan por compartir nombre o monto. Las representaciones no se suman como si fueran costos adicionales cuando describen el mismo alcance.

El mapeo y su evidencia se entregan expresamente. La referencia no deduce inclusión de parking/site/fee por nombre ni aplica jerarquía de fuentes. Dos representaciones concordantes de un alcance se conservan como evidencia, sin duplicar ese costo; una diferencia conserva todas las afirmaciones y bloquea el total. La coincidencia no demuestra verdad, independencia ni autoridad de quien la declaró.

En una misma representación se rechaza un scope_id repetido, porque no se puede saber si son particiones o duplicaciones. Si son alcances distintos, asignar IDs distintos y evidencia; si son partes de un solo alcance, suministrar la composición explícita. No repartir un total por ratios estimados ni deducir del saldo la cantidad que falta.

## Conciliaciones

Por representación completa, el total citado debe igualar la suma de sus asignaciones. Un residuo conserva ambas cifras y exige resolución; mapeo parcial/unresuelto bloquea aunque su suma aparente cerrar. Una celda faltante no se sustituye por otra fuente conocida sin resolver el conflicto/alcance. Un cero explícito conserva moneda, unidad, período y fuente.

El presupuesto canónico sólo se totaliza cuando todos los alcances requeridos expresamente están cubiertos sin discrepancias y todas las representaciones suministradas son compatibles. Alcance requerido sin cotización o alcance adicional sin tratamiento explícito son pendientes, no costo cero ni partida silenciosamente excluida. La lista de requeridos es un dato de alcance, no se genera de los documentos presentes para aparentar completitud.

Se permiten créditos documentados como efectos firmados separados; no se recorta su signo ni se confunde con pago o distribución. Moneda, unidad, base, período y contexto deben ser compatibles. Antes de usar un precio por GSF o unidad, se requiere normalización explícita desde M1/M3; no se interpreta como total monetario por conveniencia.

El total de alcance no certifica TDC all-in, costo financiero, contingencias, impuesto, aceptación GC ni viabilidad. La referencia no calcula porcentajes pendientes, no elige inclusiones C35 ni cambia la obligatoriedad del Input Sheet. Es una base estructural para recibir esa información cuando exista, manteniendo el resto del diseño en marcha.

## Prueba acotada

`references/validate_cost_scope.py` usa documentos/alcances ficticios, fracciones exactas y mapeos expresos. Detecta doble representación, discrepancias, total sin asignar, monedas/contextos/roles mezclados y faltantes; conserva créditos/cero y no elimina partidas distintas con igual monto. No audita contratos reales, autoridad de mapeo, completitud del alcance físico o reglas profesionales.
