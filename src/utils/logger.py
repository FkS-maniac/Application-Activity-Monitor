
import hashlib
import json
import logging
import threading
import time
import uuid
from collections import Counter
from datetime import datetime
from logging.handlers import RotatingFileHandler

class Formatter(logging.Formatter):
 def __init__(self,structured):super().__init__();self.structured=structured
 def format(self,r):
  data={'schema':2,'timestamp':datetime.fromtimestamp(r.created).astimezone().isoformat(timespec='milliseconds'),'level':r.levelname,'run_id':getattr(r,'run_id',''),'event':getattr(r,'code','python.log'),'message':r.getMessage(),'thread':r.threadName,'context':getattr(r,'context',{})}
  if r.exc_info:
   data['exception']=self.formatException(r.exc_info);kind=r.exc_info[0].__name__;data['error_id']=hashlib.sha256((data['event']+'|'+kind).encode()).hexdigest()[:12]
  if self.structured:return json.dumps(data,ensure_ascii=False,default=str)
  text=f"{data['timestamp']} | {data['level']:7} | {data['event']} | {data['message']}"
  if data['context']:text+=' | '+json.dumps(data['context'],ensure_ascii=False,default=str)
  if 'exception' in data:text+='\n'+data['exception']
  return text

class LogService:
 def __init__(self,base):
  self.base=base;self.run_id=uuid.uuid4().hex[:12];self.started=time.time();self.lock=threading.RLock();self.counts=Counter();self.suppressed=Counter();self.last={};self.level=logging.INFO
  self.logger=logging.getLogger('gst');self.logger.setLevel(logging.DEBUG);self.logger.propagate=False
  for h in self.logger.handlers[:]:h.close();self.logger.removeHandler(h)
  self.handlers=[]
  for name,structured in [('tracker.log',False),('tracker.jsonl',True)]:
   h=RotatingFileHandler(base/name,maxBytes=2_000_000,backupCount=3,encoding='utf-8');h.setFormatter(Formatter(structured));self.handlers.append(h);self.logger.addHandler(h)
 def set_level(self,value):self.level=getattr(logging,value)
 def event(self,code,level='INFO',message=None,exc=False,throttle=None,**context):
  with self.lock:
   self.counts[code]+=1
   if throttle:
    key=(code,str(throttle));now=time.monotonic()
    if now-self.last.get(key,-1e20)<60:self.suppressed[code]+=1;return
    if len(self.last)>4096:self.last.clear()
    self.last[key]=now
  if getattr(logging,level)<self.level:return
  self.logger.log(getattr(logging,level),message or code,exc_info=exc,extra={'run_id':self.run_id,'code':code,'context':context})
 def summary(self):
  with self.lock:return dict(run_id=self.run_id,uptime_seconds=round(time.time()-self.started,1),events=dict(self.counts),suppressed=dict(self.suppressed))
 def flush(self):
  for h in self.handlers:h.flush()
 def install_hooks(self):
  import sys
  def hook(kind,value,tb):self.logger.error('Необработанное исключение',exc_info=(kind,value,tb),extra={'run_id':self.run_id,'code':'exception.unhandled','context':{}})
  sys.excepthook=hook
  threading.excepthook=lambda args:hook(args.exc_type,args.exc_value,args.exc_traceback)
