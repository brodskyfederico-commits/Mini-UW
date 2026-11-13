"""Bind declared draw dates, availability and eligible hard cost to Inputs."""
from fractions import Fraction

from miniuw_foundation.debt_service import _fraction as amount
from miniuw_foundation.drafts import ValidationError
from worksheet_preliminary_D185 import assumption_ready


def read_stages(case, name, inputs, finish, direct_hard, hard, soft, early_soft, cutoff):
    inventory = inputs["support"]["financing"].get("construction_stages")
    if not isinstance(inventory, list) or len(inventory) != finish or finish < 2:
        return [], ["faltan etapas de obra o calendario C46 incompatible"]
    stages = []
    for index, row in enumerate(inventory, 1):
        expected = case["dates"][index]
        if (not assumption_ready(row, cutoff) or row.get("date") != expected
                or set(row) != {"date", "eligible_hard_share", "requested_draw_fraction_of_eligible", "available_draw_usd",
                                "source_ref", "as_of", "owner"}):
            return [], [f"etapa {index}: faltan fecha, datos o respaldo"]
        try:
            share = amount(row["eligible_hard_share"], 12)
            draw_fraction = amount(row["requested_draw_fraction_of_eligible"], 12)
            available = amount(row["available_draw_usd"], 12)
        except ValidationError:
            return [], [f"etapa {index}: importe inválido"]
        if any(x is None or x < 0 for x in (share, draw_fraction, available)) or share > 1:
            return [], [f"etapa {index}: falta participación, desembolso o disponibilidad"]
        eligible = direct_hard * share
        draw = eligible * draw_fraction
        if draw_fraction > 1:
            return [], [f"etapa {index}: desembolso supera costo elegible"]
        soft_due = early_soft if index == 1 else soft - early_soft if index == finish else Fraction()
        stages.append(dict(index=index, cost=hard * share + soft_due, draw=draw, available=available,
                           eligible=eligible, share=share, assumption=row,
                           pointer=f"/scenarios/{name}/support/financing/construction_stages/{index - 1}"))
    if sum(row["share"] for row in stages) != 1:
        return [], ["participación de etapas debe sumar 100% del costo directo"]
    return stages, []
