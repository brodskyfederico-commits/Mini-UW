# Renta mensual conectada a caja y retorno hasta venta

Este nuevo ejemplo sintético representa una entrada gradual de ingresos, con diez unidades constantes y renta mensual de 2 por unidad. La pérdida se declara exclusivamente como vacancia en este fixture; no se infiere ocupación física, absorción o contratos reales. La decisión sigue **PENDING**.

| Mes de 2027 | Renta potencial | Pérdida declarada | Concesión | Renta efectiva |
|---|---:|---:|---:|---:|
| Enero | 20 | 20 | 0 | 0 |
| Febrero | 20 | 10 | 0 | 10 |
| Marzo | 20 | 0 | 5 | 15 |
| Abril | 20 | 0 | 0 | 20 |
| Mayo | 20 | 0 | 0 | 20 |
| Junio | 20 | 0 | 0 | 20 |
| Total USD | 120 | 30 | 5 | 85 |

Cada mes tiene su fuente, fechas, inventario, renta y bases de pérdida/concesión expresas. Marzo aplica una concesión de 1/4 después de la pérdida, según su dato de prueba. Un cero suministrado se conserva; un mes faltante, renta desconocida, fecha incompatible o concesión duplicada bloquea el calendario. No se copia el mes anterior ni se inventa estabilización.

La renta efectiva suma 25 en el primer período y 60 en el segundo. Esas sumas coinciden exactamente con las filas residenciales de las fuentes NOI del mismo recorrido. Los otros ingresos se declaran cero dentro de este perfil. Los gastos devengados permanecen en 15 por período y los pagos en 10/20, con una cuenta por pagar de seguro de 5 que cruza la frontera y se cancela después. Los placeholders cero del productor mensual son sólo de ingreso: no eliminan los gastos operativos separados.

El NOI condicional es 10 y 45; no equivale al reparto. Las distribuciones propuestas de 100 cada una también usan caja de apertura. La caja libre sigue 590 → 395 → 205 y la restringida termina en 100. En la venta del 1 de julio, proceeds 400 más esa caja, menos principal 100, fee 10 y costo de venta 20, producen un cobro de 575.

| Movimiento del equity agregado | Fecha | USD | Por cada 10 aportados en total |
|---|---|---:|---:|
| Aporte inicial | 2026-10-01 | 1.000 | 7,1429 |
| Aporte adicional | 2026-11-01 | 400 | 2,8571 |
| Cobro operativo | 2027-03-01 | 100 | 0,7143 |
| Cobro operativo | 2027-06-01 | 100 | 0,7143 |
| Cobro neto de venta | 2027-07-01 | 575 | 4,1071 |
| Total de cobros | Hasta venta | 775 | 5,5357 |
| Resultado neto de caja | Hasta venta | −625 | −4,4643 |

El EM es **31/56 ≈ 0,5536x**. La IRR anual del ejemplo queda contenida entre **−58,26% y −58,25%**, con extremos ampliados sólo para presentación. La grilla mensual va desde octubre de 2026 hasta julio de 2027; se conservan todas las raíces/intervalos exactos sin elegir una tasa preferida. La escala por 10 usa los 1.400 de equity agregado, sin prometer un retorno personal ni certificar pérdida económica final.

La deuda de obra y su fase operativa se conservan: principal 200 en la frontera y vencimiento original en julio, sin segundo draw/aporte o prórroga. Las rentas y pagos ya pertenecen a la caja del proyecto y no se suman/restan otra vez del inversor. Cambiar una renta mensual sin una nueva fuente NOI/caja compatible retira el retorno del nuevo camino, aunque el calendario de rentas aislado calcule correctamente. Los ejemplos anteriores permanecen intactos y no se comparan como escenarios de mercado adoptados.

La vista actual exige **36 vínculos de fuentes** al instante UTC de prueba, incluidos cada mes, calendario, NOI/caja, gastos, deuda, compra/obra, venta e inversor. Una fuente vencida retira cifras actuales de rentas, gastos y retorno, conservando la historia recuperable. [Vista vigente de prueba](Revision_Vigente_Renta_Mensual_T81.md) · [Vista pendiente](Revision_Pendiente_Renta_Mensual_T81.md).

Capital remanente, equity retenido, CoC y reparto personal conservan sus bases pendientes. Las fechas de distribución son las del plan sintético: no acreditan que la renta mensual haya sido generada o cobrada antes del reparto ni suficiencia intramensual. Contratos, cobros, políticas, financiación real, revisión profesional y cierre completo de activos/devengos/TDC siguen sin acreditar. Sin despliegue ni decisiones reales.

[Contrato técnico](../technical-implementation-T79-T81.md) · [Evidencia](synthetic-rental-checked-lifecycle-demo.json) · [Cobertura incremental](../technical-coverage-T79-T81.json).
