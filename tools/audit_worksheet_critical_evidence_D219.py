"""Check critical bot claims against the independent synthetic evidence inventory."""
from argparse import ArgumentParser
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from miniuw_foundation.debt_service import rational
from worksheet_revision_D128 import review_revision

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "templates/synthetic-critical-evidence-D219.json"
BOT = ("local_review", "bots")
CHECKED = "checked_synthetic"
SCENARIOS = ("Base", "Downside")
WORKBOOKS = dict(zip(SCENARIOS, ("Inputs.xlsx", "Downside_Inputs.xlsx"), strict=True))
MISSING = object()


def get(record, path):
    for key in path:
        if isinstance(record, dict):
            record = record.get(key, MISSING)
        elif isinstance(record, list) and isinstance(key, int) and 0 <= key < len(record):
            record = record[key]
        else:
            return MISSING
    return record


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def digest(raw):
    return sha256(raw).hexdigest() if raw is not None else None


@dataclass
class Claim:
    bot: str
    record: tuple
    expected: dict
    parents: tuple = ()
    sources: tuple = ()

    def green(self, results):
        return (get(results, self.record + ("state",)) == CHECKED
                or any(get(results, parent + ("state",)) == CHECKED for parent in self.parents))

    def check(self, results):
        required = {("state",): CHECKED, ("blockers",): [], **self.expected}
        for path, expected in required.items():
            observed = get(results, self.record + path)
            if observed is MISSING:
                yield dict(bot=self.bot, path=self.record + path, reason="sin_respaldo")
            elif canonical(observed) != canonical(expected):
                yield dict(bot=self.bot, path=self.record + path, reason="discrepancia",
                           expected=expected, observed=observed)


@dataclass
class Field:
    key: str
    claims: tuple
    locator: str


def quote_claim(path, page, label, observed, digest_hex, ref):
    file = "Evidence.pdf"
    bot = path[len(BOT)]
    return Claim(bot, path, {
        ("page",): page, ("source_file",): file, ("source_sha256",): digest_hex,
        ("deal_id",): ref["deal_id"], ("revision",): ref["local_revision"],
        ("document_id",): ref["page_documents"][str(page)],
        ("locators", label): f"{file} p. {page} / {label}",
        ("observations", label): observed,
    }, (("local_review",), BOT + (bot,)), (file,))


def fields(ref):
    """Each field is counted once, even with several readers of its evidence."""
    sources = ref["sources"]
    plan = sources["Plan.pdf"]
    evidence = sources["Evidence.pdf"]
    review = (("local_review",),)
    area = rational(Fraction(ref["gross_area_m2"]))
    area_claims = [
        Claim("B03", BOT + ("B03", "documents", "plan_pdf"), {
            ("sha256",): plan, ("source_file",): "Plan.pdf", ("duplicate_sheet_pages",): {},
        }, review, ("Plan.pdf",)),
        Claim("B07", BOT + ("B07",), {("value",): area, ("unit",): "m2",
            ("plan_ref",): ref["plan_ref"]}, review, ("Plan.pdf",)),
        Claim("B08", BOT + ("B08", "area"), {
            ("value",): area, ("unit",): "m2", ("plan_ref",): ref["plan_ref"],
            ("locator",): "Evidence.pdf p. 2 / Area"}, review, ("Evidence.pdf",)),
        quote_claim(BOT + ("B08", "gc_pdf"), 2, "Area", ["m2", ref["gross_area_m2"]], evidence, ref),
        Claim("B09", BOT + ("B09",), {
            ("difference",): rational(0), ("maximum",): rational(Fraction(ref["gc_tolerance_m2"])),
            ("unit",): "m2", ("rule_ref",): ref["gc_rule_ref"]}, review, ("Plan.pdf", "Evidence.pdf")),
    ]
    for index, (bot, spec) in enumerate(ref["plan"].items()):
        page, sheet, label, line = spec
        values = {("source_sha256",): plan, ("source_file",): "Plan.pdf", ("page",): page,
                  ("value",): area, ("unit",): "m2", ("raw_line",): line,
                  ("sheet",): sheet, ("plan_ref",): ref["plan_ref"],
                  ("locator",): f"p. {page} / {sheet} / {label}"}
        path = BOT + (bot,)
        area_claims.append(Claim(bot, path, values | {("candidate_pages",): [page]}, review, ("Plan.pdf",)))
        for method in ("text", "ocr"):
            area_claims.append(Claim(bot, path + ("observations", method), values, (path,), ("Plan.pdf",)))
        area_claims.append(Claim("B07", BOT + ("B07", "readings", index), values, (BOT + ("B07",),), ("Plan.pdf",)))
    yield Field("Compartido:GBA", tuple(area_claims), "Plan.pdf A101/A601 y cotización GC")

    parcel = ref["parcel"]
    record = parcel["Record"]
    official = tuple(quote_claim(BOT + (bot, "official_pdf"), 4, label, value, evidence, ref)
                     for bot in ("B10", "B11") for label, value in parcel.items())
    verified_parcel = Claim("B11", BOT + ("B11",), {
        ("value",): int(record[2]), ("unit",): record[1], ("as_of",): ref["as_of"],
        ("document_locator",): "Evidence.pdf p. 4 / Record", ("document_sha256",): evidence,
        ("locator",): f"/records/{record[0]}/max_floors",
    }, review, ("Evidence.pdf",))
    yield Field("Compartido:max_floors", (*official, verified_parcel), "Evidence.pdf p. 4 / Record")

    for scenario in SCENARIOS:
        view = ("scenarios", scenario)
        book = WORKBOOKS[scenario]
        vertical = f"Vertical {scenario}"
        scope, unit, cost = ref["gc_cost"][scenario]
        quote = quote_claim(BOT + ("B08", "gc_pdf"), 2, vertical, [scope, unit, cost], evidence, ref)
        used_cost = Claim("B09", view + ("document_financial_binding",),
                          {("model_cost",): rational(Fraction(cost))}, sources=("Evidence.pdf", book))
        yield Field(f"{scenario}:GC_vertical", (quote, used_cost),
                    f"Evidence.pdf p. 2 / {vertical}")

        for kind, bank in ref["bank"][scenario].items():
            area_key, binding = {
                "construction": ("construction_pdf_by_scenario", "construction_financing"),
                "permanent": ("bank_pdf_by_scenario", "permanent_loan"),
            }[kind]
            page = bank["page"]
            for key, spec in bank["terms"].items():
                label, *observed = spec
                value = observed[-1] if key == "maturity_date" else rational(Fraction(observed[-1]))
                quote = quote_claim(BOT + ("B08", area_key, scenario), page, label, observed, evidence, ref)
                quote.expected["document", key] = value
                use = view + (binding, "bank_document_binding")
                bound = Claim("B08", use + ("quote",), quote.expected, (use,), ("Evidence.pdf", book))
                yield Field(f"{scenario}:{kind}:{key}", (quote, bound),
                            f"Evidence.pdf p. {page} / {label}")

        market = view + ("market_insurance_review",)
        for kind, reading in ref["market"][scenario].items():
            path = market + ("records", kind)
            for cell, value in reading["cells"].items():
                comparison = ("comparison",) if kind == "insurance" else ("comparisons", cell)
                expected = {
                    ("declared_sha256",): reading["sha256"], ("observed_sha256",): reading["sha256"],
                    ("document",): reading["document"],
                    comparison + ("value",): rational(Fraction(value)),
                    comparison + ("value_source",): f"sha256:{sources[book]}#Inputs!{cell}",
                }
                document = reading["document"]
                if kind == "insurance":
                    expected[comparison + ("insured_units",)] = document["insured_units"]
                    expected[comparison + ("coverage_ref",)] = document["coverage_ref"]
                else:
                    expected[comparison + ("range",)] = document["ranges"][cell]
                yield Field(f"{scenario}:market:{cell}", (Claim("B08", path, expected, (market,), (book,)),),
                            f"{document['source_ref']} y {book} / Inputs!{cell}")


def audit(results, documents, current_revision, ref):
    if (ref["schema"] != "miniuw.synthetic-critical-evidence.v1"
            or not ref["deal_id"].startswith("SYNTHETIC-")
            or results.get("decision") != "PENDING"
            or results.get("deployment_enabled") is not False
            or results.get("real_decisions_enabled") is not False):
        raise ValueError("Se requiere un expediente sintético con dictamen real PENDING")
    case_raw = documents.get("case.json")
    case = json.loads(case_raw) if case_raw is not None else None
    if case is not None and case.get("schema") == "miniuw.synthetic-native-rental-inputs.v34":
        from worksheet_variant_evidence_D268 import reference_issues, inventory_pending
        issues = reference_issues((json.dumps(ref) + "\n").encode(), case)
        if issues:
            return inventory_pending(issues)
    if case is not None and get(case, ("rent_inputs", "deal_id")) != ref["deal_id"]:
        raise ValueError("El inventario de cotejo corresponde a otro expediente sintético")
    revision = ("revision_review",)
    revision_ok = (
        current_revision is not None
        and current_revision == documents.get("current_revision.json")
        and get(results, revision + ("reference_sha256",)) == digest(current_revision)
        and get(results, revision + ("state",)) == "matched_synthetic_revision"
        and get(results, revision + ("blockers",)) == []
        and get(results, ("local_review", "revision")) == ref["local_revision"]
        and case_raw is not None
        and results.get("case_sha256") == digest(case_raw)
        and review_revision(case, current_revision)["state"] == "matched_synthetic_revision"
    )
    documents_ok = {name: digest(documents.get(name)) == sha for name, sha in ref["sources"].items()}
    from worksheet_horizon_fiscal_D267 import fiscal_source_issues
    fiscal_issues=fiscal_source_issues(case,ref,documents)
    rows = {}
    inventory=list(fields(ref))
    if "holding_fiscal" in ref:
        from worksheet_horizon_fiscal_D267 import critical_fiscal_fields
        inventory.extend(critical_fiscal_fields(ref))
    for field in inventory:
        issues = []
        claimed = [claim for claim in field.claims if claim.green(results)]
        if claimed:
            issues.extend(issue for claim in claimed for issue in claim.check(results))
            if ":fiscal:" in field.key:
                issues.extend(fiscal_issues.get(field.key.split(":",1)[0],[]))
            issues.extend(dict(bot=bot, path=(file,), reason="fuente_ausente_o_huella_distinta")
                          for bot, file in sorted({(claim.bot, file) for claim in claimed for file in claim.sources})
                          if not documents_ok[file])
            if not revision_ok:
                issues.append(dict(path=revision, reason="revision_no_vigente_o_sin_respaldo"))
        status = "PENDING"
        if issues:
            status = "FALSE_GREEN"
        elif len(claimed) == len(field.claims):
            status = "VERIFIED_GREEN"
        if field.key in rows:
            raise ValueError(f"Dato crítico duplicado en el inventario: {field.key}")
        rows[field.key] = dict(status=status, locator=field.locator,
                               bots=sorted({claim.bot for claim in field.claims}),
                               green_bots=sorted({claim.bot for claim in claimed}), issues=issues)
    counts = {state: sum(row["status"] == state for row in rows.values())
              for state in ("VERIFIED_GREEN", "FALSE_GREEN", "PENDING")}
    if not rows:
        raise ValueError("El inventario de cotejo está vacío")
    return dict(
        status="PASSED" if counts["VERIFIED_GREEN"] == len(rows) else "PENDING",
        decision="PENDING", critical_fields=len(rows), counts=counts,
        green_claims=sum(bool(row["green_bots"]) for row in rows.values()), current_revision_verified=revision_ok,
        fields=rows,
    )


def optional_read(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def audit_package(package, current_revision, ref):
    names = (*ref["sources"], "case.json", "current_revision.json")
    documents = {name: optional_read(package / name) for name in names}
    return audit(json.loads((package / "results.json").read_bytes()), documents, optional_read(current_revision), ref)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--current-revision", required=True, type=Path)
    args = parser.parse_args()
    report = audit_package(args.package, args.current_revision, json.loads(REFERENCE.read_bytes()))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
