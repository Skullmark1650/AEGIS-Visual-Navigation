"""Live engineering dashboard: measured transport, estimated pose, illustrative path."""
import json
import math
import queue
import time
import statistics
import threading
import csv
from pathlib import Path
from datetime import datetime

def telemetry(rows, now, last_received, connection_status):
    recent=rows[-30:]
    fps=0.
    if len(recent)>1:
        span=recent[-1]['processed_elapsed_s']-recent[0]['processed_elapsed_s']
        if span>0:fps=(len(recent)-1)/span
    latest=recent[-1] if recent else {}
    stale=last_received is None or now-last_received>1.5
    pose=latest.get('vo_status','awaiting data')
    warnings=[]
    if stale:warnings.append('STALE FEED: displayed image/pose is historical')
    if connection_status!='LIVE':warnings.append('Connection: '+connection_status)
    if pose=='rotation_only':warnings.append('Rotation-compatible model; translation UNKNOWN, path disconnected')
    elif pose=='heading_relocalized':warnings.append('Original heading reference recovered; position and motion through the gap remain UNKNOWN')
    elif pose=='heading_relocalizing':warnings.append('Checking an earlier heading reference; no heading recovery accepted yet')
    elif pose=='relocalized':warnings.append('Previous map recovered; motion during the gap is unknown')
    elif pose not in ('accepted','map_tracking'):warnings.append('Pose: '+pose+'; no new accepted motion')
    if latest.get('vo_scale_mode')=='local_map':warnings.append('Local map units; scale is shared only within this map, meters unavailable')
    else:warnings.append('Path uses independent unit steps; distance and speed unavailable')
    return dict(fps=0. if stale else fps,stale=stale,latest=latest,warnings=warnings,
        producer_gaps=sum(r['sequence_gap'] for r in rows))

def recording_clock(elapsed,duration):
    elapsed=max(0.,elapsed)
    remaining=max(0,math.ceil(duration-elapsed))
    return f'Recording: {int(elapsed)//60:02d}:{int(elapsed)%60:02d} elapsed | {remaining//60:02d}:{remaining%60:02d} remaining'


def retain_path(state, row):
    """Archive disconnected segments without drawing fictitious joins."""
    segment=row.get('vo_segment')
    if segment!=state['segment']:
        if state['path']:
            state.setdefault('history',[]).append(state['path'])
            state['history']=state['history'][-20:]
            state.setdefault('history_origins',[]).append(state.get('origin',[0,0,0]))
            state['history_origins']=state['history_origins'][-20:]
        state['path']=[];state['segment']=segment;state['accepted_seen']=False;state['orientation_seen']=False
        state['origin']=json.loads(row.get('vo_segment_origin','[0,0,0]'))
    if row.get('vo_status') in ('accepted','rotation_only','map_tracking','relocalized','heading_relocalized'):state['orientation_seen']=True
    if row.get('vo_status') in ('accepted','map_tracking','relocalized'):
        state['path'].append(json.loads(row['vo_center_arbitrary']))
        state['accepted_seen']=True


def show_dashboard(receiver):
    import tkinter as tk
    from PIL import ImageTk
    root=tk.Tk();root.title('AEGIS - Live navigation dashboard')
    root.configure(bg='#0b1220');root.geometry('1160x760')
    root.minsize(850,600)
    fg='#dbeafe';muted='#8ca6c4';panel='#131f33'
    tk.Label(root,text='AEGIS  /  LIVE NAVIGATION',font=('Segoe UI',19,'bold'),fg=fg,bg='#0b1220').pack(anchor='w',padx=18,pady=10)
    tk.Label(root,text='Camera + calibrated visual odometry | research prototype',fg=muted,bg='#0b1220').pack(anchor='w',padx=18)
    countdown=tk.Label(root,text='',fg='#ffcf75',bg='#0b1220',font=('Consolas',12,'bold'))
    countdown.pack(anchor='w',padx=18,pady=(4,0))
    main=tk.Frame(root,bg='#0b1220');main.pack(fill='both',expand=True,padx=16,pady=12)
    main.columnconfigure(0,weight=3);main.columnconfigure(1,weight=2);main.rowconfigure(0,weight=1)
    left=tk.Frame(main,bg=panel);left.grid(row=0,column=0,sticky='nsew',padx=(0,10))
    tk.Label(left,text='LIVE CAMERA / TRACKED FEATURES + FLOW',fg=muted,bg=panel).pack(anchor='w',padx=10,pady=8)
    video=tk.Label(left,bg=panel);video.pack(expand=True,fill='both')
    right=tk.Frame(main,bg=panel);right.grid(row=0,column=1,sticky='nsew')
    values=tk.Label(right,fg=fg,bg=panel,font=('Consolas',11),justify='left',anchor='nw');values.pack(fill='x',padx=12,pady=10)
    canvas=tk.Canvas(right,bg='#0c1728',height=230,highlightthickness=0);canvas.pack(fill='both',expand=True,padx=10,pady=8)
    warnings=tk.Label(root,fg='#ffcf75',bg='#0b1220',justify='left',anchor='w',wraplength=1100);warnings.pack(fill='x',padx=18)
    buttons=tk.Frame(root,bg='#0b1220');buttons.pack(fill='x',padx=18,pady=10)
    state=dict(last_received=None,row=None,path=[],segment=None,refreshes=0,refresh_ms=[],consumed=0,accepted_seen=False)
    def close():
        receiver.stop.set();root.destroy()
    tk.Button(buttons,text='Stop camera and close',command=close,padx=15).pack(side='left')
    tk.Label(buttons,text='Reports saved automatically on close | Q to stop',fg=muted,bg='#0b1220').pack(side='right')
    analysis_results=queue.Queue()
    analysis_busy=[False]
    analysis_label=tk.Label(root,text='Analysis is on demand. Cloud button sends one selected frame and telemetry to OpenAI.',fg=muted,bg='#0b1220',wraplength=1100,anchor='w')
    analysis_label.pack(fill='x',padx=18,pady=(0,8))
    def diagnose(cloud=False):
        if analysis_busy[0]:return
        if not receiver.rows:
            analysis_label.configure(text='Wait for camera telemetry.');return
        if __package__:
            from .ai_assistant import summarize_csv,analyze,write_report,ROOT
        else:
            from ai_assistant import summarize_csv,analyze,write_report,ROOT
        rows=list(receiver.rows)
        image=getattr(receiver,'selected_frame',None)
        if image is not None:image=image.copy()
        analysis_busy[0]=True
        analysis_label.configure(text='Analyzing selected evidence in background...')
        def work():
            try:
                stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                source=ROOT/'results/reports'/('selected-'+stamp+'.csv')
                with source.open('x',newline='',encoding='utf-8') as file:
                    fields=sorted({k for r in rows for k in r})
                    writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader();writer.writerows(rows)
                diagnostics=summarize_csv(source,10)
                selected=None
                if cloud and image is not None:
                    selected=ROOT/'results/reports'/('selected-frame-'+stamp+'.png');image.save(selected)
                interpretation=analyze(diagnostics,selected) if cloud else None
                destination=ROOT/'results/reports'/('analysis-'+stamp)
                write_report(destination,diagnostics,interpretation)
                analysis_results.put('Saved '+str(destination/'report.md'))
            except Exception as exc:
                # Do not expose provider response bodies, request headers or credentials.
                if getattr(exc,'code',None) in {'credit_balance_exhausted','insufficient_quota'}:
                    analysis_results.put('OpenAI API credits are unavailable. Add API credits in the platform billing page; camera continues.')
                else:
                    analysis_results.put('Analysis failed ('+type(exc).__name__+'). Check API setup/limits; camera continues.')
        threading.Thread(target=work,daemon=True).start()
    tk.Button(buttons,text='Diagnose last 10 s (local)',command=lambda:diagnose(False)).pack(side='left',padx=8)
    tk.Button(buttons,text='Analyze frame (OpenAI upload)',command=lambda:diagnose(True)).pack(side='left')
    root.bind('q',lambda _:close());root.protocol('WM_DELETE_WINDOW',close)
    def refresh():
        started=time.perf_counter()
        countdown.configure(text=recording_clock(time.monotonic()-receiver.started,receiver.args.duration))
        try:
            analysis_label.configure(text=analysis_results.get_nowait());analysis_busy[0]=False
        except queue.Empty:pass
        try:
            image,row=receiver.latest.get_nowait();state['row']=row;state['last_received']=time.monotonic()
            # The VO renderer includes a small path panel; the dashboard owns its own path plot.
            if receiver.odometry:image=image.crop((0,0,image.width,image.height-220))
            image=image.copy();image.thumbnail((max(240,left.winfo_width()-12),max(180,left.winfo_height()-45)))
            photo=ImageTk.PhotoImage(image);video.configure(image=photo);video.image=photo
        except queue.Empty:pass
        pending=receiver.rows[state['consumed']:]
        state['consumed']+=len(pending)
        for row in pending:
            retain_path(state,row)
        data=telemetry(receiver.rows,time.monotonic(),state['last_received'],receiver.status)
        row=data['latest'];pose=row.get('vo_status','awaiting data')
        orientation='Origin; no accepted pose yet'
        if state.get('orientation_seen') and row.get('vo_orientation_camera_to_world'):
            R=json.loads(row['vo_orientation_camera_to_world'])
            # ZYX Euler decomposition of Rwc, radians -> degrees.
            pitch=math.asin(max(-1,min(1,-R[2][0])))
            roll=math.atan2(R[2][1],R[2][2]);yaw=math.atan2(R[1][0],R[0][0])
            orientation=f'X roll {math.degrees(roll):.1f} / Y pitch {math.degrees(pitch):.1f}\nZ yaw {math.degrees(yaw):.1f} deg'
        values.configure(text=f"{'STALE' if data['stale'] else receiver.status}  |  {data['fps']:.2f} processing FPS\nRetained tracks: {row.get('flow_tracked',0)} / {row.get('flow_attempted',0)}\nNew seeds: {row.get('flow_added',0)}  active: {row.get('flow_active',0)}\nTracking: {row.get('flow_status','awaiting data')}\nPose: {pose}\nSupport: {row.get('vo_inliers',0)}  parallax: {row.get('vo_parallax_deg',0):.2f} deg\n\nESTIMATED ORIENTATION / SEGMENT {state['segment']}\n{orientation}\n\nESTIMATED CAPTURE-TO-RECEIPT DELAY\n{row.get('estimated_capture_receive_ms',0):.1f} +/- {row.get('clock_uncertainty_ms',0):.1f} ms\n\nMEASURED TRANSPORT\nProducer gaps: {data['producer_gaps']}\nGUI queue skips: {receiver.display_skips}\nConnection errors: {receiver.errors}")
        warnings.configure(text=' | '.join(data['warnings']))
        canvas.delete('all');w=max(200,canvas.winfo_width());h=max(100,canvas.winfo_height())
        canvas.create_text(10,12,anchor='nw',text='X/Z LOCAL UNITS | gray: past segments, origins overlap',fill='#ffcf75')
        canvas.create_line(w/2,35,w/2,h-15,fill='#263954');canvas.create_line(15,h/2,w-15,h/2,fill='#263954')
        path=[state.get('origin',[0,0,0])]+state['path']
        all_points=path+[p for segment in state.get('history',[]) for p in segment]
        scale=min(w,h)*.35/max(1,max(abs(p[i]) for p in all_points for i in [0,2]))
        for index,segment in enumerate(state.get('history',[])):
            origin=state.get('history_origins',[[0,0,0]]*len(state.get('history',[])))[index]
            old=[(w/2+p[0]*scale,h/2+p[2]*scale) for p in [origin]+segment]
            if len(old)>1:canvas.create_line(*[v for p in old for v in p],fill='#61758e',width=1)
        pts=[(w/2+p[0]*scale,h/2+p[2]*scale) for p in path]
        if len(pts)>1:canvas.create_line(*[v for p in pts for v in p],fill='#5de4c7',width=2)
        x,y=pts[-1];canvas.create_oval(x-3,y-3,x+3,y+3,fill='#ffcf75')
        state['refreshes']+=1;state['refresh_ms'].append((time.perf_counter()-started)*1000)
        receiver.dashboard_stats={'refreshes':state['refreshes'],'mean_refresh_ms':statistics.mean(state['refresh_ms']),'max_refresh_ms':max(state['refresh_ms'])}
        if receiver.stop.is_set():root.after(100,root.destroy)
        else:root.after(50,refresh)
    root.after(100,refresh);root.mainloop()
