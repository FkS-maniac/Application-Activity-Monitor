
import json
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import psutil
from src.windows_monitor import identity,session_id,metadata
from src.filtering import prefilter

class SessionTracker:
 def __init__(self,db,categories,settings,log):
  self.db=db;self.categories=categories;self.settings=settings;self.log=log;self.stop_event=threading.Event();self.reset_event=threading.Event();self.paused=threading.Event();self.lock=threading.RLock()
  self.known={};self.own={os.getpid()};self.results=queue.Queue(16);self.busy=set();self.generation=0;self.failures=0;self.completed=0;self.ms=0;self.source='starting';self.source_reason='';self.error='';self.thread=None
  self.user=psutil.Process().username().casefold();self.sid=session_id(os.getpid());self.wake=threading.Event()
 @property
 def running(self):return bool(self.thread and self.thread.is_alive())
 def start(self):
  if self.running:
   if not self.stop_event.is_set():self.paused.clear()
   return
  self.stop_event.clear();self.paused.clear();self.thread=threading.Thread(target=self.loop,name='coordinator',daemon=True);self.thread.start()
 def stop(self):
  self.stop_event.set();self.wake.set()
  if self.thread and self.thread is not threading.current_thread():self.thread.join()
 def pause(self):
  if self.paused.is_set():self.paused.clear()
  else:self.paused.set()
  self.wake.set()
 def reset(self):self.reset_event.set();self.wake.set()
 def publish(self,events):
  if not events:return
  try:self.db.enqueue(events);self.wake.set()
  except Exception:self.error='Ошибка записи буфера';self.log.event('storage.failure','ERROR',exc=True,throttle='spool')
 def observe(self,pid,parent=0,name='',sid=None):
  if pid in (0,4):return
  try:
   p=psutil.Process(pid);start=p.create_time()
   with self.lock:
    own=pid in self.own or parent in self.own
    if own:self.own.add(pid)
    e=dict(instance=identity(pid,start),pid=pid,start=start,parent=parent,name=name or p.name(),sid=sid,self_excluded=own,seen=time.time());self.known[pid]=e
   self.publish([e])
  except psutil.Error:pass
 def closed(self,pid,stamp):
  with self.lock:e=self.known.pop(pid,None);self.own.discard(pid)
  if e:self.publish([dict(e,end=max(stamp,e['start']),estimated=False,reason='event')])
  self.log.event('process.stop','DEBUG',pid=pid,instance=e['instance'] if e else None)
 def watch(self):
  try:
   import pythoncom
   import wmi
   pythoncom.CoInitialize()
   try:
    w=wmi.WMI();a=w.watch_for(raw_wql='SELECT * FROM Win32_ProcessStartTrace');b=w.watch_for(raw_wql='SELECT * FROM Win32_ProcessStopTrace');self.source='WMI';self.log.event('source.wmi',message='Источник WMI подключён')
    while not self.stop_event.is_set():
     for watcher,opening in ((a,True),(b,False)):
      try:
       e=watcher(timeout_ms=200)
       if opening:self.observe(int(e.ProcessID),int(e.ParentProcessID),str(e.ProcessName),int(e.SessionID))
       else:self.closed(int(e.ProcessID),(int(e.TIME_CREATED)-116444736000000000)/10000000)
      except wmi.x_wmi_timed_out:pass
   finally:pythoncom.CoUninitialize()
  except Exception as exc:
   self.source='polling';self.source_reason=type(exc).__name__;self.log.event('source.fallback','WARNING',message='WMI недоступен; включён опрос. Точность закрытия ограничена интервалом опроса.',exc=True,reason=self.source_reason);self.wake.set()
 def reconcile(self):
  current={};events=[];touch=[];now=time.time();own={os.getpid()}
  try:own.update(p.pid for p in psutil.Process().children(recursive=True))
  except psutil.Error:pass
  with self.lock:self.own.update(own)
  for p in psutil.process_iter(['pid','name','ppid','create_time'],ad_value=None):
   v=p.info
   if p.pid in (0,4) or v['create_time'] is None:continue
   current[p.pid]=v['create_time'];key=identity(p.pid,v['create_time'])
   with self.lock:old=self.known.get(p.pid)
   if old and old['instance']==key:
    with self.lock:
     if self.known.get(p.pid,{}).get('instance')==key:self.known[p.pid]['seen']=now
    touch.append(key);continue
   with self.lock:
    parent=v['ppid'] or 0;excluded=p.pid in self.own or parent in self.own
    if excluded:self.own.add(p.pid)
    event=dict(instance=key,pid=p.pid,start=v['create_time'],name=v['name'] or '',parent=parent,self_excluded=excluded,seen=now,sid=None);self.known[p.pid]=event
   events.append(event)
  with self.lock:known=list(self.known.values())
  for e in known:
   if current.get(e['pid'])!=e['start']:
    with self.lock:
     if self.known.get(e['pid'],{}).get('instance')==e['instance']:self.known.pop(e['pid'],None);self.own.discard(e['pid'])
    events.append(dict(e,end=e['seen'],end_upper=now,estimated=True,reason='polling' if self.source=='polling' else 'missing_event'))
  for r in self.db.open_sessions():
   if identity(r['pid'],current.get(r['pid'],0))!=r['instance']:
    events.append(dict(instance=r['instance'],pid=r['pid'],start=r['start'],end=r['last_seen'],seen=r['last_seen'],estimated=True,reason='recovery'))
  self.publish(events);self.db.touch(touch,now)
 def detect(self,row,c,g):
  begin=time.monotonic();e=json.loads(row['payload']);key=e['instance'];r=dict(instance=key,payload=row['payload'],generation=g,action='drop')
  try:
   old=self.db.existing(key)
   if old:
    name,cat=self.categories.resolve(old['process_name']);r.update(action='save',app=(old['app_key'],old['process_name'],old['exe_path'],name,cat,old['detected_at']),session=(key,old['app_key'],e['pid'],e['start'],e.get('end'),e.get('seen',time.time()),int(e.get('estimated',False)),e.get('reason')));return r
   reason=prefilter(e['pid'],e.get('name',''),e.get('sid'),c,e.get('self_excluded',False))
   if reason:
    self.log.event('detection.filtered','DEBUG',instance=key,reason=reason)
    if 'end' not in e:r.update(action='retry',due=1e15)
    return r
   if e.get('end',time.time())-e['start']<c['minimum_lifetime_seconds']:
    if 'end' not in e:r.update(action='retry',due=e['start']+c['minimum_lifetime_seconds'])
    return r
   sid=e.get('sid')
   if sid is None:sid=session_id(e['pid'])
   reason=prefilter(e['pid'],e.get('name',''),sid,c,e.get('self_excluded',False))
   if reason or (c['current_session_only'] and sid!=self.sid):
    if 'end' not in e:r.update(action='retry',due=1e15)
    self.log.event('detection.filtered','DEBUG',instance=key,reason=reason or 'other_session');return r
   p=metadata(e['pid'])
   if identity(p['pid'],p['start'])!=key:return r
   blocked=p['owner'].casefold() in {x.casefold() for x in c['excluded_users']} or (c['current_user_only'] and p['owner'].casefold()!=self.user)
   if c['mode']!='strict':blocked|=os.path.normcase(p['exe']) in {os.path.normcase(x) for x in c['excluded_paths']}
   if blocked:
    if 'end' not in e:r.update(action='retry',due=1e15)
    return r
   name,cat=self.categories.resolve(p['name']);appkey=os.path.normcase(p['exe']) or p['name'].casefold();r.update(action='save',app=(appkey,p['name'],p['exe'],name,cat,time.time()),session=(key,appkey,p['pid'],e['start'],e.get('end'),time.time(),int(e.get('estimated',False)),e.get('reason')))
   self.log.event('detection.success',message='Приложение принято',instance=key,pid=p['pid'],process=p['name'],category=cat)
  except psutil.NoSuchProcess:self.log.event('detection.gone','DEBUG',instance=key)
  except Exception as exc:
   ttl=min(c['max_retry_seconds'],c['retry_seconds']*2**min(row['attempts'],16));r.update(action='retry',due=time.time()+ttl);self.failures+=1
   level='INFO' if isinstance(exc,psutil.AccessDenied) else 'WARNING'
   self.log.event('detection.retry',level,message='Метаданные недоступны; повтор отложен',exc=level=='WARNING',throttle=type(exc).__name__,instance=key,error_type=type(exc).__name__,attempt=row['attempts']+1,retry_seconds=ttl)
  finally:r['ms']=(time.monotonic()-begin)*1000
  return r
 def loop(self):
  c=self.settings.get();workers=c['workers'];pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='detector');batch=[];scan=reload=write=metric=0
  self.busy.clear();self.db.reset();listener=threading.Thread(target=self.watch,name='wmi-events',daemon=True);listener.start();self.log.event('tracker.start',workers=workers)
  try:
   while not self.stop_event.is_set():
    now=time.time()
    if now-reload>=2:
     reload=now
     try:
      changed=self.settings.reload();cc=self.categories.reload()
      if changed:
       new=self.settings.get()
       if any(new[k]!=c[k] for k in ('workers','database','theme')):self.error='workers/database/theme: перезапустите приложение'
       c=new;self.log.set_level(c['log_level']);self.reset();self.log.event('config.reload')
      if cc:self.db.rename_categories(self.categories);self.reset()
     except Exception:self.log.event('config.invalid','ERROR',exc=True,throttle='config')
    if self.reset_event.is_set():
     self.reset_event.clear();self.generation+=1;batch.clear()
     with self.lock:self.known.clear()
     self.db.reset();scan=0;self.log.event('detection.reset',message='Детекция сброшена; реестр сохранён',generation=self.generation)
    interval=c['fallback_seconds'] if self.source=='polling' else c['reconcile_seconds']
    if now-scan>=interval:self.reconcile();scan=now
    self.db.ingest(c['batch_size'])
    while True:
     try:r=self.results.get_nowait()
     except queue.Empty:break
     self.busy.discard(r['instance']);self.completed+=1;self.ms+=r.get('ms',0)
     if r['generation']==self.generation:batch.append(r)
    if batch and (now-write>=c['flush_seconds'] or len(batch)>=c['batch_size']):self.db.commit(batch);self.log.event('storage.batch','DEBUG',count=len(batch));batch.clear();write=now
    if not self.paused.is_set():
     for row in self.db.candidates(now,workers+len(self.busy)+len(batch)):
      if len(self.busy)>=workers:break
      if row['instance'] in self.busy or any(r['instance']==row['instance'] for r in batch):continue
      self.busy.add(row['instance']);f=pool.submit(self.detect,row,c,self.generation)
      def finished(f):self.results.put(f.result());self.wake.set()
      f.add_done_callback(finished)
    if now-metric>=c['metrics_seconds']:metric=now;self.log.event('metrics.snapshot',**self.metrics(),suppressed=self.log.summary()['suppressed'])
    self.wake.wait(.05 if self.busy or batch else .5);self.wake.clear()
  except Exception:self.error='Ошибка координатора';self.log.event('storage.failure','ERROR',exc=True,phase='coordinator')
  finally:
   listener.join(timeout=2);pool.shutdown(wait=True)
   while not self.results.empty():
    r=self.results.get()
    if r['generation']==self.generation:batch.append(r)
   if batch:self.db.commit(batch)
   self.busy.clear();self.log.event('tracker.stop')
 def metrics(self):
  return dict(observed=len(self.known),inflight=len(self.busy),failures=self.failures,average_ms=round(self.ms/max(1,self.completed),2),source=self.source,source_reason=self.source_reason,error=self.error,**self.db.counts())
