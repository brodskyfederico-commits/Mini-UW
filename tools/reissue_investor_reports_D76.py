"""Reissue archived synthetic financial reports on an initial USD 10 basis."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
import json
import os
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_worksheet_refinance_D45 import EVENTS, annual_irr, render_page, replay
from miniuw_worksheet_v1 import build_package, encoded
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_investor_D74 import display


FIXTURE = "templates/synthetic-investor-report-inventory-D76.json"
TITLE = "MINI-UW | QUE RETORNO TENGO SI INVIERTO USD 10?"


def read_pinned(path, digest):
    raw = local_file(ROOT, path).read_bytes()
    require(sha(raw) == digest, f"Archived source differs: {path}")
    return raw


def normalize(story):
    if not story or story.get("currency") != "USD" or story.get("gross_contributions") is None:
        return None
    events = story.get("dated_events", story.get("events"))
    if not events or any(e["amount"] is None for e in events):
        return None
    initial = sum(amount(e["amount"]) for e in events if e["category"] == "initial_capital"
                  and e["kind"] == "contribution")
    if initial <= 0:
        return None
    factor = Fraction(10) / initial
    scaled = [dict(date=e["date"], kind=e["kind"], category=e["category"],
                   amount=rational(amount(e["amount"]) * factor))
              for e in sorted(events, key=lambda e: e["date"])]
    total = {kind: sum(amount(e["amount"]) for e in scaled if e["kind"] == kind)
             for kind in ("contribution", "distribution")}
    contributed, received = total["contribution"], total["distribution"]
    require(contributed == amount(story["gross_contributions"]) * factor
            and received == amount(story["gross_distributions"]) * factor,
            "The historical gross cash ledger does not reconcile")
    return dict(initial_equity=rational(Fraction(10)), contributions=rational(contributed),
                distributions=rational(received), net_cash=rational(received - contributed),
                unrecovered_at_cutoff=rational(max(0, contributed - received)), events=scaled,
                equity_multiple=rational(received / contributed),
                annual_irr_roots=story.get("annual_irr_roots") or [])


def first_blockers(value):
    if isinstance(value, dict):
        return [reason for child in value.values() for reason in first_blockers(child)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def reissue(identity, data):
    candidate = data.get("candidate_snapshot")
    if candidate is not None:
        data = candidate
    require(data.get("decision") == "PENDING", "Archive is outside the synthetic pending scope")
    story = data.get("current_project_return_story", data.get("project"))
    cash = normalize(story)
    blockers = first_blockers(data.get("blockers"))
    label = "Candidato historico | Equity agregado" if candidate is not None else "Ejemplo historico | Equity agregado"
    if cash is None:
        lines = [("Retorno por USD 10 iniciales: PENDIENTE.", True),
                 ("Faltan flujos vigentes o una base positiva y verificable en USD.", False)]
        lines.extend((f"Motivo registrado: {reason[:96]}", False) for reason in blockers[:2])
    else:
        lines = [
            (f"Por USD 10 iniciales: cobros USD {display(cash['distributions'])} | "
             f"Resultado neto USD {display(cash['net_cash'])}", True),
            (f"Aportes totales USD {display(cash['contributions'])} | "
             f"Caja sin recuperar al corte USD {display(cash['unrecovered_at_cutoff'])}", False),
            (f"Multiplo {display(cash['equity_multiple'])}x | TIR anual {annual_irr(cash['annual_irr_roots'])}", False),
            ("Calendario por USD 10 iniciales | USD", True),
        ]
        shown = cash["events"]
        if len(shown) > 19:
            shown = shown[:9] + shown[-9:]
        for e in shown:
            category = EVENTS.get(e["category"], e["category"])
            lines.append((f"{e['date']}  {category} | USD {display(e['amount'])}", False))
        if len(shown) < len(cash["events"]):
            lines.append(("Primeros y ultimos movimientos. Calendario completo en el JSON.", False))
    lines.append(("Retorno personal real pendiente. El calendario representa caja del proyecto.", False))
    pdf = render_page(identity, lines, 17, TITLE, "PENDIENTE | " + label)
    return pdf, dict(decision="PENDING", state="computed_synthetic" if cash else "PENDING",
                     scope="synthetic_aggregate_project_equity", cash=cash, blockers=blockers)


def build_archive():
    fixture_raw = local_file(ROOT, FIXTURE).read_bytes()
    fixture = json.loads(fixture_raw)
    require(fixture["schema"] == "miniuw.synthetic-investor-report-inventory.v1",
            "Unsupported report inventory")
    entries = {}
    files = {}
    rows = fixture["archives"] + fixture["delivered"]
    identities = [row["id"] for row in rows]
    require(len(set(identities)) == len(rows) and all(re.fullmatch("[A-Za-z0-9_-]+", x) for x in identities),
            "Report names must be unique regular ZIP entries")
    for row in fixture["archives"]:
        raw = read_pinned(row["source"], row["source_sha256"])
        read_pinned(row["original_pdf"], row["original_pdf_sha256"])
        identity = row["id"]
        pdf, result = reissue(identity, json.loads(raw))
        entries[identity] = result | {"verification": "archived_bytes_sha256",
                                     "source_path": row["source"], "source_sha256": row["source_sha256"]}
        files[identity + ".pdf"] = pdf
    replayed = {}
    for row in fixture["delivered"]:
        raw = row["case_raw"].encode()
        if raw not in replayed:
            replayed[raw] = build_package(raw)
        package, data = replayed[raw]
        original = package["MiniUW_Resumen.pdf"]
        if row.get("legacy_render") == "D45":
            _, legacy, original = next(replay(data["archive_case"]))
            require(legacy["return_story"] == data["project"], "Legacy refinance ledger differs")
        require(sha(original) == row["original_pdf_sha256"]
                and sha(package["results.json"]) == row["results_sha256"], "Delivered case did not reproduce")
        identity = row["id"]
        if "illustrative_investor" in data or "scenarios" in data:
            pdf, result = original, dict(decision="PENDING", state="already_leads_with_usd_10",
                                         scope="synthetic_participant",
                                         investor=data.get("illustrative_investor", data.get("scenarios")))
        else:
            pdf, result = reissue(identity, data)
        entries[identity] = result | {"verification": "source_first_replay",
                                     "source_path": row["original_pdf"], "source_sha256": row["results_sha256"]}
        files[identity + ".pdf"] = pdf
    for row in rows:
        identity = row["id"]
        entries[identity].update(original_pdf_sha256=row["original_pdf_sha256"],
                                 reissued_pdf_sha256=sha(files[identity + ".pdf"]))
    files["Resultados_por_USD_10.json"] = encoded(dict(schema="miniuw.synthetic-investor-reissues.v1",
                                                       decision="PENDING", inventory_sha256=sha(fixture_raw),
                                                       reports=entries))
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = ZipInfo(name)
            archive.writestr(info, raw, compress_type=ZIP_DEFLATED)
    return buffer.getvalue(), dict(status="passed", decision="PENDING", reports=len(entries),
                                  computed=sum(e["state"] == "computed_synthetic" for e in entries.values()),
                                  pending=sum(e["state"] == "PENDING" for e in entries.values()),
                                  already_usd_10=sum(e["state"] == "already_leads_with_usd_10" for e in entries.values()),
                                  archived_hash_checks=len(fixture["archives"]),
                                  delivered_source_first_checks=len(fixture["delivered"]))


def main():
    parser = ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--output", type=Path)
    group.add_argument("--audit", type=Path)
    args = parser.parse_args()
    try:
        archive, summary = build_archive()
        if args.audit:
            require(args.audit.is_file() and not args.audit.is_symlink()
                    and args.audit.stat().st_size == len(archive) and args.audit.read_bytes() == archive,
                    "Reissued archive differs from the source replay")
        if args.output:
            with TemporaryDirectory(dir=args.output.parent) as temp:
                prepared = Path(temp) / "reports.zip"
                prepared.write_bytes(archive)
                os.link(prepared, args.output)
        print(json.dumps(summary, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps(dict(status="blocked", decision="PENDING", reason=str(error)), ensure_ascii=False),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
