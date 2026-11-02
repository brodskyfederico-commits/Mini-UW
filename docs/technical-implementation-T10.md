# T10 — Productor sintético de servicio de deuda y conexión a DSCR

Se implementa un perfil explícito de principal constante inicial, tasa efectiva por intervalo fija no negativa, cuotas vencidas iguales y amortización por número de pagos. Las hipótesis se declaran en `miniuw.synthetic-loan-terms.v1`: no se deducen de una tasa anual ni se convierten préstamos interest-only, flotantes, con nuevos draws o fees capitalizados en este perfil. Los términos desconocidos son null, sin defaults monetarios. El contexto es sintético y el contrato se almacena por sus bytes originales, separado de los 55 inputs del workbook.

La definición se ancla con línea/hash en `docs/model-refinance-contract.md:24,26,27,29,31` y `docs/refinance-capacity-bridge.md:13`. Cuota por unidad: 1/n si la tasa es cero explícito; i/[1-(1+i)^(-n)] para i positiva. Las pruebas contrastan contra valor presente independiente y recurrencia de saldos. Se conserva precisión racional exacta, sin redondeo contractual supuesto. Límites técnicos: 600 pagos, 4096 bits por racional reducido y presupuesto acotado de potencia exacta; excederlos bloquea, no aproxima ni clasifica FAIL.

## Amortización, vencimiento y efectivo

Cada pago conserva saldo inicial, interés, principal, cuota regular y saldo posterior. El vencimiento por conteo es distinto de n: si llega antes, el saldo posterior al pago programado queda como balloon debido. No se extiende el plazo, se inventa otro refi ni se extingue el saldo por suponer que el balloon fue pagado. La suma modelada incluye solo cuota y balloon de principal; no certifica ausencia de otros fees/obligaciones ni el payoff completo.

El equivalente anual para sizing es pagos/año explícitos × cuota regular. Falta de esa frecuencia bloquea únicamente esta salida; no se infiere de fechas. Se etiqueta como equivalente anual, no como efectivo de un año fechado. Falta de maturity bloquea el calendario/saldo residual sin inferir maturity=n.

Las fechas de origen y cada pago se suministran explícitamente: ISO válidas, crecientes, únicas y posteriores al origen. No se generan fechas, meses, stubs, vencimientos o ajustes de feriados. Se declara regularidad financiera del intervalo como hipótesis; no se certifica que la separación de fechas valide esa convención. Faltan fechas → ventanas fechadas bloqueadas, aunque cuota/equivalente puedan calcularse.

Las ventanas usan límites expresos [inicio inclusivo, fin exclusivo]. Cada vista conserva índices seleccionados, interés/principal/cuotas debidos y balloon. Ventanas superpuestas son vistas independientes, no un agregado que se pueda sumar automáticamente. Una ventana sin pagos debidos con calendario completo produce cero conocido; una ventana sin evidencia de fechas permanece pendiente. Todo es importe contractual modelado debido, no efectivo pagado ni conciliación bancaria.

## DSCR con servicio producido

El puente verifica/reproduce el contrato, la producción de deuda y la cadena fuente→normalización→NOI ascendente. Exige hash exacto del préstamo, contexto de deal/escenario/run/definiciones, moneda y período coincidentes. El NOI sigue siendo declarado, no derivado/aprobado por M2 o un banco.

En modo anual usa exclusivamente el equivalente regular, sin balloon ni ventana fechada. En modo fechado exige la ventana exacta y una elección explícita entre cuotas programadas o cuotas más balloon debido. No se elige cuál corresponde al mínimo bancario; se mantienen etiquetas distintas. Servicio cero o dato no disponible bloquea DSCR. El componente no activa un umbral, criterio de inversión, crédito, desembolso o decisión real.

## Archivo y reproducción

El archivo incorpora APIs tipadas para fuente de préstamo, producción de deuda y puente DSCR. Captura/recuperación verifican bytes y reproducen la cadena con código/documentos compatibles, reutilizando la tabla de objetos sin migración. Fuente de préstamo y paquete se insertan en una sola transacción local. Los inputs NOI T01 conservan la semántica anterior de dos bases; no se afirma atomicidad distribuida o publicación vigente. Runtime/DB siguen excluidos de GitHub/ZIP documental.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_debt_service.py
```

Las plantillas `synthetic-loan-terms.json`, `synthetic-loan-windows.json` y `synthetic-debt-dscr-case.json` son ficticias. El ejemplo tiene principal 1200, tasa cero explícita, 12 pagos de amortización y vencimiento al tercero: cuota 100, balloon 900, equivalente anual 1200. En la ventana de vencimiento, NOI declarado 300 produce 3x sobre cuota o 0,3x sobre cuota+balloon. Ambos son cálculos de escenarios explícitos, no elección de política o aprobación. El slot de NOI es portador numérico del fixture, sin redefinir el Input Sheet operativo.

24 pruebas nuevas (229 técnicas totales) cubren hipótesis, matemática independiente, datos faltantes/cero, maturity, fechas/ventanas, límites, archivo/rollback/falsificación y consumo de servicio calculado por DSCR. Permanecen aparte 26 suites de referencia, ocho controles estructurales y 36 casos de aceptación financiera del producto aún no ejecutados.

No se cierran M6/IMP-02/IMP-03 ni puertas financieras: faltan términos auténticos, calendarios generales/irregulares, redondeo, otros cargos, cash pagado conciliado, NOI financiero, revisión y publicación. `financially_validated`, `cash_paid_verified`, `payoff_verified` y producción siguen false; decisión PENDING.
