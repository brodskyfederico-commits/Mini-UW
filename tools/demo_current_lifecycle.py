"""Current and expired internal views of the same recovered synthetic lifecycle."""
from pathlib import Path
import copy,json,hashlib
from miniuw_foundation.drafts import canonical
from miniuw_foundation.lifecycle_bundle import recover_lifecycle_bundle
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.current_lifecycle import required_lifecycle_sources,assemble_current_lifecycle
from miniuw_foundation.lifecycle_review import render_current_lifecycle_review

ROOT=Path(__file__).resolve().parents[1]
AS_OF='2027-07-01T12:00:00Z'
def raw(p):return canonical(p).encode()


def recover_case():
    r=recover_lifecycle_bundle((ROOT/'templates/synthetic-lifecycle-bundle-example.json').read_bytes())
    return (r.opening_args,r.opening_run,r.capacity_args,r.capacity_run,r.investor_raw,r.binding_raw),r.run


def registry(arguments):
    requirements=required_lifecycle_sources(arguments)
    return {'schema':'miniuw.synthetic-evidence-currency.v1','context':arguments[1].payload['context'],
        'inventory_declared_complete':True,'inventory_basis_ref':'SYNTHETIC-complete-lifecycle-transport-not-original-evidence-authentication',
        'requirements':requirements,'evidence':[{'evidence_id':'SYNTHETIC-lifecycle-evidence-'+str(i),**r,
            'issued_at':'2027-01-01T00:00:00Z','valid_from':'2027-01-01T00:00:00Z','valid_until':'2027-07-02T00:00:00Z',
            'review_status':'accepted_synthetic','value_status':'declared_synthetic','superseded_by_sha256':None,
            'basis_ref':'SYNTHETIC-express-test-validity-not-market-TTL-or-professional-approval'}for i,r in enumerate(requirements)]}


def current(arguments,run,source,at=AS_OF):
    currency=evaluate_evidence_currency(source,at);args=(arguments,run,source,currency,at)
    return args,assemble_current_lifecycle(*args)


def main():
    args,historical=recover_case();declared=registry(args)
    path=ROOT/'templates/synthetic-lifecycle-evidence-example.json';path.write_text(json.dumps(declared,ensure_ascii=False,indent=2)+'\n');source=path.read_bytes()
    ca,valid=current(args,historical,source);valid_report=render_current_lifecycle_review(ca,valid)
    expired=copy.deepcopy(declared);next(r for r in expired['evidence']if r['requirement_id']=='/opening/preopening_cash')['valid_until']=AS_OF
    expired_raw=raw(expired);ea,stale=current(args,historical,expired_raw);stale_report=render_current_lifecycle_review(ea,stale)
    assert valid.payload['current_project_return_story']is not None and stale.payload['current_project_return_story']is None
    for path,r in [('docs/review/Revision_Vigente_Compra_Venta_T62.md',valid_report),('docs/review/Revision_Pendiente_Compra_Venta_T62.md',stale_report)]:(ROOT/path).write_text(r.payload['markdown'])
    return {'purpose':'synthetic_current_lifecycle_and_internal_review_demo','evaluated_as_of_UTC':AS_OF,'required_source_bindings':len(required_lifecycle_sources(args)),
        'historical_lifecycle_run_sha256':historical.sha256,'registry_source_sha256':hashlib.sha256(source).hexdigest(),
        'current_run_sha256':valid.sha256,'current_state':valid.payload['state'],'current_report_sha256':valid_report.payload['markdown_sha256'],
        'expired_registry_json':expired_raw.decode(),'expired_run_sha256':stale.sha256,'expired_state':stale.payload['state'],
        'expired_evidence_blockers':stale.payload['evidence_blockers'],'expired_current_story':stale.payload['current_project_return_story'],
        'pending_report_sha256':stale_report.payload['markdown_sha256'],'historical_calculation_preserved':True,
        'external_decision_pdf_produced':False,'live_expiry_monitor_enabled':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
