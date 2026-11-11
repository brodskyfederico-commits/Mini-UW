# Si invierto USD 10, ¿cuánto cobro y cuándo a la tasa mensual ingresada?

D112 lleva la comparación del plano A-601 revisado al comando habitual del Mini-UW. La entrada declara la solicitud sintética de refinanciación, los hashes de los planos y la tasa de descuento mensual en fracción exacta. El PDF de una página muestra las cuatro variantes de Base y Downside con aportes, cobros por fecha, saldo sin recuperar y valor actual neto (VAN) por USD 10. El expediente conserva las cifras exactas y el origen de la solicitud.

El [caso sintético incluido](../templates/synthetic-plan-discount-comparison-D112.json) elige **2 % mensual** y un principal de **USD 1.100.000**. Los cuatro casos aportan USD 10 el 30/03/2027 y USD 0,42 extra el 30/06/2027. Con refi cobran USD 4,49 el 30/03/2028. El PDF separa operación y venta del 30/06/2028. Los VAN se calculan al 30/03/2027, sobre cobros menos aportes.

| Escenario | VAN sin refi | VAN con refi | Saldo nominal sin recuperar, sin refi / con refi |
| --- | ---: | ---: | ---: |
| Base | −1,17 | −1,08 | 0,00 / 0,00 |
| Downside | −4,39 | −4,30 | 2,34 / 2,49 |

Con **0 % mensual** explícito, el orden por VAN se invierte. El [reporte D111](review/MiniUW_D111_Tasa_de_Equilibrio_Refinanciacion.pdf) documenta la tasa a la que se igualan las alternativas. El orden se calcula con valores exactos.

La solicitud de **USD 1.400.000** conserva las dos variantes de Base y la variante sin refinanciación de Downside. Downside con refi y su comparación de VAN quedan **PENDING** por capacidad. Con una solicitud de **USD 2.000.000**, quedan PENDING las dos variantes con refi y se conservan las dos corridas sin refi. Una tasa ausente o inválida se rechaza. El perfil admite tasas no negativas explícitas.

## Reproducción

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-plan-discount-comparison-D112.json --output /tmp/miniuw-D112
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D112
PYTHONPATH=src python3 tools/check_plan_discount_D112.py
```

La auditoría vuelve a correr los flujos desde la entrada original y coteja el PDF y el JSON. Los importes representan el capital agregado de un caso sintético. La decisión de inversión permanece PENDING.
