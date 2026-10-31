
import json
import threading
from pathlib import Path
BASE_CATEGORIES={'Games':'Игры','Browser':'Браузеры','Communication':'Коммуникация','System':'Система','Development':'Разработка','Work':'Работа','Media':'Медиа','Other':'Остальные'}
class Categories:
 def __init__(self,path):
  self.path=Path(path);self.rules={};self.lock=threading.RLock();self.raw=None;self.reload()
 @staticmethod
 def validate(rules):
  if not isinstance(rules,dict):raise ValueError('rules должен быть объектом')
  for k,r in rules.items():
   if not k or not isinstance(r,dict) or not isinstance(r.get('display_name'),str) or not isinstance(r.get('category'),str) or not r['category'].strip():raise ValueError('Некорректное правило')
  return rules
 def reload(self):
  if not self.path.exists():return False
  raw=self.path.read_text(encoding='utf-8-sig')
  if raw==self.raw:return False
  rules=self.validate(json.loads(raw)['rules'])
  with self.lock:self.rules={k.casefold():v for k,v in rules.items()};self.raw=raw
  return True
 def snapshot(self):
  with self.lock:return json.loads(json.dumps(self.rules))
 def resolve(self,name):
  with self.lock:r=self.rules.get(name.casefold(),{})
  return r.get('display_name',name),r.get('category','Other')
 def keys(self):
  with self.lock:return list(dict.fromkeys([*BASE_CATEGORIES,*sorted({r['category'] for r in self.rules.values()})]))
 def save(self,rules):
  self.validate(rules);p=self.path.with_suffix('.tmp');p.write_text(json.dumps({'rules':rules},ensure_ascii=False,indent=2),encoding='utf-8');p.replace(self.path);self.reload()
