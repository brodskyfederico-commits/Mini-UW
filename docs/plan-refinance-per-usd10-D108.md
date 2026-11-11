# Si invierto USD 10, ¿cuánto cobro y cuándo si hay refinanciación?

El ensayo usa los dos cuadros sintéticos de la lámina A-601. En los casos con capacidad, aportás **USD 10 iniciales el 30/03/2027**. El aporte extra se paga al financiar la obra. La refinanciación distribuye los fondos netos el **30/03/2028**. El **30/06/2028** se distribuye la caja operativa después de la cuota y luego el neto de venta después de cancelar el saldo de deuda.

| Escenario y plano | Aporte extra 30/06/2027 | Cobro neto de refi 30/03/2028 | Cobro de operación 30/06/2028 | Cobro neto de venta 30/06/2028 | Cobro total | Sin recuperar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base, original | 3,54 | 5,72 | 1,39 | 10,87 | 17,97 | 0,00 |
| Base, revisado | 0,42 | 5,72 | 0,89 | 5,62 | 12,22 | 0,00 |
| Downside, original | 3,54 | 5,72 | 1,05 | 4,96 | 11,73 | 1,82 |
| Downside, revisado | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

USD por USD 10 de equity inicial del proyecto. Las columnas se redondean de forma independiente. El saldo sin recuperar incluye el aporte inicial y los extras y se mide al vender, en USD nominales. Las cifras representan capital agregado y provienen de datos sintéticos de prueba.

## Capacidad del préstamo

El préstamo bruto solicitado se mantiene en USD 1.400.000 para los cuatro cruces. La capacidad es el menor límite entre el porcentaje del valor del activo (LTV) y la cobertura mínima del servicio anual de deuda (DSCR). Los importes de esta tabla corresponden al proyecto entero.

| Escenario y plano | NOI anual de valoración | NOI anual bancario | Capacidad LTV | Capacidad DSCR | Resultado del préstamo solicitado |
| --- | ---: | ---: | ---: | ---: | --- |
| Base, original | 377.198,40 | 354.854,40 | 2.451.789,60 | 2.223.300,01 | Compatible |
| Base, revisado | 257.815,20 | 242.083,20 | 1.675.798,80 | 1.516.744,85 | Compatible |
| Downside, original | 296.760,00 | 274.416,00 | 1.928.940,00 | 1.719.322,34 | Compatible |
| Downside, revisado | 201.180,00 | 185.448,00 | 1.307.670,00 | 1.161.903,42 | PENDING |

En Downside revisado la solicitud supera la capacidad en **USD 238.096,58**. Limita el DSCR. La prueba conserva la solicitud y retira los flujos del escenario bloqueado. Verifica aparte que USD 1.161.903,42 queda dentro del límite y USD 1.161.903,43 lo supera. Esos importes son pruebas del límite y el cuadro de cobros usa exclusivamente la solicitud original.

## De dónde salen las cifras

- Los [cuadros sintéticos D105](plan-schedule-intake-D105.md) mantienen 20 unidades 1BR-A, cuya superficie rentable por unidad baja de 710 a 690 ft². Las unidades 2BR-A pasan de seis a cero. El [caso D107](plan-return-per-usd10-D107.md) aporta las tarifas, la base de obra por unidad, el equity inicial de USD 2.400.000, los supuestos de renta, gastos y venta de cada escenario y el calendario. Con obra por unidad, la ausencia de superficie bruta queda fuera del cálculo.
- D108 declara un préstamo nuevo de USD 1.400.000, comisión de 2 %, tasa efectiva trimestral de 1,25 %, amortización en 40 cuotas y vencimiento a las ocho cuotas. El activo llega a la refinanciación con deuda previa igual a cero. El neto de USD 1.372.000 se distribuye al refinanciar.
- Para calcular capacidad, se eligen cap de refi de 10 %, LTV máximo de 65 % y DSCR mínimo de 1,25×. El NOI bancario se calcula con 5 puntos porcentuales adicionales de vacancia respecto del NOI de valoración. El NOI de salida se calcula por separado bajo las condiciones de D107. Todos estos parámetros pertenecen al ensayo.
- Para los casos compatibles, el 30/06/2028 la cuota regular de USD 44.689,98 se resta de caja operativa. Luego el cierre de venta resta el saldo de USD 1.372.810,02. El cálculo concilia que la cuota y el saldo de cancelación se tomen del mismo préstamo que pasó el control de capacidad.

## Reproducción

```bash
PYTHONPATH=src python3 tools/plan_refinance_D108.py check
PYTHONPATH=src python3 tools/plan_refinance_D108.py report
```

El JSON conserva el origen de las cantidades del plano, las fuentes vinculadas de capacidad y los flujos por fecha. La ruta sintética usa los módulos de capacidad T35, servicio y corte de deuda T10/T31, caja y cierre T25/T29 y retornos T23/T30. La validación cubre el caso de refinanciación al final de la tenencia y una cuota antes de cancelar el préstamo en la venta. Las condiciones reales de crédito, datos de Lorena y decisión de inversión siguen PENDING.
