import json
import os
from pathlib import Path
DEFAULT = {'schema_version': 1, 'mode': 'all_user_apps', 'workers': 2, 'minimum_lifetime_seconds': 5, 'reconcile_seconds': 60, 'fallback_seconds': 10, 'retry_seconds': 60, 'max_retry_seconds': 1800, 'flush_seconds': 2, 'batch_size': 100, 'theme': 'darkly', 'minimize_to_tray': True, 'current_user_only': True, 'current_session_only': True, 'exclude_self_and_children': True, 'excluded_users': ['NT AUTHORITY\\SYSTEM', 'NT AUTHORITY\\LOCAL SERVICE', 'NT AUTHORITY\\NETWORK SERVICE'], 'excluded_session_ids': [0], 'excluded_processes': [], 'excluded_paths': [], 'allowlist': [], 'exclude_os_background': True, 'database': 'process_tracker_v2.db', 'ui_refresh_seconds': 15, 'log_level': 'INFO', 'metrics_seconds': 60}

def validate(c):
 c=dict(c)
 for k,v in DEFAULT.items():c.setdefault(k,v)
 if c['schema_version']!=1:raise ValueError('schema_version должен быть 1')
 if c['mode'] not in ('all_user_apps','strict','allowlist_with_exclusions'):raise ValueError('mode')
 for k,lo,hi in [('workers',1,2),('minimum_lifetime_seconds',0,3600),('reconcile_seconds',10,3600),('fallback_seconds',2,3600),('retry_seconds',1,3600),('max_retry_seconds',1,86400),('flush_seconds',1,60),('batch_size',1,1000),('ui_refresh_seconds',5,300),('metrics_seconds',15,3600)]:
  if type(c[k]) is not int or not lo<=c[k]<=hi:raise ValueError(k)
 for k in ('minimize_to_tray','current_user_only','current_session_only','exclude_self_and_children','exclude_os_background'):
  if type(c[k]) is not bool:raise ValueError(k)
 for k in ('excluded_users','excluded_processes','excluded_paths','allowlist'):
  if not isinstance(c[k],list) or not all(isinstance(v,str) for v in c[k]):raise ValueError(k)
 if not isinstance(c['excluded_session_ids'],list) or not all(type(x) is int for x in c['excluded_session_ids']):raise ValueError('excluded_session_ids')
 if not isinstance(c['database'],str) or not c['database']:raise ValueError('database')
 if c['theme'] not in ('darkly','superhero','flatly','cyborg'):raise ValueError('theme')
 if c['log_level'] not in ('INFO','DEBUG','WARNING'):raise ValueError('log_level')
 return c
class Settings:
 def __init__(self,path):
  self.path=Path(path);self.raw=None
  if not self.path.exists():self.save(DEFAULT)
  self.reload()
 def get(self):return json.loads(json.dumps(self.data))
 def reload(self):
  raw=self.path.read_text(encoding='utf-8-sig')
  if raw==self.raw:return False
  data=validate(json.loads(raw));self.data=data;self.raw=raw;return True
 def save(self,c):
  c=validate(c);p=self.path.with_suffix('.tmp');p.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(p,self.path)
