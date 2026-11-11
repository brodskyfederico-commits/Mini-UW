# D106 — Impacto de un cambio de plano en renta y costos

## Qué revisar

| Dato que cambia | Cálculos que se revisan | Condición de cálculo |
| --- | --- | --- |
| Superficie rentable **por unidad** de un grupo | Renta bruta mensual si la tarifa se expresa en USD/ft² al mes. Recalcular las pérdidas y concesiones sobre sus bases y los gastos ligados al ingreso efectivo. | Usar el área rentable del grupo y su conteo. Si la tarifa se expresa en USD/unidad, el área queda fuera de la multiplicación. |
| Cantidad de unidades de un grupo | Renta de ambas bases, disponibilidad para renta, otros ingresos por unidad elegible y gastos por unidad. Revisar también seguro y reservas si su base es por unidad. | Verificar el conteo aplicable a cada concepto y su período. Para gastos, unidades aseguradas o depósitos puede corresponder un conteo distinto del de unidades para renta. |
| Superficie bruta del edificio (GSF) o conteo del alcance vertical | Costo vertical por GSF o por unidad, según la base de la cotización. Revisar contingencia, costos blandos, desembolsos y financiación si dependen de ese presupuesto. | Conciliar alcance e inclusiones antes de actualizar. Si el costo vertical es un total explícito, revalidar su alcance con el proveedor. El monto suministrado permanece fijo en este ejercicio. |
| Superficie comercial elegible o cantidad documentada de estacionamientos | Renta comercial anual por ft², TI/LC o costos de parking, según la partida y la base documentada. | Confirmar uso, área o espacios, alcance y período. El cuadro residencial del ejemplo carece de estos datos. |

Fuentes de cálculo en los [contratos D09, F01–F05](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.md#conexiones-y-condiciones-de-uso), [D10, F09–F19](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.md), [M2, ingresos y gastos](model-operations-contract.md#contratos-por-salida) y [M3/M4, presupuesto y calendario](model-budget-schedule.md). El cálculo vertical excluye parking y site work bajo el alcance D09. La superficie rentable por unidad, el total rentable de un alcance y el GSF tienen identidades distintas.

## Prueba sintética en el VPS

Se comparan las [dos revisiones D105 de la lámina A-601](plan-schedule-intake-D105.md). Las 20 unidades 1BR-A pasan de 710 a 690 ft² rentables cada una. El grupo 2BR-A pasa de seis unidades a cero explícito y pierde su dato de área. La revisión nueva omite el GSF.

| Cálculo con tarifa sintética constante | Antes (USD) | Después (USD) | Cambio (USD) |
| --- | ---: | ---: | ---: |
| Renta bruta 1BR-A a 2/ft² por mes | 28.400 | 27.600 | −800/mes |
| Renta bruta 1BR-A a 1.400/unidad por mes, alternativa | 28.000 | 28.000 | 0 |
| Renta bruta 2BR-A a 1.800/unidad por mes | 10.800 | 0 | −10.800/mes |
| Renta bruta potencial de ambos grupos, sin la alternativa | 39.200 | 27.600 | −11.600/mes |
| Renta residencial efectiva con 5 % de vacancia y 2 % de concesiones, ambas sobre el bruto | 36.456 | 25.668 | −10.788/mes |
| Gasto operativo a 600/unidad por año, prorrateado a un mes | 1.300 | 1.000 | −300/mes |
| Administración al 5 % de la renta residencial efectiva | 1.822,80 | 1.283,40 | −539,40/mes |
| Gasto operativo fijo mensual | 900 | 900 | 0 |
| Costo vertical a 160/GSF | 4.000.000 | PENDING | GSF ausente |
| Costo vertical a 125.000/unidad | 3.250.000 | 2.500.000 | −750.000 |
| Costo vertical fijo según monto suministrado | 3.600.000 | 3.600.000 | 0 |

Las tres bases de costo vertical son alternativas. En una prueba adicional, reducir sólo el GSF declarado de 25.000 a 24.000 ft² reduce el costo vertical por GSF en USD 160.000 y deja las otras filas iguales. Si el conteo de 2BR-A está ausente o el grupo desaparece del cuadro, las filas que requieren ese conteo quedan PENDING. Si se selecciona tarifa por ft² para 2BR-A, el productor T21 exige el área rentable del grupo incluso con cero unidades explícitas. La comisión sintética usa renta residencial efectiva. Para aplicar el campo C58 se necesita conciliar el EGI residencial elegible.

## Reproducción y límite

Ejecutar desde la raíz del repositorio.

```bash
PYTHONPATH=src python3 tools/plan_impact_D106.py check
PYTHONPATH=src python3 tools/plan_impact_D106.py report
```

El reporte conserva las revisiones, hash de archivo y puntero de cada cantidad D105, y muestra deltas en racionales exactos. La prueba usa el [productor residencial T21](../src/miniuw_foundation/rental_operations.py) y las tres multiplicaciones alternativas del contrato de costo vertical. Los supuestos fueron elegidos para aislar el efecto de la revisión. El ensayo toma cantidades declaradas en el cuadro, con lectura de CAD y validación técnica del plano pendientes.

**Por cada USD 10 iniciales, el cobro, las fechas, los aportes adicionales y la caja sin recuperar quedan PENDING.** Para calcularlos, hace falta una corrida integrada de Base y Downside con cantidades y cotizaciones conciliadas, calendario de renta y pagos, y efectos verificados en caja, deuda y venta. Las cifras de esta prueba se mantienen fuera de la corrida financiera.
