"""Apply D219 before candidate cash, metrics or reports become an integral result."""
import json

from audit_worksheet_critical_evidence_D219 import audit, digest
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE
from worksheet_native_mapping_D139 import SCENARIOS


def withhold_unverified_cash(views, documents, revision, case_sha256, reference, sources):
    claims = dict(case_sha256=case_sha256, local_review=documents, revision_review=revision,
                  scenarios=views, decision="PENDING", real_decisions_enabled=False, deployment_enabled=False)
    evidence = audit(claims, sources, sources[CURRENT_REVISION_FILE], json.loads(reference))
    blockers = {name: [] for name in SCENARIOS}
    for field, row in evidence["fields"].items():
        status = row["status"]
        if status == "VERIFIED_GREEN":
            continue
        scope, _, _ = field.partition(":")
        reason = "falso_verde" if status == "FALSE_GREEN" else "respaldo_pendiente"
        for name in SCENARIOS if scope == "Compartido" else (scope,):
            blockers[name].append(f"B12:D219:{reason}:{field}")

    affected = [name for name in SCENARIOS if blockers[name]]
    checked = {
        name: dict(state="PENDING", cash_per_usd_10=None, capacity=None, noi_by_period={},
                   blockers=blockers[name] + views[name]["blockers"])
        for name in affected
    }
    return views | checked, evidence | dict(reference_sha256=digest(reference), affected_scenarios=affected)
