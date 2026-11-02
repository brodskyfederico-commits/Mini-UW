"""T18 bounded one-page internal preview; no approval, publication or financial calculation."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,textwrap
from .drafts import ValidationError,canonical,digest
from .scenario_threshold_rehearsal import ScenarioThresholdRun,simulate_scenario_thresholds

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LABELS={'YoC':'YoC','spread':'Spread','equity_recovered':'Equity recuperado','equity_cash_in':'Equity cash-in',
 'breakeven_occupancy':'Ocupacion equilibrio','post_refi_CoC':'CoC pos-refi','asking_relative_to_supported_price':'Asking / precio soportado',
 'equity_TDC':'Equity / TDC','IRR':'IRR apalancada','equity_multiple':'Equity Multiple'}
STATES={'PASS_CONDITION':'PASS','FAIL_CONDITION':'FAIL','BAND':'BANDA','PENDING':'PENDIENTE',
 'PASS_MISS_PENDING':'NO CUMPLE PASS','CONFLICT':'CONFLICTO'}


class PreviewLayoutError(ValidationError):pass


@dataclass(frozen=True)
class SyntheticPreview:
    pdf_bytes:bytes
    manifest_json:str
    manifest_sha256:str
    @property
    def manifest(self):return json.loads(self.manifest_json)


def _amount(q,metric):
    if q is None:return 'FALTA'
    value=Fraction(int(q['numerator']),int(q['denominator']))
    scale,suffix=(10000,' bps')if metric=='spread'else((1,'x')if metric=='equity_multiple'else(100,'%'))
    value*=scale;den=value.denominator
    while den%2==0:den//=2
    while den%5==0:den//=5
    if den==1:
        # Decimal expansion is exact; no presentation rounding changes a comparison.
        numerator,denominator=value.numerator,value.denominator
        whole,remainder=divmod(abs(numerator),denominator);digits=''
        while remainder:
            remainder*=10;digit,remainder=divmod(remainder,denominator);digits+=str(digit)
            if len(digits)>24:raise PreviewLayoutError('exact decimal exceeds preview budget')
        result=('-'if numerator<0 else'')+str(whole)+('.'+digits if digits else'')
    else:result=str(value.numerator)+'/'+str(value.denominator)
    return result+suffix



def _blocker_text(blocker):
    if blocker=='intermediate_band_pending_professional_review':return 'Banda intermedia: pendiente de revision profesional.'
    parts=blocker.split(':')
    if len(parts)!=3 or parts[0]not in LABELS:raise PreviewLayoutError('unknown blocker cannot be summarized safely')
    metric,scenario,reason=parts
    reasons={'metric_record_missing':'falta la fila de la metrica', 'metric_value_missing':'falta el valor de la metrica',
        'pass_condition_and_applicability_unresolved':'falta regla o evidencia de aplicabilidad',
        'downside_pass_not_met_pending_review':'no alcanza PASS; pendiente de revision'}
    if reason not in reasons:raise PreviewLayoutError('unknown blocker cannot be summarized safely')
    return LABELS[metric]+' en '+scenario+': '+reasons[reason]+'.'


def _pdf_string(text):
    if type(text)is not str or any(ord(c)<32 or ord(c)==127 for c in text):raise PreviewLayoutError('control characters cannot be rendered')
    try:encoded=text.encode('cp1252')
    except UnicodeEncodeError as error:raise PreviewLayoutError('preview font cannot represent source identity; no silent replacement')from error
    return encoded.replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')


def _pdf(commands):
    stream=b'\n'.join(commands)+b'\n'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream']
    output=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(output));output.extend(str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(output);output.extend(b'xref\n0 7\n0000000000 65535 f \n')
    for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n')
    return bytes(output)


def render_synthetic_onepager(document_raw,case_raw,run):
    if type(run)is not ScenarioThresholdRun or simulate_scenario_thresholds(document_raw,case_raw)!=run:
        raise ValidationError('preview requires exact replay-verified scenario evidence')
    p=run.payload;commands=[];lines=[]
    def text(x,y,value,size=8,width=732,bold=False):
        encoded=_pdf_string(value)
        if len(value)*size*0.6>width or y<25 or y+size>587:raise PreviewLayoutError('preview content cannot fit legibly on one page')
        font='F2'if bold else'F1'
        commands.append(f'BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+encoded+b') Tj ET')
        lines.append(value)
    commands.append(b'0.08 0.20 0.29 rg')
    text(30,570,'MINI-UW | VISTA SINTETICA INTERNA',16,bold=True)
    text(30,550,'ESTADO OPERATIVO: PENDIENTE | Sin aprobacion ni decision real',11,bold=True)
    text(30,531,'Simulacion: '+('PENDIENTE'if p['simulation_result']=='PENDING'else p['simulation_result'])+' | Alcance: '+('Solo Base'if p['required_scenarios']==['Base']else'Base y Downside'),9)
    for i,(key,label)in enumerate([('deal_id','Deal'),('case_id','Caso'),('run_id','Ejecucion')]):
        text(30,513-i*12,label+': '+p['context'][key],7.5)
    text(30,467,'Valores ficticios. Umbrales documentales NO adoptados. Sin validacion financiera.',8,bold=True)
    text(30,452,'B = Base; D = Downside. No se calculan NOI, TDC, IRR ni retornos desde datos de proyecto.',7)
    xs=[30,210,284,358,432,506,580];widths=[175,69,69,69,69,69,182]
    headers=['Metrica','Valor B','Valor D','PASS B','PASS D','FAIL B','Comparacion B / D']
    commands.append(b'0.87 0.92 0.94 rg 27 423 738 19 re f 0.08 0.20 0.29 rg')
    for x,w,label in zip(xs,widths,headers):text(x,430,label,7,width=w,bold=True)
    rows={(r['metric_id'],r['scenario_id']):r for r in p['comparisons']};display=[]
    for index,metric in enumerate(p['source_profile']['metrics']):
        mid=metric['metric_id'];base=rows[(mid,'Base')];down=rows.get((mid,'Downside'))
        bvalue=(base.get('metric_record')or{}).get('value');dvalue=(down.get('metric_record')or{}).get('value')if down else None
        values=[LABELS[mid],_amount(bvalue,mid),_amount(dvalue,mid)if down else'NO ENSAYADO',
            _amount(metric['pass_base'],mid),_amount(metric['pass_downside'],mid)if metric['pass_downside']is not None else'SIN REGLA',_amount(metric['fail_base'],mid)]
        y=408-index*25
        for x,w,value in zip(xs[:6],widths[:6],values):text(x,y,value,7,width=w)
        bstate=STATES[base['state']];dstate=STATES[down['state']]if down else'NO ENSAYADO'
        text(xs[6],y,'B: '+bstate,7,width=widths[6]);text(xs[6],y-10,'D: '+dstate,7,width=widths[6])
        commands.append(f'0.77 0.82 0.85 RG 27 {y-14} m 765 {y-14} l S'.encode())
        display.append({'metric_id':mid,'base_value':values[1],'downside_value':values[2],'base_state':bstate,'downside_state':dstate})
    blockers=p['simulation_blockers'];text(30,133,'BLOQUEOS REQUERIDOS: '+str(len(blockers)),8,bold=True)
    wrapped=[]
    blocker_texts=[_blocker_text(blocker)for blocker in blockers]
    for blocker in blocker_texts:wrapped.extend(textwrap.wrap(blocker,width=150,break_long_words=False,break_on_hyphens=False))
    if len(wrapped)>3:raise PreviewLayoutError('blockers exceed bounded internal preview; no omission or clipping allowed')
    if not wrapped:wrapped=['Sin bloqueos en el alcance sintetico ensayado; esto no equivale a Mini-UW completo.']
    for i,line in enumerate(wrapped):text(30,119-i*10,line,6.5)
    text(30,81,'Run SHA256: '+run.sha256,6.5)
    text(30,70,'Caso SHA256: '+p['case_source_sha256'],6.5)
    text(30,59,'Fuente SHA256: '+p['source_sha256'],6.5)
    text(30,40,'PRUEBA INTERNA. No publicar como dictamen. Requiere evidencia y revision autenticas para uso real.',7,bold=True)
    pdf=_pdf(commands)
    manifest={'component':'T18','purpose':'internal_synthetic_preview_only','engine_sha256':ENGINE_SHA256,
        'document_sha256':hashlib.sha256(document_raw).hexdigest(),'case_sha256':hashlib.sha256(case_raw).hexdigest(),
        'scenario_run_sha256':run.sha256,'pdf_sha256':hashlib.sha256(pdf).hexdigest(),'page_count_by_construction':1,
        'displayed_metrics':display,'blockers_displayed':blockers,'blocker_display_texts':blocker_texts,'display_lines':lines,'decision':'PENDING',
        'financial_values_verified':False,'professional_review_authenticated':False,'production_authorized':False,'publication_authorized':False}
    encoded=canonical(manifest);return SyntheticPreview(pdf,encoded,digest(encoded))
