"""Exercise documentary intake with synthetic architectural sheets."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from worksheet_documentary_intake import intake
from worksheet_plan_checklist import calculate_if_plan_clear, plan_preflight, plan_values


COVER = """SHEET INDEX
G0.0
G0.0
A2.1
A2.1
PROPOSED LEVEL 1 FLOOR PLAN
CONSISTING OF 50 SF OF RETAIL/OFFICE"""
SITE = """A1.0
A1.0
BUILDING DATA
MULTI-FAMILY RESIDENTIAL
OFFICE
RETAIL
RESTAURANT
OPEN SPACE
PROVIDED
2 UNITS
25 S.F.
12 S.F.
13 S.F.
UNIT DATA
STUDIO (1 UNITS)
1-BEDROOM (1 UNITS)
2-BEDROOM (0 UNITS)
3-BEDROOM (0 UNITS)
TOTAL UNITS (2 UNITS)
--
1
1"""
FLOOR = """A2.1
A2.1
W-101
UNIT TYPE X
STUDIO
W-102
UNIT TYPE Y
1 BEDROOM"""
LETTER = "Proposed to be replaced by a mixed-use development consisting of 52sf of Retail/Office"

SHARED = {"noi", "operating_cash", "refinance_capacity", "sale_valuation", "return_per_usd_10"}
BY_AREA = {"residential_rentable_area", "residential_rent_by_area"}
BY_MIX = BY_AREA | {"unit_mix", "residential_costs_by_type", "residential_rent_by_unit"}
BY_COUNT = BY_MIX | {"unit_count", "reserves_by_unit", "construction_cost_by_unit"}
EXPECTED = {
    "duplicate_unit_id": BY_COUNT | SHARED,
    "unit_total_mismatch": BY_COUNT | SHARED,
    "unit_mix_mismatch": BY_MIX | SHARED,
    "unit_area_missing": BY_AREA | SHARED,
    "commercial_area_mismatch": {"commercial_area", "commercial_rent"} | SHARED,
}


def write_pdf(path, *pages):
    with pymupdf.open() as document:
        for text in pages:
            document.new_page().insert_text((32, 32), text, fontsize=9)
        document.save(path)


def verify(root):
    architecture = root / "plan.pdf"
    letter = root / "narrative.pdf"
    schedule = root / "areas.csv"
    schedule.write_text("unit_type,area_sf\nX,450\nY,610\n", encoding="utf-8")
    write_pdf(letter, LETTER)
    write_pdf(architecture, SITE, *("Other sheet" for _ in range(54)), COVER, FLOOR)
    result = intake(architecture, area_schedule=schedule)
    assert result["sources"]["architecture"]["pages"] == 57
    assert result["plan"]["floor_sheets"] == {"A2.1": [57]}
    assert result["plan"]["state"] == "READ" and not result["plan"]["findings"]
    verified = result["plan"]["verified_inputs"]
    assert verified == {"unit_count": 2, "unit_mix": {"STUDIO": 1, "1 BEDROOM": 1, "2 BEDROOM": 0, "3 BEDROOM": 0},
                        "residential_rentable_area": "1060", "commercial_area": "50"}
    assert result["preflight"]["pending_items"] == 0
    assert result["state"] == result["decision"] == "PENDING" and result["ranking"] == []
    assert all(s["cash"] is None and s["return_per_usd_10"] == "PENDING" for s in result["scenarios"].values())

    clean = result["plan"]
    area_catalog = result["sources"]["area_schedule"]["unit_types"]

    changed_floor = FLOOR.replace("W-102", "W-101").replace("TYPE Y\n1 BEDROOM", "TYPE Z\nSTUDIO")
    write_pdf(architecture, changed_floor, COVER, SITE)
    result = intake(architecture, narrative=letter, area_schedule=schedule)
    findings = result["plan"]["findings"]
    assert Counter(row["code"] for row in findings) == {
        "duplicate_unit_id": 1, "unit_total_mismatch": 1, "unit_mix_mismatch": 2,
        "commercial_area_mismatch": 1, "unit_area_missing": 1,
    }
    area = next(row for row in findings if row["code"] == "commercial_area_mismatch")
    assert area["site_page"] == 3 and area["claim"]["page"] == 1 and area["difference_sf"] == "2"
    assert all(row["plan_blockers"] == [f"plan-{i}" for i in range(1, 7)] for row in result["scenarios"].values())

    for finding in findings:
        # With a complete control, apply one checklist row through the same
        # gate the intake uses. Related document findings can occur together.
        expected = EXPECTED[finding["code"]]
        isolated = plan_preflight([finding])
        assert set(isolated["checklist"][0]["affects"]) == expected
        assert {key for key, gate in isolated["calculations"].items() if gate["plan_blockers"] == ["plan-1"]} == expected
        invoked = set()
        for key in isolated["calculations"]:
            calculate_if_plan_clear(isolated, key, lambda: invoked.add(key))
        assert invoked == isolated["calculations"].keys() - expected
        scoped = plan_values(isolated, clean["site"], clean["units"], area_catalog)
        assert scoped == {key: None if key in expected else value for key, value in verified.items()}

    # A conflict on either branch must leave traceable, independent blockers at NOI.
    joint = plan_preflight([findings[0], area])
    assert joint["calculations"]["noi"]["plan_blockers"] == ["plan-1", "plan-2"]
    assert joint["calculations"]["commercial_rent"]["plan_blockers"] == ["plan-2"]
    assert joint["calculations"]["residential_rent_by_unit"]["plan_blockers"] == ["plan-1"]

    for pages, expected in (
        ((COVER, SITE), "missing_sheet"),
        ((COVER, SITE, FLOOR, FLOOR), "duplicate_sheet"),
        ((COVER, SITE, FLOOR.replace("1 BEDROOM", "UNREADABLE")), "incomplete_unit_labels"),
    ):
        write_pdf(architecture, *pages)
        result = intake(architecture, area_schedule=schedule)
        assert result["plan"]["state"] == "PENDING"
        assert expected in {row["code"] for row in result["plan"]["findings"]}


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        verify(Path(directory))
    print("Documentary intake checks passed")
