"""Compute synthetic NNN rent and its recognized months from C16–C21."""
from datetime import date
from fractions import Fraction

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from plan_refinance_D108 import BANK_PERIOD, VALUE_PERIOD
from plan_return_D107 import FORWARD_PERIOD, OPERATING_PERIOD
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


USES = {"C16": "retail", "C17": "restaurant", "C18": "office"}
WINDOW_STARTS = {OPERATING_PERIOD: "2027-07-01", FORWARD_PERIOD: "2028-07-01",
                 BANK_PERIOD: "2028-04-01", VALUE_PERIOD: "2028-04-01"}
POLICY = "SYNTHETIC-D141-net-nnn-after-vacancy-full-months"


def month(day):
    return day.year * 12 + day.month - 1


def commercial_terms(raw, review):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and synthetic_id(source.get("source_ref")),
            "commercial_recognition_policy_unconfirmed")
    rows = {row["value_cell"].split("!")[1]: row for row in review["rows"]}
    inventory = object_or_empty(source.get("uses"))
    require(inventory.keys() == set(USES.values()), "commercial_use_inventory_unconfirmed")
    active = {}
    for cell, name in USES.items():
        use = object_or_empty(inventory[name])
        area = _fraction(use.get("rentable_sf"))
        require(synthetic_id(use.get("source_ref")) and type(use.get("applies")) is bool
                and area is not None, f"commercial_area_or_applicability_unconfirmed:{cell}")
        if use["applies"]:
            require(area > 0 and rows[cell]["state"] == "CONFIRMED_SYNTHETIC",
                    f"commercial_rate_or_area_unconfirmed:{cell}")
            rate = _fraction(rows[cell]["value"])
            require(rate >= 0, f"commercial_rate_outside_profile:{cell}")
            active[name] = dict(cell=cell, area=rational(area), rate=rational(rate), source_ref=use["source_ref"])
        else:
            require(area == 0 and rows[cell]["state"] == "NOT_APPLICABLE",
                    f"commercial_non_applicability_unconfirmed:{cell}")

    cells = {f"C{i}": rows[f"C{i}"].get("sensitivity_value_source_ref", f"sha256:{review['workbook_sha256']}#Inputs!C{i}")
             for i in range(16, 22)}
    evidence = dict(uses=active, cell_sources=cells, inventory_source_ref=source["source_ref"])
    if not active:
        require(all(rows[cell]["state"] == "NOT_APPLICABLE" for cell in ("C19", "C20", "C21")),
                "commercial_non_applicability_unconfirmed:C19-C21")
        return evidence | dict(lease_start=None, vacancy=rational(0), non_recoverable=rational(0))

    require(all(rows[cell]["state"] == "CONFIRMED_SYNTHETIC" for cell in ("C19", "C20", "C21")),
            "commercial_vacancy_cost_or_delay_unconfirmed:C19-C21")
    vacancy, non_recoverable, delay = (_fraction(rows[cell]["value"]) for cell in ("C19", "C20", "C21"))
    require(0 <= vacancy <= 1 and 0 <= non_recoverable <= 1 and delay >= 0 and delay.denominator == 1,
            "commercial_fraction_or_month_count_outside_profile")
    tco = date.fromisoformat(source["tco_date"])
    require(tco.day == 1 and synthetic_id(source.get("tco_source_ref")), "commercial_tco_unconfirmed")
    year, offset = divmod(month(tco) + int(delay), 12)
    lease_start = date(year, offset + 1, 1)
    return evidence | dict(lease_start=lease_start.isoformat(), tco_date=tco.isoformat(),
                           tco_source_ref=source["tco_source_ref"], vacancy=rational(vacancy),
                           non_recoverable=rational(non_recoverable))


def commercial_income(terms, period, *, window_start=None, rent_month_factors=None):
    window_start = WINDOW_STARTS[period] if window_start is None else window_start
    start = month(date.fromisoformat(window_start))
    lease_start = terms["lease_start"]
    months = 0 if lease_start is None else max(0, start + 12 - max(start, month(date.fromisoformat(lease_start))))
    annual = sum((_fraction(use["area"]) * _fraction(use["rate"]) for use in terms["uses"].values()), Fraction())
    if rent_month_factors is None:
        months_at_base_rate = Fraction(months)
    else:
        months_at_base_rate = sum((_fraction(factor) for factor in rent_month_factors[12 - months:]), Fraction())
    gross = annual * months_at_base_rate / 12
    vacancy = gross * _fraction(terms["vacancy"])
    non_recoverable = (gross - vacancy) * _fraction(terms["non_recoverable"])
    return dict(window_start=window_start, lease_start=lease_start, recognized_months=months,
                gross=rational(gross), vacancy=rational(vacancy), non_recoverable=rational(non_recoverable),
                net=rational(gross - vacancy - non_recoverable))
