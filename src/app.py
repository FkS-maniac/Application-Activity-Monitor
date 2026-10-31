
import ctypes
import sys
from pathlib import Path
from src.settings import Settings
from src.categories import Categories
from src.database import Database
from src.tracker import SessionTracker
from src.utils.logger import LogService

_MUTEX=None

def run_app():
 global _MUTEX
 if sys.platform!='win32':raise SystemExit('Требуется Windows 10/11')
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.restype=ctypes.c_void_p;kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
 _MUTEX=kernel.CreateMutexW(None,0,'Local\\GameSessionTrackerRC1')
 if not _MUTEX:raise OSError('Не удалось создать mutex')
 if ctypes.get_last_error()==183:
  kernel.CloseHandle(_MUTEX);ctypes.windll.user32.MessageBoxW(None,'Приложение уже запущено. Проверьте трей.','Game Session Tracker',0);return
 base=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
 log=LogService(base);log.install_hooks();log.event('app.start',version='1.0.0-rc.1',python=sys.version.split()[0])
 try:
  from src.ui.main_window import MainWindow
  settings=Settings(base/'config_v2.json');log.set_level(settings.get()['log_level']);categories=Categories(base/'categories.json');path=Path(settings.get()['database'])
  if not path.is_absolute():path=base/path
  path.parent.mkdir(parents=True,exist_ok=True);db=Database(path);tracker=SessionTracker(db,categories,settings,log);MainWindow(db,categories,settings,tracker,base,log).mainloop()
 except Exception:log.event('exception.unhandled','ERROR',exc=True,phase='startup');log.flush();raise
 finally:kernel.CloseHandle(_MUTEX)
