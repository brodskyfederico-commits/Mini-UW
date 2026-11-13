"""Bind a synthetic bank addendum and compute its debt yield ceiling."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import number, object_or_empty, synthetic_id


BASIS = "annual_bank_noi_over_gross_new_principal"
LIMIT_ID = "DEBT_YIELD"
PROFILE = "synthetic_documented_debt_yield"


def bank_debt_yield_terms(raw, name, quote):
    record = object_or_empty(object_or_empty(raw).get(name))
    require(quote is not None and not quote["blockers"]
            and record.keys() == {"source_ref", "quote_document_id", "quote_source_sha256", "applicability",
                                  "basis", "minimum"}
            and synthetic_id(record["source_ref"]) and record["quote_document_id"] == quote["document_id"]
            and record["quote_source_sha256"] == quote["source_sha256"] and record["basis"] == BASIS,
            "debt_yield_addendum_missing_or_incompatible")
    if record["applicability"] == "not_applicable":
        require(record["minimum"] is None, "debt_yield_not_applicable_with_minimum")
    else:
        minimum = number(record["minimum"])
        require(record["applicability"] == "applicable" and minimum is not None and minimum > 0,
                "positive_bank_debt_yield_minimum_required")
    return record | {"addendum_sha256": sha(encoded(record))}


def debt_yield_capacity(terms, bank_noi, principal):
    noi = _fraction(bank_noi, 1300)
    require(noi is not None and noi >= 0 and principal > 0, "bank_noi_and_positive_principal_required_for_debt_yield")
    minimum = number(terms["minimum"])
    limit = None if minimum is None else rational(noi / minimum)
    require(limit is None or number(limit) is not None, "debt_yield_capacity_outside_exact_amount_domain")
    return terms | dict(annual_bank_noi=bank_noi, gross_principal=rational(principal),
                        achieved=rational(noi / principal), principal_limit=limit)
