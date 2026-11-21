from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import os,subprocess,json
from regression_ocr_cache_D277 import install
class OCRCacheHarnessTests(TestCase):
 def test_only_identical_success_bytes_reused_and_changes_execute_again(self):
  real=subprocess.run
  try:
   with TemporaryDirectory() as d:
    binary=Path(d)/'tesseract';binary.write_bytes(b'fixture-binary');calls=[]
    def underlying(args,**kw):calls.append((args,kw));return subprocess.CompletedProcess(args,0,b'actual TSV bytes',b'')
    with patch('subprocess.run',underlying):
     install(Path(d)/'cache','runtime-A');cmd=[str(binary),'stdin','stdout','--psm','6','tsv'];kw=dict(input=b'raster-1',capture_output=True,check=False,timeout=15,env={'LC_ALL':'C'})
     self.assertEqual(subprocess.run(cmd,**kw).stdout,b'actual TSV bytes');subprocess.run(cmd,**kw);self.assertEqual(len(calls),1)
     subprocess.run(cmd,**(kw|dict(input=b'raster-2')));self.assertEqual(len(calls),2)
     subprocess.run(cmd,**(kw|dict(env={'LC_ALL':'other'})));self.assertEqual(len(calls),3)
     binary.write_bytes(b'changed-binary');subprocess.run(cmd,**kw);self.assertEqual(len(calls),4)
     subprocess.run([str(binary),'--version'],capture_output=True);self.assertEqual(len(calls),5)
  finally:subprocess.run=real
 def test_failures_not_cached_and_corrupt_cache_blocks(self):
  real=subprocess.run
  try:
   with TemporaryDirectory() as d:
    binary=Path(d)/'tesseract';binary.write_bytes(b'binary');calls=[]
    def underlying(args,**kw):calls.append(1);return subprocess.CompletedProcess(args,1 if len(calls)<3 else 0,b'TSV',b'')
    with patch('subprocess.run',underlying):
     install(Path(d)/'cache','runtime');cmd=[str(binary),'stdin','stdout','tsv'];kw=dict(input=b'x',capture_output=True,check=False)
     subprocess.run(cmd,**kw);subprocess.run(cmd,**kw);self.assertEqual(len(calls),2);self.assertEqual(len(list((Path(d)/'cache').glob('*.json'))),0);subprocess.run(cmd,**kw)
     file=next((Path(d)/'cache').glob('*.json'));record=json.loads(file.read_bytes());record['stdout_sha256']='0'*64;file.write_text(json.dumps(record))
     with self.assertRaises(ValueError):subprocess.run(cmd,**kw)
  finally:subprocess.run=real
