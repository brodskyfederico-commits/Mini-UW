"""Deterministic, blank-safe OOXML templates for independent review instruments."""
from io import BytesIO
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from xml.etree.ElementTree import Element,SubElement,tostring
from pathlib import Path
from argparse import ArgumentParser
import json
from worksheet_review_controls_D275 import empty_roles,STUDY_SCHEMA
from worksheet_backtest_D275 import METRICS,SCHEMA as BACKTEST

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
D='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
R='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'

def col(n):
 s=''
 while n:n,a=divmod(n-1,26);s=chr(65+a)+s
 return s

def xlsx(sheets):
 parts={};book=Element('{'+M+'}workbook');ss=SubElement(book,'{'+M+'}sheets');SubElement(book,'{'+M+'}calcPr',calcId='191029',fullCalcOnLoad='1',forceFullCalc='1')
 rels=Element('{'+R+'}Relationships');root=Element('{'+R+'}Relationships');SubElement(root,'{'+R+'}Relationship',Id='rId1',Type=D+'/officeDocument',Target='xl/workbook.xml')
 types=Element('{'+C+'}Types');SubElement(types,'{'+C+'}Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml');SubElement(types,'{'+C+'}Default',Extension='xml',ContentType='application/xml')
 SubElement(types,'{'+C+'}Override',PartName='/xl/workbook.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
 for i,(title,rows) in enumerate(sheets.items(),1):
  SubElement(ss,'{'+M+'}sheet',name=title,sheetId=str(i),attrib={'{'+D+'}id':'rId'+str(i)});SubElement(rels,'{'+R+'}Relationship',Id='rId'+str(i),Type=D+'/worksheet',Target=f'worksheets/sheet{i}.xml')
  SubElement(types,'{'+C+'}Override',PartName=f'/xl/worksheets/sheet{i}.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
  ws=Element('{'+M+'}worksheet');views=SubElement(ws,'{'+M+'}sheetViews');view=SubElement(views,'{'+M+'}sheetView',workbookViewId='0');SubElement(view,'{'+M+'}pane',ySplit='1',topLeftCell='A2',activePane='bottomLeft',state='frozen')
  columns=SubElement(ws,'{'+M+'}cols')
  for j in range(max((len(r) for r in rows),default=1)):SubElement(columns,'{'+M+'}col',min=str(j+1),max=str(j+1),width='26',customWidth='1')
  data=SubElement(ws,'{'+M+'}sheetData')
  for row_no,values in enumerate(rows,1):
   row=SubElement(data,'{'+M+'}row',r=str(row_no))
   for n,value in enumerate(values,1):
    if value is None:continue
    at=col(n)+str(row_no)
    if isinstance(value,dict) and set(value)=={'formula'}:
     cell=SubElement(row,'{'+M+'}c',r=at);SubElement(cell,'{'+M+'}f').text=value['formula']
    elif type(value) in (int,float):cell=SubElement(row,'{'+M+'}c',r=at);SubElement(cell,'{'+M+'}v').text=str(value)
    else:
     cell=SubElement(row,'{'+M+'}c',r=at,t='inlineStr');inline=SubElement(cell,'{'+M+'}is');SubElement(inline,'{'+M+'}t').text=str(value)
  parts[f'xl/worksheets/sheet{i}.xml']=tostring(ws,encoding='utf-8',xml_declaration=True)
 parts.update({'[Content_Types].xml':tostring(types),'_rels/.rels':tostring(root),'xl/workbook.xml':tostring(book),'xl/_rels/workbook.xml.rels':tostring(rels)})
 buffer=BytesIO()
 with ZipFile(buffer,'w') as z:
  for name,raw in sorted(parts.items()):
   item=ZipInfo(name,(2026,1,1,0,0,0));item.compress_type=ZIP_DEFLATED;z.writestr(item,raw)
 return buffer.getvalue()


def templates(output):
 output.mkdir(parents=True,exist_ok=False)
 (output/'roles_registry.json').write_text(json.dumps(empty_roles(),ensure_ascii=False,indent=2)+'\n')
 backtest=[['Proyecto','Corte original','Corte observado','Escenario','Ruta','Métrica','Unidad','Pronóstico original','Observado real','Diferencia','Fuente original','Fuente observado']]
 for scenario in ('Base','Downside'):
  for route in ('with_refinance','without_refinance'):
   for metric,unit in METRICS.items():
    row=len(backtest)+1;backtest.append([None,None,None,scenario,route,metric,unit,None,None,{'formula':f'IF(COUNT(H{row}:I{row})=2,I{row}-H{row},NA())'},None,None])
 calendar=[['Proyecto','Hito','Fecha prevista original','Fecha observada real','Fuente / cita'],[None,'Compra'],[None,'Fin de obra'],[None,'Estabilización'],[None,'Refinanciación'],[None,'Venta']]
 attribution=[['Proyecto','Escenario','Ruta','Métrica','Categoría','Importe atribuido','Fuente / cita','Revisor'],[None,None,None,None,None,None,None,None]]
 instructions=[['Uso','Regla'],['Sin rellenar','Vacío no equivale a cero. La fórmula de diferencia exige dos valores numéricos.'],['Pronóstico','Usar sólo la información disponible en la fecha original; ligar al paquete auditado.'],['Observado','Cargar resultados reales documentados; nunca usar supuestos sintéticos como observaciones reales.'],['Atribución','Usar fuentes / plazo / costo / NOI / servicio_deuda / venta / aportes / cobros; cualquier resto se muestra no explicado.'],['TIR','Registrar intervalo certificado y período en el JSON; no escoger un punto medio para simular precisión.'],['Dictamen','Este instrumento no acredita aprobación, despliegue ni validación empírica del modelo.']]
 (output/'backtest_case_template.xlsx').write_bytes(xlsx({'Instrucciones':instructions,'Pronostico y observado':backtest,'Calendario':calendar,'Atribuciones':attribution}))
 study=[['ID crítico','Documento','Tipo','Bot','Escenario','Unidad','Base','Valor bot','Estado bot','SHA fuente bot','Cita bot','Valor humano','Respaldo humano sí/no','Revisor independiente','SHA referencia humana','Cita humana']]
 for doc,bot in [('plano','B05'),('cotizacion_gc','B08'),('term_sheet','B08'),('fiscal','B11')]:study.append([None,None,doc,bot,None,None,None,None,None,None,None,None,None,None,None,None])
 (output/'false_green_independent_reference.xlsx').write_bytes(xlsx({'Instrucciones':[['Uso','Regla'],['Referencia humana','Una persona verifica cada dato, su unidad, escenario, cita y fuente.'],['Muestra completa','Conservar el inventario esperado; no quitar casos fallidos.'],['Pendiente','Sin verdad independiente no se mide la tasa total; no se cuenta como correcto.'],['Falso verde','Verde sin cita válida, con fuente o ubicación diferente o dato discrepante cuenta como falso verde.'],['Confianza','Wilson bilateral 95 %; cero observado no implica tasa real cero.']],'Muestra':study}))
 return sorted(p.name for p in output.iterdir())


def main():
 p=ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(templates(a.output)))
if __name__=='__main__':main()
