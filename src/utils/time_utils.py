
from datetime import datetime,timedelta

def duration(seconds):
 h,r=divmod(max(0,int(seconds)),3600);m,s=divmod(r,60);return f'{h:02}:{m:02}:{s:02}'
def bounds(start,end):
 a=datetime.strptime(start,'%Y-%m-%d');b=datetime.strptime(end,'%Y-%m-%d')+timedelta(days=1)
 if b<=a or (b-a).days>366:raise ValueError('Выберите корректный диапазон до 366 дней')
 return a.timestamp(),b.timestamp()
def stamp(t):return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S') if t is not None else 'Работает'
