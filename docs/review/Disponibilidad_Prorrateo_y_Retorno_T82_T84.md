# Disponibilidad, renta parcial y retorno hasta venta

Este perfil de prueba separa capacidad declarada, disponibilidad propuesta, pérdida de renta y prorrateo. No acredita entregas, permisos, ocupación o contratos reales. La decisión continúa **PENDING**.

La capacidad del grupo es diez unidades. Cada unidad disponible tiene renta mensual de referencia de 2. Las fracciones de enero de 1/2 y 1/2 son datos suministrados; no se calculan de los 15 y 16 días de los tramos ni se adoptan como convención contractual.

| Tramo de 2027, fin excluido | Disponibles | Fracción de mes | Potencial ponderado | Pérdida | Concesión | Efectiva |
|---|---:|---:|---:|---:|---:|---:|
| 01 ene–16 ene | 0 | 1/2 | 0 | 0 | 0 | 0 |
| 16 ene–01 feb | 5 | 1/2 | 5 | 0 | 0 | 5 |
| 01 feb–01 mar | 5 | 1 | 10 | 2 | 0 | 8 |
| 01 mar–01 abr | 10 | 1 | 20 | 0 | 5 | 15 |
| Abril, mayo y junio, cada mes | 10 | 1 | 20 | 0 | 0 | 20 |

En febrero la pérdida suministrada es 1/5; en marzo la concesión es 1/4 después de pérdida cero. El primer período suma potencial 35, pérdida 2, concesión 5 y renta efectiva 28. El segundo suma 60 de renta efectiva. Las unidades disponibles pueden cambiar entre tramos, sin confundir ese cambio con una variación de capacidad o una ocupación certificada.

El ejemplo independiente de **período parcial 16 ene–01 feb** reproduce renta efectiva 5 bajo su fracción suministrada. No se extiende automáticamente hasta el inicio del mes. Aunque ese recorte conserve el mismo ingreso agregado en otro caso, sólo puede conectarse a caja si sus fechas coinciden con la ventana operativa; no mueve la apertura de deuda o genera financiación.

Los 28 y 60 coinciden con las filas residenciales de las fuentes NOI de este caso nuevo. Otros ingresos e impuesto condicional son cero explícito de prueba, sin exención real acreditada. Gastos devengados 15/15 y pagos 10/20 conservan la cuenta por pagar de seguro 0 → 5 → 0. Los NOI condicionales son 13/45, distintos de los repartos propuestos de 100 cada uno, que también usan caja de apertura.

La caja libre pasa de 590 a 398 y después a 208; termina además con caja restringida 100. La venta del 1 de julio usa proceeds 400 más esa caja y paga principal 100, fee 10 y costo de venta 20, por lo que distribuye 578. El principal de obra 200 se conserva en la frontera operativa y el vencimiento original no se prorroga. Rentas, gastos y principal no se cuentan dos veces en el retorno.

| Movimiento del equity agregado | Fecha | USD |
|---|---|---:|
| Aporte inicial | 2026-10-01 | 1.000 |
| Aporte adicional | 2026-11-01 | 400 |
| Cobro operativo | 2027-03-01 | 100 |
| Cobro operativo | 2027-06-01 | 100 |
| Cobro neto de venta | 2027-07-01 | 578 |
| Total de cobros | Hasta venta | 778 |
| Resultado neto de caja | Hasta venta | −622 |

Por cada 10 del total aportado de 1.400, los cobros son **389/70 ≈ 5,5571** y el resultado neto de caja **−311/70 ≈ −4,4429**. El EM es **389/700 ≈ 0,5557x**. La IRR anual del ejemplo queda contenida entre **−58,02% y −58,01%**, con extremos ampliados sólo para presentación; se conservan todas las raíces/intervalos exactos, sin elegir una tasa preferida. Son retornos de equity agregado, sin términos de reparto personal ni certificación de pérdida económica final.

El control bloquea disponibilidad superior a capacidad, fracciones desconocidas, grupos omitidos, huecos/solapamientos y prorrateos incompatibles con el perfil. Cambiar la disponibilidad exige nueva fuente NOI/caja compatible y recalcular la cadena. Los ejemplos anteriores permanecen intactos; éste no se adopta como escenario de mercado ni se selecciona por su retorno.

La revisión actual exige **37 vínculos de fuentes**, incluidos cada calendario/capacidad/bases y cada referencia de tramo. El vencimiento de una fuente retira cifras actuales de disponibilidad, gastos y retorno, conservando la historia recuperable. [Vista vigente de prueba](Revision_Vigente_Disponibilidad_y_Retorno_T84.md) · [Vista pendiente](Revision_Pendiente_Disponibilidad_y_Retorno_T84.md).

Capital remanente, equity retenido, CoC, reparto personal, prorrateo contractual, entregas/permisos/cobros, liquidez intraperíodo y cierre completo de activos/devengos/TDC conservan sus pendientes. Sin despliegue ni decisiones reales.

[Contrato técnico](../technical-implementation-T82-T84.md) · [Evidencia](synthetic-phased-rental-demo.json) · [Cobertura incremental](../technical-coverage-T82-T84.json).
