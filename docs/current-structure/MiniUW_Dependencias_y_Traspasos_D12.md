# Dependencias y traspasos entre módulos del Mini-UW

Cada cálculo necesita recibir cantidades, bases, fechas y versiones compatibles con su definición. Este mapa reúne las 33 rutas agregadas del diseño I01, seis puntos de traspaso y cinco casos que requieren tratamiento separado del recorrido base. Permite localizar qué revisar cuando cambia una fuente, manteniendo las conexiones financieras de la hoja pendientes de activación.

La implementación sintética conservada es T111. El mapa describe entregas y revisiones; no instala un ejecutor incremental, un solver financiero ni un orden obligatorio para todas las tareas. Las 20 conexiones de [D11](MiniUW_Activacion_y_Aceptacion_D11.md), los 55 campos originales y las 23 salidas del inversor conservan sus definiciones y pendientes.

## Recorrido base de las entregas

La [matriz de 33 rutas](MiniUW_Rutas_33_D12.csv) conserva productor, consumidores, requisitos de transporte y regla de consumo del [registro I01](../structural-integration-register.json). El resumen siguiente muestra algunas entregas principales; la matriz conserva también las rutas directas entre módulos que el esquema omite.

```mermaid
flowchart LR
  M1["M1 Entradas y evidencia"] --> M2["M2 Operación y NOI"]
  M1 --> M3["M3 Presupuesto"]
  M2 --> M4["M4 Calendario y caja"]
  M3 --> M4
  M4 --> M5["M5 Capital y obra"]
  M5 --> M6["M6 Refinanciación"]
  M6 --> M7["M7 Tenencia venta y retornos"]
  M7 --> M8["M8 Escenarios y precio"]
  M8 --> M9["M9 Comparación revisión y salida"]
```

Las rutas base entre los nueve módulos forman un grafo sin ciclos. Su agrupación conservadora de entregas es M1; M2/M3; M4; M5; M6; M7; M8; M9. Eso no obliga a esperar para recibir hitos, recopilar fuentes o trabajar en definiciones independientes. Los módulos contienen actividades distintas y sus entregas agregadas no son una agenda completa de ejecución.

La ausencia de ciclos en ese grafo tampoco prueba que la financiación pueda resolverse ni que una política financiera sea aplicable. Los casos siguientes conservan sus propias dependencias y definiciones.

## Circularidades y pasadas separadas

| Caso | Tratamiento conservado |
| --- | --- |
| Costo, calendario y financiación | M3/M4/M5 pueden acoplar costo financiero y TDC. El método, dominio, residuales y precisión necesitan definición; ordenar módulos no demuestra convergencia. El perfil sintético de draws no se convierte en un solver general. |
| Impuesto y NOI | M2-07 contiene una hipótesis simultánea con cierre algebraico condicionado. Su solución matemática queda separada de la regla fiscal, elegibilidad, fuentes y parámetros aplicables. C61/C62 no completan por sí solos esa definición. |
| Ocupación de equilibrio | M2-08 utiliza servicio de deuda después de M6 en una pasada diagnóstica. Requiere la función de ingresos/costos/impuesto y la definición de ocupación. No sustituye el NOI base ni elige entre denominadores históricos en conflicto. |
| Escenarios y precio | M8 puede requerir recalcular dependencias en un contexto nuevo y aislado. Las sensibilidades individuales no se suman para producir un escenario integrado; no se presupone monotonía global del precio. |
| Criterios y comparaciones | Una revisión puede afectar comparaciones y precio dependiente. La conservación de caja exige acreditar su independencia. Una banda completa sigue PENDING y la variable original no se ajusta automáticamente para conseguir PASS. |

Los cuatro controles intermodulares proceden del registro I01. El caso interno impuesto/NOI se enlaza a M2-07 y a la ficha F18. El [registro estructurado](MiniUW_Dependencias_y_Traspasos_D12.json) conserva sus ubicaciones y hashes. Ninguno de estos controles activa un nuevo método, tolerancia o regla financiera.

## Seis puntos de traspaso

La [matriz de traspasos](MiniUW_Traspasos_6_D12.csv) detalla los registros necesarios, las conexiones relacionadas y la consecuencia de un faltante. Un registro puede respaldar varios traspasos cuando coincidan identidad, alcance y período.

| Traspaso | Qué necesita recibir el consumidor |
| --- | --- |
| Cantidades y bases hacia renta y costos | Identidad de grupo/tipo, conteos y áreas diferenciadas, tarifas, unidades y aplicabilidad. GSF, NRSF, área comercial y espacios de parking conservan bases distintas. |
| Presupuesto y calendario hacia financiación | Partidas exclusivas, saldos sin asignar/programar, hitos, pagos, bases elegibles y compromiso. Un residual no se reparte ni se transforma en cero para completar el flujo. |
| Operación y NOI hacia sizing y diagnóstico | Ingresos, gastos e impuesto del mismo período; ajustes del NOI bancario; servicio de deuda y función de ocupación cuando correspondan. NOI devengado y efectivo distribuible permanecen separados. |
| Deuda de obra hacia refi y tenencia | Identidad del préstamo, principal, intereses, fees, payoff y fechas; préstamo seleccionado, draw y movimientos brutos. Cambiar de fase no crea financiación ni aportes. |
| Caja, saldos y reservas hacia venta | Caja libre/restringida, devengos y pagos, obligaciones, precio/valor de salida y contrapartidas de liquidación. Una prima/cuota nominal no acredita pago; un pago incluido no se descuenta otra vez. |
| Movimientos hacia retorno y una página | Aportes/cobros fechados, ventana, stocks/bases, reparto personal, criterios y revisión del mismo snapshot. Valor retenido y cash, capital y déficit, proyecto y persona conservan evidencias diferentes. |

Las 33 rutas quedan asociadas a por lo menos un traspaso. Esa asociación organiza la revisión; no prueba una traducción financiera desde cada celda. El índice de las 20 conexiones enlaza sus contratos declarados con rutas del mismo módulo. Compartir módulo no demuestra que un campo alimente todos sus puertos: el vínculo exacto continúa pendiente.

## Cambios de fuente y alcance de revisión

Siete ejemplos documentales calculan qué módulos quedan alcanzados por las rutas base ante una revisión de M1, M3, M2, M6, M7, M8 o M9. El alcance es conservador y agregado. Sirve para localizar revisión, no para afirmar qué cifras concretas deben invalidarse o pueden reutilizarse. Los controles de circularidad, escenarios y diagnóstico se revisan aparte cuando corresponda al cambio.

Por ejemplo, revisar M6 alcanza M7/M8/M9 en el recorrido base. La ocupación de equilibrio puede necesitar además su diagnóstico M2-08; eso no introduce automáticamente la deuda dentro del NOI base. Revisar criterios desde M9 exige examinar su relación con precio y comparación sin asumir que cambia toda la caja.

El comportamiento disponible de T111 es más concreto: una incompatibilidad de su puerta global retira los 11 grupos `current_`. Los resultados sintéticos guardados muestran:

| Ejemplo T111 | Puerta de hoja | Resultado actual |
| --- | --- | --- |
| Hoja coincidente y fuentes compatibles | Abierta | 11 grupos presentes dentro del perfil condicional. |
| Fuente vencida | Abierta | PENDING, con los 11 grupos retirados. |
| Cero declarado en conflicto | Bloqueada | PENDING, con los 11 grupos retirados. |

Cada ejemplo conserva 59 requerimientos de fuentes y declara que no usa el resultado padre como reemplazo actual. Son observaciones de archivos guardados, no nuevas corridas financieras. Una hoja conciliada no prueba vigencia global; este mapa tampoco habilita publicación parcial de cifras bloqueadas.

## Revisión pendiente de los traspasos

La [plantilla vacía](../../templates/handoff-review-D12-empty.json) contiene seis revisiones de traspaso y cinco de control/acoplamiento. Sus fuentes, aplicabilidad, definiciones y casos esperados empiezan vacíos. Es documentación de revisión, sin aceptación por el runtime actual ni nuevas aprobaciones por paso.

La [verificación documental](D12-design-validation.json) comprueba rutas, referencias, alcance estructural, estados guardados y filas vacías. No ejecuta aceptación financiera ni activa conexiones. Se conserva T111 con sus 1.619 pruebas existentes, los criterios vacíos por deal y los pendientes de capital, CoC y retorno personal. Datos sintéticos, sin despliegue ni decisiones reales; la ampliación del Full UW sigue diferida.
