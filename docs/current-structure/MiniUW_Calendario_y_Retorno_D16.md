# Calendario de aportes y cobros y conciliación del retorno

El retorno debe poder explicarse movimiento por movimiento: cuánto se aporta, cuándo se cobra y cómo esos importes llegan a los totales y al múltiplo. Esta revisión concilia las dos versiones sintéticas de [la comparación de fuentes](MiniUW_Revision_y_Vigencia_D15.md) desde sus movimientos brutos hasta las fechas, categorías, años y escala de referencia por 10. Conserva por separado los pendientes de capital, CoC y retorno personal.

Cada versión tiene ocho movimientos de equity sobre diez fechas declaradas. Tres movimientos son aportes explícitos de cero; cinco fechas no contienen movimientos de equity. Se conservan ambos tipos de registro: un cero declarado tiene identidad y procedencia; una fecha vacía del calendario conserva la duración. Ninguno acredita ausencia de gastos, ingresos o actividad dentro del proyecto.

## Cuánto se aporta y cuándo se cobra

Los importes siguientes son USD ficticios del equity agregado del proyecto. Las fechas pertenecen al ejemplo y no son fechas de una inversión real.

| Fecha | Concepto | Aporte bruto | Cobro de referencia | Cobro de la versión comparada |
| --- | --- | ---: | ---: | ---: |
| 1 octubre 2026 | Capital inicial | 1.000 | 0 | 0 |
| 1 noviembre 2026 | Capital adicional | 400 | 0 | 0 |
| 1 marzo 2027 | Operación | 0 explícito | 100 | 100 |
| 1 junio 2027 | Operación | 0 explícito | 100 | 100 |
| 1 julio 2027 | Venta | 0 por residual positivo del perfil | 578 | 576 |
| Total de la ventana | Equity del proyecto | 1.400 | 778 | 776 |

Las filas de operación y venta contienen cada una dos movimientos distintos, aporte y distribución, aunque compartan fecha. El calendario completo incluye además diciembre de 2026 y enero, febrero, abril y mayo de 2027, con neto de equity cero en esos puntos declarados. No se comprime el plazo ni se asigna orden intradía a los movimientos.

En la referencia, el neto de caja es −622 y el equity multiple es 389/700. En la versión comparada son −624 y 97/175. Los cobros de venta ya representan el residual hacia el equity: sumar otra vez la caja libre o la liberación de reserva incluidas en ese cierre duplicaría cobros. El saldo nominal del préstamo tampoco es un aporte del inversor.

## Cómo se comprueba cada movimiento

La [matriz de 16 movimientos](MiniUW_Movimientos_16_D16.csv) conserva las dos versiones con identidad, fecha, clase bruta, categoría, moneda, importe y escala. Cada fila enlaza la declaración de destino vacía, el binding por ID, la fuente de fecha e importe, el evento compilado y el evento del resultado. La ubicación se expresa mediante archivo, hash y punteros dentro de los JSON incorporados.

Los dos aportes previos provienen de eventos expresos de la fuente de caja previa. Sus referencias también se cotejan con los bytes y hashes del resultado previo incorporado y sus movimientos exportables. Esa coincidencia acredita consistencia interna del paquete sintético, sin autenticar transferencias bancarias.

Las distribuciones y los aportes operativos se cotejan con sus importes y fechas declarados. El cobro de venta se reproduce con la expresión de residual de [las conciliaciones de caja](MiniUW_Conciliaciones_D13.md), seleccionando el input de la versión correspondiente. Su residual positivo explica el aporte cero de cierre dentro de este perfil; no se sustituye un faltante por cero ni se adopta una regla de financiación para otros casos.

Para los seis movimientos de operación y venta de cada versión, la referencia de productor coincide con el hash declarado en la fuente de ventana y con su puntero esperado. Esta revisión no reconstruye independientemente los bytes de ese productor a partir de su hash. La procedencia declarada, la reproducción aritmética y la autenticidad de la fuente conservan alcances distintos; un identificador o hash aislado no completa las tres.

## Fechas categorías y años

La [matriz de 20 fechas](MiniUW_Fechas_20_D16.csv) concilia aportes y cobros brutos con el neto de cada punto del calendario. Cada uno de los ocho eventos aparece exactamente una vez dentro de su versión, incluidos los ceros. El detalle bruto permanece disponible después de agrupar por fecha.

La [matriz de 26 agregados](MiniUW_Agregados_26_D16.csv) reúne siete categorías, dos años y cuatro totales por versión. En 2026 se aportan 1.400 y no se cobra equity. En 2027 se cobran 778 o 776, de los cuales 200 corresponden a distribuciones operativas. El cobro de venta no entra como distribución operativa del CoC.

Las categorías de cash-out y cash-in de refinanciación y otros cobros conservan cero en estos inventarios declarados completos sin refi. La ausencia de eventos de una categoría respalda ese cero sólo dentro de este perfil; no aporta términos para un proyecto que refinancie. Las filas anuales agrupan fechas de caja del calendario: no anualizan períodos incompletos, acreditan cobertura operativa del año ni completan un denominador de CoC.

## Qué significa la referencia por 10

La base expresamente declarada incluye los cinco IDs de aporte, incluidos sus tres ceros: suma 1.400. La referencia es 10 y el factor exacto es 1/140. Se comprueba el mismo factor en los ocho movimientos de cada versión, sin cambiar sus fechas, clases o categorías.

| Medida sobre la base declarada por 10 | Referencia | Comparada |
| --- | ---: | ---: |
| Aportes totales | 10 | 10 |
| Cobros totales | 389/70 ≈ 5,5571 | 194/35 ≈ 5,5429 |
| Neto de caja | −311/70 ≈ −4,4429 | −156/35 ≈ −4,4571 |

Son escalas del equity agregado, no una oferta ni una asignación personal para alguien que invierte 10. El capital inicial representa 50/7 de esa escala y el adicional 20/7, en fechas distintas. No se interpreta toda la base como inversión en la primera fecha. El capital aún invertido, el equity retenido y la pérdida económica final requieren sus propias definiciones y evidencias; el neto de caja no los determina.

La TIR conserva el calendario y las evidencias ya existentes. Esta revisión no vuelve a ejecutar productores, recalcular raíces o escoger una tasa puntual; tampoco obtiene CoC o participación personal a partir del múltiplo.

## Errores que puede ocultar un neto correcto

El [registro estructurado](MiniUW_Calendario_y_Retorno_D16.json) reproduce ocho alteraciones de vistas de revisión: mover una fecha dentro del mismo año, duplicar u omitir un cero, compensar un aporte con un cobro en la misma fecha, reclasificar un cobro, compensar importes entre dos fechas, suprimir una fecha vacía y cambiar sólo una referencia de fuente.

Las ocho conservan el neto total de la ventana y presentan una discrepancia de identidad, fecha, importe bruto, categoría, calendario o referencia. En la compensación bruta, aportes y cobros suben en 10 sin cambiar los netos por fecha: el neto deja de ser suficiente para reconstruir el múltiplo. Son contraejemplos de revisión en memoria, con operaciones y hashes reproducibles; no modifican fuentes del modelo, prueban un rechazo nuevo del runtime ni generan escenarios financieros.

## Pendientes para el Mini UW

Ambas versiones mantienen PENDING y diez criterios vacíos. Los 54 mapeos semánticos, la autoridad financiera de las fuentes, la aceptación profesional, los stocks de capital y equity, la base anual de CoC y los términos personales siguen abiertos. La fuente vencida de la comparación anterior conserva los 11 grupos actuales retirados; esta revisión no utiliza sus cifras históricas como reemplazo.

La [verificación del calendario y retorno](D16-design-validation.json) registra el alcance comprobado. Se conserva T111 y sus 1.619 pruebas técnicas existentes, con datos sintéticos, sin despliegue ni decisiones reales. La entrega externa mantiene una página; estas tablas son evidencia interna.
