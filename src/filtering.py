
OS_BACKGROUND={'svchost.exe','runtimebroker.exe','textinputhost.exe','taskhostw.exe','sihost.exe','shellexperiencehost.exe','startmenuexperiencehost.exe','searchhost.exe','shellhost.exe','applicationframehost.exe','ctfmon.exe','conhost.exe','smartscreen.exe','securityhealthsystray.exe','useroobebroker.exe'}

def prefilter(pid,name,sid,c,own=False):
 name=name.casefold();allowed=name in {v.casefold() for v in c['allowlist']}
 if pid in (0,4):return 'kernel_pid'
 if own and c['exclude_self_and_children']:return 'own_process'
 if sid is not None:
  if sid in c['excluded_session_ids']:return 'excluded_session'
 if c['mode']!='all_user_apps' and not allowed:return 'allowlist'
 if c['exclude_os_background'] and name in OS_BACKGROUND and not allowed:return 'os_background'
 if c['mode']!='strict' and name in {x.casefold() for x in c['excluded_processes']}:return 'excluded_name'
 return None
