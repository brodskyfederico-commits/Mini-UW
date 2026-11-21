from unittest import TestCase
from copy import deepcopy
from worksheet_decision_page_D275 import render,amount
from worksheet_review_controls_D275 import empty_roles
from pypdf import PdfReader
from io import BytesIO


def view():
 return dict(schema='miniuw.synthetic-nine-block-decision-page.v1',project='SYNTHETIC-UNPROVIDED-TEST',address=None,revision='SYNTHETIC-R1',case_sha256='a'*64,decision='PENDING',roles=empty_roles(),scenario={s:dict(coverage={'PENDING':55},units=0,nrsf=None,gsf=None,commercial_sf=None,stories={r:dict(cash=None,summary=None,blockers=['source_pending']) for r in ('with_refinance','without_refinance')},calendar={},tdc=None,equity=None,construction_debt=None,permanent_debt=None,blockers=['source_pending']) for s in ('Base','Downside')},metrics={s:{k:None for k in ('YoC','spread','DSCR','debt_yield','LTC','LTV','occupancy','equity_TDC','CoC','equity_recovered')} for s in ('Base','Downside')},analyses={})

class DecisionPageTests(TestCase):
 def test_missing_values_visible_in_nine_blocks_on_one_letter_page(self):
  raw,fields=render(view());doc=PdfReader(BytesIO(raw));self.assertEqual(len(doc.pages),1);self.assertEqual((float(doc.pages[0].mediabox.width),float(doc.pages[0].mediabox.height)),(792,612))
  text=doc.pages[0].extract_text();self.assertIn('PENDING',text)
  for label in ['1. Expediente','2. Caja','3. Métricas','4. Fronteras','5. Precio','6. Tornado','7. Fuentes','8. Banderas','9. Revisión']:self.assertIn(label,text)
  self.assertNotIn('PASS',text);self.assertNotIn('FAIL',text)
  self.assertTrue(all(str(f['display']).startswith('PENDING') for f in fields if f['value'] is None))
 def test_long_project_name_does_not_leave_page_and_is_preserved_in_metadata(self):
  a=view();a['project']='SYNTHETIC-'+('PROYECTO EXTENSO DE PRUEBA '*25);raw,_=render(a);doc=PdfReader(BytesIO(raw));self.assertEqual(doc.metadata['/Subject'],a['project'])
  def check(text,cm,tm,font,size):
   if not text.strip():return
   from reportlab.pdfbase.pdfmetrics import stringWidth
   name=str((font or {}).get('/BaseFont','/Helvetica')).lstrip('/')
   x=cm[0]*tm[4]+cm[2]*tm[5]+cm[4]
   for line in text.splitlines():
    self.assertGreaterEqual(x,20);self.assertLessEqual(x+stringWidth(line,name,size),773)
  doc.pages[0].extract_text(visitor_text=check)
 def test_deterministic_and_no_input_mutation(self):
  a=view();old=deepcopy(a);self.assertEqual(render(a),render(a));self.assertEqual(a,old)
 def test_explicit_zero_formatted_but_blank_and_bool_are_not_zero(self):
  self.assertEqual(amount(0),'0,00')
  for value in [None,'',False]:self.assertEqual(amount(value),'PENDING')
 def test_missing_price_point_remains_pending_without_crash(self):
  a=view();a['analyses']['price_grid']={s:dict(price_grid=[dict(price=None,values=None)]*5) for s in ('Base','Downside')};raw,fields=render(a);self.assertTrue(raw.startswith(b'%PDF-'));self.assertIn('PENDING',PdfReader(BytesIO(raw)).pages[0].extract_text())
