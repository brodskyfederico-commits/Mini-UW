# Si invierto USD 10, ¿cuánto cobro y cuándo?

PRELIMINAR con M2 estima los flujos de equity agregado del caso sintético residencial con deuda de obra por etapas. Los importes se calculan antes de redondear. [Informe de una página con aportes y cobros fechados](review/MiniUW_Preliminar_Impuesto_D204.pdf)

| Escenario | Aporte adicional total | Refinanciación el 30/12/2027 | Cobro de operación trimestral en 2028 | Cobro neto de venta el 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el total adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

## Integración de M2

El perfil PRELIMINAR v4 usa los mismos padrones, retasaciones y tasas separadas de M2 que D203. C62 queda como dato del perfil histórico. V4 exige evidencia fiscal para valorar la refinanciación, calcular la caja de los trimestres estabilizados y proyectar el NOI de venta. Los períodos usan los meses completos que siguen a cada cierre trimestral. La obra y la absorción conservan los costos del expediente, con el costo de tenencia de absorción declarado en el respaldo de calendario. [Regla fiscal y alcance de D203](workbook-florida-tax-D203.md)

En el ejemplo, el tope deja la tasación no escolar de Base en USD 189.000 en 2028. En Downside, una mejora declarada como calificada produce una retasación a USD 265.000. El impuesto anual del vendedor resulta USD 2.841 y USD 3.445, respectivamente. Para el NOI de salida, el primer padrón del comprador usa la retasación por cambio de titularidad y lleva ese impuesto a USD 4.290 en Base y USD 3.705 en Downside.

La fuente, fecha de corte y responsable fiscal se registran por escenario. El expediente conserva el detalle de cada ventana, los valores escolares y no escolares, el millage, el tratamiento y las citas a los respaldos. La corrida completa entra al ranking sintético con el múltiplo actualizado de Downside. El dictamen formal y el retorno personal quedan PENDING.

Se probaron expediente fiscal ausente, millage faltante, retasación sin fecha, tasación del comprador faltante y evidencia posterior al corte. Se verificó también un aumento del impuesto que reduce la capacidad por debajo del refi solicitado. En esos casos se retira el deal del ranking. Si el faltante afecta a Downside, Base conserva su caja. El millage cero explícito conserva su valor y un blanco en C62 no cambia el flujo v4. [Resultados y motivos](review/MiniUW_Verificacion_D204.json)

## Reproducción en el VPS

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_tax_D204.py
```

[Entrada sintética v4](../templates/synthetic-preliminary-florida-tax-D204.json)
