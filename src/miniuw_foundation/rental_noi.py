"""T22 evidence-bound assembly from computed residential operations to conditional NOI."""
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .operating_noi import OperatingNoiRun,produce_operating_noi,parse_operating_noi
from .rental_operations import RentalOperationsRun,produce_rental_operations

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-residential-noi-assembly.v1'


def parse_rental_noi_spec(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic assembly spec required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid assembly JSON')from error
    keys={'schema','context','rental_source_sha256','rental_run_sha256','additional_income_inventory_declared_complete','additional_income_rows','tax_floor','tax_coefficient','noi_modelling_assumptions'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA:raise ValidationError('exact synthetic assembly contract required')
    if type(p['context'])is not dict:raise ValidationError('explicit context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    for k in ['rental_source_sha256','rental_run_sha256']:
        if type(p[k])is not str or not re.fullmatch('[a-f0-9]{64}',p[k]):raise ValidationError('exact producer binding required')
    if p['additional_income_inventory_declared_complete']is not None and type(p['additional_income_inventory_declared_complete'])is not bool:raise ValidationError('explicit declared inventory status required')
    # Validate caller-supplied amount metadata and NOI assumptions through the existing contract.
    candidate={'schema':'miniuw.synthetic-operating-noi.v1','profile_id':'SYNTHETIC-M2-MAX-TAX-v1','context':p['context'],
        'currency':None,'period_ref':None,'income_rows':p['additional_income_rows'],'expense_rows':[],
        'tax_floor':p['tax_floor'],'tax_coefficient':p['tax_coefficient'],'modelling_assumptions':p['noi_modelling_assumptions']}
    parse_operating_noi(canonical(candidate).encode())
    return p


@dataclass(frozen=True)
class RentalNoiRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def compiled_raw(self):
        value=self.payload['compiled_noi_source_json'];return None if value is None else value.encode()
    @property
    def noi_run(self):
        value=self.payload['noi_run'];return None if value is None else OperatingNoiRun(**value)


def assemble_rental_noi(rental_raw,rental_run,spec_raw):
    if type(rental_run)is not RentalOperationsRun or produce_rental_operations(rental_raw)!=rental_run:raise ValidationError('residential producer must reproduce from exact source')
    p=parse_rental_noi_spec(spec_raw);r=rental_run.payload;blockers=[];compiled=None;noi=None
    if p['rental_source_sha256']!=r['source_sha256']:blockers.append('rental_source_identity_mismatch')
    if p['rental_run_sha256']!=rental_run.sha256:blockers.append('rental_run_identity_mismatch')
    if p['context']!=r['context']:blockers.append('assembly_context_mismatch')
    if r['state']!='computed_synthetic':blockers.append('residential_producer_blocked')
    if p['additional_income_inventory_declared_complete']is not True:blockers.append('additional_income_inventory_not_declared_complete')
    if not p['additional_income_rows']:blockers.append('additional_income_inventory_empty_not_assumed_zero')
    if not blockers:
        def amount(value,identity,locator):
            return {'item_id':identity,'value':value,'currency':r['currency'],'period_ref':r['period_ref'],
                'unit':'currency_per_declared_period','basis':'accrual','source_ref':'derived:'+rental_run.sha256+':'+locator}
        incomes=[amount(r['residential_effective_rent'],'SYNTHETIC-derived-residential-rent','/residential_effective_rent')]+p['additional_income_rows']
        expenses=[amount(row['amount'],'SYNTHETIC-derived-expense-'+row['item_id'],'/expenses/'+str(i)+'/amount')for i,row in enumerate(r['expenses'])]
        source={'schema':'miniuw.synthetic-operating-noi.v1','profile_id':'SYNTHETIC-M2-MAX-TAX-v1','context':p['context'],
            'currency':r['currency'],'period_ref':r['period_ref'],'income_rows':incomes,'expense_rows':expenses,
            'tax_floor':p['tax_floor'],'tax_coefficient':p['tax_coefficient'],'modelling_assumptions':p['noi_modelling_assumptions']}
        compiled=(canonical(source)+'\n').encode()
        try:noi=produce_operating_noi(compiled)
        except ValidationError:blockers.append('compiled_NOI_outside_consumer_contract_or_transport_budget')
        if noi is not None:blockers.extend('NOI:'+reason for reason in noi.payload['blockers'])
    payload={'component':'T22','purpose':'conditional_synthetic_residential_to_NOI_assembly','engine_sha256':ENGINE_SHA256,
        'rental_source_sha256':r['source_sha256'],'rental_run_sha256':rental_run.sha256,'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),
        'rental_run':asdict(rental_run),'context':p['context'],'compiled_noi_source_json':None if compiled is None else compiled.decode(),
        'compiled_noi_source_sha256':None if compiled is None else hashlib.sha256(compiled).hexdigest(),
        'noi_run':None if noi is None else asdict(noi),'computed_noi':None if noi is None else noi.payload['noi'],
        'residential_blockers':r['blockers'],'blockers':sorted(set(blockers)),
        'state':'computed_synthetic'if not blockers and noi is not None else'blocked',
        'additional_income_scope_independently_verified':False,'tax_policy_adopted':False,'financially_validated':False,
        'decision':'PENDING','run_ready':False,'review_authenticated':False,'production_authorized':False,'financial_module_closed':False}
    encoded=canonical(payload);return RentalNoiRun(encoded,digest(encoded))
