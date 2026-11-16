# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Comparación de una página](review/MiniUW_D248_Downside_Recorte_Adicional_2pct.pdf). Downside sintético de D238, con venta bruta fija de USD 6.000.000 el 30/03/2030, comisión del 7 % y tasa del 2 % mensual. El costo directo original era USD 2.744.000 y quedaban USD 1.372.000 después del recorte inicial del 50 %.

| Ruta | Recorte adicional desde el 50 % | Puntos adicionales sobre la obra original | Recorte total | Obra directa resultante |
| --- | ---: | ---: | ---: | ---: |
| Con refi | USD 165.495,75 | 6,0312 pp | 56,0312 % | USD 1.206.504,25 |
| Sin refi | USD 201.114,39 | 7,3292 pp | 57,3292 % | USD 1.170.885,61 |

El recorte adicional equivale al 12,0624 % de la obra que quedaba con refi y al 14,6585 % sin refi. El ensayo reduce en la misma proporción la obra vertical, el estacionamiento y el sitio. A partir de ese presupuesto se recalculan contingencia, indirectos, desembolsos, intereses y aportes. Cada ruta mantiene su calendario de venta y sus condiciones de deuda.

| Por USD 10 iniciales al recorte mínimo | Aporte adicional | Cobro nominal total | Cobro neto en la venta del 30/03/2030 |
| --- | ---: | ---: | ---: |
| Con refi | USD 1,68 | USD 22,23 | USD 18,77 |
| Sin refi | USD 1,39 | USD 22,67 | USD 22,14 |

El VPS reprodujo los flujos de [D246](worksheet-downside-fixed-sale-discount-rates-D246.md) con el recorte del 50 % y cotejó los nuevos saldos descontando cada movimiento al 30/03/2027. Cada recorte informado es el primer centavo que da un VAN no negativo. Con un centavo menos, queda un faltante. En el PDF están los aportes y cobros por fecha, incluido el desembolso neto de la refi del 30/03/2029.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

Desde la raíz del repositorio, con las dependencias de [D246](worksheet-downside-fixed-sale-discount-rates-D246.md), pasá las rutas al expediente sintético y su constancia vigente como los dos argumentos.

```sh
PYTHONPATH=src:tools:tests python3 - expediente vigente.json <<'PY'
from datetime import date
from fractions import Fraction
from pathlib import Path
from sys import argv
import json

from check_discounted_sale_recovery_D34 import present_value
from worksheet_annual_coc import quantity as amount
from worksheet_annual_comparison import ROUTES, audited_annual_comparison
from worksheet_annual_crossover_construction import construction_at_cut, minimum_construction_cut, reprice_route
from worksheet_annual_discount_crossover import exact_rows, monthly_flows
from worksheet_downside_fixed_sale_construction import cash_with_sale_price

labels = ("annual_hold_with_refinance", "annual_hold_without_refinance")
files, _, _, _ = audited_annual_comparison(Path(argv[1]), Path(argv[2]), labels)
model = json.loads(files["results.json"])
inputs = json.loads(files["case.json"])["rent_inputs"]
name = "Downside"
view = model["scenarios"][name]
starting_cut = amount(view["construction_budget"]["direct_hard_cost"]) / 2
commission = amount(view["valuation_and_sale"]["sale_cost_fraction"])
for label, (caption, _, _) in zip(labels, ROUTES, strict=True):
    original = model["calendar_checks"][name][label]
    terms = inputs["calendar_checks"][name][label]
    origin = date.fromisoformat(original["cash_per_usd_10"]["events"][0]["date"])

    def evaluate(extra):
        _, funding = construction_at_cut(model, inputs, name, starting_cut + extra)
        trial = reprice_route(view, terms, original, funding)
        cash = cash_with_sale_price(trial, 6_000_000, commission)
        van = present_value(exact_rows(monthly_flows(cash, origin)), Fraction(1, 50))
        return (van, van), cash

    extra, at_minimum, below, _ = minimum_construction_cut(starting_cut, evaluate)
    assert below < 0 <= at_minimum[0]
    print(f"{caption} | {extra:.2f}")
PY
```
