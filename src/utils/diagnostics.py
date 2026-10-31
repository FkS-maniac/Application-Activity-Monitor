
import json
import platform
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime
from importlib.metadata import version,PackageNotFoundError

def redact(text):
 home=str(Path.home())
 if len(home)>3:text=re.sub(re.escape(home),'<USER_HOME>',text,flags=re.I)
 pattern='(?i)[A-Z]:[\\\\/]+Users[\\\\/]+[^\\\\/\\s"\']+'
 return re.sub(pattern,'<USER_HOME>',text)

def tail(path,budget):
 with path.open('rb') as f:
  f.seek(0,2);size=f.tell();n=min(size,budget,512*1024);f.seek(size-n);raw=f.read(n)
 if n<size:raw=raw.partition(b'\n')[2]
 return raw.decode('utf-8',errors='replace'),n,n<size

def build_report(base,settings=None,tracker=None,log=None,anonymize=True):
 base=Path(base)
 if log:log.flush()
 parts=['GAME SESSION TRACKER 1.0.0-rc.1 — DIAGNOSTICS','Generated: '+datetime.now().astimezone().isoformat(),'Python: '+sys.version.replace('\n',' '),'Platform: '+platform.platform(),'','=== PACKAGES ===']
 for p in ('ttkbootstrap','psutil','matplotlib','pystray','Pillow','WMI','pywin32'):
  try:v=version(p)
  except PackageNotFoundError:v='not installed'
  parts.append(p+': '+v)
 if log:parts+=['','=== CURRENT RUN COUNTERS ===',json.dumps(log.summary(),ensure_ascii=False,indent=2)]
 if tracker:
  try:parts+=['','=== LIVE METRICS ===',json.dumps(tracker.metrics(),ensure_ascii=False,indent=2)]
  except Exception as exc:parts.append('Metrics unavailable: '+repr(exc))
 if settings:
  c=settings.get()
  if anonymize:
   for k in ('excluded_users','excluded_paths'):c[k]='<redacted; count='+str(len(c[k]))+'>'
   c['database']=Path(c['database']).name
  parts+=['','=== CONFIGURATION ===',json.dumps(c,ensure_ascii=False,indent=2)]
 samples=[];budget=2*1024*1024;counts=Counter();errors=Counter();recent=[]
 for name in ('tracker.jsonl','tracker.jsonl.1','tracker.jsonl.2','tracker.jsonl.3','tracker.log','tracker.log.1','tracker.log.2','tracker.log.3'):
  p=base/name
  if not p.exists() or budget<=0:continue
  try:text,used,truncated=tail(p,budget);budget-=used;samples.append((name,text,truncated))
  except Exception as exc:samples.append((name,repr(exc),False));continue
  if 'jsonl' in name:
   for line in text.splitlines():
    try:r=json.loads(line)
    except ValueError:continue
    counts[r.get('event','unknown')]+=1
    if r.get('level') in ('WARNING','ERROR','CRITICAL'):errors[(r.get('event',''),r.get('error_id',''))]+=1;recent.append(r)
 parts+=['','=== LOG SUMMARY (EXPORTED TAILS, MAY INCLUDE EARLIER RUNS) ===',json.dumps({'events':dict(counts),'error_groups':[{'event':k[0],'error_id':k[1],'count':v} for k,v in errors.most_common(20)]},ensure_ascii=False,indent=2),'','=== LATEST WARNING / ERROR SAMPLES ===']
 for r in sorted(recent,key=lambda r:r.get('timestamp',''),reverse=True)[:10]:parts.append(json.dumps(r,ensure_ascii=False))
 parts+=['','=== LOG TAILS ===','Max 512 KiB per file, 2 MiB log input total. Older content may be omitted.']
 for name,text,truncated in samples:parts+=['','--- '+name+(' [beginning omitted]' if truncated else '')+' ---',text]
 if not samples:parts.append('No logs found.')
 parts+=['','=== INTERPRETATION ===','source=polling means approximate process termination detection.','parked means filtered tasks waiting for config/reset; not a worker backlog.','average_ms is detection latency, not CPU percent.','pending includes parked and delayed retries; spool is durable input.','=== PRIVACY ===','No automatic upload. Review before sharing; redaction is best effort.','No database, command lines, keyboard input or window contents attached.']
 text='\n'.join(parts);return redact(text) if anonymize else text

def write_report(path,base,settings=None,tracker=None,log=None,anonymize=True):
 p=Path(path)
 if p.suffix.lower()!='.txt':raise ValueError('Выберите .txt файл')
 text=build_report(base,settings,tracker,log,anonymize);p.write_text(text,encoding='utf-8-sig')
 if log:log.event('diagnostics.export',characters=len(text),anonymized=anonymize)
 return p

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='diagnostics.txt');parser.add_argument('--raw',action='store_true');a=parser.parse_args();print(write_report(a.output,Path(__file__).resolve().parents[2],anonymize=not a.raw))
