# D181 · Informe por USD 10 y dictamen integrado

El perfil sintético v29 reproduce los escenarios principales de D178 y agrega la comparación B14 y el informe B15 en la misma corrida. El informe de una página detalla aportes y cobros fechados, resultado neto, saldo sin recuperar, dependencia de la venta y el cobro neto de salida requerido para recuperar todos los aportes a valor nominal. Los importes se expresan por USD 10 de aporte inicial al equity agregado del proyecto, antes de impuestos personales. El reparto personal LP/GP y la decisión real están PENDING.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro operativo | USD 1,43 el 30/12/2028 | USD 0,55 el 30/06/2029 |
| Cobro neto de venta | USD 13,78 el 30/12/2028 | USD 3,08 el 30/06/2029 |
| Cobro total | USD 18,06 | USD 6,08 |
| Resultado nominal | +USD 3,19 | −USD 12,11 |
| Sin recuperar | USD 0,00 | USD 12,11 |

El capital remanente documentado y el valor del inmueble retenido se muestran a la fecha de refi. El segundo es el valor de refi menos el principal nuevo, expresado por USD 10, y se excluye de los cobros. Los montos se redondean después de calcular cada total sobre importes exactos. La dependencia de venta usa el cobro neto de venta dividido por los cobros totales. El mínimo de venta se expresa como cobro **neto al equity** en la fecha de salida, manteniendo fijos los aportes y cobros previos del caso. Usa valor nominal y piso de cero.

## Comparaciones B14

Los dos escenarios tienen diez filas cada uno. Ocho métricas por escenario se calculan y comparan con los criterios sintéticos del mismo expediente. Cada fila identifica su fuente en los resultados, su ventana, su unidad y su regla en `case.json`. Los umbrales y el cap comparable de 7 % son entradas de prueba para verificar la comparación. Los criterios reales siguen pendientes.

| Métrica | Fuente y alcance | Base | Downside |
| --- | --- | ---: | ---: |
| Múltiplo | Cobros totales ÷ todos los aportes del libro fechado | 1,21× | 0,33× |
| Equity recuperado en refi | Cobro neto de refi ÷ aporte inicial | 28,47 % | 24,46 % |
| Aporte en refi | Aporte del cierre cotejado con el libro de caja. B14 compara USD del proyecto y B15 expresa USD por USD 10 | USD 0,00 | USD 0,00 |
| Yield on Cost | NOI de valoración de 12 meses completos, incluida la renta comercial estabilizada, ÷ TDC conciliado hasta la refi | 10,48 % | 4,99 % |
| Spread | (YoC − cap comparable con la misma ventana) × 10.000 | +347,81 pb | −200,66 pb |
| Equity/TDC | Equity aplicado hasta la refi ÷ TDC conciliado | 84,89 % | 86,42 % |
| CoC posrefi | (NOI del tramo declarado − servicio regular de deuda del tramo) ÷ equity remanente documentado, sin anualizar | 11,46 % | 1,79 % |
| TIR anual | Intervalo de la TIR única calculado sobre la grilla trimestral de aportes y cobros | 13,44 % a 13,45 % | −46,16 % a −46,15 % |
| Ocupación de equilibrio | SRC-02 · falta confirmar la definición aplicable al expediente | PENDING | PENDING |
| Precio pedido / RLV | SRC-03 · falta confirmar la definición de RLV de la casa y sus restricciones | PENDING | PENDING |

El TDC concilia usos de adquisición y desarrollo, financiación de estabilización, comisión inicial e intereses pagados de la deuda de obra. Al corte de refi, el equity aportado menos la caja libre remanente, más los desembolsos de deuda de obra, debe igualar el TDC. El resultado es USD 4.203.090 en Base y USD 5.051.442 en Downside. Se usa el NOI de la ventana de valoración de refi, con 12 meses completos de ocupación comercial modelada bajo los supuestos de cada escenario. El cap comparable tiene su propia fuente, distinta de las tasas de capitalización usadas para refi y venta. El CoC sigue la base del tramo definida en D173 y la caja distribuida de operación se muestra por separado.

La simulación conserva PENDING ante un dato o criterio faltante, incompatible o desactualizado y ante una comparación en banda. Un FAIL parcial se registra en su fila. Con la ocupación económica y el RLV sin confirmar, el dictamen integrado de la corrida es PENDING. Si el préstamo supera la capacidad, la caja del escenario afectado se retira. Si sólo falta una regla de comparación, la caja calculada queda visible con su estado.

## Reproducción y cobertura

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_integrated_screening_D181.py --output /tmp/miniuw-d181
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d181 --current-revision templates/synthetic-workbook-current-revision-D181.json
```

La prueba compara ambos escenarios con el [cotejo independiente D179](review/MiniUW_Cotejo_Independiente_D179.json), prueba cambios de criterio, faltantes, banda, revisión anterior y exceso de capacidad, y reabre el PDF de una página. [Informe](review/MiniUW_Informe_USD10_D181.pdf) · [Resultado de la prueba](review/MiniUW_Verificacion_D181.json).

| Recomendación en la revisión | Cobertura del hito | Pendiente |
| --- | --- | --- |
| Flujo pp. 1–2 · ítem 5 y respuesta al inversor | B15 reúne aportes y cobros fechados, resultado neto, saldo sin recuperar, EM y TIR de los mismos escenarios cotejados | Términos vigentes para reportar el retorno personal |
| Flujo p. 3 · ítem 2 | Dependencia de la venta y mínimo nominal de salida en la página | Sensibilidad adicional bajo escenarios y bases aprobados |
| Flujo pp. 2–3 · métricas y comparación | B14 ejecuta ocho métricas con criterios explícitos y registra las diez por escenario | SRC-02, SRC-03 y criterios vigentes para el uso real |
| Fórmulas p. 1 · ítem 1 | El CoC del tramo de D173 se compara en B14 con período y definición exactos | Confirmar con evidencia real la base de equity remanente, el NOI y el criterio |

[Batería unitaria y comprobación del PDF en variantes PENDING](general-regression-D182.md).

[Vínculo con la revisión de los tres informes D180](review/MiniUW_Cierre_Revision_Profesional_D180.md).
