"""Check a synthetic workbook's intake before any financial calculation."""
from base64 import b64decode
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_unified_worksheet_D48 import call
from check_worksheet_exit_D62 import FIXTURE as EXIT
from check_worksheet_refinance_D45 import FIXTURE as REFI
from check_worksheet_sale_costs_D63 import FIXTURE as SALE
from miniuw_foundation.scheduled_expense_case import sha


def verify():
    fixtures = {key: json.loads(local_file(ROOT, key).read_bytes()) for key in (SALE, EXIT, REFI)}
    deal_id = fixtures[EXIT]["scenario_context"]["deal_id"]
    as_of = fixtures[EXIT]["worksheet_as_of_UTC"]
    expectations = (
        ("completa", SALE, "base", as_of, {}),
        ("cero_explícito", SALE, "zero", as_of, {}),
        ("falta_costo", SALE, "missing", as_of, {"C68": "FALTANTE"}),
        ("fórmula", REFI, "formula-dscr", as_of, {"C67": "FALTANTE", "C68": "FALTANTE", "C72": "PENDING"}),
        ("otro_caso", REFI, "different-deal", as_of, {"B3": "CONFLICTO", "C67": "FALTANTE", "C68": "FALTANTE"}),
        ("otro_corte", SALE, "base", "2027-08-01T12:00:00Z", {"E3": "CONFLICTO"}),
        ("cap_cero", EXIT, "zero", as_of, {"C67": "INVÁLIDO", "C68": "FALTANTE"}),
    )
    with TemporaryDirectory(prefix="miniuw-d116-") as temp:
        path = Path(temp) / "workbook.xlsx"
        reports = {}
        for name, fixture, key, snapshot, expected in expectations:
            record = fixtures[fixture]["workbooks"][key]
            raw = b64decode(record["xlsx_base64"], validate=True)
            require(sha(raw) == record["sha256"], "Synthetic workbook bytes differ")
            path.write_bytes(raw)
            result = call("preflight", path, "--deal-id", deal_id, "--snapshot", snapshot)
            require(path.read_bytes() == raw and result["workbook_sha256"] == sha(raw)
                    and result["financial_calculation_run"] is result["real_decisions_enabled"]
                    is result["deployment_enabled"] is False and result["checked_fields"] == 5,
                    "Preflight modified the source, dropped provenance or acquired calculation authority")
            rows = {item["cell"].split("!")[-1]: item for item in result["checklist"]}
            issues = {address: row["state"] for address, row in rows.items() if row["action"] is not None}
            require(issues == expected and result["pending_items"] == len(expected)
                    and result["status"] == ("PENDING" if expected else "checked_synthetic_inputs"),
                    f"The intake checklist differs for {name}: {issues}")
            if name == "cero_explícito":
                require(rows["C68"]["state"] == "LEÍDO" and amount(rows["C68"]["value"]) == 0,
                        "Explicit zero sale cost was lost")
            if name == "fórmula":
                require(rows["C72"]["formula"] and rows["C72"]["cached_value"] is not None
                        and rows["C72"]["value"] is None, "A spreadsheet formula or cached value was used")
            if name == "otro_corte":
                require(rows["E3"]["received"] == as_of and rows["E3"]["expected"] == snapshot,
                        "The conflicting snapshot lost its actual or expected value")
            reports[name] = result

        path.write_bytes(b"invalid workbook")
        call("preflight", path, "--deal-id", deal_id, "--snapshot", as_of, blocked=True)
        call("preflight", path, "--deal-id", "real-project", "--snapshot", as_of, blocked=True)
    return dict(status="passed", decision="PENDING", cases=len(reports), checked_fields=5, rejected_inputs=2,
                examples={name: {key: reports[name][key] for key in ("status", "pending_items")} for name in reports})


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
