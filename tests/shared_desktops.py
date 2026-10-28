#!/usr/bin/env python3
"""Nested integration for hyprexpo + virtual-desktops. No parent output/input changes."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
expo=str(Path(sys.argv[1]).resolve())
vdesk=str(Path(sys.argv[2]).resolve())
mode=sys.argv[3] if len(sys.argv)>3 else 'monitors'
root=Path(tempfile.mkdtemp(prefix='hyprexpo-shared-test-'))
config=root/'test.lua'
config.write_text('''hl.monitor({output="",mode="800x600@60",position="auto",scale=1})
hl.config({debug={disable_logs=false},animations={enabled=true},cursor={no_warps=false,warp_on_change_workspace=1,hide_on_key_press=true}})
if hl.plugin.virtual_desktops then hl.config({plugin={virtual_desktops={cycleworkspaces=0,notifyinit=0,rememberlayout="'''+mode+'''",monitor_order="WAYLAND-1,VTEST-2,VTEST-3",names="1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8,9:9"}}}) end
if hl.plugin.hyprexpo then hl.config({plugin={hyprexpo={virtual_desktops=1,overview_mode="grid",columns=3,rows=3,dynamic_grid=0,keynav_enable=0,max_workspace=9,label_enable=1,label_text_mode="id",wallpaper_bg=1}}}) end
''')
env=os.environ.copy();env.update(AQ_DRM_DEVICES='/dev/null',HYPRLAND_NO_SD_VARS='1',HYPRLAND_NO_SD_NOTIFY='1',HYPRLAND_NO_RT='1')
log=(root/'compositor.log').open('w')
p=subprocess.Popen(['Hyprland','--config',str(config)],env=env,stdout=log,stderr=subprocess.STDOUT)
try:
 instance=None
 for _ in range(100):
  if p.poll() is not None:raise RuntimeError('nested exited: '+str(root))
  instances=json.loads(subprocess.check_output(['hyprctl','instances','-j']))
  instance=next((i['instance'] for i in instances if i['pid']==p.pid),None)
  if instance:break
  time.sleep(.1)
 assert instance
 nested_env=env.copy()
 nested_env["WAYLAND_DISPLAY"]=next(i["wl_socket"] for i in instances if i["pid"]==p.pid)
 assert nested_env["WAYLAND_DISPLAY"] != env.get("WAYLAND_DISPLAY"), "Refuse to inject into parent"
 def key(name):subprocess.run(["wtype","-k",name],env=nested_env,check=True,timeout=5)
 def ctl(*args):
  r=subprocess.run(['hyprctl','-i',instance,*args],capture_output=True,text=True)
  if r.returncode or r.stdout.startswith('error'):raise RuntimeError((args,r.stdout,r.stderr,str(root)))
  return r.stdout
 def q(cmd):return json.loads(ctl('-j',cmd))
 def lua(code):
  result=ctl('eval',code)
  assert result.strip()=='ok',result
 def desk(n):lua('hl.plugin.virtual_desktops.vdesk("'+str(n)+'")')
 def ex(command):lua('hl.plugin.hyprexpo.expo('+json.dumps(command)+')')
 def state():return q('hyprexpostate')['sessions']
 def wait_closed():
  for _ in range(60):
   if not state():return
   time.sleep(.05)
  raise AssertionError(('overview not closed',state()))
 def membership():return {w['address']:(w['workspace']['id'],w['monitor']) for w in q('clients')}
 for _ in range(50):
  if q('monitors'):break
  time.sleep(.1)
 primary=q('monitors')[0]['name']
 ctl('output','create','headless','VTEST-2');time.sleep(.3)
 ctl('plugin','load',vdesk)
 ctl('plugin','load',expo)
 assert not ctl('configerrors').strip()
 # Malformed bridge commands must fail without changing the active desktop.
 for arg in ('snapshot 0','snapshot 65','select -1','select 2 garbage'):
  assert 'error' in subprocess.run(['hyprctl','-i',instance,'vdeskoverview',arg],capture_output=True,text=True).stdout
 expected={}
 for n,output in ((1,primary),(1,'VTEST-2'),(2,primary),(3,'VTEST-2')):
  desk(n);ctl('dispatch','hl.dsp.focus({monitor='+json.dumps(output)+'})')
  before=set(membership())
  command = "foot --app-id=SHARED-OVERVIEW-TEST -- /usr/bin/bash -c 'for i in {1..1000}; do printf x; sleep .2; done'" if os.getenv('HYPREXPO_TEST_LIVE') and n == 2 else 'foot --app-id=SHARED-OVERVIEW-TEST -- /usr/bin/sleep 300'
  lua('hl.exec_cmd('+json.dumps(command)+')')
  for _ in range(50):
   added=set(membership())-before
   if added:break
   time.sleep(.1)
  assert len(added)==1
  expected[added.pop()]=n
 desk(1)
 original=membership()
 def verify_open(stage):
  before=membership()
  active={m['id']:m['activeWorkspace']['id'] for m in q('monitors')}
  ex('toggle');time.sleep(.6)
  sessions=state();assert len(sessions)==len(active),(stage,sessions)
  layouts={d['id']:set(d['workspaces']) for d in q('printstate')}
  seen=set()
  for s in sessions:
   assert s['shared'] and not s['closing'] and len(s['tiles'])==9,(stage,s)
   for tile in s['tiles']:
    wid=tile['workspace'];assert wid not in seen,(stage,'duplicate tile')
    seen.add(wid);assert wid in layouts[tile['desktop']],(stage,'wrong logical desktop',tile)
    ws=next((w for w in q('workspaces') if w['id']==wid),None)
    if ws:assert ws['monitorID']==s['monitor'],(stage,'foreign monitor preview',tile,ws)
    windows=sum(1 for a,(w,m) in membership().items() if m==s['monitor'] and w==wid)
    assert windows==tile['windows'] and tile['captured'],(stage,'bad preview',tile,windows)
  assert before==membership(),(stage,'opening moved windows')
  assert active=={m['id']:m['activeWorkspace']['id'] for m in q('monitors')},(stage,'opening selected workspace')
  return sessions
 def assert_desk(n):
  current=next(d for d in q('printstate') if d['focused'])
  assert current['id']==n,current
  assert {m['activeWorkspace']['id'] for m in q('monitors')}==set(current['workspaces'])
 def choose(n):lua('hl.plugin.hyprexpo.kb_selectn('+str(n)+')');wait_closed();assert_desk(n)
 verify_open('two outputs')
 subprocess.run(['grim','-o',primary,str(root/'overview.png')],env=nested_env,check=True,timeout=10)
 if os.getenv('HYPREXPO_TEST_LIVE'):
  for label in ('before','after'):
   time.sleep(1)
   path=root/(label+'.png')
   subprocess.run(['grim','-o',primary,str(path)],env=nested_env,check=True,timeout=10)
   subprocess.run(['magick',str(path),'-crop','266x200+267+0','+repage',str(root/(label+'-tile.png'))],check=True)
  comparison=subprocess.run(['magick','compare','-metric','AE',str(root/'before-tile.png'),str(root/'after-tile.png'),'null:'],capture_output=True,text=True)
  assert float(comparison.stderr.split()[0])>0,('Inactive preview frozen',comparison.stderr,root)
  print('PASS live inactive preview: changed pixels',comparison.stderr.strip(),flush=True)
 print('PASS',mode,'two outputs; screenshot',root/'overview.png',flush=True)
 ex('cancel');wait_closed();assert_desk(1)
 verify_open('keyboard navigation')
 lua('hl.plugin.hyprexpo.kb_focus("right")')
 assert {s['focusedDesktop'] for s in state()}=={2},state()
 lua('hl.plugin.hyprexpo.kb_confirm()');wait_closed();assert_desk(2)
 verify_open('native keyboard')
 key('Right');assert {s['focusedDesktop'] for s in state()}=={3},state()
 key('Return');wait_closed();assert_desk(3)
 verify_open('raw digit');key('9');wait_closed();assert_desk(9)
 verify_open('raw escape');key('Escape');wait_closed();assert_desk(9)
 verify_open('empty desk');choose(9);assert original==membership()
 verify_open('return');choose(1)
 # Programmatic native drag helper also uses the correct per-monitor workspace.
 verify_open('drag between shared desks')
 window=next(a for a,(w,m) in membership().items() if w==next(t['workspace'] for ss in state() if ss['monitor']==q('activewindow')['monitor'] for t in ss['tiles'] if t['desktop']==1))
 lua('hl.plugin.hyprexpo.move_window('+json.dumps('1 2 '+window)+')')
 assert membership()[window][0] in next(d['workspaces'] for d in q('printstate') if d['id']==2)
 lua('hl.plugin.hyprexpo.move_window('+json.dumps('2 1 '+window)+')')
 assert original==membership()
 ex('cancel');wait_closed()
 # Changes in monitor topology must close the stale grid before the next snapshot.
 for n in range(2):
  verify_open('before unplug '+str(n));ctl('output','remove','VTEST-2');time.sleep(.3);assert not state()
  verify_open('one output '+str(n));choose(2)
  ctl('output','create','headless','VTEST-2');time.sleep(.3)
  verify_open('reconnect '+str(n));choose(1)
 ctl('output','create','headless','VTEST-3');time.sleep(.3)
 verify_open('three outputs');choose(3)
 verify_open('reload while open');ctl('reload');time.sleep(.3)
 ex('cancel');wait_closed()
 verify_open('after reload');choose(1)
 # Every original window stays on the logical desktop it started on.
 layouts={d['id']:set(d['workspaces']) for d in q('printstate')}
 assert set(expected)==set(membership())
 assert all(wid in layouts[expected[a]] for a,(wid,_) in membership().items())
 assert not ctl('configerrors').strip()
 ctl('plugin','unload',vdesk)
 failed=subprocess.run(['hyprctl','-i',instance,'eval','hl.plugin.hyprexpo.expo("toggle")'],capture_output=True,text=True).stdout
 assert 'required' in failed and not state(),failed
 print('PASS',mode,'per-monitor previews, 1–9, synchronized focus/selection, cancel, empty desk, 2→1→2→3, reload, window ownership',flush=True)
except Exception:
 if p.poll() is None:
  try:(root/'rolling.log').write_text(ctl('rollinglog'))
  except Exception:pass
 print('Diagnostics:',root,flush=True)
 raise
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 log.close()
