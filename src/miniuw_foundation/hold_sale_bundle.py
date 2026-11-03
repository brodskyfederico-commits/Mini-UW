"""T66 strict portable exact-source replay for the no-refinance cash profile."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical
from .intake import _unique_object,_invalid_constant
from . import hold_sale_cash,hold_sale_opening,hold_sale_returns,lifecycle_bundle
from .lifecycle_bundle import _shape,_list,_bytes,_loan_record,_loan,MAX_BYTES
from .hold_sale_returns import HoldSaleReturnRun,assemble_hold_sale_returns
from .hold_sale_opening import HoldSaleOpeningRun,reconcile_hold_sale_opening
from .hold_sale_cash import reconcile_hold_sale_cash
from .holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from .operating_noi import produce_operating_noi
from .operating_cash import reconcile_operating_cash
from .closing_cash import produce_closing_cash
from .debt_closing import reconcile_debt_closing
from .project_cash import CheckedClosingEvidence
from .preopening_cash import reconcile_preopening_cash

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T66-T67.md'
def versions():return dict(T63=hold_sale_cash.ENGINE_SHA256,T64=hold_sale_opening.ENGINE_SHA256,T65=hold_sale_returns.ENGINE_SHA256,T66=ENGINE_SHA256,transport_utilities=lifecycle_bundle.ENGINE_SHA256,definition=hashlib.sha256(DEFINITION.read_bytes()).hexdigest())


def export_hold_sale_bundle(opening_args,opening_run,investor_raw,binding_raw,run):
    if type(run)is not HoldSaleReturnRun or assemble_hold_sale_returns(opening_args,opening_run,investor_raw,binding_raw)!=run:raise ValidationError('complete no-refinance return must reproduce before export')
    pre,_,periods,sale,holding,_,hold_spec,_,cash_binding,opening_spec=opening_args
    body=dict(schema='miniuw.synthetic-hold-sale-bundle.v1',versions=versions(),preopening_source=pre.decode(),
        periods=[dict(noi_source=e.noi_raw.decode(),cash_spec=e.spec_raw.decode())for e in periods],
        sale=dict(closing_id=sale.closing_id,closing_source=sale.closing_raw.decode(),loans=[_loan_record(e)for e in sale.loans],debt_spec=sale.debt_spec_raw.decode()),
        holding_manifest=holding.decode(),hold_sale_spec=hold_spec.decode(),cash_boundary_binding=cash_binding.decode(),opening_spec=opening_spec.decode(),
        investor_source=investor_raw.decode(),investor_binding=binding_raw.decode(),expected_run=asdict(run))
    data=canonical(body).encode()
    if len(data)>MAX_BYTES:raise ValidationError('hold/sale bundle transport budget exceeded')
    return data


@dataclass(frozen=True)
class RecoveredHoldSale:
    opening_args:tuple
    opening_run:HoldSaleOpeningRun
    investor_raw:bytes
    binding_raw:bytes
    run:HoldSaleReturnRun
    bundle_sha256:str


def recover_hold_sale_bundle(raw):
    if type(raw)is not bytes or not raw or len(raw)>MAX_BYTES:raise ValidationError('bounded immutable hold/sale bundle required')
    try:b=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid hold/sale bundle JSON')from error
    _shape(b,['schema','versions','preopening_source','periods','sale','holding_manifest','hold_sale_spec','cash_boundary_binding','opening_spec','investor_source','investor_binding','expected_run'])
    if b['schema']!='miniuw.synthetic-hold-sale-bundle.v1'or b['versions']!=versions():raise ValidationError('unsupported hold/sale bundle schema or version')
    periods=[]
    for row in _list(b['periods'],65):
        _shape(row,['noi_source','cash_spec']);nr=_bytes(row['noi_source']);sr=_bytes(row['cash_spec']);noi=produce_operating_noi(nr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=reconcile_operating_cash(nr,noi,sr)))
    periods=tuple(periods);s=_shape(b['sale'],['closing_id','closing_source','loans','debt_spec']);cr=_bytes(s['closing_source']);dr=_bytes(s['debt_spec']);closing=produce_closing_cash(cr);loans=tuple(_loan(e)for e in _list(s['loans'],64))
    sale=CheckedClosingEvidence(closing_id=s['closing_id'],closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr))
    hr=_bytes(b['holding_manifest']);holding=reconcile_holding_cash(periods,hr);hs=_bytes(b['hold_sale_spec']);hold=reconcile_hold_sale_cash(periods,sale,hr,holding,hs);pre=_bytes(b['preopening_source'])
    args=(pre,reconcile_preopening_cash(pre),periods,sale,hr,holding,hs,hold,_bytes(b['cash_boundary_binding']),_bytes(b['opening_spec']));opening=reconcile_hold_sale_opening(*args)
    ir=_bytes(b['investor_source']);binding=_bytes(b['investor_binding']);run=assemble_hold_sale_returns(args,opening,ir,binding)
    _shape(b['expected_run'],['payload_json','sha256'])
    if b['expected_run']!=asdict(run):raise ValidationError('stored hold/sale result does not reproduce from exact sources')
    return RecoveredHoldSale(args,opening,ir,binding,run,hashlib.sha256(raw).hexdigest())
