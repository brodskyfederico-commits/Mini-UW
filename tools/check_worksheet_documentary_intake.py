"""Exercise documentary intake with synthetic architectural sheets."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from worksheet_documentary_intake import intake


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
    assert result["state"] == result["decision"] == "PENDING" and result["ranking"] == []
    assert all(s["cash"] is None and s["return_per_usd_10"] == "PENDING" for s in result["scenarios"].values())

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
