from tempfile import TemporaryDirectory
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from xml.etree import ElementTree as ET
from unittest import TestCase
from worksheet_review_templates_D275 import xlsx,templates,M
from worksheet_review_controls_D275 import review_roles
import json

class ReviewTemplateTests(TestCase):
 def test_blank_is_absent_cell_and_explicit_zero_stays_numeric(self):
  raw=xlsx({'Test':[['vacío','cero'],[None,0]]})
  with ZipFile(BytesIO(raw)) as z:xml=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
  cells={c.get('r'):c for c in xml.iter('{'+M+'}c')};self.assertNotIn('A2',cells);self.assertEqual(cells['B2'].find('{'+M+'}v').text,'0')
 def test_formulas_live_and_no_invented_cached_zero(self):
  raw=xlsx({'Test':[[{'formula':'IF(COUNT(B2:C2)=2,C2-B2,NA())'}]]})
  with ZipFile(BytesIO(raw)) as z:xml=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
  cell=next(xml.iter('{'+M+'}c'));self.assertIsNotNone(cell.find('{'+M+'}f'));self.assertIsNone(cell.find('{'+M+'}v'))
 def test_templates_deterministic_and_real_roles_empty(self):
  with TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b';templates(a);templates(b)
   for p in a.iterdir():self.assertEqual(p.read_bytes(),(b/p.name).read_bytes())
   self.assertFalse(review_roles(json.loads((a/'roles_registry.json').read_bytes()),'2027-01-01',{})['structurally_complete'])
 def test_backtest_has_all_32_measurement_rows_and_blank_observed_values(self):
  with TemporaryDirectory() as d:
   p=Path(d)/'a';templates(p)
   with ZipFile(p/'backtest_case_template.xlsx') as z:xml=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
   rows=list(xml.iter('{'+M+'}row'));self.assertEqual(len(rows),33)
   cells={c.get('r'):c for c in xml.iter('{'+M+'}c')}
   self.assertTrue(all(f'I{i}' not in cells for i in range(2,34)));self.assertTrue(all('COUNT' in cells[f'J{i}'].find('{'+M+'}f').text for i in range(2,34)))
