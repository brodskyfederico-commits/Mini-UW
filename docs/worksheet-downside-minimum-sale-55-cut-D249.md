# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Comparación de una página](review/MiniUW_D249_Downside_Venta_Minima_Obra_55pct.pdf). Downside sintético de D238, con recorte del 55 % sobre la obra directa original de USD 2.744.000. La obra queda en USD 1.234.800. La venta es el 30/03/2030, con comisión del 7 % y tasa de descuento del 2 % mensual.

| Ruta | Faltante por USD 10 si la venta queda en USD 6 M | Aumento requerido | Aumento sobre USD 6 M | Venta bruta mínima |
| --- | ---: | ---: | ---: | ---: |
| Con refi | USD 0,1202 | USD 63.292,98 | 1,0549 % | USD 6.063.292,98 |
| Sin refi | USD 0,2664 | USD 140.239,75 | 2,3373 % | USD 6.140.239,75 |

El VAN descuenta todos los aportes y cobros al 30/03/2027. Se recalcularon presupuesto, desembolsos, intereses y aportes de obra al 55 %. Para despejar la venta mínima, cada USD 1 de aumento deja USD 0,93 después de comisión en el mes 36. El ensayo conserva las fechas y condiciones de deuda de cada ruta al variar la venta.

| Por USD 10 iniciales al precio mínimo | Aporte adicional | Cobro nominal total | Cobro neto en la venta del 30/03/2030 |
| --- | ---: | ---: | ---: |
| Con refi | USD 1,80 | USD 22,44 | USD 19,01 |
| Sin refi | USD 1,67 | USD 23,14 | USD 22,62 |

El cobro total con refi incluye USD 3,21 el 30/03/2029. En el VPS se reprodujo el expediente sintético y se cotejó el escenario de control al 50 % contra D246. Se comprobó VAN cero al precio exacto, VAN negativo un centavo por debajo del mínimo publicado y VAN no negativo al mínimo publicado. El PDF incluye los aportes y cobros por fecha.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

Desde la raíz del repositorio, con las dependencias de [D246](worksheet-downside-fixed-sale-discount-rates-D246.md), pasá las rutas al expediente sintético vigente y su constancia.

```sh
PYTHONPATH=src:tools:tests python3 - expediente vigente.json <<'PY'
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from sys import argv
import json

from miniuw_foundation.debt_service import rational
from miniuw_foundation.lorena_screening import encode
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_construction import construction_at_cut, normalized_route, reprice_route
from worksheet_annual_crossover_sale_price import certified_sale_price

labels = ("annual_hold_with_refinance", "annual_hold_without_refinance")
files, _, _, _ = audited_annual_comparison(Path(argv[1]), Path(argv[2]), labels)
model = json.loads(files["results.json"])
inputs = json.loads(files["case.json"])["rent_inputs"]
name = "Downside"
view = model["scenarios"][name]
cut = amount(view["construction_budget"]["direct_hard_cost"]) * Fraction(55, 100)
_, funding = construction_at_cut(model, inputs, name, cut)
rate = rational(Fraction(2, 100))
for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
    original = model["calendar_checks"][name][label]
    terms = inputs["calendar_checks"][name][label]
    trial = reprice_route(view, terms, original, funding)
    annual = normalized_route(trial)
    cash = annual["cash_per_usd_10"]
    annual["cash_sha256"] = sha256(encode(cash)).hexdigest()
    point = dict(purchase_date=cash["events"][0]["date"], sale_date=annual["sale_date"],
                 monthly_rate_lower=rate, monthly_rate_upper=rate)
    result = certified_sale_price(trial, annual, view["valuation_and_sale"], point)
    minimum = amount(result["minimum_gross_at_cents"])
    print(f"{caption} | {minimum:.2f} | +{minimum - 6_000_000:.2f}")
PY
```
