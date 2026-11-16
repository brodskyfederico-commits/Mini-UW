# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Comparación de una página](review/MiniUW_D246_Downside_6M_Tasas_1y2.pdf). Los dos calendarios sintéticos de D238 conservan los ajustes de D245. Venta bruta de USD 6.000.000 el 30/03/2030, recorte de obra directa del 50 % y comisión de salida del 7 %.

| Tasa mensual | VAN con refi por USD 10 | VAN sin refi por USD 10 | Mayor valor presente |
| --- | ---: | ---: | --- |
| 1 % | +USD 3,5507 | +USD 3,6500 | Sin refi por USD 0,0993 |
| 2 % | −USD 0,7032 | −USD 0,8383 | Con refi por USD 0,1351 |

El VAN descuenta los cobros y los aportes al 30/03/2027. Un saldo positivo recupera los USD 10 iniciales y los aportes adicionales en valor presente. Un saldo negativo muestra cuánto falta a esa fecha. Las tasas de prueba están a ambos lados del cruce de 1,3528 % mensual de D245.

La ruta con refi aporta USD 2,39 adicionales y cobra USD 22,05 en total nominal, incluidos USD 3,07 el 30/03/2029 por la refinanciación. La ruta sin refi aporta USD 2,27 adicionales y cobra USD 22,44 en total nominal. Ambas cobran la venta neta el 30/03/2030. El PDF detalla los movimientos por fecha.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

Generá el recibo de [D245](worksheet-downside-fixed-sale-crossover-D245.md) desde el expediente sintético vigente de D238 y guardá el JSON de salida como `d245.json`. Incluí `tests` en el `PYTHONPATH` de esa corrida y usá el OCR del expediente. Con el mismo intérprete y las dependencias del ensayo, desde la raíz del repositorio:

```sh
PYTHONPATH=src:tools:tests python3 - <<'PY'
from datetime import date
from fractions import Fraction
import json

from check_discounted_sale_recovery_D34 import present_value
from miniuw_foundation.debt_service import rational
from worksheet_annual_discount_crossover import exact_rows, monthly_flows
from worksheet_downside_fixed_sale_balance import balance_money

with open("d245.json") as file:
    downside = json.load(file)["downside"]
origin = date.fromisoformat(downside["cross"]["purchase_date"])
for rate in (Fraction(1, 100), Fraction(2, 100)):
    for name, path in downside["paths"].items():
        balance = present_value(exact_rows(monthly_flows(path, origin)), rate)
        print(f"{rate:.0%} | {name} | USD {balance_money(rational(balance))}")
PY
```

En el VPS se reprodujeron el recibo y el PDF de D245 byte por byte. Se cotejaron las huellas de los flujos de D238 y D245 y los cuatro saldos exactos, descontando ingresos y aportes por separado y comparando con la suma de los flujos netos mensuales.
