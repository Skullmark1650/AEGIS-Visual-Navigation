"""Controlled fresh validation with owned SSH connection fault and clean shutdown."""
import argparse,json,subprocess,socket,time,datetime
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--control',required=True,type=Path);p.add_argument('--recording',required=True,type=Path);p.add_argument('--experiment',default='phase8-v2-connection-final');a=p.parse_args();root=Path(__file__).resolve().parents[1];control=a.control.resolve();control.mkdir(parents=True,exist_ok=True);events=control/'events.jsonl';stop=control/'stop';request=control/'interrupt';assert not stop.exists() and not request.exists();client=None;tunnel=None;log=None
 def event(kind,**kw):
  with events.open('a') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic_s=time.monotonic(),event=kind,**kw))+'\n')
 def start_tunnel():
  nonlocal log
  log=(control/'tunnel.log').open('a');child=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=10','-L','127.0.0.1:8765:127.0.0.1:8765','aegis-pi'],stdout=subprocess.DEVNULL,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  for _ in range(50):
   if child.poll() is not None:raise RuntimeError('Owned SSH tunnel exited')
   try:
    with socket.create_connection(('127.0.0.1',8765),timeout=.1):return child
   except OSError:time.sleep(.1)
  child.terminate();child.wait(timeout=5);raise RuntimeError('Owned SSH tunnel did not listen')
 try:
  with socket.socket() as probe:
   if probe.connect_ex(('127.0.0.1',8765))==0:raise RuntimeError('Existing local forward; refusing to disturb it')
  subprocess.run(['ssh','aegis-pi','cd ~/AEGIS && .venv/bin/python pi/stream_control.py start'],check=True)
  tunnel=start_tunnel();report=root/'results/reports'/('connection-final-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json');event('started',tunnel_pid=tunnel.pid,report=str(report))
  client=subprocess.Popen([str(root/'.venv/Scripts/python.exe'),'laptop/camera_client.py','--duration','600','--features','none','--tracking','--dashboard','--odometry','results/calibration/phase4-reviewed-camera.json','--record-directory',str(a.recording),'--experiment',a.experiment,'--status-file',str(control/'live.json'),'--stop-file',str(stop),'--report',str(report)],cwd=root)
  fault_done=False
  while client.poll() is None:
   if request.exists() and not fault_done:
    event('disconnect_requested',old_pid=tunnel.pid);tunnel.terminate();tunnel.wait(timeout=5);event('owned_forward_closed');time.sleep(2);event('reconnect_requested');tunnel=start_tunnel();event('forward_listening',new_pid=tunnel.pid);fault_done=True
   time.sleep(.1)
  event('receiver_finished',exit_code=client.returncode)
 finally:
  if client is not None and client.poll() is None:
   stop.touch()
   try:client.wait(timeout=10)
   except subprocess.TimeoutExpired:client.terminate();client.wait(timeout=5);event('receiver_force_closed')
  if tunnel is not None and tunnel.poll() is None:tunnel.terminate();tunnel.wait(timeout=5)
  if log is not None:log.close()
  subprocess.run(['ssh','aegis-pi','cd ~/AEGIS && .venv/bin/python pi/stream_control.py stop'],check=True);event('cleanup_finished')
if __name__=='__main__':main()
