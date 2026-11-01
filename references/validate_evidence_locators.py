"""Local literal-evidence reference. No semantic truth, official authenticity or financial approval."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as ET
from tempfile import TemporaryDirectory
from io import BytesIO
import json,hashlib,re
from jsonschema import Draft202012Validator
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'schemas/evidence-claim.schema.json').read_text());Draft202012Validator.check_schema(SCHEMA)
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
X={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
records=json.loads((ROOT/'docs/source-register.json').read_text())
SOURCES={x['sha256']:ROOT/x['backup_path'] for x in records}
def normal(s):return re.sub(r'\s+',' ',s).strip()
def xlsx_literal(path,sheet,cell):
 with ZipFile(path) as z:
  wb=ET.fromstring(z.read('xl/workbook.xml'));rels={x.attrib['Id']:x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  sh=next((s for s in wb.findall('m:sheets/m:sheet',X) if s.attrib['name']==sheet),None)
  if sh is None:raise ValueError('sheet missing')
  target=rels[sh.attrib['{'+R+'}id']];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
  # Read ZIP members only; no extraction, formula evaluation or external links.
  if '..' in Path(target).parts or target not in z.namelist():raise ValueError('unresolved/unsafe worksheet relationship')
  root=ET.fromstring(z.read(target));c=root.find('.//m:sheetData/m:row/m:c[@r="'+cell+'"]',X)
  if c is None:return None,None
  formula=c.find('m:f',X);f=formula.text if formula is not None else None
  if c.attrib.get('t')=='inlineStr':return ''.join(t.text or '' for t in c.findall('.//m:t',X)),f
  v=c.find('m:v',X);value=v.text if v is not None else None
  if c.attrib.get('t')=='s' and value is not None:
   strings=ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',X)
   value=''.join(t.text or '' for t in strings[int(value)].findall('.//m:t',X))
  return value,f

def verify(claim,sources):
 Draft202012Validator(SCHEMA).validate(claim)
 sha=claim['source_sha256']
 if sha not in sources:raise ValueError('source not inventoried')
 path=Path(sources[sha]);data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('original bytes changed')
 locator=claim['locator'];kind=locator['kind'];formula=None
 if kind=='pdf_page_text':
  if path.suffix.lower()!='.pdf':raise ValueError('source format/locator mismatch')
  reader=PdfReader(BytesIO(data));page=locator['page']
  if type(page) is not int or not 1<=page<=len(reader.pages):raise ValueError('page out of bounds')
  observed=reader.pages[page-1].extract_text() or '';expected=claim['expected_literal']
  matched=expected is not None and normal(expected)!='' and normal(expected) in normal(observed)
 elif kind=='docx_paragraph':
  if path.suffix.lower()!='.docx':raise ValueError('source format/locator mismatch')
  with ZipFile(BytesIO(data)) as z:paras=ET.fromstring(z.read('word/document.xml')).findall('.//w:p',W)
  pos=locator['paragraph']
  if type(pos) is not int or not 1<=pos<=len(paras):raise ValueError('paragraph out of bounds')
  observed=''.join(t.text or '' for t in paras[pos-1].findall('.//w:t',W));expected=claim['expected_literal']
  matched=expected is not None and normal(expected)!='' and normal(expected) in normal(observed)
 else:
  if path.suffix.lower()!='.xlsx':raise ValueError('source format/locator mismatch')
  observed,formula=xlsx_literal(path,locator['sheet'],locator['cell']);matched=observed==claim['expected_literal']
 return {'claim_id':claim['claim_id'],'source_sha256':sha,'locator':locator,'literal_match':matched,'formula':formula,'formula_executed':False,'status':'cached_literal_match_formula_unexecuted' if matched and formula is not None else 'literal_match_only' if matched else 'literal_not_matched','semantic_meaning_verified':False,'official_authenticity_verified':False,'source_authority_approved':False}

def claim(sha,kind,expected,**loc):return {'purpose':'design_or_synthetic_reference','authorization':'not_granted','claim_id':'REFERENCE-CLAIM','source_sha256':sha,'locator':dict(kind=kind,**loc),'expected_literal':expected,'semantic_meaning_verified':False}
checks=[]
def ok(name,result):
 assert result,name;checks.append(name)
def reject(name,c,sources=SOURCES):
 from jsonschema import ValidationError
 try:verify(c,sources)
 except (ValueError,ValidationError):checks.append(name)
 else:raise AssertionError('invalid claim accepted: '+name)
workbook='b433468ec6cb2ebf6b9950325fef212dc9df365ac9adbca4895ca1df39234600'
roadmap='af24c12776010d35f742b2f6b50b2dec4d310989506cf80997ab57dc9a5f292b'
standards='38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9'
c=claim(workbook,'xlsx_cell','Rent basis',sheet='Inputs',cell='A7');ok('original_xlsx_label_matches',verify(c,SOURCES)['literal_match'])
c=claim(workbook,'xlsx_cell',None,sheet='Inputs',cell='C38');ok('original_blank_preserved',verify(c,SOURCES)['literal_match'])
c['expected_literal']='0';ok('original_blank_not_numeric_zero',not verify(c,SOURCES)['literal_match'])
c=claim(roadmap,'pdf_page_text','MINI-UW 3.1',page=1);ok('original_pdf_title_found',verify(c,SOURCES)['literal_match'])
c['expected_literal']='SYNTHETIC LITERAL NOT IN ORIGINAL';ok('invented_pdf_citation_rejected',not verify(c,SOURCES)['literal_match'])
c=claim(standards,'docx_paragraph','Underwriting Standards',paragraph=1);ok('original_docx_title_found',verify(c,SOURCES)['literal_match'])
c['expected_literal']='SYNTHETIC LITERAL NOT IN ORIGINAL';ok('invented_docx_citation_rejected',not verify(c,SOURCES)['literal_match'])
reject('unknown_source_not_arbitrary_path',claim('0'*64,'pdf_page_text','x',page=1))
reject('out_of_bounds_page',claim(roadmap,'pdf_page_text','x',page=9999))
reject('out_of_bounds_paragraph',claim(standards,'docx_paragraph','x',paragraph=99999))
reject('missing_sheet',claim(workbook,'xlsx_cell','x',sheet='NOT A SHEET',cell='A1'))
reject('bad_cell_reference',claim(workbook,'xlsx_cell','x',sheet='Inputs',cell='../../secret'))
reject('wrong_source_type',claim(workbook,'pdf_page_text','x',page=1))
c=claim(roadmap,'pdf_page_text','x',page=1);c['semantic_meaning_verified']=True;reject('claim_cannot_self_authenticate_meaning',c)
c=claim(roadmap,'pdf_page_text','x',page=1);c['path']='/arbitrary/path';reject('path_injection_not_schema_field',c)
with TemporaryDirectory(prefix='miniuw-evidence-reference-') as tmp:
 p=Path(tmp)/'synthetic.xlsx'
 with ZipFile(p,'w',ZIP_DEFLATED) as z:
  z.writestr('xl/workbook.xml','<workbook xmlns="'+X['m']+'" xmlns:r="'+R+'"><sheets><sheet name="Inputs" sheetId="1" r:id="r1"/></sheets></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
  z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="'+X['m']+'"><sheetData><row r="1"><c r="A1"><v>0</v></c><c r="B1"><f>1+1</f><v>2</v></c><c r="C1" t="inlineStr"><is><t>5%</t></is></c></row></sheetData></worksheet>')
 sha=hashlib.sha256(p.read_bytes()).hexdigest();sources={sha:p}
 c=claim(sha,'xlsx_cell','0',sheet='Inputs',cell='A1');ok('explicit_synthetic_zero_preserved',verify(c,sources)['literal_match'])
 c=claim(sha,'xlsx_cell',None,sheet='Inputs',cell='A1');ok('explicit_zero_not_blank',not verify(c,sources)['literal_match'])
 c=claim(sha,'xlsx_cell','2',sheet='Inputs',cell='B1');z=verify(c,sources);ok('cached_formula_not_execution',z['literal_match'] and z['formula']=='1+1' and z['status']=='cached_literal_match_formula_unexecuted' and not z['formula_executed'])
 c=claim(sha,'xlsx_cell','0.05',sheet='Inputs',cell='C1');ok('percentage_literal_not_silently_normalized',not verify(c,sources)['literal_match'])
 p.write_bytes(b'changed synthetic bytes');reject('changed_source_bytes_rejected',c,sources)
# Originals must remain unchanged after all reader operations.
ok('all_inventoried_originals_unchanged',all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for sha,p in SOURCES.items()))
report={'status':'passed','checks':checks,'total':len(checks),'original_formats_exercised':['PDF text page','DOCX paragraph','XLSX label/blank cell'],'scope':'Literal location/byte-integrity only on supplied originals and explicitly synthetic workbook fixtures. Not semantic extraction, independent readers, legal/official authenticity, financial interpretation, approval or production.'}
Path(__file__).with_name('evidence-locators-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
