# NOI pagos y distribuciones durante la operación

El NOI devengado, la caja neta operativa y la distribución propuesta responden preguntas distintas. Esta revisión reconstruye sus puentes por concepto y período en las dos versiones sintéticas existentes. Permite explicar cuánto produce la operación, qué pagos quedan pendientes y cómo interviene la caja de apertura en el plan suministrado.

El ejemplo propone distribuir 200 durante la operación. La caja neta operativa de esos períodos suma 63 en la referencia y 61 en la versión comparada. La conservación del plan usa también la caja de apertura; no demuestra que los 200 sean utilidad operativa recurrente, CoC anual o devolución de capital.

## De ingreso devengado a caja

Los importes siguientes son USD ficticios, por los períodos declarados, sin anualización ni autenticación bancaria.

| Medida | Referencia período 1 | Referencia período 2 | Comparada período 1 | Comparada período 2 |
| --- | ---: | ---: | ---: | ---: |
| Ingreso devengado | 28 | 60 | 28 | 60 |
| Gastos devengados sin impuesto | 15 | 15 | 15 | 17 |
| Impuesto del perfil sintético | 0 | 0 | 0 | 0 |
| NOI devengado | 13 | 45 | 13 | 43 |
| Cobros operativos | 28 | 60 | 28 | 60 |
| Pagos operativos | 10 | 15 | 10 | 17 |
| Caja neta operativa | 18 | 45 | 18 | 43 |
| Distribución propuesta | 100 | 100 | 100 | 100 |

Los cobros se concilian desde ingreso devengado, ajustes sin caja y cambios en receivables e ingresos anticipados. Los pagos se concilian desde gasto/impuesto, ajustes sin caja y cambios en payables y prepagos. La caja neta es cobros menos pagos; no se obtiene restando otra vez los gastos a un NOI que ya los descontó.

El impuesto cero depende de coeficiente y piso expresamente cero en estas fuentes. No activa una exención ni una regla fiscal real. Los ingresos comerciales cero y los demás ceros también conservan el alcance del perfil suministrado.

## Gastos pagos y saldos por concepto

La [matriz de doce observaciones de gasto](MiniUW_Conceptos_12_D19.csv) conserva tres conceptos —seguro, otro gasto e impuesto— por dos períodos y dos versiones. Cada fila enlaza el detalle con su puntero declarado al NOI, conserva los IDs de ambas fuentes y verifica:

`Pagos = gasto devengado + payable inicial − payable final + prepago final − prepago inicial`.

En el primer período, el seguro devenga 10 y paga 5: el payable pasa de cero a 5. El otro gasto devenga y paga 5. Por eso el gasto total es 15 y los pagos son 10; la caja neta de 18 supera en 5 al NOI de 13. Ese ajuste refleja un saldo pendiente, no cinco adicionales de ingreso o utilidad.

En el segundo período, el payable del seguro sigue en 5 antes de venta. El gasto y el pago del seguro son 10 en la referencia y 12 en la comparada; el otro gasto conserva 5. La [matriz de ocho pagos previstos](MiniUW_Pagos_8_D19.csv) mantiene sus IDs, fechas, importes y fuentes: son cuatro pagos por versión. Los cuatro inventarios de pagos de impuesto están explícitamente completos y vacíos, con gasto y saldos cero; un inventario incompleto no recibiría ese tratamiento.

Los pagos pertenecen a períodos semiabiertos: inicio incluido y fin excluido. La liquidación de seguro de 5 en la fecha de venta queda fuera de estos pagos operativos y conserva su vínculo al uso de cierre descrito en [la conciliación de venta](MiniUW_Cierre_y_Uso_Unico_D17.md).

## Caja antes y después de la distribución propuesta

La [matriz de cuatro puentes operativos](MiniUW_Puentes_Operativos_4_D19.csv) separa el flujo generado de la caja que ya existía.

| Medida | Referencia período 1 | Referencia período 2 | Comparada período 1 | Comparada período 2 |
| --- | ---: | ---: | ---: | ---: |
| Caja libre de apertura | 590 | 398 | 590 | 398 |
| Caja neta operativa | 18 | 45 | 18 | 43 |
| Principal pagado | 40 | 60 | 40 | 60 |
| Capex | 20 | 20 | 20 | 20 |
| Depósito en reserva | 50 | 50 | 50 | 50 |
| Caja libre antes de distribución propuesta | 498 | 313 | 498 | 311 |
| Distribución propuesta | 100 | 100 | 100 | 100 |
| Caja libre de cierre | 398 | 213 | 398 | 211 |

La caja previa a distribución incluye el saldo de apertura y los demás movimientos expresos. Es un resultado aritmético del plan; no acredita un derecho a distribuir. La distribución permanece como importe propuesto, sin ajustarse automáticamente al máximo de caja ni a un porcentaje del NOI.

En el agregado, 590 de apertura más 63 de caja neta, menos 100 de principal, 40 de capex, 100 destinados a reserva y 200 de distribución dejan 213 libres. Con caja neta de 61 quedan 211. La reserva restringida termina en 100 y conserva su cuenta separada.

La diferencia entre distribuciones y caja neta operativa es 137 o 139. Es una comparación de importes dentro de la ventana, no una asignación de cada dólar a una fuente ni una clasificación contable, fiscal o contractual como devolución de capital. Esa definición sigue pendiente.

## Continuidad y agregación

El [registro con fuentes y fórmulas](MiniUW_NOI_Pagos_y_Distribuciones_D19.json) conserva 16 cotejos entre saldos por concepto y saldos agregados, 20 continuidades de working balances y detalle, y 34 comparaciones con la salida operativa guardada. Las dos versiones se mantienen vinculadas a sus propios inputs y resultados.

Los flujos se suman por período. Los stocks conservan la primera apertura y el último cierre: sumar saldos de caja sucesivos produciría otra magnitud. Los hashes de bytes de las fuentes se verifican; los hashes de corrida declarados se cotejan entre registros, sin afirmar una reproducción independiente de esos productores en esta revisión.

## Pendientes del retorno

El CoC anual conserva su base de capital y cobertura operativa sin definir. Los 200 de cobros operativos del calendario de caja no se anualizan ni se convierten en un rendimiento personal. Capital aún invertido, equity retenido, clasificación de devolución de capital y términos de reparto conservan sus evidencias propias, como exige [el plan de aceptación de salidas](MiniUW_Activacion_y_Aceptacion_D11.md).

La [verificación del puente operativo](D19-design-validation.json) registra los cálculos y la conservación de los archivos. No se modifica código, llama a productores, recalcula TIR o activa criterios. Permanecen 54 mapeos semánticos pendientes y decisión PENDING. Datos sintéticos, sin despliegue ni decisiones reales; estas tablas son evidencia interna y la salida externa mantiene una página.
