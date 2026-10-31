
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from src.settings import DEFAULT,validate,Settings
from src.filtering import prefilter
from src.database import Database
from src.categories import Categories
from src.statistics import union,report
from src.utils.logger import LogService
from src.utils.diagnostics import redact,write_report
from src.utils.time_utils import bounds

def row(key='a',cat='Games',start=0,end=10):return dict(app_key=key,display_name=key,category=cat,process_name=key+'.exe',start=start,end=end)

class StatsTests(unittest.TestCase):
 def test_union(self):self.assertEqual(union([(0,10),(5,15),(20,30)]),25)
 def test_empty(self):self.assertEqual(report([],0,20,now=20)['share'],0)
 def test_category(self):self.assertEqual(report([row(),row('b','Browser')],0,20,'Games',20)['share'],50)
 def test_overlap(self):
  r=report([row(),row(start=5,end=15)],0,20,now=20);self.assertEqual(r['total'],15);self.assertEqual(r['process_seconds'],20)
 def test_parallel_apps(self):
  r=report([row(),row('b')],0,20,now=20);self.assertEqual(r['total'],20);self.assertEqual(r['overlap_free'],10)
 def test_clip(self):self.assertEqual(report([row(end=100)],20,30,now=100)['total'],10)
 def test_open(self):self.assertEqual(report([row(end=None)],0,100,now=30)['active'],1)
 def test_history_active(self):self.assertEqual(report([row(end=None)],0,10,now=30)['active'],0)
 def test_custom(self):self.assertEqual(report([row(cat='Custom')],0,20,'Custom',20)['total'],10)
 def test_zero(self):self.assertEqual(report([row(start=10,end=10)],0,20,now=20)['count'],0)
 def test_dates(self):
  with self.assertRaises(ValueError):bounds('2026-02-02','2026-01-01')

class FilterTests(unittest.TestCase):
 def setUp(self):self.c=copy.deepcopy(DEFAULT)
 def test_pid_zero(self):self.assertEqual(prefilter(0,'System Idle Process',None,self.c),'kernel_pid')
 def test_pid_four(self):self.assertEqual(prefilter(4,'System',None,self.c),'kernel_pid')
 def test_session_zero(self):self.assertEqual(prefilter(100,'x.exe',0,self.c),'excluded_session')
 def test_runtime(self):self.assertEqual(prefilter(100,'RuntimeBroker.exe',1,self.c),'os_background')
 def test_background_allow_override(self):
  self.c['allowlist']=['RuntimeBroker.exe'];self.assertIsNone(prefilter(100,'RuntimeBroker.exe',1,self.c))
 def test_allow_does_not_override_session(self):
  self.c['allowlist']=['RuntimeBroker.exe'];self.assertEqual(prefilter(100,'RuntimeBroker.exe',0,self.c),'excluded_session')
 def test_self(self):self.assertEqual(prefilter(100,'python.exe',1,self.c,True),'own_process')
 def test_strict(self):
  self.c['mode']='strict';self.c['allowlist']=['a.exe'];self.assertIsNone(prefilter(100,'a.exe',1,self.c));self.assertEqual(prefilter(101,'b.exe',1,self.c),'allowlist')

class StorageTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=Database(Path(self.tmp.name)/'db')
 def tearDown(self):self.tmp.cleanup()
 def result(self,key='1:100'):
  return dict(instance=key,action='save',payload='{}',app=('a','a.exe','a.exe','App','Other',100),session=(key,'a',1,100,None,110,0,None))
 def test_reset_preserves(self):
  self.db.commit([self.result()]);self.db.reset();self.assertEqual(self.db.counts()['applications'],1);self.assertIsNotNone(self.db.existing('1:100'))
 def test_upsert(self):
  self.db.commit([self.result(),self.result()]);self.assertEqual(len(self.db.rows(0,1000)),1)
 def test_pid_reuse(self):
  self.db.commit([self.result(),self.result('1:200')]);self.assertEqual(len(self.db.rows(0,1000)),2)
 def test_merge(self):
  self.db.enqueue([dict(instance='x',start=1),dict(instance='x',end=2)]);self.db.ingest(10);self.assertEqual(json.loads(self.db.candidates(10,10)[0]['payload'])['end'],2)
 def test_old_retry_cannot_delay_stop(self):
  self.db.enqueue([dict(instance='x',start=1)]);self.db.ingest(10);old=self.db.candidates(10,1)[0];self.db.enqueue([dict(instance='x',end=2)]);self.db.ingest(10);self.db.commit([dict(instance='x',payload=old['payload'],action='retry',due=1e15)]);self.assertEqual(len(self.db.candidates(10,10)),1)
 def test_stop_wakes_parked(self):
  self.db.enqueue([dict(instance='x',start=1)]);self.db.ingest(10);old=self.db.candidates(10,1)[0];self.db.commit([dict(instance='x',payload=old['payload'],action='retry',due=1e15)]);self.assertEqual(self.db.counts()['parked'],1)
  self.db.enqueue([dict(instance='x',end=2)]);self.db.ingest(10);self.assertEqual(len(self.db.candidates(10,10)),1)
 def test_touch_no_new_pending(self):
  self.db.commit([self.result()]);self.db.touch(['1:100'],200);self.assertEqual(self.db.existing('1:100')['last_seen'],200);self.assertEqual(self.db.counts()['pending'],0)
 def test_config(self):
  c=copy.deepcopy(DEFAULT);c['workers']=4
  with self.assertRaises(ValueError):validate(c)
 def test_old_config_defaults(self):
  c=copy.deepcopy(DEFAULT);c.pop('exclude_os_background');self.assertTrue(validate(c)['exclude_os_background'])
 def test_categories(self):
  cats=Categories(Path(self.tmp.name)/'c.json');cats.save({'A.EXE':{'display_name':'A','category':'Custom'}});self.assertEqual(cats.resolve('a.exe'),('A','Custom'))

class LoggerTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.log=LogService(self.base)
 def tearDown(self):
  for h in self.log.handlers:self.log.logger.removeHandler(h);h.close()
  self.tmp.cleanup()
 def read(self):
  self.log.flush();return [json.loads(x) for x in (self.base/'tracker.jsonl').read_text(encoding='utf-8').splitlines()]
 def test_schema(self):
  self.log.event('test',pid=100);r=self.read()[0];self.assertEqual(r['schema'],2);self.assertEqual(r['context']['pid'],100)
 def test_trace(self):
  try:raise ValueError('test')
  except ValueError:self.log.event('test','ERROR',exc=True)
  self.assertIn('ValueError',self.read()[0]['exception'])
 def test_throttle(self):
  for _ in range(5):self.log.event('test','WARNING',throttle='same')
  self.assertEqual(len(self.read()),1);self.assertEqual(self.log.summary()['suppressed']['test'],4)
 def test_debug(self):
  self.log.event('test','DEBUG');self.assertEqual(len(self.read()),0)
 def test_txt(self):
  self.log.event('source.fallback','WARNING');p=self.base/'r.txt';write_report(p,self.base,log=self.log);self.assertIn('source.fallback',p.read_text(encoding='utf-8-sig'))
 def test_redaction_plain(self):self.assertNotIn('SecretUser',redact(r'C:\Users\SecretUser\Downloads\x.py'))
 def test_redaction_json(self):
  text=json.dumps({'exception':r'C:\Users\SecretUser\Downloads\x.py'});self.assertNotIn('SecretUser',redact(text))
 def test_rotation(self):
  self.log.handlers[1].maxBytes=300
  for i in range(10):self.log.event('test',n=i)
  self.assertTrue((self.base/'tracker.jsonl.1').exists())
 def test_extension(self):
  with self.assertRaises(ValueError):write_report(self.base/'r.log',self.base)

if __name__=='__main__':unittest.main()
