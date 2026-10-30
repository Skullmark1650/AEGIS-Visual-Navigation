"""Render the actual dashboard using synthetic input; no camera, network, or API."""
import argparse
import json
import queue
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laptop.navigation_dashboard import show_dashboard

def main():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshot', type=Path, help='Save only this application window, then close (Windows)')
    args = parser.parse_args()
    scene = Image.new('RGB', (640, 480), '#dedede')
    draw = ImageDraw.Draw(scene)
    for row in range(7):
        for col in range(10):
            x, y = 105+col*40, 95+row*40
            draw.rectangle((x,y,x+39,y+39), fill='white' if (row+col)%2 else '#252525')
            if row and col:
                draw.ellipse((x-2,y-2,x+2,y+2), fill='#00aa77')
                draw.line((x,y,x+8,y+2), fill='#00aa77', width=2)
    draw.rectangle((0,0,639,48), fill='#142338')
    draw.text((16,16), 'SYNTHETIC OFFLINE DEMO - NOT MEASURED CAMERA DATA', fill='white')
    row = dict(processed_elapsed_s=0,sequence_gap=0,vo_status='map_tracking',
               vo_segment=1,vo_scale_mode='local_map',vo_center_arbitrary='[0,0,0]',
               vo_orientation_camera_to_world=json.dumps([[1,0,0],[0,1,0],[0,0,1]]),
               flow_tracked=54,flow_attempted=60,flow_added=6,flow_active=60,
               flow_status='tracking',vo_inliers=50,vo_parallax_deg=1.2)
    rows=[]
    for i in range(30):
        item=dict(row,processed_elapsed_s=i/15,vo_center_arbitrary=json.dumps([i*.015,0,i*.005]))
        rows.append(item)
    receiver=SimpleNamespace(stop=threading.Event(), latest=queue.Queue(), rows=rows,
                             status='OFFLINE DEMO', odometry=None, started=time.monotonic(),
                             args=SimpleNamespace(duration=3600), display_skips=0, errors=0)
    receiver.latest.put((scene,row))
    if args.screenshot:
        import tkinter as tk
        from PIL import ImageGrab
        original=tk.Tk
        def window(*a,**kw):
            root=original(*a,**kw)
            root.tk.call('tk', 'scaling', 1.0)
            def capture():
                root.update_idletasks()
                root.lift()
                root.update()
                x,y=root.winfo_rootx(),root.winfo_rooty()
                args.screenshot.parent.mkdir(parents=True,exist_ok=True)
                ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height())).save(args.screenshot)
                receiver.stop.set()
                root.destroy()
            root.after(1100,capture)
            return root
        tk.Tk=window
    show_dashboard(receiver)

if __name__=='__main__':
    main()
