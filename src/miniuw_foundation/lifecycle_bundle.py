"""T60 bounded JSON transport of exact synthetic sources and replayed lifecycle proofs."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical
from .intake import _unique_object,_invalid_constant
from . import opening_debt,lifecycle_returns
from .opening_debt import reconcile_opening_debt,OpeningDebtRun
from .lifecycle_returns import assemble_lifecycle_returns,LifecycleReturnRun
from .operating_noi import produce_operating_noi
from .operating_cash import reconcile_operating_cash
from .holding_cash import OperatingPeriodEvidence
from .debt_service import DateWindow,produce_debt_service
from .debt_closing import DatedLoanEvidence,reconcile_debt_closing
from .closing_cash import produce_closing_cash
from .project_cash import CheckedClosingEvidence,reconcile_project_cash
from .refinance_capacity import RefinanceInputs,size_refinance
from .capacity_project_returns import assemble_capacity_checked_returns,CapacityProjectReturnRun,binding_from_record
from .preopening_cash import reconcile_preopening_cash

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T60.md'
MAX_BYTES=16_777_216


def versions():return {'T58':opening_debt.ENGINE_SHA256,'T59':lifecycle_returns.ENGINE_SHA256,'T60':ENGINE_SHA256,'definition_T60':hashlib.sha256(DEFINITION.read_bytes()).hexdigest()}
def _shape(value,keys):
    if type(value)is not dict or set(value)!=set(keys):raise ValidationError('exact lifecycle bundle record required')
    return value
def _list(value,limit):
    if type(value)is not list or len(value)>limit:raise ValidationError('bounded lifecycle inventory required')
    return value
def _bytes(value):
    if type(value)is not str:raise ValidationError('exact UTF-8 source text required')
    try:result=value.encode()
    except UnicodeError as error:raise ValidationError('source text must encode as UTF-8')from error
    if not result or len(result)>1_048_576:raise ValidationError('bounded nonempty source text required')
    return result
def _loan_record(e):return {'source':e.loan_raw.decode(),'windows':[asdict(w)for w in e.windows]}
def _loan(record):
    _shape(record,['source','windows']);source=_bytes(record['source']);windows=tuple(DateWindow(**_shape(w,['window_id','start_date','end_date','boundary']))for w in _list(record['windows'],128))
    return DatedLoanEvidence(loan_raw=source,windows=windows,run=produce_debt_service(source,windows))


def export_lifecycle_bundle(opening_args,opening_run,capacity_args,capacity_run,investor_raw,binding_raw,run):
    if type(run)is not LifecycleReturnRun or assemble_lifecycle_returns(opening_args,opening_run,capacity_args,capacity_run,investor_raw,binding_raw)!=run:raise ValidationError('complete lifecycle proof must reproduce before export')
    pre,_,periods,closings,manifest,_,cash_binding,debt_spec=opening_args
    inputs,capacity_spec=capacity_args[4:6]
    body={'schema':'miniuw.synthetic-lifecycle-bundle.v1','versions':versions(),
        'preopening_source':pre.decode(),'cash_boundary_binding':cash_binding.decode(),'opening_debt_spec':debt_spec.decode(),
        'periods':[{'noi_source':e.noi_raw.decode(),'cash_spec':e.spec_raw.decode()}for e in periods],
        'closings':[{'closing_id':e.closing_id,'closing_source':e.closing_raw.decode(),'loans':[_loan_record(l)for l in e.loans],'debt_spec':e.debt_spec_raw.decode()}for e in closings],
        'project_manifest':manifest.decode(),
        'capacity':{'valuation_noi_source':inputs.valuation_noi_raw.decode(),'bank_noi_source':inputs.bank_noi_raw.decode(),'new_loan':_loan_record(inputs.new_loan),'closing_source':inputs.closing_raw.decode(),'spec':capacity_spec.decode()},
        'window_investor_source':capacity_args[7].decode(),'window_binding':asdict(capacity_args[8]),
        'lifecycle_investor_source':investor_raw.decode(),'lifecycle_binding':binding_raw.decode(),
        'opening_run':asdict(opening_run),'capacity_run':asdict(capacity_run),'lifecycle_run':asdict(run)}
    raw=canonical(body).encode()
    if len(raw)>MAX_BYTES:raise ValidationError('lifecycle bundle transport budget exceeded')
    return raw


@dataclass(frozen=True)
class RecoveredLifecycle:
    opening_args:tuple
    opening_run:OpeningDebtRun
    capacity_args:tuple
    capacity_run:CapacityProjectReturnRun
    investor_raw:bytes
    binding_raw:bytes
    run:LifecycleReturnRun
    bundle_sha256:str


def recover_lifecycle_bundle(raw):
    if type(raw)is not bytes or not raw or len(raw)>MAX_BYTES:raise ValidationError('bounded immutable lifecycle bundle required')
    try:b=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid lifecycle bundle JSON')from error
    _shape(b,['schema','versions','preopening_source','cash_boundary_binding','opening_debt_spec','periods','closings','project_manifest','capacity','window_investor_source','window_binding','lifecycle_investor_source','lifecycle_binding','opening_run','capacity_run','lifecycle_run'])
    if b['schema']!='miniuw.synthetic-lifecycle-bundle.v1'or b['versions']!=versions():raise ValidationError('unsupported lifecycle bundle schema or component version')
    periods=[];closings=[]
    for row in _list(b['periods'],65):
        _shape(row,['noi_source','cash_spec']);nr=_bytes(row['noi_source']);sr=_bytes(row['cash_spec']);noi=produce_operating_noi(nr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=reconcile_operating_cash(nr,noi,sr)))
    for row in _list(b['closings'],64):
        _shape(row,['closing_id','closing_source','loans','debt_spec']);cr=_bytes(row['closing_source']);dr=_bytes(row['debt_spec']);loans=tuple(_loan(l)for l in _list(row['loans'],64));closing=produce_closing_cash(cr)
        closings.append(CheckedClosingEvidence(closing_id=row['closing_id'],closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr)))
    periods,closings=tuple(periods),tuple(closings);manifest=_bytes(b['project_manifest']);project=reconcile_project_cash(periods,closings,manifest)
    pre=_bytes(b['preopening_source']);opening_args=(pre,reconcile_preopening_cash(pre),periods,closings,manifest,project,_bytes(b['cash_boundary_binding']),_bytes(b['opening_debt_spec']))
    opening=reconcile_opening_debt(*opening_args)
    c=_shape(b['capacity'],['valuation_noi_source','bank_noi_source','new_loan','closing_source','spec']);vr=_bytes(c['valuation_noi_source']);br=_bytes(c['bank_noi_source']);cr=_bytes(c['closing_source']);spec=_bytes(c['spec'])
    inputs=RefinanceInputs(valuation_noi_raw=vr,valuation_noi_run=produce_operating_noi(vr),bank_noi_raw=br,bank_noi_run=produce_operating_noi(br),new_loan=_loan(c['new_loan']),closing_raw=cr,closing_run=produce_closing_cash(cr))
    capacity=size_refinance(inputs,spec);capacity_args=(periods,closings,manifest,project,inputs,spec,capacity,_bytes(b['window_investor_source']),binding_from_record(b['window_binding']))
    window=assemble_capacity_checked_returns(*capacity_args);ir=_bytes(b['lifecycle_investor_source']);binding=_bytes(b['lifecycle_binding']);run=assemble_lifecycle_returns(opening_args,opening,capacity_args,window,ir,binding)
    for key,actual in [('opening_run',opening),('capacity_run',window),('lifecycle_run',run)]:
        _shape(b[key],['payload_json','sha256'])
        if b[key]!=asdict(actual):raise ValidationError(key+' does not reproduce from exact source bytes')
    return RecoveredLifecycle(opening_args,opening,capacity_args,window,ir,binding,run,hashlib.sha256(raw).hexdigest())
