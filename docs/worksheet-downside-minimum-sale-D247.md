# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Comparación de una página](review/MiniUW_D247_Downside_Precio_Minimo_2pct.pdf). Downside sintético de D238, con recorte del 50 % sobre el costo directo de obra, tasa del 2 % mensual y fecha de venta 30/03/2030. El precio es bruto y la comisión de venta sigue siendo el 7 %.

| Ruta | Faltante en valor presente por USD 10 con venta en USD 6 M | Venta bruta mínima | Aumento requerido | Aumento sobre USD 6 M |
| --- | ---: | ---: | ---: | ---: |
| Con refi | USD 0,7032 | USD 6.370.187,07 | USD 370.187,07 | 6,1698 % |
| Sin refi | USD 0,8383 | USD 6.441.281,45 | USD 441.281,45 | 7,3547 % |

El VAN se mide al 30/03/2027. El mayor precio modifica el cobro de venta del mes 36. Cada dólar de aumento deja USD 0,93 después de comisión. El efecto por USD 10 se escala sobre el aporte inicial del proyecto, USD 2.400.000, y se descuenta 36 meses. Subsisten los calendarios de obra, aportes, cobros operativos, deuda y refi de D246.

En el VPS se reprodujo el expediente sintético vigente y se cotejaron los flujos a USD 6 millones con las huellas y los VAN de D246. Se verificó VAN cero al precio exacto. El centavo anterior al mínimo informado sigue dando VAN negativo y el mínimo informado lo recupera. El PDF muestra qué aporta y qué cobra cada ruta al precio mínimo que le corresponde.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

Generá `d245.json` desde el expediente vigente con el comando y las dependencias de [D246](worksheet-downside-fixed-sale-discount-rates-D246.md). El aporte inicial se toma del primer movimiento de obra del calendario Downside de cada ruta en `results.json` de ese expediente.

```sh
PYTHONPATH=src:tools:tests python3 - <<'PY'
from datetime import date
from fractions import Fraction
from math import ceil
import json

from check_discounted_sale_recovery_D34 import present_value
from worksheet_annual_coc import quantity as amount
from worksheet_annual_discount_crossover import exact_rows, monthly_flows

with open("d245.json") as file:
    result = json.load(file)["downside"]
gross = amount(result["gross_sale"])
commission = amount(result["sale_cost_fraction"])
equity = Fraction(2_400_000)
origin = date.fromisoformat(result["cross"]["purchase_date"])
rate = Fraction(1, 50)
for route, cash in result["paths"].items():
    flows = monthly_flows(cash, origin)
    van = present_value(exact_rows(flows), rate)
    slope = (10 / equity) * (1 - commission) / (1 + rate) ** (len(flows) - 1)
    minimum = Fraction(ceil(100 * (gross - van / slope)), 100)
    assert van + (minimum - gross - Fraction(1, 100)) * slope < 0
    assert van + (minimum - gross) * slope >= 0
    print(f"{route} | {minimum:.2f} | +{minimum-gross:.2f}")
PY
```
