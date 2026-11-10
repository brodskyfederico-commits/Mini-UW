"""Check that pending reasons reach the PDF and the prior schema remains auditable."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_unified_worksheet_D48 import call, save


REASONS = {
    "missing_cost": "Falta C68 (costo variable de venta) en la hoja.",
    "tax_pending": "Falta resolver si aplica el impuesto de venta.",
}


def verify():
    templates = ROOT / "templates"
    previous = json.loads((templates / "synthetic-unified-worksheet-costed-sale-D65.json").read_bytes())
    current = json.loads((templates / "synthetic-unified-worksheet-costed-sale-D67.json").read_bytes())
    with TemporaryDirectory(prefix="miniuw-d67-") as temp:
        root = Path(temp)
        for key, reason in REASONS.items():
            results = []
            for label, case in (("previous", previous), ("current", current)):
                folder = root / f"{key}-{label}"
                source = folder.with_suffix(".json")
                save(source, case | {"archive_case": key})
                created = call("run", source, "--output", folder)
                audited = call("audit", folder)
                require(created["pdf_sha256"] == audited["pdf_sha256"], "PDF audit changed its hash")
                page, = PdfReader(folder / "MiniUW_Resumen.pdf").pages
                text = page.extract_text()
                require((reason in text) == (label == "current") and "Minimo VP USD" not in text,
                        "The PDF lost its versioned pending explanation or exposed an amount")
                require(all(other not in text for other in REASONS.values() if other != reason),
                        "The PDF attributed a blocker to the wrong source")
                result = json.loads((folder / "results.json").read_bytes())
                require(result["state"] == result["decision"] == "PENDING"
                        and result["project"] is result["risk"] is result["cash_recovery"] is None
                        and result["deployment_enabled"] is result["real_decisions_enabled"] is False,
                        "The pending diagnosis acquired a decision or return")
                del result["pdf_sha256"], result["provenance"]["case_sha256"]
                results.append(result)
            require(results[0] == results[1], "A presentation revision changed financial results")

        sale_only = json.loads((templates / "synthetic-unified-worksheet-sale-D47.json").read_bytes())
        unsupported = root / "unsupported.json"
        save(unsupported, sale_only | {"schema": current["schema"]})
        call("run", unsupported, "--output", root / "unsupported", blocked=True)
    return dict(status="passed", decision="PENDING", previous_pdfs_audited=2,
                diagnostic_pdfs_audited=2, unsupported_profile_rejected=True)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
