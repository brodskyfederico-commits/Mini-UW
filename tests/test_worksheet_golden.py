from unittest import TestCase
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import json,hashlib
from worksheet_golden_D275 import workbook,SOURCE_FILES
from worksheet_intake_D198 import read_source_directory
from check_golden_excel_D275 import read_cells,mutate
from miniuw_worksheet_v1 import build_results,encoded

ROOT=Path(__file__).resolve().parents[1]/'templates/golden_case_v1'

class GoldenSourceTests(TestCase):
 def test_fixed_source_hashes(self):
  index=json.loads((ROOT/'golden_manifest.json').read_bytes());self.assertEqual(set(index['files']),set(SOURCE_FILES))
  for p,h in index['files'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
 def test_source_workbook_deterministic_and_has_live_not_cached_formulas(self):
  spec=json.loads((ROOT/'case.json').read_bytes());sources=read_source_directory(ROOT,include_reference=True)
  a=workbook(spec,sources);self.assertEqual(a,workbook(spec,sources))
  with ZipFile(BytesIO(a)) as z:
   formulas=sum(z.read(n).count(b'<ns0:f>') for n in z.namelist() if n.startswith('xl/worksheets/'))
   self.assertGreater(formulas,1000)
   self.assertNotIn(b'<ns0:v>0</ns0:v>',z.read('xl/worksheets/sheet18.xml'))
 def test_mutation_is_source_only_and_blank_differs_from_explicit_zero(self):
  spec=json.loads((ROOT/'case.json').read_bytes());book=workbook(spec,read_source_directory(ROOT,include_reference=True))
  original=read_cells(book);blank=read_cells(mutate(book,'blank'));zero=read_cells(mutate(book,'explicit_zero'));changed=read_cells(mutate(book,'changed'))
  self.assertNotIn('C8',blank['B Inputs']);self.assertEqual(zero['B Inputs']['C53'],0);self.assertNotEqual(original['B Inputs']['C8'],changed['B Inputs']['C8'])
 def test_unintegrated_extension_never_silently_uses_old_cash(self):
  for key in ['monthly_construction','commercial_leaseup','builders_risk','review_extensions']:
   case=dict(schema='miniuw.synthetic-native-rental-inputs.v34',rent_inputs={key:None})
   with self.assertRaisesRegex(ValueError,'extensiones experimentales'):build_results(encoded(case))
