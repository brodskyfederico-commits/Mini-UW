"""Exercise the public worksheet command from the case file through the audited PDF."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from math import ceil
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import json
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require


TOOL = ROOT / "tools/miniuw_worksheet_v1.py"
TEMPLATES = {
    "without_refinance": ROOT / "templates/synthetic-unified-worksheet-sale-D47.json",
    "with_refinance": ROOT / "templates/synthetic-unified-worksheet-refinance-D47.json",
}
CASES = {
    "without_refinance": ("matched", "twelve", "parent-expired", "zero-conflict"),
    "with_refinance": ("cash-out", "cash-in", "above-capacity", "zero-ltv", "missing-dscr", "formula-dscr",
                       "different-deal"),
}
SALE_RECEIPTS = {"matched": Fraction(578), "twelve": Fraction(576),
                 "cash-out": Fraction(54662401, 60602), "cash-in": Fraction(54662401, 60602)}
RATE = Fraction(1, 50)
CLOSE = "2027-07-01"


def call(*args, blocked=False):
    proc = run([sys.executable, str(TOOL), *(str(arg) for arg in args)], cwd=ROOT, capture_output=True,
               text=True, timeout=90, check=False)
    require(proc.returncode == (2 if blocked else 0), f"Unexpected CLI outcome: {proc.stderr}")
    value = json.loads(proc.stderr if blocked else proc.stdout)
    require(value["decision"] == "PENDING", "CLI acquired a real decision")
    return value


def q(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def expected_events(name):
    events = [("2027-03-01", "distribution", "operating_distribution", 100),
              ("2027-06-01", "distribution", "operating_distribution", 100),
              (CLOSE, "distribution", "net_sale_distribution", SALE_RECEIPTS[name])]
    if name in ("matched", "twelve"):
        return events + [("2026-10-01", "contribution", "initial_capital", 1000),
                         ("2026-11-01", "contribution", "additional_capital", 400)]
    refi = ("distribution", "net_refinance_distribution", 200) if name == "cash-out" else (
        "contribution", "refinance_cash_in", 80)
    return events + [("2027-01-01", "contribution", "initial_capital", 1000), ("2027-04-01", *refi)]


def verify_capacity(name, result):
    if result["profile"] == "without_refinance":
        require(result["capacity"] is result["refinance"] is None, "Sale-only case acquired refinance values")
        return
    capacity = result["capacity"]
    if capacity is None:
        require(name in ("missing-dscr", "formula-dscr", "different-deal"), "Capacity was withdrawn unexpectedly")
        return
    unit_payment = Fraction(1, 100) / (1 - Fraction(101, 100) ** -3)
    dscr_limit = 2000 / (Fraction(5, 4) * 12 * unit_payment)
    ltv_limit = 0 if name == "zero-ltv" else 400
    require(q(capacity["capacity_limits"]["DSCR"]) == dscr_limit
            and q(capacity["capacity_limits"]["LTV"]) == ltv_limit
            and q(capacity["maximum_principal_capacity"]) == min(ltv_limit, dscr_limit),
            "Worksheet capacity differs from the independent DSCR/LTV calculation")
    refi = result["refinance"]
    if refi is not None:
        sources = 150 + 820 + 100
        uses = 100 + (20 if name == "cash-out" else 300) + 150 + 600
        bridge = refi["sources_and_uses"]
        require(refi["date"] == "2027-04-01" and q(refi["gross_loan"]) == 150
                and q(bridge["total_sources"]) == sources and q(bridge["total_uses"]) == uses
                and q(refi["cash_out"]) == max(0, sources - uses) and q(refi["cash_in"]) == max(0, uses - sources),
                "Refinance closing did not reconcile to the independent sources and uses")


def verify_figures(name, result, page):
    project = result["project"]
    recovery = result["cash_recovery"]
    verify_capacity(name, result)
    if name not in SALE_RECEIPTS:
        require(result["state"] == "PENDING" and project is recovery is result["risk"] is result["refinance"] is None
                and "Minimo VP USD" not in page and "Minimo para recuperar (VP):" not in page,
                "Blocked page exposed project cash or a recovery price")
        return
    require(result["state"] == "computed_synthetic_project_cash", "Expected project cash is missing")
    events = expected_events(name)
    actual = Counter((row["date"], row["kind"], row["category"], q(row["amount"]))
                     for row in project["events"] if q(row["amount"]) != 0)
    require(actual == Counter(events), "Dated cash differs from the independent event inventory")
    contributions = sum(value for _, kind, _, value in events if kind == "contribution")
    distributions = sum(value for _, kind, _, value in events if kind == "distribution")
    profit = distributions - contributions
    require((q(project["gross_contributions"]), q(project["gross_distributions"]), q(project["net_cash_profit"]),
             q(project["equity_multiple"]), q(result["risk"]["cash_shortfall_at_horizon"]))
            == (contributions, distributions, profit, distributions / contributions, max(0, -profit)),
            "Gross cash, multiple or shortfall differs from the independently summed events")
    net_by_date = Counter()
    for date, kind, _, value in events:
        net_by_date[date] += value if kind == "distribution" else -value
    flows = project["dated_net_flows"]
    require(all(q(row["net"]) == net_by_date.pop(row["date"], 0) for row in flows) and not net_by_date
            and flows[-1]["date"] == CLOSE, "Net cash calendar differs")
    start = min(date for date, _, _, _ in events)

    def index(date):
        return 12 * (int(date[:4]) - int(start[:4])) + int(date[5:7]) - int(start[5:7])

    def present_value(rate):
        return sum((value if kind == "distribution" else -value) / (1 + rate) ** index(date)
                   for date, kind, _, value in events)

    root, = project["periodic_irr"]["roots"]
    interval = root["periodic_rate_interval"]
    lower, upper = Fraction(interval["lower"]), Fraction(interval["upper"])
    annual, = project["annual_irr_roots"]
    require(lower < upper and present_value(lower) * present_value(upper) <= 0
            and (q(annual["annual_rate_interval"]["lower"]), q(annual["annual_rate_interval"]["upper"]))
            == ((1 + lower) ** 12 - 1, (1 + upper) ** 12 - 1),
            "Reported TIR interval does not bracket dated cash or annualize exactly")

    for year in project["annual_cash_receipts"]:
        flows_in_year = [(kind, category, value) for date, kind, category, value in events
                         if int(date[:4]) == year["calendar_cash_receipt_year"]]
        year_a = sum(value for kind, _, value in flows_in_year if kind == "contribution")
        year_d = sum(value for kind, _, value in flows_in_year if kind == "distribution")
        year_op = sum(value for _, category, value in flows_in_year if category == "operating_distribution")
        require((q(year["gross_contributions"]), q(year["gross_distributions"]), q(year["operating_distributions_only"]))
                == (year_a, year_d, year_op), "Annual cash differs from the dated event inventory")

    price = 400 - present_value(RATE) * (1 + RATE) ** index(CLOSE)
    cents = ceil(price * 100)
    shown_price = f"{cents // 100}.{cents % 100:02d}"
    require(recovery["sale_date"] == CLOSE and Fraction(recovery["minimum_gross_sale_price"]) == price
            and recovery["minimum_gross_sale_price_in_cents"] == cents
            and shown_price in page, "Recovery price or PDF differs from the independent discounted ledger")


def verify_case(profile, name, temp):
    source = load(TEMPLATES[profile])
    source["archive_case"] = name
    entry = temp / f"{name}.json"
    save(entry, source)
    directory = temp / name
    written = call("run", entry, "--output", directory)
    verified = call("audit", directory)
    result = load(directory / "results.json")
    pdf = directory / "MiniUW_Resumen.pdf"
    page, = PdfReader(pdf).pages
    text = page.extract_text()
    require("PENDIENTE" in text and result["decision"] == "PENDING"
            and result["deployment_enabled"] is result["real_decisions_enabled"] is False
            and result["personal_investor_return"] is None, "Synthetic decision guard differs")
    require(written["pdf_sha256"] == verified["pdf_sha256"] == result["pdf_sha256"]
            == sha256(pdf.read_bytes()).hexdigest() and (directory / "case.json").read_bytes() == entry.read_bytes(),
            "CLI evidence lost the exact input or PDF")
    verify_figures(name, result, text)
    return dict(profile=profile, state=result["state"], pdf_sha256=result["pdf_sha256"])


def verify_failed_publication(temp):
    good = temp / "matched.json"
    target = temp / "matched"
    require(call("run", good, "--output", target)["status"] == "verified_identical_output",
            "Identical retry did not reuse the package")
    call("run", temp / "cash-out.json", "--output", target, blocked=True)
    require(call("audit", target)["status"] == "verified_source_first", "A different run modified the package")

    cases = (
        ("bad-hash", load(good) | {"archive_sha256": "0" * 64}),
        ("wrong-profile-case", load(good) | {"archive_case": "cash-out"}),
        ("missing-rate", {key: value for key, value in load(good).items() if key != "monthly_discount_rate"}),
    )
    for name, case in cases:
        entry = temp / f"{name}.json"
        save(entry, case)
        call("run", entry, "--output", temp / name, blocked=True)
        require(not (temp / name).exists(), "Invalid input materialized a package")

    manifest_path = target / "package.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    result = target / "results.json"
    pdf = target / "MiniUW_Resumen.pdf"
    original_result = result.read_bytes()
    for changed, value in ((result, original_result.replace(b'"decision":"PENDING"', b'"decision":"PASS"')),
                           (pdf, pdf.read_bytes() + b"\n% forged PDF\n")):
        original = changed.read_bytes()
        require(original != value, "Tamper probe did not change the artifact")
        changed.write_bytes(value)
        row = next(row for row in manifest["files"] if row["path"] == changed.name)
        old = row.copy()
        row.update(bytes=len(value), sha256=sha256(value).hexdigest())
        save(manifest_path, manifest)
        call("audit", target, blocked=True)
        changed.write_bytes(original)
        row.update(old)
    manifest_path.write_bytes(manifest_bytes)
    call("audit", target)
    return len(cases) + 3


def verify():
    with TemporaryDirectory(prefix="miniuw-d48-") as temp:
        path = Path(temp)
        cases = {name: verify_case(profile, name, path) for profile, names in CASES.items() for name in names}
        probes = verify_failed_publication(path)
    return dict(status="passed", decision="PENDING", pages=len(cases), computed=len(SALE_RECEIPTS),
                pending=len(cases)-len(SALE_RECEIPTS), rejection_probes=probes, cases=cases)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), sort_keys=True))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
