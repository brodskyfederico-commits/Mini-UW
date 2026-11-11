# Si invierto USD 10, ¿cuánto tendría que dejar la venta para recuperar lo aportado?

La [entrada sintética D113](../templates/synthetic-plan-sale-recovery-D113.json) lleva la recuperación en valor presente a la comparación de Base y Downside del plano revisado. Usa la misma solicitud de **USD 1.100.000** y la tasa elegida de **2 % mensual**. La página conserva los aportes y cobros por fecha del perfil D112 y añade el mínimo de venta para que el VAN alcance cero.

| Escenario | Refinanciación | Neto mínimo de venta por USD 10 iniciales | Venta bruta mínima del proyecto |
| --- | --- | ---: | ---: |
| Base | Sin refi | USD 12,92 | USD 3.262.203,15 |
| Base | Con refi | USD 8,30 | USD 3.230.379,76 |
| Downside | Sin refi | USD 13,15 | USD 3.321.819,15 |
| Downside | Con refi | USD 8,53 | USD 3.289.995,76 |

La venta se fecha el 30/06/2028 y el valor presente se calcula al 30/03/2027. Se conservan el aporte inicial, el aporte extra de obra, los cobros anteriores y la caja de operación. El mínimo bruto incluye el costo de venta de **5 % del precio** y el saldo de deuda a cancelar. El neto mostrado y el precio bruto se redondean hacia arriba por separado. El expediente conserva ambas cifras exactas.

La prueba independiente confirma que un centavo por debajo del mínimo bruto deja VAN negativo y que el mínimo al centavo lo lleva a cero o ligeramente por encima. Se prueban también la tasa 0 % y una solicitud que excede la capacidad de Downside. Esa variante retira su VAN y su precio mínimo y queda **PENDING**. La decisión de inversión sigue PENDING en los casos disponibles.

## Reproducción

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-plan-sale-recovery-D113.json --output /tmp/miniuw-D113
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D113
PYTHONPATH=src python3 tools/check_plan_sale_recovery_D113.py
```

El perfil conserva el calendario, la fórmula de costos de venta y el saldo de deuda al variar el precio. El cálculo representa capital agregado de un caso sintético. [Comparación anterior y fuentes](plan-discount-comparison-D112.md).
