
import time
from datetime import datetime,timedelta

def union(intervals):
 merged=[]
 for a,b in sorted(intervals):
  if b<=a:continue
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 return sum(b-a for a,b in merged)

def aggregate(rows,start,end,now=None):
 now=time.time() if now is None else now;groups={}
 for r in rows:
  a=max(start,r['start']);b=min(end,now if r['end'] is None else r['end'])
  if b<=a:continue
  g=groups.setdefault(r['app_key'],dict(app_key=r['app_key'],app=r['display_name'],category=r['category'],process_name=r['process_name'],seconds=0,count=0,active=0,intervals=[],first=a,last=b))
  g['seconds']+=b-a;g['count']+=1;g['active']+=int(r['end'] is None and r['start']<=now<end);g['intervals'].append((a,b));g['first']=min(g['first'],a);g['last']=max(g['last'],b)
 for g in groups.values():g['union_seconds']=union(g.pop('intervals'));g['average_seconds']=g['seconds']/g['count']
 return sorted(groups.values(),key=lambda g:(-g['union_seconds'],g['app'].casefold()))

def report(rows,start,end,category=None,now=None):
 now=time.time() if now is None else now;selected=[r for r in rows if category is None or r['category']==category];apps=aggregate(selected,start,end,now);all_apps=aggregate(rows,start,end,now) if category is not None else apps;total=sum(r['union_seconds'] for r in apps);denominator=sum(r['union_seconds'] for r in all_apps)
 intervals=[(max(start,r['start']),min(end,now if r['end'] is None else r['end'])) for r in selected];daily=[];day=datetime.fromtimestamp(start).replace(hour=0,minute=0,second=0,microsecond=0)
 while day.timestamp()<end:
  nxt=day+timedelta(days=1);a=max(start,day.timestamp());b=min(end,nxt.timestamp())
  if a<b:daily.append((day.strftime('%Y-%m-%d'),sum(g['union_seconds'] for g in aggregate(selected,a,b,now))))
  day=nxt
 cats={}
 for g in all_apps:cats[g['category']]=cats.get(g['category'],0)+g['union_seconds']
 return dict(apps=apps,total=total,process_seconds=sum(g['seconds'] for g in apps),overlap_free=union(intervals),count=sum(g['count'] for g in apps),active=sum(g['active'] for g in apps),share=total/denominator*100 if denominator else 0,daily=daily,categories=cats)
