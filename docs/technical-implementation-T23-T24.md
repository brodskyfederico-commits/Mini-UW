# Aportes y cobros del inversor con TIR periódica verificable

T23 calcula el retorno de un ledger sintético explícito de equity agregado del proyecto. Responde cuánto se aporta, cuánto se cobra y cuándo, ganancia de caja, múltiplo, distribución operativa por año de cobro y normalización sobre una base elegida. T24 aísla todas las soluciones de TIR periódica y permite anualizarlas cuando la frecuencia declarada es coherente. Estos componentes consumen movimientos suministrados: todavía no generan esas distribuciones desde costos, NOI, refinanciación o venta.

## Qué recibe el inversor en el ejemplo

La fuente ficticia `templates/synthetic-investor-returns.json` declara aporte inicial de 1.000, refinanciación neta al equity de 500, dos distribuciones operativas de 100 y venta neta al equity de 900. La normalización elige expresamente el aporte inicial como base y un importe de referencia de 10.

| Fecha ficticia | Movimiento por cada $10 iniciales |
|---|---:|
| 2027-01-01 | Aporte inicial: 10 |
| 2028-01-01 | Cobro neto de refinanciación: 5 |
| 2028-01-01 | Distribución operativa: 1 |
| 2029-01-01 | Distribución operativa: 1 |
| 2029-01-01 | Cobro neto de venta: 9 |

Aportes 10; cobros 16; ganancia de caja 6; EM 1,6x. El ejemplo también declara, tras refinanciar, capital aún invertido de 5 y valor retenido de 8: son stocks suministrados por una fuente distinta, no cifras deducidas de los cobros, y el valor retenido no se suma a los 16. El capital base anual declarado para CoC es 5 en 2028/2029; el cobro operativo anual de 1 produce CoC condicionado de 20%. No se reemplaza esa base por los 10 iniciales sin una revisión expresa.

La TIR anual única queda en un intervalo certificado alrededor de 34,403%; el JSON conserva extremos racionales exactos y su apertura/cierre. La demostración imprime límites porcentuales ampliados hacia afuera, sin usar el punto medio ni una tasa redondeada para decidir. Estos resultados describen únicamente el ejemplo ficticio, no un rendimiento ofrecido o contractual de un LP.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_synthetic_investor_returns.py
```

## Contrato y cálculos

`produce_investor_returns` requiere contexto SYNTHETIC, moneda, inventario de movimientos declarado completo y cuadrícula mensual regular con fechas explícitas. Conserva por separado aportes brutos A y distribuciones brutas D: ganancia = suma(D) − suma(A); EM = suma(D) / suma(A) si A > 0. La TIR usa el vector neto por punto, conservando ceros y fechas. Un aporte y un cobro simultáneos pueden mantener el neto y cambiar el múltiplo; nunca se reconstruyen brutos desde los signos del neto.

Sólo admite categorías de equity explícitas. Un giro bancario, NOI o valor de propiedad no se convierte automáticamente en cobro del inversor. Los movimientos deben coincidir exactamente con un punto de la cuadrícula; no se aplica XIRR, traslado de fechas, ajuste de fin de mes o asignación tácita a períodos. Se muestran todos los años calendario del horizonte, incluso sin cobros; el inventario declarado no prueba completitud financiera o cobertura de años operativos completos.

La normalización necesita importe positivo, IDs de aportes válidos y referencia de base. Aportes adicionales y cash-in permanecen visibles y pueden superar el importe de referencia si sólo se eligió el aporte inicial. Los snapshots de capital y equity necesitan fecha, moneda y referencias propias. Su ausencia no borra cobros calculables, pero impide completar la vista declarada. CoC usa sólo distribuciones operativas y un denominador anual explícito positivo; refinanciación y venta se conservan aparte.

Faltantes de importe/fuente, moneda incompatible, importes brutos negativos, fechas sin vínculo o inventario no declarado completo bloquean los totales. Falta de normalización, capital base o snapshot bloquea esa vista sin inventar valores. Un agotamiento del presupuesto de TIR mantiene los totales de caja calculados. Cero aportes deja EM indefinido. `declared_cash_story_computable` sólo describe computabilidad del caso suministrado; `investor_story_complete`, revisión, cierre financiero y producción permanecen falsos y la decisión PENDING.

## Aislamiento de TIR y recuperación

El polinomio de flujos en q = 1/(1+r) se analiza en q > 0, equivalente a r > −1. El motor usa aritmética racional, cota de Cauchy, parte libre de cuadrados, secuencia de Sturm y bisección con multiplicidad. Conserva raíces tangentes y todas las raíces múltiples; distingue polinomio idénticamente cero, ausencia de raíz, varias raíces y trabajo agotado. No elige una tasa favorable. Las raíces q = 0 quedan excluidas y no se transforman en una tasa finita.

Se exigen ancho de intervalo, presupuesto de divisiones del intervalo y presupuesto de operaciones explícitos. Límites técnicos: 65 puntos, grado 64, hasta 2.048 divisiones, 200.000 operaciones y racionales de 4.096 bits. Los presupuestos se aíslan por contexto de ejecución. La anualización `(1+r)^m−1` requiere `m × meses_por_paso = 12`; transforma extremos monótonamente, sin alterar su cierre. No se adopta una convención financiera por verificar esta identidad matemática.

`save_investor_returns` captura fuente y ejecución en una transacción local; `load_investor_returns` verifica bytes, versiones, documentos y reproducción completa. Una ejecución alterada aunque lleve un hash nuevo se rechaza. El ejemplo reabre el archivo temporal y reproduce la ejecución; ninguna base runtime se incluye en GitHub o ZIP.

## Evidencia y trabajo pendiente

25 pruebas de T23 y 16 de T24, 41 nuevas y 460 técnicas en total. Cubren brutos frente a netos, aportes/cash-in, normalización, stock frente a caja, CoC, fechas/ceros, datos faltantes, anualización, raíces conocidas/irracionales/tangentes/cercanas/múltiples, presupuestos concurrentes y recuperación con fallos/alteraciones.

Pendientes: producir los movimientos desde presupuestos, reservas, deuda/refinanciación, operación y venta; reconciliar toda la caja del proyecto; definir y acreditar bases reales de capital/CoC y políticas aplicables; tratamiento fiscal, LP/JV/waterfall, riesgos/sensibilidades e integración del PDF final del deal. No se completa el motor financiero, los 36 casos originales de aceptación financiera o los 56 casos de diseño D02/D03, ni se adopta criterio de inversión alguno.
