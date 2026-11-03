"""T62 internal presentation only after complete current lifecycle proof replay."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .current_lifecycle import CurrentLifecycleRun,assemble_current_lifecycle
from .investor_review import _render,literal,amount,ENGINE_SHA256 as PRESENTATION_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T61-T62.md'


@dataclass(frozen=True)
class LifecycleReviewRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def render_current_lifecycle_review(arguments,run):
    if type(arguments)is not tuple or len(arguments)!=5 or type(run)is not CurrentLifecycleRun or assemble_current_lifecycle(*arguments)!=run:raise ValidationError('entire current lifecycle output must reproduce before presentation')
    p=run.payload;story=p['current_project_return_story']
    row={'case_id':'Compra a venta: alcance sintético declarado','state':p['state'],'current_matched_case':None if story is None else{'candidate_project_return_story':story},
        'blockers':p['blockers'],'comparison_blockers':[],'reference_evidence_blockers':[],'candidate_evidence_blockers':p['evidence_blockers'],
        'reference_calculation_blockers':[],'candidate_calculation_blockers':p['calculation_blockers']+p['opening_debt_blockers']+p['bank_capacity_blockers'],
        'reference_original_cost_blockers':[],'candidate_original_cost_blockers':[]}
    markdown=_render({'evaluated_as_of_UTC':p['evaluated_as_of_UTC'],'blockers':[],'case_rows':[row]})
    if story is not None:
        markdown+='\n## Deuda de apertura conciliada bajo calendario sintético\n\n| Préstamo | Principal al abrir operación |\n|---|---:|\n'
        for loan in story['opening_debt_checks']:markdown+='| '+literal(loan['loan_id'])+' | '+amount(loan['scheduled_opening_principal'])+' |\n'
        markdown+='\nLa caja de apertura procede del historial y no se agrega como otro aporte. Los pagos/activos/fondos reales y el retorno personal siguen pendientes.\n'
    result={'component':'T62','purpose':'internal_current_lifecycle_review','engine_sha256':ENGINE_SHA256,'presentation_engine_sha256':PRESENTATION_ENGINE_SHA256,
        'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),'current_lifecycle_run_sha256':run.sha256,'markdown':markdown,'markdown_sha256':digest(markdown),
        'new_financial_calculations_produced':False,'external_decision_pdf_produced':False,'financial_publication_authorized':False,'decision':'PENDING','production_authorized':False}
    encoded=canonical(result);return LifecycleReviewRun(encoded,digest(encoded))
