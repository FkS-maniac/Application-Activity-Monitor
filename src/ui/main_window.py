
import json
import queue
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from tkinter import messagebox,filedialog
import ttkbootstrap as tb
from src.statistics import report
from src.categories import BASE_CATEGORIES
from src.utils.time_utils import duration,bounds,stamp
from src.utils.export import export_csv
from src.utils.diagnostics import write_report
from src.ui.category_stats import CategoryStats,table,fill,app_values,HEADERS

class MainWindow(tb.Window):
 def __init__(self,db,categories,settings,tracker,base,log):
  super().__init__(themename=settings.get()['theme']);self.db=db;self.categories=categories;self.settings=settings;self.tracker=tracker;self.base=base;self.log=log
  self.title('Game Session Tracker 1.0.0-rc.1');self.geometry('1330x880');self.minsize(1000,700);self.exiting=False;self.inbox=queue.Queue();self.commands=queue.Queue();self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='stats');self.busy=False;self.dirty=False;self.cache={};self.tray=None;self.tray_ready=False;self.category_views={};self.export_busy=False
  top=tb.Frame(self,padding=8);top.pack(fill='x')
  for label,cmd in [('Запуск',self.start),('Пауза обработки',tracker.pause),('Остановить',self.stop),('Сброс детекции',tracker.reset),('Обновить',lambda:self.refresh(True))]:tb.Button(top,text=label,command=cmd).pack(side='left',padx=3)
  tb.Button(top,text='Выход',command=self.quit_app).pack(side='right');self.status=tb.StringVar(value='Запуск…');tb.Label(self,textvariable=self.status,padding=6,wraplength=1280).pack(fill='x')
  self.source_label=tb.StringVar(value='Источник: подключение…');tb.Label(self,textvariable=self.source_label,padding=5,wraplength=1280,bootstyle='warning').pack(fill='x')
  tb.Label(self,text='Фоновые программы учитываются без фокуса окна. Время приложения — объединение интервалов его EXE; не время работы пользователя.',wraplength=1280,padding=4).pack(fill='x')
  self.tabs=tb.Notebook(self);self.tabs.pack(fill='both',expand=True,padx=8,pady=5);self.today=tb.Frame(self.tabs,padding=6);self.history=tb.Frame(self.tabs,padding=6);self.stats=tb.Frame(self.tabs,padding=6);self.options=tb.Frame(self.tabs,padding=6)
  for frame,label in [(self.today,'Сегодня'),(self.history,'История'),(self.stats,'Статистика'),(self.options,'Настройки')]:self.tabs.add(frame,text=label)
  self.today_summary=tb.StringVar();tb.Label(self.today,textvariable=self.today_summary,padding=5).pack(fill='x');self.today_tree=table(self.today,HEADERS)
  today=datetime.now().strftime('%Y-%m-%d');self.history_start=tb.StringVar(value=today);self.history_end=tb.StringVar(value=today);ctl=tb.Frame(self.history);ctl.pack(fill='x')
  for label,var in [('С',self.history_start),('По',self.history_end)]:tb.Label(ctl,text=label).pack(side='left');tb.Entry(ctl,textvariable=var,width=13).pack(side='left',padx=5)
  tb.Button(ctl,text='Показать',command=lambda:self.refresh(True)).pack(side='left');tb.Button(ctl,text='CSV',command=self.export_history).pack(side='left',padx=5);self.history_tree=table(self.history,HEADERS,height=8);self.session_tree=table(self.history,['Приложение','PID','Начало','Конец','Длительность','Завершение'],height=8)
  ctl=tb.Frame(self.stats);ctl.pack(fill='x');self.period=tb.StringVar(value='7 дней');combo=tb.Combobox(ctl,textvariable=self.period,values=['Сегодня','7 дней','30 дней','Свой период'],state='readonly',width=15);combo.pack(side='left');combo.bind('<<ComboboxSelected>>',lambda e:self.refresh(True));self.stats_start=tb.StringVar(value=today);self.stats_end=tb.StringVar(value=today)
  for label,var in [('С (YYYY-MM-DD)',self.stats_start),('По',self.stats_end)]:tb.Label(ctl,text=label).pack(side='left',padx=4);tb.Entry(ctl,textvariable=var,width=13).pack(side='left')
  tb.Button(ctl,text='Применить',command=lambda:self.refresh(True)).pack(side='left',padx=5);tb.Button(ctl,text='CSV категории',command=self.export_category).pack(side='right');self.range_label=tb.StringVar();tb.Label(self.stats,textvariable=self.range_label,padding=5).pack(fill='x');self.category_tabs=tb.Notebook(self.stats);self.category_tabs.pack(fill='both',expand=True);self.ensure_categories(['__all__',*categories.keys(),*db.all_categories()]);self.category_tabs.bind('<<NotebookTabChanged>>',lambda e:self.refresh())
  editors=tb.Notebook(self.options);editors.pack(fill='both',expand=True);conf=tb.Frame(editors,padding=5);cats=tb.Frame(editors,padding=5);editors.add(conf,text='Конфигурация');editors.add(cats,text='Категории')
  tb.Label(conf,text='workers/database/theme требуют перезапуска. Пауза останавливает обработку очереди, но не время жизни процесса.',wraplength=1200).pack(anchor='w');self.editor=tb.Text(conf,wrap='none');self.editor.pack(fill='both',expand=True);self.editor.insert('1.0',json.dumps(settings.get(),ensure_ascii=False,indent=2));tb.Button(conf,text='Сохранить конфиг',command=self.save_config).pack(pady=4)
  self.cat_editor=tb.Text(cats,wrap='none');self.cat_editor.pack(fill='both',expand=True);self.cat_editor.insert('1.0',json.dumps({'rules':categories.snapshot()},ensure_ascii=False,indent=2));tb.Button(cats,text='Сохранить категории',command=self.save_categories).pack(pady=4)
  buttons=tb.Frame(self.options);buttons.pack(fill='x')
  tb.Button(buttons,text='Папка данных',command=lambda:os.startfile(str(base))).pack(side='left');tb.Button(buttons,text='Экспорт диагностики TXT',command=self.export_diagnostics).pack(side='left',padx=6);tb.Button(buttons,text='Очистить историю',command=self.clear_history,bootstyle='danger').pack(side='left',padx=8)
  self.diagnostics=tb.StringVar();tb.Label(self,textvariable=self.diagnostics,padding=6,wraplength=1280).pack(fill='x');self.tabs.bind('<<NotebookTabChanged>>',lambda e:self.refresh());self.protocol('WM_DELETE_WINDOW',self.on_close);self.tray_setup();tracker.start();self.after(200,self.tick);self.after(500,self.refresh);self.after(15000,self.periodic)
 def report_callback_exception(self,exc,value,tb):
  self.log.logger.error('Ошибка UI',exc_info=(exc,value,tb),extra={'run_id':self.log.run_id,'code':'ui.failure','context':{}});messagebox.showerror('Ошибка','Ошибка записана. Экспортируйте диагностику из Настроек.')
 def ensure_categories(self,keys):
  for key in dict.fromkeys(keys):
   if key not in self.category_views:
    frame=CategoryStats(self.category_tabs,key);self.category_views[key]=frame;self.category_tabs.add(frame,text='Обзор' if key=='__all__' else BASE_CATEGORIES.get(key,key))
 def request(self):
  tab=self.tabs.index(self.tabs.select());day=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
  if tab==0:return ('today',day.timestamp(),(day+timedelta(days=1)).timestamp(),None)
  if tab==1:
   a,b=bounds(self.history_start.get(),self.history_end.get());return ('history',a,b,None)
  if tab==2:
   selected=self.category_tabs.select();key=next((k for k,v in self.category_views.items() if str(v)==selected),'__all__')
   if self.period.get()=='Свой период':a,b=bounds(self.stats_start.get(),self.stats_end.get())
   else:
    days={'Сегодня':1,'7 дней':7,'30 дней':30}[self.period.get()];a=(day-timedelta(days=days-1)).timestamp();b=(day+timedelta(days=1)).timestamp()
   return ('stats',a,b,key)
  return ('options',0,0,None)
 def refresh(self,force=False):
  if self.exiting:return
  try:req=self.request()
  except (ValueError,KeyError) as exc:
   if force:messagebox.showerror('Период',str(exc))
   return
  if not force and req in self.cache and time.monotonic()-self.cache[req][0]<self.settings.get()['ui_refresh_seconds']:self.render(req,self.cache[req][1]);return
  if self.busy:self.dirty=True;return
  self.busy=True;self.dirty=False;self.status.set('Расчёт статистики…')
  def work():
   try:
    kind,a,b,key=req;rows=self.db.rows(a,b) if kind!='options' else [];r=report(rows,a,b,None if key in (None,'__all__') else key) if kind!='options' else None;data=dict(report=r,rows=rows[:1000] if kind=='history' else [],metrics=self.tracker.metrics(),categories=[*self.categories.keys(),*self.db.all_categories()]);self.inbox.put((req,data,None))
   except Exception as exc:self.log.event('statistics.failure','ERROR',exc=True,throttle='query');self.inbox.put((req,None,str(exc)))
  self.pool.submit(work)
 def render(self,req,data):
  self.ensure_categories(data['categories']);r=data['report'];kind,a,b,key=req
  if kind=='today':
   fill(self.today_tree,app_values(r));self.today_summary.set(f"Время приложений: {duration(r['total'])} | Хотя бы одно работало: {duration(r['overlap_free'])} | Сессий: {r['count']} | Работающих процессов: {r['active']}")
  elif kind=='history':
   fill(self.history_tree,app_values(r));fill(self.session_tree,[(x['display_name'],x['pid'],stamp(x['start']),stamp(x['end']),duration((x['end'] if x['end'] is not None else time.time())-x['start']),('~ ' if x['estimated'] else '')+(x['reason'] or 'open')) for x in data['rows']])
  elif kind=='stats':self.range_label.set(f"Период: {stamp(a)[:10]} — {stamp(b-1)[:10]}");self.category_views[key].render(r)
  m=data['metrics'];self.source_label.set('Источник: WMI' if m['source']=='WMI' else 'Источник: '+m['source']+' — завершения могут быть приблизительными; причина: '+m['source_reason']);state='Пауза обработки' if self.tracker.paused.is_set() else ('Работает' if self.tracker.running else 'Остановлен');self.status.set(state+' | '+datetime.now().strftime('Обновлено %H:%M:%S'));self.diagnostics.set(json.dumps(m,ensure_ascii=False))
 def tick(self):
  if self.exiting:return
  try:
   while True:
    cmd=self.commands.get_nowait()
    if isinstance(cmd,tuple):
     kind,value=cmd
     if kind=='diagnostics_ok':self.export_busy=False;messagebox.showinfo('Диагностика','TXT сохранён. Проверьте перед отправкой.\n'+value)
     elif kind=='diagnostics_error':self.export_busy=False;messagebox.showerror('Диагностика',value)
     elif kind=='categories_done':self.cache.clear();self.refresh(True)
     continue
    if cmd=='open':self.deiconify();self.lift()
    elif cmd=='pause':self.tracker.pause()
    elif cmd=='stop':self.stop()
    elif cmd=='exit':self.quit_app();return
    elif cmd=='ready':self.tray_ready=True
    elif cmd=='failed':self.tray_ready=False
  except queue.Empty:pass
  try:
   req,data,error=self.inbox.get_nowait();self.busy=False
   if error:self.status.set('Ошибка: '+error)
   else:
    self.cache[req]=(time.monotonic(),data)
    if len(self.cache)>32:self.cache.pop(next(iter(self.cache)))
    if req==self.request() and not self.dirty:self.render(req,data)
   if self.dirty:self.dirty=False;self.refresh()
  except queue.Empty:pass
  except Exception:self.log.event('ui.failure','ERROR',exc=True,throttle='render')
  self.after(200,self.tick)
 def periodic(self):
  if self.exiting:return
  if self.state()!='withdrawn':self.refresh(True)
  self.after(self.settings.get()['ui_refresh_seconds']*1000,self.periodic)
 def start(self):self.tracker.start();self.cache.clear();self.refresh(True)
 def stop(self):threading.Thread(target=self.tracker.stop,daemon=True).start();self.cache.clear()
 def save_config(self):
  try:self.settings.save(json.loads(self.editor.get('1.0','end')));self.cache.clear();messagebox.showinfo('Конфиг','Сохранено; применение до 2 секунд')
  except Exception as exc:messagebox.showerror('Конфиг',str(exc))
 def save_categories(self):
  try:
   rules=json.loads(self.cat_editor.get('1.0','end'))['rules'];self.categories.validate(rules);self.categories.save(rules)
   def update():
    try:self.db.rename_categories(self.categories);self.tracker.reset();self.commands.put(('categories_done',''))
    except Exception:self.log.event('storage.failure','ERROR',exc=True,phase='categories')
   self.pool.submit(update);self.cache.clear();self.ensure_categories(self.categories.keys())
  except Exception as exc:messagebox.showerror('Категории',str(exc))
 def export_report(self,r,name):
  if not r:messagebox.showinfo('CSV','Дождитесь загрузки отчёта');return
  path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile=name,filetypes=[('CSV','*.csv')])
  if not path:return
  headers=['Приложение','Категория','Время приложения, сек','Процессное время, сек','Сессий','Средняя сессия, сек','Доля, %','Активных','Начало','Конец'];rows=[(x['app'],x['category'],round(x['union_seconds'],3),round(x['seconds'],3),x['count'],round(x['average_seconds'],3),round(100*x['union_seconds']/r['total'],2) if r['total'] else 0,x['active'],stamp(x['first']),stamp(x['last'])) for x in r['apps']]
  try:export_csv(path,headers,rows)
  except Exception as exc:messagebox.showerror('CSV',str(exc))
 def export_category(self):
  data=self.cache.get(self.request());self.export_report(data[1]['report'] if data else None,'category-statistics.csv')
 def export_history(self):
  try:
   a,b=bounds(self.history_start.get(),self.history_end.get());data=self.cache.get(('history',a,b,None));self.export_report(data[1]['report'] if data else None,'history.csv')
  except ValueError as exc:messagebox.showerror('CSV',str(exc))
 def export_diagnostics(self):
  if self.export_busy:return
  mask=messagebox.askyesnocancel('Диагностика','Скрыть домашнюю папку и личные пути?\nДа — маскировка (рекомендуется).\nНет — полный текст.')
  if mask is None:return
  path=filedialog.asksaveasfilename(defaultextension='.txt',initialfile='tracker-diagnostics-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.txt',filetypes=[('TXT','*.txt')])
  if not path:return
  self.export_busy=True
  def export():
   try:write_report(path,self.base,self.settings,self.tracker,self.log,mask);self.commands.put(('diagnostics_ok',path))
   except Exception as exc:self.log.event('diagnostics.failure','ERROR',exc=True);self.commands.put(('diagnostics_error',str(exc)))
  self.pool.submit(export)
 def clear_history(self):
  if self.tracker.running:messagebox.showwarning('История','Сначала остановите трекер');return
  if messagebox.askyesno('Удаление','Удалить сессии? Реестр останется.'):
   self.db.clear_history();self.cache.clear();self.refresh(True)
 def tray_setup(self):
  try:
   import pystray
   from PIL import Image,ImageDraw
   image=Image.new('RGB',(64,64),'#18212b');ImageDraw.Draw(image).ellipse((12,12,52,52),fill='#28c985')
   def cb(cmd):return lambda icon,item:self.commands.put(cmd)
   self.tray=pystray.Icon('GST',image,'Game Session Tracker',pystray.Menu(pystray.MenuItem('Открыть',cb('open'),default=True),pystray.MenuItem('Пауза обработки',cb('pause')),pystray.MenuItem('Остановить',cb('stop')),pystray.MenuItem('Выход',cb('exit'))))
   def run():
    try:
     def setup(icon):icon.visible=True;self.commands.put('ready')
     self.tray.run(setup=setup)
    except Exception:self.log.event('tray.failure','WARNING',exc=True);self.commands.put('failed')
   threading.Thread(target=run,daemon=True).start()
  except Exception:self.log.event('tray.failure','WARNING',exc=True)
 def on_close(self):
  if self.settings.get()['minimize_to_tray'] and self.tray_ready:self.withdraw()
  else:self.quit_app()
 def quit_app(self):
  if self.exiting:return
  self.exiting=True;self.status.set('Сохранение и выход…')
  def stop():
   self.tracker.stop();self.pool.shutdown(wait=True)
   if self.tray:self.tray.stop()
   self.log.event('app.stop');self.log.flush()
  t=threading.Thread(target=stop,daemon=True);t.start()
  def wait():
   if t.is_alive():self.after(100,wait)
   else:self.destroy()
  wait()
