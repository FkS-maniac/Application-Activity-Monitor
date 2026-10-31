
import ttkbootstrap as tb
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.categories import BASE_CATEGORIES
from src.utils.time_utils import duration
HEADERS=['Приложение','Категория','Время приложения','Процессное время','Сессий','Средняя сессия','Доля','Работает']
def table(parent,headers,height=10):
 box=tb.Frame(parent);box.pack(fill='both',expand=True,pady=4);tree=tb.Treeview(box,columns=[str(i) for i in range(len(headers))],show='headings',height=height)
 for i,label in enumerate(headers):tree.heading(str(i),text=label,command=lambda c=str(i):sort_table(tree,c));tree.column(str(i),width=160,minwidth=65)
 sy=tb.Scrollbar(box,command=tree.yview);sy.pack(side='right',fill='y');sx=tb.Scrollbar(box,orient='horizontal',command=tree.xview);sx.pack(side='bottom',fill='x');tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);tree.pack(fill='both',expand=True);return tree

def sort_table(tree,col):
 def key(item):
  text=tree.set(item,col)
  try:
   if text.count(':')==2 and '-' not in text:return (0,sum(int(v)*m for v,m in zip(text.split(':'),(3600,60,1))))
   return (0,float(text.rstrip('%')))
  except ValueError:return (1,text.casefold())
 rev=getattr(tree,'reverse_sort',False)
 for pos,item in enumerate(sorted(tree.get_children(),key=key,reverse=rev)):tree.move(item,'',pos)
 tree.reverse_sort=not rev

def fill(tree,rows):
 children=tree.get_children()
 if children:tree.delete(*children)
 for r in rows:tree.insert('','end',values=r)

def app_values(r):return [(a['app'],BASE_CATEGORIES.get(a['category'],a['category']),duration(a['union_seconds']),duration(a['seconds']),a['count'],duration(a['average_seconds']),f"{100*a['union_seconds']/r['total']:.1f}%" if r['total'] else '0.0%',a['active']) for a in r['apps']]

class CategoryStats(tb.Frame):
 def __init__(self,parent,key):
  super().__init__(parent,padding=5);self.key=key;self.summary=tb.StringVar();tb.Label(self,textvariable=self.summary,wraplength=1180,padding=6).pack(fill='x');self.figure=Figure(figsize=(10,3),dpi=90);self.canvas=FigureCanvasTkAgg(self.figure,master=self);self.canvas.get_tk_widget().pack(fill='both',expand=True);self.tree=table(self,HEADERS,height=7)
 def render(self,r):
  self.summary.set(f"Приложений: {len(r['apps'])} | Сессий: {r['count']} | Работает: {r['active']} | Время приложений: {duration(r['total'])} | Хотя бы одно: {duration(r['overlap_free'])} | Процессное: {duration(r['process_seconds'])} | Доля общего: {r['share']:.1f}%")
  fill(self.tree,app_values(r));self.figure.clear();overview=self.key=='__all__';a=self.figure.add_subplot(131 if overview else 121);b=self.figure.add_subplot(132 if overview else 122)
  if r['apps']:
   days=[d[0][5:] for d in r['daily']];a.bar(range(len(days)),[d[1]/3600 for d in r['daily']],color='#2ecc71');step=max(1,len(days)//8);ticks=list(range(0,len(days),step));a.set_xticks(ticks,[days[i] for i in ticks],rotation=30);top=r['apps'][:10];b.barh([v['app'][:30] for v in reversed(top)],[v['union_seconds']/3600 for v in reversed(top)],color='#4dabf7')
  else:
   for ax in (a,b):ax.text(.5,.5,'Нет данных за период',ha='center',va='center',transform=ax.transAxes)
  a.set_title('По дням');a.set_ylabel('Часы');b.set_title('Топ приложений');b.set_xlabel('Часы')
  if overview:
   c=self.figure.add_subplot(133);v=r['categories']
   if v:c.barh([BASE_CATEGORIES.get(k,k) for k in v],[x/3600 for x in v.values()],color='#f0ad4e')
   else:c.text(.5,.5,'Нет данных',ha='center',va='center',transform=c.transAxes)
   c.set_title('Категории');c.set_xlabel('Часы')
  self.figure.tight_layout();self.canvas.draw_idle()
