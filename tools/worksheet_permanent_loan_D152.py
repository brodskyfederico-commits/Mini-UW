"""Bind confirmed C69–C72 to the declared quarterly permanent-loan terms."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import MAX_PAYMENTS, _date, _fraction, rational
from worksheet_local_sources_D127 import object_or_empty, synthetic_id
from worksheet_project_calendar_D145 import offset


POLICY = "SYNTHETIC-D152-permanent-loan-and-capacity"
PAYMENTS_PER_YEAR = 4
RULES = dict(rate="nominal_annual_fixed_convertible_quarterly", payment="regular_in_arrears",
             amortization="whole_years_times_declared_frequency", payments_per_year=PAYMENTS_PER_YEAR,
             maturity="separately_declared_quarterly_maturity", capacity="minimum_of_ltv_and_dscr_only")


def declared_loan_terms(raw, name, review, calendar):
    source = object_or_empty(raw)
    require(source.get("policy") == POLICY and source.get("rules") == RULES and source.get("currency") == "USD"
            and synthetic_id(source.get("source_ref")), "permanent_loan_rate_or_schedule_policy_unconfirmed:C69-C72")
    record = object_or_empty(object_or_empty(source.get("scenarios")).get(name))
    require(record.keys() == {"terms_ref", "maturity_payments", "maturity_ref", "other_limits_declared_complete", "other_limits_ref"}
            and record["other_limits_declared_complete"] is True
            and all(synthetic_id(record[key]) for key in ("terms_ref", "maturity_ref", "other_limits_ref")),
            "permanent_loan_terms_or_limit_inventory_unconfirmed:C69-C72")
    rows = {row["field_id"]: row for row in review["rows"]}
    rates, refs = {}, {}
    for cell in ("C69", "C70", "C71", "C72"):
        row = rows[f"INPUT_{cell}"]
        value = _fraction(row["value"])
        require(row["state"] == "CONFIRMED_SYNTHETIC" and value is not None and value >= 0,
                f"permanent_loan_input_unconfirmed_or_negative:{cell}")
        rates[cell] = value
        refs[cell] = f"sha256:{review['workbook_sha256']}#{row['value_cell']}"
    annual, years, ltv, dscr = (rates[cell] for cell in ("C69", "C70", "C71", "C72"))
    frequency = PAYMENTS_PER_YEAR
    require(annual <= 1, "permanent_loan_nominal_rate_outside_profile:C69")
    require(years.denominator == 1 and 0 < years * frequency <= MAX_PAYMENTS, "permanent_loan_amortization_years_outside_profile:C70")
    require(ltv <= 1, "permanent_loan_ltv_outside_profile:C71")
    require(dscr > 0, "permanent_loan_dscr_outside_profile:C72")
    amortization_payments = int(years * frequency)
    maturity = record["maturity_payments"]
    require(type(maturity) is int and 2 <= maturity <= amortization_payments, "permanent_loan_maturity_outside_sale_profile")
    origination = _date(calendar["refinance_date"])
    dates = [offset(origination, 3 * index).isoformat() for index in range(1, maturity + 1)]
    require(dates[0] == calendar["sale_date"], "permanent_loan_first_quarterly_payment_must_match_sale_cutoff")
    return dict(policy_ref=source["source_ref"], rules=source["rules"], cell_sources=refs, **record,
                annual_nominal_rate=rational(annual), periodic_rate=rational(annual / frequency), payments_per_year=frequency,
                amortization_years=int(years), amortization_payments=amortization_payments,
                maturity_date=dates[-1], payment_dates=dates, maximum_ltv=rational(ltv), minimum_dscr=rational(dscr))
