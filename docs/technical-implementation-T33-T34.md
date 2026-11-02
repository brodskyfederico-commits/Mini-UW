# Caja de operación conectada con refinanciación venta y retorno del inversor

T33 encadena una ventana de caja declarada: operación → refinanciación → operación → venta. Reproduce las fuentes de NOI/caja y las conciliaciones de deuda de ambos cierres. Comprueba saldos, fechas, cuotas regulares, préstamo nuevo y conservación total antes de exportar movimientos de equity. T34 compila todos esos movimientos en un solo ledger del inversor, sin modificar el original ni producir un candidato parcial.

El perfil abarca una refinanciación entre períodos operativos y una venta terminal, con cierres antes de la cuota regular de su fecha. Los importes son proyecciones sintéticas; no prueban pagos reales, liquidez intraperíodo, derecho a distribuir o financiación disponible. Construcción, adquisición e historia de activos/deuda anterior al estado inicial quedan fuera de esta ventana y pendientes de integración financiera.

## Ejemplo conectado

| Nodo | Período o fecha | Apertura libre/restringida | Cierre libre/restringido | Distribución proyectada |
|---|---|---:|---:|---:|
| Operación previa | [2027-01-01, 2027-04-01) | 1.000 / 0 | 820 / 100 | 100 el 2027-03-01 |
| Refinanciación | 2027-04-01 | 820 / 100 | 600 / 150 | 353,01 |
| Operación posterior | [2027-04-01, 2027-07-01) | 600 / 150 | 273,9398 / 200 | 100 el 2027-06-01 |
| Venta | 2027-07-01 | 273,9398 / 200 | 0 / 0 | 745,9097 |

La operación suma cobros 150 y pagos operativos 30. El préstamo anterior, a tasa cero con principal 120 y cuotas regulares de 10, tiene pagos de principal 30 dentro del primer período; antes de la cuarta cuota se cancela su principal restante 90. La refi aporta proceeds brutos 303,01 y abre un préstamo distinto por ese mismo importe.

El préstamo nuevo tiene tasa efectiva sintética de 1% por intervalo mensual y tres cuotas calculadas de 103,0301. Las dos cuotas anteriores a la venta incluyen principal 201 e interés 5,0602. El payoff antes de la tercera exige principal 102,01 e interés 1,0201; no se suma de nuevo principal ya amortizado o balloon. Fees de cierre 15, costos de cierre 40 y capex 40 siguen expresos.

Depósitos y liberaciones de reservas suman 300 cada uno. Se concilian por cuenta, pero no se vuelven a sumar como ingresos o distribuciones. El control global, en cantidades exactas, es:

`1.000 + 150 + 303,01 + 400 = 30 + 423,01 + 6,0803 + 15 + 40 + 40 + 1.298,9197`.

La contribución inicial de 1.000 coincide exactamente con la caja inicial declarada y se cuenta una sola vez. Por cada 10 iniciales, el ledger registra operación 1, refi 3,5301, operación 1 y venta 7,459097: cobros 12,989197; ganancia de caja 2,989197; EM 1,2989197x. Fechas y meses sin flujos permanecen en el vector; la TIR periódica y anualizada se conserva como intervalo certificado, sin seleccionar un punto medio para decidir.

Son cifras de un caso ficticio, no una rentabilidad ofrecida. Capital aún invertido y valor retenido del equity se dejan expresamente sin valor y mantienen la historia completa PENDING: no se deducen de caja libre/reservas ni se añade una valoración a los cobros. El CoC del año calendario del ejemplo usa una base suministrada y cobertura parcial del año, no una rentabilidad anual recurrente acreditada.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_integrated_project_cash_returns.py
```

## Continuidad y ausencia de doble cuenta

El manifiesto exige IDs ordenados, tipos, hashes de fuente/ejecución y productor anterior, contexto, moneda, fechas inicial/terminal y referencias de base. Todos los inputs se reproducen, incluso fuentes adicionales fuera del manifiesto. Faltantes, extras, duplicados, fuentes alteradas o inventario no declarado completo impiden exportar. El orden no se repara automáticamente.

En cada enlace, el cierre libre/restringido del nodo anterior debe coincidir por valor exacto con la apertura siguiente. El final semiabierto de un período operativo coincide con el instante del cierre y el inicio posterior; el orden asumido es operación previa → cierre → operación siguiente. Una separación, solapamiento o reversión de fechas bloquea, sin inventar movimientos intermedios o trasladar fechas. Los pagos/distribuciones dentro de los períodos conservan las fechas proyectadas de sus fuentes; este submodelo de totales no prueba disponibilidad diaria de caja.

Las cuatro familias de saldos de trabajo se conservan entre períodos, también al atravesar la refi, bajo referencia expresa de que ésta no las modifica. En venta, este perfil reducido exige que estén ya liquidadas en la operación anterior. Un saldo distinto de cero requiere otro contrato de cobro/transferencia/liquidación y queda pendiente; no se da de baja en silencio.

Cada período operativo compara principal e interés suministrados con las cuotas calculadas cuyas fechas pertenecen a su intervalo. La cuota de la fecha de cierre queda fuera y el cierre T31 se verifica antes de esa cuota. Los fees dentro de operación deben ser cero expresos en este perfil reducido; fees no nulos, balloon dentro de operación o deuda originada dentro de una fase requieren tratamiento adicional. No se supone que un pago agregado distinto de la cuota sea correcto porque la caja cuadre.

La deuda que llega a venta debe ser exactamente el préstamo nuevo de refi: ID, principal de originación y fecha de origen coinciden. Diferencias permanecen pendientes. Eso no acredita aprobación/desembolso bancario real. Los pagos anteriores son hipótesis T31, no extractos verificados.

La conservación global suma sólo fuentes/usos externos, aportes/repartos y saldos extremos. No suma caja retenida de cada nodo como nuevo cobro, ni depósitos/liberaciones internos dos veces. El presupuesto de fuentes es 8 MiB, hasta 65 nodos, con racionales limitados a 4.096 bits; un exceso bloquea aunque los nodos aislados sean válidos.

## Ledger integrado del inversor

T34 reproduce T33 y verifica hashes de manifiesto, ejecución y ledger. El perfil de apertura exige IDs de aportes iniciales explícitos, conocidos, con fecha/moneda/fuente, cuya suma coincida con caja inicial libre más restringida. Es un perfil de financiación de esa apertura; no reconstruye inversiones históricas anteriores o capital gastado fuera de la ventana.

Cada nodo necesita su propio movimiento bruto de distribución vacío, incluso si es cero. Un aporte adicional positivo necesita otro movimiento vacío independiente, con clasificación adecuada de cash-in de refi o capital adicional. La hipótesis de financiación exigida por T29 sigue siendo una proyección, no fondos comprometidos. El inventario del ledger debe ser exactamente aporte inicial más eventos vinculados; no se aceptan otros movimientos sin conciliar o IDs reutilizados.

Todos los targets se validan antes de compilar. Una única discrepancia deja el original intacto y no emite una compilación parcial. Cada importe conserva hash de ejecución y JSON Pointer del productor operativo o de cierre. Sólo después se ejecutan aportes/cobros, ganancia, EM, caja por año y TIR T23–T24. Los criterios de inversión y las decisiones no se activan por este ensamblaje.

## Recuperación evidencia y límites

Los nuevos paquetes locales capturan todos los períodos NOI/caja, cierres, préstamos/ventanas, especificaciones de deuda, manifiesto, ejecuciones, binding y fuentes original/compilada. Al recuperar verifican bytes, versiones, definiciones y reproducción completa. La demostración reabre ambos paquetes y verifica el enlace de ejecución y los bytes del ledger. Cada captura es transaccional; no se afirma atomicidad distribuida o publicación financiera. Bases temporales excluidas de GitHub/ZIP.

21 pruebas T33 y 17 T34: 38 nuevas, 652 técnicas en total. Incluyen identidades independientes, las seis fronteras de caja, cuatro saldos de trabajo, pago regular frente a payoff, cambios pese a cierres aislados válidos, préstamo de refi a venta, cash-in bruto separado, cero y meses vacíos, raíz/intervalos sobre el vector completo, límite aritmético real con nodos válidos, no cambios parciales, fuentes inmutables, fallos/reapertura/versiones y fuentes ausentes.

La ventana declarada conciliada no cierra todo el modelo. Siguen pendientes historia de construcción/adquisición/funding, valoración y capacidades bancarias, reglas reales de impuestos/reservas/reparto, pagos auténticos, casos fuera del perfil, capital aún invertido/equity, LP/JV/waterfall, riesgos y PDF final. Originales, I01, matriz de 398 filas, criterios vacíos y revisión pendiente permanecen intactos. No se cierran los 36 casos financieros originales ni los 56 escenarios D02/D03. Decisión PENDING; sin despliegue o decisiones reales.
