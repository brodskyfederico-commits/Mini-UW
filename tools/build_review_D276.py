from pathlib import Path
import json, hashlib, math, re
from fractions import Fraction
from decimal import Decimal, localcontext, ROUND_HALF_UP
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from argparse import ArgumentParser
arg=ArgumentParser();arg.add_argument('validation_directory',type=Path);arg.add_argument('--outcome',required=True,type=Path);args=arg.parse_args()
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT;WORK=args.validation_directory;WORK.mkdir(parents=True,exist_ok=True)
OUT=WORK/'report-body.pdf';TOTAL=8;FOOTER_OFFSET=1
for name,file in [('D','DejaVuSans.ttf'),('DB','DejaVuSans-Bold.ttf')]:
 pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+file))
pdfmetrics.registerFontFamily('D',normal='D',bold='DB',italic='D',boldItalic='DB')
NAVY=colors.HexColor('#153348'); TEAL=colors.HexColor('#176A69'); AMBER=colors.HexColor('#925909'); BLUE=colors.HexColor('#396487'); MUTED=colors.HexColor('#526B7A'); PALE=colors.HexColor('#EEF4F6'); LINE=colors.HexColor('#D6E1E7')
GREEN_BG=colors.HexColor('#EAF5F0'); AMBER_BG=colors.HexColor('#FFF4DF'); BLUE_BG=colors.HexColor('#EDF3FB')
styles={}
for n,sz,lead,font,col in [('body',10.1,13.5,'D',NAVY),('small',8.7,11.5,'D',NAVY),('cell',8.6,11.2,'D',NAVY),('head',9,12,'DB',colors.white),('note',8.1,10.8,'D',MUTED),('box',8.3,11,'D',NAVY)]:
 styles[n]=ParagraphStyle(n,fontName=font,fontSize=sz,leading=lead,textColor=col,spaceAfter=0)
styles['box'].alignment=1
c=canvas.Canvas(str(OUT),pagesize=letter,pageCompression=1,invariant=1)
c.setTitle('Mini-UW — actualización profesional D276 y resultado de una página')
c.setAuthor('Mini-UW — documentación del modelo D276')
c.setSubject('Procedimientos A–Z, Dots, bots, decisiones, fórmulas principales y pendientes; ejemplo sintético, sin aprobación real')
layouts=[]; PAGE=0

def p(txt,x,y,w,style='body'):
 q=Paragraph(txt,styles[style]); ww,hh=q.wrap(w,2000)
 if y-hh<38: raise ValueError(('overflow',PAGE,txt[:85],y,hh))
 q.drawOn(c,x,y-hh); layouts.append({'page':PAGE,'kind':'text','bbox':[x,y-hh,x+w,y]})
 return y-hh-7

def page(title,kicker='',wide=False):
 global PAGE,W,H,L,R,CW
 if PAGE:c.showPage()
 PAGE+=1; W,H=landscape(letter) if wide else letter; c.setPageSize((W,H)); L=35;R=35;CW=W-L-R
 c.setFillColor(NAVY);c.rect(0,H-79,W,79,fill=1,stroke=0)
 c.setFillColor(colors.white);c.setFont('DB',17);c.drawString(L,H-36,title)
 c.setFont('D',8.2);c.drawString(L,H-56,kicker)
 c.setStrokeColor(LINE);c.line(L,31,W-R,31)
 c.setFillColor(MUTED);c.setFont('D',7.2)
 c.drawString(L,19,'Mini-UW · D276 · revisión 21 nov 2026 (Nueva York) · revisión profesional')
 c.drawRightString(W-R,19,f'{PAGE+FOOTER_OFFSET} / {TOTAL}')
 c.bookmarkPage('p'+str(PAGE));c.addOutlineEntry(title,'p'+str(PAGE),level=0)
 return H-94

def section(txt,y):
 c.setFillColor(TEAL);c.setFont('DB',10.8);c.drawString(L,y-10,txt);return y-23

def table(headers,rows,widths,y,sz='cell',x=None,pad=4):
 x=L if x is None else x
 data=[[Paragraph(str(a),styles['head']) for a in headers]]+[[Paragraph(str(a),styles[sz]) for a in row] for row in rows]
 t=Table(data,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([
 ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),pad),('RIGHTPADDING',(0,0),(-1,-1),pad),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,0),(-1,0),.5,NAVY),('LINEBELOW',(0,1),(-1,-1),.2,LINE)]))
 tw,th=t.wrap(sum(widths),2000)
 if y-th<40:raise ValueError(('table overflow',PAGE,y,th))
 t.drawOn(c,x,y-th);layouts.append({'page':PAGE,'kind':'table','bbox':[x,y-th,x+tw,y]})
 return y-th-10

def callout(txt,y,bg=AMBER_BG):
 q=Paragraph(txt,styles['body']);_,h=q.wrap(CW-20,2000)
 if y-h-20<39:raise ValueError(('callout overflow',PAGE,y,h))
 c.setFillColor(bg);c.roundRect(L,y-h-16,CW,h+16,5,fill=1,stroke=0);q.drawOn(c,L+10,y-h-8)
 return y-h-25

# 2: vector flow, human approvals are a distinct lane.
y=page('Flujo de decisiones · del ingreso a la entrega','Verde = ensayos dirigidos sintéticos · Ámbar = condición / PENDING · Azul = intervención humana pendiente',True)
c.saveState();c.scale(.93,.93)
def box(txt,x,y,w,h,fill=GREEN_BG,stroke=TEAL,dashed=False):
 c.setFillColor(fill);c.setStrokeColor(stroke);c.setLineWidth(.8);c.setDash(3,2) if dashed else c.setDash()
 c.roundRect(x,y,w,h,5,fill=1,stroke=1);c.setDash()
 q=Paragraph(txt,styles['box']);_,ph=q.wrap(w-12,h)
 if ph>h-8:raise ValueError(('box overflow',txt,ph,h))
 q.drawOn(c,x+6,y+(h-ph)/2)
 layouts.append({'page':PAGE,'kind':'box','bbox':[x,y,x+w,y+h]})
def diamond(txt,cx,cy,w=105,h=65):
 c.setFillColor(AMBER_BG);c.setStrokeColor(AMBER);path=c.beginPath();path.moveTo(cx-w/2,cy);path.lineTo(cx,cy+h/2);path.lineTo(cx+w/2,cy);path.lineTo(cx,cy-h/2);path.close();c.drawPath(path,fill=1,stroke=1)
 q=Paragraph(txt,styles['box']);_,ph=q.wrap(w*.72,200);q.drawOn(c,cx-w*.36,cy-ph/2)
def arrow(points,label=None,lx=0,ly=0,color=MUTED):
 c.setStrokeColor(color);c.setLineWidth(.9);c.setDash();path=c.beginPath();path.moveTo(*points[0])
 for pt in points[1:]:path.lineTo(*pt)
 c.drawPath(path)
 (a,b),(u,v)=points[-2:];ang=math.atan2(v-b,u-a);n=5
 c.line(u,v,u-n*math.cos(ang-.45),v-n*math.sin(ang-.45));c.line(u,v,u-n*math.cos(ang+.45),v-n*math.sin(ang+.45))
 if label:c.setFillColor(color);c.setFont('DB',7.4);c.drawString(lx,ly,label)
box('<b>1. Recibir</b><br/>ID · estrategia · revisión<br/>B01–B03',35,416,133,61)
box('<b>2. Leer y conciliar</b><br/>Planilla B04 · planos B05–B07<br/>GC / banco B08 → B09<br/>Oficiales B10–B11',192,408,172,77)
diamond('¿Mínimos y fuentes válidos?',435,447,110,76)
box('<b>3. Calcular B13</b><br/>M1–M7 · Base / Downside<br/>Caja por USD 10',511,416,143,61)
box('<b>Separar rutas</b><br/>Con refi / sin refi<br/>Cada deuda y vencimiento',682,416,125,61)
arrow([(168,447),(192,447)]);arrow([(364,447),(380,447)]);arrow([(490,447),(511,447)],'Sí',493,455);arrow([(654,447),(682,447)])
box('<b>PENDING afectado</b><br/>Falta dato / fuente o conflicto.<br/>Falso verde: bloquea PDF.<br/>Corregir → nueva revisión.',373,301,129,70,AMBER_BG,AMBER)
arrow([(435,409),(435,371)],'No',443,390)
diamond('¿Refi dentro de capacidad?',745,336,118,75)
arrow([(745,416),(745,373)])
box('<b>Refi PENDING</b><br/>No ajustar préstamo solo.<br/>Sin refi: sigue si es válida.',538,304,128,64,AMBER_BG,AMBER)
arrow([(686,336),(666,336)],'No',669,344)
box('<b>Flujos disponibles</b><br/>y rutas bloqueadas<br/>identificados',682,215,125,56)
arrow([(745,299),(745,271)],'Sí',754,283)
arrow([(602,304),(602,287),(695,287),(695,271)])
diamond('¿Criterios vigentes y comparables?',435,243,123,80)
arrow([(682,243),(497,243)])
box('<b>4. B14 · cotejar</b><br/>Cumple / no cumple / banda<br/>Faltante o regla sin confirmar:<br/>PENDING',198,209,174,69)
arrow([(373,243),(372,243)],'Sí',375,253)
box('<b>5. B15 · borrador</b><br/>Resultados reproducidos<br/>B16 audita cifras y fuentes',35,209,139,69)
arrow([(198,243),(174,243)])
box('<b>Sin criterio vigente</b><br/>Dictamen PENDING.<br/>PRELIMINAR sólo con mínimos.',375,119,135,64,AMBER_BG,AMBER)
arrow([(435,203),(435,183)],'No',445,189)
arrow([(375,151),(185,151),(185,224),(174,224)])
diamond('¿Auditoría y revisión actual válidas?',105,137,132,76)
arrow([(105,209),(105,175)])
box('<b>Bloquear entrega</b><br/>Corregir → nueva revisión',35,45,139,41,AMBER_BG,AMBER)
arrow([(105,99),(105,86)],'No',114,90)
arrow([(35,65),(22,65),(22,447),(35,447)],'Reingresar',25,492)
box('<b>6. Entregar revisión vigente</b><br/>PDF de una página + expediente<br/>No equivale a aprobar inversión.',220,54,165,62)
arrow([(171,137),(202,137),(202,85),(220,85)],'Sí',182,145)
box('<b>CARRIL HUMANO · separado</b><br/>Custodio → revisor financiero → aprobador acreditado.<br/>Resolver PENDING y documentar aceptación / excepción.<br/>Real / inversión / Full UW: sin automatismo ni autorización vigente.',535,54,272,83,BLUE_BG,BLUE,True)
arrow([(385,85),(535,85)],'Revisión',443,93,color=BLUE)
box('<b>B17 · por versión, fuera del flujo por deal</b><br/>Regresión sintética, referencias y aceptación reproducible.',539,160,268,43,PALE,MUTED)
p('El carril PRELIMINAR no otorga PASS formal. Sin mínimo, evidencia fiscal requerida o capacidad: PENDING y fuera del ranking. Una corrección invalida dependencias y exige volver a auditar; se conserva el historial.',35,395,315,'note')

c.restoreState()
# 3 and 4: complete A-Z procedure index.
A=[
('A','Definir expediente','ID, estrategia rentar–estabilizar–vender, fecha de corte, Base / Downside y revisión.','B01 · contexto único; no combinar revisiones incompatibles.'),
('B','Preservar originales','Inventario, nombres, tamaño, hash SHA-256, fecha y procedencia.','B02 · original intacto; una modificación exige nueva versión.'),
('C','Clasificar y localizar','Formato, páginas y hojas; texto, OCR, rotación y recortes en perfiles soportados.','B03 · faltantes, duplicados o lectura ambigua: PENDING.'),
('D','Importar planilla','Mapear los 55 campos por celda, escenario y plantilla; incorporar datos suplementarios.','B04 · vínculo celda → fuente → cálculo, sin completar vacíos.'),
('E','Validar cada entrada','Tipo, unidad, moneda, base, período, aplicabilidad, fuente y revisión.','B04 · vacío ≠ 0; cero explícito válido se conserva; N/A justificado.'),
('F','Separar criterios','Versionar umbrales y operadores; comprobar igualdad, vigencia, escenarios y métricas.','B14 + responsable · criterios del ensayo no se adoptan como reales.'),
('G','Leer plano A','Extraer superficies, unidades y usos con página / región y cita.','B05 · lectura documentada; no asumir cantidades ausentes.'),
('H','Contrastar plano','Segunda lectura / texto frente a OCR en el perfil declarado.','B06 · conservar ambas lecturas y su evidencia.'),
('I','Conciliar programa','Confrontar áreas, unidades y fuentes según regla y tolerancia declaradas.','B07 · discrepancia no resuelta bloquea magnitudes dependientes.'),
('J','Leer respaldos financieros','GC, banco de obra / permanente, rentas, cap comparable, seguro y sus exclusiones.','B08 · paralelo a planos; siempre antes de B09.'),
('K','Cruzar plano y presupuesto','Conciliar B07 con alcance, base de precio y cantidades del GC / B08.','B09 · no sustituye take-off o revisión técnica profesional.'),
('L','Verificar copia oficial','Jurisdicción, autorización, fecha, aplicabilidad y vigencia fiscal / AMI / beneficios.','B10 · no es investigación web autónoma desplegada.'),
('M','Citar evidencia exacta','Localizar dato, página, unidad y fecha de la copia oficial.','B11 · afirmación sin copia / cita vigente: PENDING.')]
B=[
('N','Abrir puertas de cálculo','Consolidar dependencias y auditoría crítica; identificar faltantes por dato y módulo.','B12 · falso verde bloquea cálculo afectado y exportación.'),
('O','Armar operación','Programa M1; renta, pérdidas, gastos, reservas e impuestos M2. Separar bases de NOI.','B13 · fuente de áreas → renta / gastos / NOI / valoración.'),
('P','Cerrar presupuesto','Terreno y C33, vertical, parking, site, contingencia, soft y TI/LC; usos sin duplicación.','M3 · TDC y fuentes / usos; precio solicitado separado del evaluado.'),
('Q','Construir calendario','Compra, obra, TCO, lease-up, estabilización, refi y salida; horizonte explícito.','M4 · v37 integra calendario mensual; conserva perfiles trimestrales.'),
('R','Desembolsar deuda de obra','LTC, costo elegible, compromiso disponible, fechas, fees, intereses y vencimiento.','M5 · draw no supera autorización; faltante lo cubre aporte sólo si está definido.'),
('S','Operar y estabilizar','Reconocer renta / gastos, NOI, servicio, reservas y caja libre / restringida por período.','M2 / M7 · no distribuir reservas o depósitos sin autorización.'),
('T','Evaluar refi y alternativa','Capacidad menor entre LTV, DSCR y debt yield si aplica; payoff, fees y nueva deuda.','M6 · refi fuera de capacidad PENDING; sin refi tiene validación propia.'),
('U','Cerrar venta del activo','NOI forward / cap compatible o precio respaldado; costos, deuda y liberaciones.','M7 · venta neta conciliada; sin doble conteo de reservas / caja.'),
('V','Explicar retorno','Aporte inicial y extra, cobros operativos / refi / venta, fechas, EM, TIR, pico y recupero.','M7 · normalizar por equity inicial; retorno personal necesita reparto real.'),
('W','Comparar escenarios','Base / Downside, cambios aislados y conjuntos, sensibilidades y RLV.','M8 · RLV conserva todos los criterios aplicables; Rangos y pruebas matemáticas declarados; fuente real pendiente.'),
('X','Emitir clasificación','Comparar métricas compatibles; PRELIMINAR, banda y faltantes según contrato vigente.','M9 / B14 · PASS simulado ≠ dictamen real o aprobación de inversión.'),
('Y','Auditar y exportar','B15 arma borrador; B16 reproduce fuentes, flujos y huellas y verifica revisión vigente.','Sólo PDF integral vigente; inconsistencias bloquean entrega.'),
('Z','Revisar y archivar','Revisor y aprobador acreditados; registrar decisión, motivos, vigencia y excepciones.','Carril humano; correcciones reinician dependencias. B17 valida por versión.')]
for title,rows in [('Procedimientos A–M · ingreso y evidencia',A),('Procedimientos N–Z · cálculo y entrega',B)]:
 y=page(title,'Secuencia completa del Mini-UW · Las lecturas paralelas convergen antes de liberar cálculos')
 y=table(['Paso','Procedimiento','Acción y resultado','Control / responsable'],rows,[25,94,198,CW-317],y,pad=4.3)
 y=callout('<b>Regla transversal:</b> un dato faltante bloquea sus dependencias; no se reemplaza por cero ni por el valor de Base. Fuente, regla de inversión y aprobación humana son controles distintos. El archivo original se conserva y toda corrección deja trazabilidad.',y,PALE)

# 5: roles, components and accurate automation boundaries.
y=page('Dots y bots · responsabilidades y bloqueos','7 Dots · 17 componentes locales · No representan 17 agentes autónomos desplegados')
bots=[
('D01','B01','Orquestar expediente, estrategia, escenarios y revisión.','Contexto incompatible: no combinar.'),
('D01','B02','Inventariar y conservar archivos, hashes y versiones.','Fuente modificada: invalidar dependientes.'),
('D01','B03','Clasificar documento / hoja / página y modalidad de lectura.','Página faltante, duplicada o ilegible: PENDING.'),
('D02','B04','Importar / validar 55 campos, unidades, aplicabilidad y citas.','Vacío, conflicto o mapa incierto: bloquear dependencias.'),
('D03','B05','Extraer lectura A de plano con página, región y evidencia.','Sin respaldo geométrico: dato PENDING.'),
('D03','B06','Contrastar segunda lectura y texto / OCR.','Desacuerdo: conservar ambas lecturas.'),
('D03','B07','Conciliar áreas y unidades con regla explícita.','Sin regla / tolerancia: no escoger valor.'),
('D03','B08','Leer GC, préstamos, rentas / caps y seguros.','Dato sin cita / vigencia: PENDING. Antes de B09.'),
('D03','B09','Cruzar programa conciliado con cotización y alcance.','Incompatibilidad de base / cantidad: bloquear costo.'),
('D04','B10','Validar inventario y aplicabilidad de copias oficiales.','Sin copia local vigente: PENDING.'),
('D04','B11','Validar cada cita y dato fiscal / AMI / beneficio.','Sin evidencia exacta: no aplicar beneficio.'),
('D05','B12','Consolidar bloqueos, capacidad y auditoría crítica.','Falso verde: cálculo PENDING y PDF bloqueado.'),
('D05','B13','Calcular módulos M1–M9 y registros fechados de caja.','Sin dato mínimo: no fabricar flujo ni métrica.'),
('D05','B14','Comparar con criterios versionados compatibles.','Regla faltante / banda: PENDING, sin PASS formal.'),
('D06','B15','Renderizar resumen de resultados reproducidos.','No introducir números manuales en el PDF.'),
('D07','B16','Auditar fuente → cálculo → PDF y revisión actual.','Hash, revisión o cifra incoherente: no exportar.'),
('D07','B17','Ejecutar regresión / referencias / aceptación de versión.','Fuera de la cadena por deal; registrar código probado.')]
y=table(['Dot','Bot','Función / salida','Bloqueo'],bots,[36,35,237,CW-308],y,pad=4)
y=callout('<b>Alcance de validación:</b> lectores, reconciliadores y cadena local están probados en los perfiles documentados. Los ensayos OCR sintéticos y la experiencia documental del 1101 no certifican una tasa de error con documentos reales. B16 reproduce; no sustituye al revisor financiero independiente.',y,BLUE_BG)

# 6: input ranges and principal formulas, with source references for full inventory.
y=page('Entradas, conexiones y fórmulas principales','Resumen del motor M1–M9 · Detalle completo: D272 + anexo electrónico D276; no sustituye sus definiciones de base y período')
y=p('<b>55 campos de entrada:</b> C7–C15 renta / pérdidas; C16–C21 comercial; C25–C28 servicios; C32–C42 terreno / obra / presupuesto; C46–C47 calendario; C51–C53 deuda de obra; C57–C60 gastos / seguro / reserva; C61–C62 impuestos; C66–C74 valoración / venta / deuda permanente / refi; C75–C76 crecimiento; C80–C82 alternativas. Cada rango conserva sus celdas habilitadas; no implica que todas sus filas sean entradas.',L,y,CW,'small')
y=p('<b>Suplementos H01–H08:</b> horizonte de venta, vencimiento, aplicabilidad Live Local, unidades asequibles, AMI, desglose de pérdidas, costos fijos de venta y vacancia bancaria adicional. Fuentes, fechas, moneda, unidades y supuestos deben acompañar los valores.',L,y,CW,'small')
f=[
('M1 → M2 / M3','Unidades × renta/unidad, o área × renta/SF, con período explícito. Áreas compatibles alimentan renta, seguro y cantidades de obra.'),
('M2 · renta / NOI','EGI = renta reconocida tras pérdidas + otros ingresos. NOI operativo = EGI − gastos − impuesto; NOI_uw = NOI operativo − reservas de reposición. Impuesto por base y millage; tope no escolar y retasación sólo con evidencia aplicable.'),
('M3 · costo total','Terreno = P × (1 + C33). Vertical = cantidad compatible × costo unitario. Hard = directos + contingencia; soft según base declarada; TDC = usos mutuamente excluyentes, incluyendo financiación / reservas según alcance.'),
('M4 / M5 · obra','Fin = inicio + C46; estabilización = TCO + C47. Compromiso ≤ menor de LTC × costo elegible y máximo contractual. Saldo final = inicial + draws + capitalización autorizada − principal pagado. Interés mensual = suma de saldo por intervalo × tasa × fracción de días ACT/360 o 30E/360 declarada.'),
('M6 · permanente','Pago = P × i / [1 − (1+i)^(-n)]; si i = 0: P/n. IO, madurez y balloon separados. Valor refi = NOI de valoración / cap compatible.'),
('M6 · capacidad / caja','Capacidad = mín(LTV × valor; NOI banco / [DSCR × constante anual]; NOI banco / debt yield, si aplica). Refi neta = préstamo + caja / liberaciones autorizadas − payoff − fees − nuevos depósitos restringidos.'),
('M7 · venta / flujo','Venta = NOI forward compatible / cap de salida, o precio respaldado. Cobro neto = precio + liberaciones autorizadas − gastos / obligaciones − deuda pendiente. Flujo = cobros − aportes, conservando ambos brutos y sus fechas.'),
('M7 · USD 10 / retorno','k = 10 / equity inicial verificado. EM = cobros / todos los aportes; sin recuperar = máx(0, aportes − cobros). Pico = máx por fecha del acumulado aportes − cobros. TIR: raíz única admisible de Σ CF(t)z^t = 0; anual = z^(-m) − 1, m = 4 o 12 según calendario; sin certificación: PENDING.'),
('M8 / M9 · métricas','YoC = NOI_uw / TDC. Spread = 10.000 × (YoC comparable − cap). CoC = (NOI_uw − servicio anual) / equity remanente, con ventana / base declaradas. Equilibrio resuelve caja = 0; físico requiere desglose C14. RLV: deuda fija, ΔTDC = ΔP × (1 + C33), todos los criterios aplicables juntos.')]
y=table(['Módulo / enlace','Definición resumida'],f,[98,CW-98],y,pad=3.5)
y=callout('<b>Consistencia obligatoria:</b> DSCR / debt yield usan NOI bancario; valoración y salida usan la base de su cap. Si el cap comparable es antes de reservas, sólo el spread utiliza un YoC comparable antes de reservas, rotulado; el YoC oficial sigue con NOI_uw. Cap sin base: spread PENDING. RLV negativo se muestra con bandera; inalcanzable no es cero.',y,PALE)

y=page('Validación del corte y ajustes del especialista','Pruebas de componentes, integración, regresión y uso real son evidencias distintas')
validation=json.loads((WORK/'validation-summary.json').read_bytes())
y=p('<b>Integración mensual v37:</b> planilla original de 55 campos, lectura de plano y cotizaciones, M2 fiscal, comercial por local, seguro de obra, deuda / intereses, permanente y venta. Base y Downside conservan con y sin refi. Fuentes sintéticas; no valida un préstamo o proyecto real.',L,y,CW,'small')
y=p('<b>Cotejo independiente:</b> 1.828 comparaciones exactas desde celdas literales y respaldos: usos, impuestos mensuales, NOI, deuda, aportes y cobros brutos por fecha, venta y TIR. Equivalencia trimestral exacta de las cuatro rutas, sin cambiar el perfil conservado. Pruebas dirigidas: '+str(validation['directed_tests'])+' aprobadas.',L,y,CW,'small')
y=p('<b>Regresión general D275:</b> '+escape(validation['D275_regression_note'])+'<br/><b>Corte D276:</b> '+escape(validation['D276_regression_note'])+' Un resultado anterior no certifica el código nuevo.',L,y,CW,'small')
y=table(['Tema','Corrección / evidencia','Límite vigente'],[
('Caso dorado','v1 intacto; v2 separado con oráculo fijo. Obra/hard directo 62,5%; LTV aprox. 61–62%; DSCR aprox. 1,252.','El porcentaje sobre TDC se muestra aparte; deuda sintética, no oferta bancaria.'),
('T6 · calendario','Devengo ACT/360 y 30E/360, pagos / draws fechados, caja, M2 y TIR mensual integrados.','Fuera de los perfiles y fechas soportados: PENDING; no redondear fechas.'),
('T7 · comercial','Por local: inicio, free rent, escalones, gastos / NNN, recuperos y TI/LC con asignación M3 u operación.','Caps por uso sin asignación fiscal / reservas compatible: PENDING.'),
('T8 · seguro de obra','Prima citada, plazo de cobertura, cargo a presupuesto / financiación una sola vez.','La cotización auténtica y suficiencia de cobertura siguen sin validar.'),
('Rangos ampliados','Renta −50%; cap +500 bps; vertical +50%; tasas +500 bps; lease-up +24 meses; vacancia +30 pp. Mejoras visibles si ya pierde capital.','Contrafactual matemático: no afirma nueva lectura OCR ni disponibilidad real de términos estresados.'),
('Precio objetivo','Grilla mensual para TIR anual ≥15%, con deuda y flujos futuros fijos; cuatro rutas.','Meta hipotética, no criterio de Lorena ni RLV de la casa. Fuera de rango / dominio: visible.'),
('Presentación','Un edificio / GSF; terreno igual en v2; EM 2 decimales, TIR 1, unidades enteras, spread bps, dependencia de venta.','v1 no se reescribe; discrepancias y motivos sin evidencia quedan señalados.'),
('T12 · hallazgos','YoC y spread pueden agruparse con causa probada y revisión vinculada. Caja y todas las comparaciones se conservan.','No se elimina ningún criterio aplicable del RLV ni se modifica la precedencia de dictamen.')],[83,213,CW-296],y,pad=3)
y=p('<b>Puertas que siguen abiertas:</b> criterios / vigencia y reglas aplicables; responsables acreditados; términos personales LP/GP; evidencia real; backtest de 3–5 cerrados y falsos verdes con verdad humana independiente. Las herramientas T10/T11 no equivalen a esos resultados.',L,y,CW,'note')

y=page('Cierre de revisión y próximos controles','No se amplía el Mini-UW a Full UW · No hay despliegue, dictamen real ni aprobación automática')
y=section('Qué cambia y qué debe revisar el especialista',y)
y=table(['Referencia','Revisión solicitada'],[
('1 · Resultado','Cuatro rutas por USD 10 iniciales: aportes adicionales separados, cobros y fechas, dependencia de venta, EM y TIR. El retorno personal sigue PENDING sin reparto.'),
('2 · Decisiones','Carril humano, B08 antes de B09; una refi bloqueada conserva la alternativa sin refi si su deuda y vencimiento son válidos.'),
('3–4 · A–Z','La ruta mensual nueva exige evidencia adicional explícita. No acepta un JSON de resultados ni reutiliza un flujo anterior cuando falta un dato.'),
('5 · Dots / bots','Confirmar alcance de lectores y validadores. Un hash acredita identidad de archivo; no acredita verdad de mercado, autoridad ni ausencia real de errores OCR.'),
('6 · Fórmulas','Devengo por días; reserva C60 y comercial sin doble conteo; NOI compatible con cada cap; costo total reconciliado y todos los criterios RLV aplicables juntos.'),
('7 · Validación','Distinguir las pruebas dirigidas, oráculo del v2, equivalencia trimestral y batería general. No sumar cifras de distintos cortes como si fueran una sola corrida.'),
('Anexo Lorena','Confirmar 40 condiciones / alcances sin llenar vacíos con referencias históricas. El 15% del ensayo de precio no activa un umbral nuevo.')],[104,CW-104],y,pad=4)
y=section('Qué falta antes de un uso real',y)
y=p('Criterios vigentes con responsables, fecha, fuente y aprobación; documentos del deal conciliados; reglas fiscales aplicables y copias oficiales; cuatro funciones con identidad y autoridad acreditadas; autorización expresa de operación real. Luego cotejo profesional, backtest y corridas paralelas. Sin evidencia mínima: PENDING; PRELIMINAR no da PASS formal.',L,y,CW,'small')
y=p('Los umbrales reales y la regla de agregación no se deducen de un ejemplo sintético. No completar FAIL Downside con Base. La ausencia de dato, el cero numérico válido y N/A son estados distintos. La caja sin recuperar al horizonte se muestra sin convertirla automáticamente en pérdida definitiva.',L,y,CW,'small')
y=section('Expediente electrónico reproducible',y)
for title,path in [('Matriz requisito → código → prueba → estado','docs/review/MiniUW_Cobertura_Revision_D276.json'),('Validación dirigida y límites del corte','docs/review/MiniUW_Validacion_D276.json'),('Caso v2 y expectativas independientes','templates/golden_case_v2/golden_manifest.json'),('Motor mensual y su contrato','docs/workbook-monthly-integration-D276.md'),('Inventario completo previo de procesos / fórmulas','docs/MiniUW_Expediente_Integral_Revision_Profesional_D272.md'),('Cotejo externo preservado del caso v1','docs/review/MiniUW_Validacion_Excel_D275.json')]:
 y=p('<link href="https://github.com/brodskyfederico-commits/Mini-UW/blob/main/'+path+'" color="#176A69">'+escape(title)+'</link>',L,y,CW,'note')
y=p('<b>Responder por ID A–Z / B / M / T y requisito D276:</b> ubicación, evidencia, hallazgo y regla propuesta. Separar corrección técnica de confirmación financiera. El 1101 real y su retorno histórico siguen PENDING.',L,y,CW,'note')
assert PAGE==7;c.save()
import pymupdf as fitz
main=fitz.open();main.insert_pdf(fitz.open(args.outcome));main.insert_pdf(fitz.open(OUT));final=REPO/'docs/review/MiniUW_Actualizacion_Profesional_D276.pdf';main.set_metadata(dict(title='Mini-UW · revisión D276',author='Mini-UW',subject='8 páginas · resultado, flujo, A–Z, Dots, bots, conexiones y límites'));main.save(final,deflate=True);main.close()

OUT=REPO/'docs/review/MiniUW_Anexo_Lorena_D276.pdf';TOTAL=2;FOOTER_OFFSET=0;PAGE=0
c=canvas.Canvas(str(OUT),pagesize=letter,pageCompression=1,invariant=1);c.setTitle('Mini-UW · confirmaciones de Lorena D276')
criteria=[('YoC (NOI_uw)','6,50 %','5,75 %','5,25 %','≥ / <'),('Spread comparable','100 pb','50 pb','0 pb','≥ / <'),('Equity recuperado refi','60 %','40 %','25 %','≥ / <'),('Cash-in / equity','5 %','10 %','20 %','≤ / >'),('Ocupación equilibrio','85 %','90 %','93 %','≤ / >'),('CoC posrefi','6,0 %','4,0 %','3,0 %','≥ / <'),('Pedido / precio soportado','0 %','—','15 %','≤ / >'),('Equity / TDC','35 %','40 %','45 %','≤ / >'),('TIR anual','15 %','12 %','10 %','≥ / <'),('Múltiplo equity','1,75x','1,50x','1,35x','≥ / <')]
y=page('Lorena · confirmar criterios vigentes','Anexo separado del informe técnico · No solicita completar documentos del proyecto')
y=callout('Las cifras siguientes son <b>referencias originales, no criterios activos</b>. El archivo original no define umbrales numéricos de FAIL en Downside. «—», vacío y cero no son equivalentes. La fecha literal 10/12/2026 necesita interpretación y vigencia confirmadas.',y)
y=table(['Métrica','PASS Base','PASS Down','FAIL Base','Operadores'],criteria,[141,83,83,83,CW-390],y,pad=3)
y=p('Para cada métrica: confirmar <b>PASS Base, FAIL Base, PASS Downside y FAIL Downside</b>, o declarar expresamente «sin FAIL» / «no aplica» con motivo. Los campos de confirmación del Excel adjunto quedan vacíos; la referencia no los completa automáticamente.',L,y,CW,'small')
y=section('Definición que acompaña a cada número',y)
y=p('Indicar unidad, denominador, base de NOI, ventana temporal, operador e igualdad; versión, fecha de inicio / vencimiento y fuente aprobada. En la banda intermedia el resultado permanece PENDING / revisión, según la decisión vigente del usuario.',L,y,CW,'small')
y=p('YoC oficial sobre NOI_uw. El spread requiere base de NOI compatible con el cap; si el cap está antes de reservas, sólo su YoC comparable usa esa base y debe rotularse. DSCR y debt yield usan NOI bancario. Valoración y salida usan la base documentada de sus caps.',L,y,CW,'small')
y=p('Esta confirmación <b>no modifica importes ni fechas de los flujos</b>. El dictamen real sigue PENDING hasta tener fuente y aprobación válidas; un criterio sintético estricto o laxo sólo prueba el enchufe.',L,y,CW,'small')
y=page('Lorena y equipo · decisiones pendientes','Separar criterios de inversión, documentación y autorización')
y=table(['ID / responsable','Confirmación requerida'],[
('L01 · Lorena','Versión, vigencia y diez métricas; cuatro comparadores por métrica. Sin heredar valores de otro deal o escenario.'),
('L02 · Lorena','Operadores, igualdad, unidades, períodos y bases. CoC: primer año completo o ventana aprobada; TIR y múltiplo: horizonte declarado.'),
('L03 · Lorena','Política para FAIL Downside ausente y N/A; toda exclusión documentada, sin confundirla con un cero explícito.'),
('L04 · Lorena','Alcance RLV en Base, Downside y sin refi; estrategias aplicables. Se mantienen juntos todos los criterios aplicables, incluyendo YoC y spread.'),
('L05 · responsable criterios','Regla de agregación cuando hay FAIL verificado y otros faltantes. Banda intermedia PENDING y sin dictamen real automático.'),
('L06 · criterios + equipo','Autoridad para excepciones; materialidad; regla y tolerancia de discrepancias; jerarquía de evidencia y beneficios fiscales aplicables.'),
('L07 · responsable criterios','Ranking PRELIMINAR y mínimos reales; supuesto con fuente / fecha. Sin mínimo o capacidad válida: PENDING y fuera del ranking.'),
('Equipo del proyecto','Archivos del deal: planillas y respaldos, planos conciliados, GC con exclusiones, préstamos, rentas / caps con base NOI y seguro.'),
('Custodio / revisión','Copias fiscales oficiales y vigencia; cuatro funciones con personas acreditadas; autorización de datos reales y revisión independiente.'),
('Reparto / validación','Términos reales LP/GP para retorno personal; proyectos cerrados y verdad humana para backtest y estudio de falsos verdes.')],[132,CW-132],y,pad=3)
y=callout('<b>Cotejo del primer piloto:</b> comparar por USD 10 iniciales cada aporte adicional y cada cobro fechado (operación, refi y venta), saldos de deuda, reservas, sin recuperar, múltiplo y TIR. El caso real no hereda los importes del ejemplo sintético. Fuente o regla ausente: PENDING.',y,BLUE_BG)

assert PAGE==2;c.save()
checks={}
for path,count in [(final,8),(OUT,2),(args.outcome,1)]:
 doc=fitz.open(path);assert len(doc)==count;alltext='\n'.join(pg.get_text() for pg in doc)
 assert '\ufffd' not in alltext
 for i,pg in enumerate(doc):
  assert tuple(round(v) for v in sorted((pg.rect.width,pg.rect.height)))==(612,792),(path,i,'not Letter')
  for block in pg.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    for span in line['spans']:
     x0,y0,x1,y1=span['bbox'];assert x0>=12 and x1<=pg.rect.width-10 and y0>=3 and y1<=pg.rect.height-3,(path.name,i,span)
  pg.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(WORK/(path.stem+'-'+str(i+1)+'.png'))
 if count==8:
  for bot in range(1,18):assert f'B{bot:02}' in alltext
  for row in A+B:assert row[1] in ' '.join(alltext.split())
 if count==2:
  assert '2 / 8' not in alltext and '3 / 8' not in alltext
  for index,pg in enumerate(doc):assert pg.get_text().count(str(index+1)+' / 2')==1
 checks[path.name]=dict(page_count=len(doc),letter=True,inside_page=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(WORK/'report-validation.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
