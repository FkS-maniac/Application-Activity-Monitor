
import json
import sqlite3

class Database:
 def __init__(self,path):
  self.path=str(path)
  with self.connect() as d:
   d.executescript("""PRAGMA journal_mode=WAL;
   CREATE TABLE IF NOT EXISTS applications(app_key TEXT PRIMARY KEY,process_name TEXT,exe_path TEXT,display_name TEXT,category TEXT,detected_at REAL);
   CREATE TABLE IF NOT EXISTS sessions(instance TEXT PRIMARY KEY,app_key TEXT,pid INTEGER,start REAL,end REAL,last_seen REAL,estimated INTEGER DEFAULT 0,reason TEXT);
   CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start);
   CREATE INDEX IF NOT EXISTS idx_sessions_end ON sessions(end);
   CREATE TABLE IF NOT EXISTS pending(instance TEXT PRIMARY KEY,payload TEXT,due REAL DEFAULT 0,attempts INTEGER DEFAULT 0);
   CREATE TABLE IF NOT EXISTS spool(id INTEGER PRIMARY KEY AUTOINCREMENT,payload TEXT);
   CREATE INDEX IF NOT EXISTS idx_pending_due ON pending(due);
   """)
 def connect(self):
  d=sqlite3.connect(self.path,timeout=20);d.row_factory=sqlite3.Row;return d
 def enqueue(self,events):
  with self.connect() as d:d.executemany('INSERT INTO spool(payload) VALUES (?)',[(json.dumps(e),) for e in events])
 def ingest(self,limit):
  with self.connect() as d:
   for r in d.execute('SELECT * FROM spool ORDER BY id LIMIT ?',(limit,)).fetchall():
    e=json.loads(r['payload']);old=d.execute('SELECT payload FROM pending WHERE instance=?',(e['instance'],)).fetchone();merged=json.loads(old[0]) if old else {};merged.update(e)
    d.execute('INSERT INTO pending(instance,payload) VALUES (?,?) ON CONFLICT(instance) DO UPDATE SET payload=excluded.payload,due=CASE WHEN excluded.payload LIKE ? THEN 0 ELSE pending.due END',(e['instance'],json.dumps(merged),'%"end":%'));d.execute('DELETE FROM spool WHERE id=?',(r['id'],))
 def candidates(self,now,limit):
  with self.connect() as d:return [dict(r) for r in d.execute('SELECT * FROM pending WHERE due<=? ORDER BY due LIMIT ?',(now,limit))]
 def existing(self,key):
  with self.connect() as d:
   r=d.execute('SELECT s.*,a.process_name,a.exe_path,a.display_name,a.category,a.detected_at FROM sessions s JOIN applications a USING(app_key) WHERE instance=?',(key,)).fetchone();return dict(r) if r else None
 def open_sessions(self):
  with self.connect() as d:return [dict(r) for r in d.execute('SELECT * FROM sessions WHERE end IS NULL')]
 def reset(self):
  with self.connect() as d:d.execute('UPDATE pending SET due=0,attempts=0')
 def touch(self,keys,now):
  with self.connect() as d:d.executemany('UPDATE sessions SET last_seen=? WHERE instance=? AND end IS NULL',[(now,k) for k in keys])
 def commit(self,results):
  with self.connect() as d:
   for r in results:
    if r['action']=='retry':
     d.execute('UPDATE pending SET due=?,attempts=attempts+1 WHERE instance=? AND payload=?',(r['due'],r['instance'],r['payload']));continue
    if r['action']=='save':
     d.execute('INSERT INTO applications VALUES (?,?,?,?,?,?) ON CONFLICT(app_key) DO UPDATE SET display_name=excluded.display_name,category=excluded.category',r['app'])
     d.execute("""INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(instance) DO UPDATE SET end=COALESCE(excluded.end,sessions.end),last_seen=MAX(excluded.last_seen,sessions.last_seen),estimated=CASE WHEN excluded.end IS NOT NULL THEN excluded.estimated ELSE sessions.estimated END,reason=COALESCE(excluded.reason,sessions.reason)""",r['session'])
    d.execute('DELETE FROM pending WHERE instance=? AND payload=?',(r['instance'],r['payload']))
 def rows(self,start,end):
  with self.connect() as d:return [dict(r) for r in d.execute('SELECT s.*,a.process_name,a.display_name,a.category FROM sessions s JOIN applications a USING(app_key) WHERE s.start<? AND (s.end IS NULL OR s.end>?) ORDER BY s.start DESC',(end,start))]
 def counts(self):
  with self.connect() as d:
   result={x:d.execute('SELECT COUNT(*) FROM '+x).fetchone()[0] for x in ('applications','pending','spool')}
   result['parked']=d.execute('SELECT COUNT(*) FROM pending WHERE due>=1e14').fetchone()[0];result['open_sessions']=d.execute('SELECT COUNT(*) FROM sessions WHERE end IS NULL').fetchone()[0];return result
 def all_categories(self):
  with self.connect() as d:return [r[0] for r in d.execute('SELECT DISTINCT category FROM applications ORDER BY category')]
 def clear_history(self):
  with self.connect() as d:d.execute('DELETE FROM sessions')
 def rename_categories(self,categories):
  with self.connect() as d:
   for r in d.execute('SELECT app_key,process_name FROM applications').fetchall():
    name,cat=categories.resolve(r['process_name']);d.execute('UPDATE applications SET display_name=?,category=? WHERE app_key=?',(name,cat,r['app_key']))
