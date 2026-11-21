"""Opt-in test harness: memoize successful deterministic Tesseract byte outputs.

Never imported by deal intake. A fresh cache is used for the final regression.
Every cache key includes the exact raster bytes, arguments, complete environment
fingerprint and runtime inventory hash. Parsing, confidence, citations, source
hashes, gates and tests always execute. Failure outputs are never cached.
"""
from pathlib import Path
from hashlib import sha256
import subprocess,json,os,base64,tempfile


def install(directory,runtime_sha256):
 root=Path(directory);root.mkdir(parents=True,exist_ok=True);os.chmod(root,0o700);original=subprocess.run
 def run(args,*pos,**kw):
  eligible=(not pos and isinstance(args,(list,tuple)) and len(args)>3 and Path(str(args[0])).name=='tesseract' and list(args[1:3])==['stdin','stdout'] and args[-1]=='tsv' and isinstance(kw.get('input'),bytes) and kw.get('capture_output') is True and kw.get('check') is False and not kw.get('text') and not kw.get('encoding') and set(kw)<= {'input','capture_output','check','timeout','env'})
  if not eligible:return original(args,*pos,**kw)
  binary=Path(args[0]);metadata=dict(arguments=list(args),environment_sha256=sha256(json.dumps(kw.get('env',dict(os.environ)),sort_keys=True).encode()).hexdigest(),binary_sha256=sha256(binary.read_bytes()).hexdigest(),runtime_sha256=runtime_sha256,input_sha256=sha256(kw['input']).hexdigest(),timeout=kw.get('timeout'));key=sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest();path=root/(key+'.json');hit=False
  if path.is_file():
   item=json.loads(path.read_bytes());out=base64.b64decode(item['stdout'],validate=True);err=base64.b64decode(item['stderr'],validate=True)
   if item['metadata']!=metadata or sha256(out).hexdigest()!=item['stdout_sha256'] or sha256(err).hexdigest()!=item['stderr_sha256']:raise ValueError('OCR cache integrity mismatch')
   result=subprocess.CompletedProcess(args,0,out,err);hit=True
  else:
   result=original(args,*pos,**kw)
   if result.returncode==0:
    item=dict(metadata=metadata,stdout=base64.b64encode(result.stdout).decode(),stderr=base64.b64encode(result.stderr).decode(),stdout_sha256=sha256(result.stdout).hexdigest(),stderr_sha256=sha256(result.stderr).hexdigest());fd,tmp=tempfile.mkstemp(dir=root,prefix='.atomic-');os.write(fd,json.dumps(item,sort_keys=True).encode());os.close(fd);os.replace(tmp,path)
  # One short append is atomic on this single-host test harness.
  fd=os.open(root/'events.jsonl',os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600);os.write(fd,(json.dumps(dict(key=key,hit=hit,returncode=result.returncode))+'\n').encode());os.close(fd);return result
 subprocess.run=run
 return original
