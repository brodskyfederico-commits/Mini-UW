# Presupuesto deuda y aportes antes de la operación

La caja previa debe explicar de dónde llegan los fondos, qué pagos cubren y qué saldos entran a operación. Esta revisión reconstruye los 17 eventos del ejemplo sintético existente y separa esa conciliación del presupuesto completo, la elegibilidad bancaria y el TDC all in, que conservan sus definiciones pendientes.

Las dos versiones de [la comparación de fuentes](MiniUW_Revision_y_Vigencia_D15.md) contienen exactamente los mismos bytes del paquete previo de obra y de su contrato de transición de deuda. Se registra una sola reconstrucción común, vinculada por hash a ambos inputs externos. Esa igualdad no permite reutilizar los resultados operativos o de venta que sí cambian; tampoco instala ejecución incremental o una caché.

## Fondos y pagos del ejemplo

Todos los importes son USD ficticios de fuentes suministradas, sin autenticación bancaria.

| Concepto en la ventana previa | Importe | Alcance |
| --- | ---: | --- |
| Aporte inicial | 1.000 | Equity declarado con fecha propia. |
| Aporte adicional | 400 | Otro aporte de equity, en su fecha. |
| Draws brutos | 250 | Deuda desembolsada según el plan suministrado. |
| Pagos de compra, obra y soft | 1.000 | 300, 600 y 100 respectivamente; no acreditan presupuesto completo. |
| Pagos de interés y fees de draws | 10 | 5 de interés y 5 de fees, bajo el perfil suministrado. |
| Repago de principal | 50 | Uso de caja que reduce deuda; no es otro costo de obra. |
| Caja libre que queda | 590 | Saldo que pasa a operación; no es un aporte nuevo. |

La identidad de caja es 1.400 de equity más 250 de draws, menos 1.000 de pagos no financieros, 10 de interés/fees y 50 de principal: quedan 590. El principal pendiente es 250 de draws menos 50 de repagos: quedan 200. Los 590 y los 200 describen cuentas distintas.

La [matriz de 17 eventos](MiniUW_Eventos_Previos_17_D18.csv) conserva ID, fecha, categoría, préstamo, signo de caja, fuente, binding y evento guardado. Cinco importes proceden directamente de la fuente previa. Las otras doce casillas originales permanecen vacías y sus importes se reconstruyen mediante los vínculos de préstamo ya existentes, sin escribir sobre los inputs ni sustituir vacíos por cero.

## Compromiso disponibilidad draw y principal

El compromiso suministrado es 300 y el perfil es no revolvente. Cada draw debe respetar tanto el disponible declarado de su período como el límite de draws brutos acumulados. Un repago reduce el principal; no repone compromiso consumido.

| Período | Principal inicial | Draw | Disponible declarado del período | Repago al final | Principal final del período | Draws acumulados | Compromiso no utilizado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Octubre a noviembre | 0 | 100 | 100 | 0 | 100 | 100 | 200 |
| Noviembre a diciembre | 100 | 100 | 100 | 50 | 150 | 200 | 100 |
| Diciembre a enero | 150 | 50 | 50 | 0 | 200 | 250 | 50 |

Los 50 de compromiso no utilizado son 300 menos 250. No se calculan como 300 menos el principal pendiente de 200: esa resta da 100 y no representa capacidad de nuevos draws en este perfil. Tampoco se supone que los 50 estén disponibles después de la ventana de obra; necesitarían condiciones y fuente aplicables. La fase operativa suministrada declara ausencia de nuevos draws.

La [matriz de tres períodos](MiniUW_Periodos_Deuda_3_D18.csv) conserva cada fuente y las restricciones comprobadas. El interés utiliza el saldo de exposición del intervalo y el factor suministrado de 1/100; produce 1, 2 y 2. El fee usa 1/50 de cada draw bruto; produce 2, 2 y 1. Estas fracciones pertenecen al ejemplo: no convierten una tasa anual ni activan la base del fee de originación de la hoja.

## Caja al cierre de cada fecha

La [matriz de cuatro fechas](MiniUW_Caja_Por_Fecha_4_D18.csv) agrupa todos los eventos del día sin asignarles una prioridad contractual intradía.

| Fecha | Caja libre al cierre | Principal al cierre del día |
| --- | ---: | ---: |
| 1 octubre 2026 | 798 | 100 |
| 1 noviembre 2026 | 695 | 200 |
| 1 diciembre 2026 | 592 | 200 |
| 1 enero 2027 | 590 | 200 |

El principal final del segundo período es 150 antes de incorporar el draw del período siguiente. Ambos cortes comparten el 1 de diciembre; después de incluir todos los eventos de esa fecha, el principal es 200. Son alcances distintos del mismo calendario, no dos saldos intercambiables. Los saldos de cierre del día no prueban liquidez intradía.

## Qué llega a operación y al retorno

La transición suministrada mantiene la misma obligación, sin nueva caja, ajustes de principal o prórroga inferidos. Se cotejan sus fuentes y declaraciones: los 200 de principal pasan a los términos de deuda operativa y los 590 de caja libre a la apertura del primer período. La caja restringida es cero en ambos lados.

Los aportes brutos del proyecto conservan 1.400 en las dos versiones externas. La caja de apertura de 590 no se suma como otro aporte del inversor. El [calendario de retorno](MiniUW_Calendario_y_Retorno_D16.md) y el [cierre de venta](MiniUW_Cierre_y_Uso_Unico_D17.md) mantienen sus propias fechas y alcances.

## Lo que falta para acreditar presupuesto y financiación completos

Cuadrar estos pagos no demuestra que estén cubiertos todos los costos del proyecto. El [registro con fuentes y fórmulas](MiniUW_Presupuesto_Deuda_y_Aportes_D18.json) mantiene seis puertas documentales pendientes, enlazadas a los contratos originales de [presupuesto y calendario](../model-budget-schedule.md) y [financiación de obra](../model-construction-finance.md).

| Puerta pendiente | Evidencia necesaria |
| --- | --- |
| Presupuesto exclusivo | Cantidades, bases, compra evaluada e inclusiones/exclusiones; contingencia, soft y TI/LC con su alcance. |
| Presupuesto a calendario | Partidas, pesos y fechas respaldados; devengos/pagos separados y saldos sin asignar o programar explícitos. |
| Costo elegible y LTC | Base contractual elegible, porcentaje y condiciones. No derivar un LTC de compromiso dividido por pagos. |
| Selección y disponibilidad de fondos | Equity requerido/comprometido/aportado, condiciones de draws y tratamiento de faltantes sin fondos automáticos. |
| Financiación y TDC | Clasificación del costo financiero, capitalización, convenciones generales y método de circularidad cuando aplique. |
| Continuidad de fases | Obligación, principal, interés, fees y caja sustentados al corte, con cambios contractuales si existen. |

El presupuesto total, el costo elegible, el monto sin asignar/programar, la capitalización y el TDC permanecen sin valor. Un saldo pendiente desconocido no es cero; los pagos no determinan por sí solos esos importes. Los nombres de las seis puertas organizan la revisión y no añaden un circuito de aprobación por paso.

La [verificación de caja y financiación](D18-design-validation.json) registra la reconstrucción exacta y la conservación de las fuentes. No se llama a productores, recalcula TIR ni modifica código. Los 54 mapeos semánticos, criterios, capital/CoC y retorno personal continúan pendientes. Datos sintéticos, sin despliegue ni decisiones reales; estas tablas son evidencia interna y la salida externa mantiene una página.
