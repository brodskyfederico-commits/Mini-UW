# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto D178, los importes de Base y Downside cuadran con un cálculo independiente del flujo. Son importes del equity del proyecto, antes de impuestos personales.

| Por USD 10 de equity inicial | Base | Downside |
|---|---:|---:|
| Aporte inicial, 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales, por fecha en el CSV | USD 4,87 | USD 8,19 |
| Refi neta | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Caja operativa al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Venta neta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| **Cobro total** | **USD 18,06** | **USD 6,08** |
| Ganancia o déficit de caja | +USD 3,19 | −USD 12,11 |
| Sin recuperar al cierre | USD 0,00 | USD 12,11 |
| Múltiplo sobre todos los aportes | 1,2147x | 0,3341x |
| TIR efectiva anual | 13,45 % | −46,15 % |

Se redondea después de conciliar. La TIR corresponde a los flujos de D178, que incluyen el impuesto del comprador y los costos fijos de venta declarados. Se obtiene sobre el calendario trimestral y anualiza cuatro trimestres. El expediente mantiene la decisión real y el retorno personal PENDING.

## Cotejo línea por línea

De 736 filas, 734 cuadraron con igualdad exacta y las dos TIR independientes quedaron contenidas en sus intervalos de referencia. El [CSV de conciliación](review/MiniUW_Cotejo_Independiente_D179.csv) incluye el importe independiente, el del Mini-UW, su diferencia y el localizador del resultado. Las columnas de fracciones guardan los valores exactos. El importe del proyecto y el normalizado por USD 10 quedan en bloques distintos.

| Concepto | Base | Downside |
|---|---:|---:|
| NOI operativo | USD 402.439,10 | USD 228.710,17 |
| NOI de valoración de refinanciación | USD 440.405,68 | USD 252.238,85 |
| NOI bancario de refinanciación | USD 418.133,44 | USD 234.530,11 |
| NOI de salida con impuesto del comprador | USD 421.941,95 | USD 231.728,09 |
| Venta neta distribuida al equity del proyecto | USD 3.307.591,08 | USD 739.483,28 |

- **NOI.** Se reconstruyeron rentas por tipología, vacancia, concesiones, otros ingresos, local comercial, gastos, servicios e impuestos en las cuatro ventanas.
- **Deuda.** Se cotejaron desembolsos, saldos e intereses de obra por trimestre, fondeo, topes LTV/DSCR/debt yield, cierre de refinanciación y calendario contractual del préstamo permanente. En el calendario, el saldo al vencimiento se lee tras la cuota regular. El pago final de capital figura en su propia línea. El piloto vende antes del vencimiento y liquida el saldo de la fecha de venta.
- **Venta y retorno.** Se cotejaron precio, costos fijos y variables, liquidación de deuda, liberación y transferencia de reservas, y cada aporte y cobro por fecha, incluido el cero explícito de aporte operativo.
- **TIR.** La referencia usa bisección racional sobre el polinomio del flujo trimestral. El signo cambia una sola vez en cada escenario, lo que permite acotar una raíz positiva única. El intervalo independiente de cada caso quedó contenido en el intervalo del motor (D167 aplicado al libro de caja de D178). Cada flujo trimestral neto se cotejó también por separado.

La referencia lee directamente el XML de los XLSX sintéticos y los datos explícitos de `case.json`. Se calcula antes de generar o leer `results.json`. Usa la biblioteca estándar y las fórmulas documentadas del perfil. Las superficies, el aporte inicial sintético de D107, las bases fiscales y los términos bancarios siguen siendo supuestos del expediente. B16 reproduce por su cuenta el paquete del motor, incluida su lectura documental. Esta conciliación aritmética cubre los dos escenarios principales D178.

## Reproducción en el VPS

Usar el entorno de referencia con OCR fijado y ejecutar desde la raíz del repositorio.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_reconciliation_D179.py --csv /tmp/MiniUW_Cotejo_Independiente_D179.csv
```
