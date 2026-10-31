
import ctypes
import psutil

def identity(pid,start):return f'{pid}:{round(start*1000000)}'
def session_id(pid):
 n=ctypes.c_ulong()
 if not ctypes.windll.kernel32.ProcessIdToSessionId(pid,ctypes.byref(n)):raise OSError('ProcessIdToSessionId failed')
 return n.value

def metadata(pid):
 p=psutil.Process(pid)
 with p.oneshot():return dict(pid=pid,start=p.create_time(),name=p.name(),owner=p.username(),exe=p.exe())
