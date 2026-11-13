# Si invierto USD 10, ¿cuánto cobro y cuándo?

El caso sintético aporta USD 10 el 30/03/2027 al equity agregado del proyecto. La [página de PRELIMINAR](review/MiniUW_Preliminar_Refinanciacion_D187.pdf) presenta los movimientos por fecha, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales totales, incluido aporte de refi | USD 6,17 | USD 7,95 |
| Aporte al refinanciar · 30/12/2027 | USD 0,00 | USD 0,17 |
| Cobro neto al refinanciar · 30/12/2027 | USD 2,65 | USD 0,00 |
| Cobro operativo por trimestre · marzo a diciembre de 2028 | USD 0,65 | USD 0,42 |
| Cobro neto de venta · 30/12/2028 | USD 26,05 | USD 8,47 |
| Total cobrado | USD 31,29 | USD 10,15 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,80 |

Se redondea después de calcular con fracciones exactas. El dictamen formal y el retorno personal quedan PENDING.

## Ruta residencial financiada

La entrada común recibe dos XLSX del formato original Inputs, una copia por escenario. Las huellas, datos complementarios y respaldos se declaran en el JSON. El perfil `miniuw.synthetic-preliminary-loi-workbook.v2` conserva la base por USD 10 sobre la compra. D185 y D186 mantienen sus esquemas y salidas.

| Celdas y respaldo | Cálculo |
| --- | --- |
| C51–C53 · LTC, interés nominal anual y comisión | El compromiso es el menor entre el máximo declarado y LTC sobre costo directo elegible. El perfil desembolsa una vez al terminar la obra. Resta ese desembolso del aporte de obra y suma la comisión en la misma fecha. Cobra interés simple al fin de cada trimestre de absorción y cancela el principal al refinanciar. Exige vencimiento de obra explícito. |
| C66, C69–C72 · Cap de refi, tasa fija, amortización, LTV y DSCR | El motor de deuda calcula la cuota trimestral y el servicio anual equivalente. El valor de refi usa NOI estabilizado de valoración y C66. El DSCR usa NOI bancario, con H08 explícito y antes de reservas en este ensayo. Si el respaldo declara debt yield aplicable, se agrega su tope. La solicitud completa debe quedar dentro del menor límite. |
| C73–C74 · Costos y reserva permanente | Al refinanciar, el principal nuevo cubre la cancelación de obra, los costos y la reserva permanente. El remanente es cobro o aporte, según el signo. Un aporte requiere cobertura dentro del monto de equity declarado. |
| H02, C60, C67–C68 y liquidación de reservas | Se descuentan cuotas de la caja operativa trimestral. La venta cancela el saldo después de la última cuota. El cierre añade la reserva de reposición liberada y la fracción explícita liberada de la reserva permanente. Se registra por separado el saldo de reserva permanente transferido. |

El piloto usa calendario trimestral, refi al estabilizar, un desembolso de obra al cierre de construcción y deuda permanente fija con cuota regular hasta venta. El desembolso único es una convención del ensayo y requiere otra ruta para modelar desembolsos progresivos. El primer fixture usa tasa permanente cero explícita para facilitar el cotejo independiente y una variante ejercita la tasa positiva. Los valores no son términos bancarios vigentes.

## Verificación

Se conciliaron todos los aportes y cobros fechados de Base y Downside contra una referencia aritmética independiente. Se probaron faltantes, fórmula con caché, vencimientos, aporte de refi sin fondeo, exceso por LTV, DSCR y debt yield, igualdad en capacidad, no aplicabilidad de debt yield, tasa positiva y venta insuficiente. Un bloqueo en un escenario retira su caja, conserva la caja independiente y excluye el deal del ranking. La comparación de revisión usa el múltiplo de Downside de la política sintética D185.

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_finance_D187.py --output /tmp/miniuw-d187
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d187
```

[Registro de verificación](review/MiniUW_Verificacion_D187.json).
