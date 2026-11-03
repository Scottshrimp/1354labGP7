"""Rhythm Chart Studio — standalone tap-note editor for Rhythm Hold v4.1.
Python 3.10+; ffmpeg and pygame optional until audio is loaded/played.
"""
import copy
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import wave
import io
import array
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

DIRS=('UP','RIGHT','DOWN','LEFT')
MARKS=('↑','→','↓','←')
LANE_COLORS=('#7bcaf1','#9cddaa','#edbd7e','#c5a1f0')
LEFT=90
TOP=110
STEP=54

class Studio:
    def __init__(self, root):
        self.root=root
        root.title('Rhythm Chart Studio — Tap Only')
        root.geometry('1190x740')
        root.minsize(800,510)
        self.notes=[]
        self.chart_path=None
        self.temp=None
        self.peaks=[]
        self.duration=156565
        self.bpm=tk.StringVar(value='92')
        self.title=tk.StringVar(value='Untitled')
        self.snap=tk.BooleanVar(value=True)
        self.subdivision=tk.StringVar(value='1/4')
        self.offset=tk.StringVar(value='0')
        self.time_input=tk.StringVar(value='0')
        self.selected=None
        self.dirty=False
        self.undo_stack=[]
        self.redo_stack=[]
        self.zoom=15_000
        self.view_start=0
        self.cursor=0
        self.dragging=False
        self.panning=False
        self.pan_x=0
        self.pan_start=0
        self.playing=False
        self.play_started=0.0
        self.play_offset=0
        self.pcm_data=None
        self.sample_rate=44100
        self.channel=None
        self.active_sound=None
        self.paused=False
        self.status=tk.StringVar(value='Open a chart and/or import AAC.  Double-click lane to add a note.')
        self._build()
        self.redraw()
        root.after(40,self.tick)
        root.protocol('WM_DELETE_WINDOW',self.close)

    def _build(self):
        bar=ttk.Frame(self.root,padding=7);bar.pack(fill='x')
        for name,cmd in [('Open Chart',self.open_chart),('Import Audio',self.import_audio),('Save',self.save),('Save As',self.save_as),('Undo',self.undo),('Redo',self.redo),('Delete',self.delete)]:
            ttk.Button(bar,text=name,command=cmd).pack(side='left',padx=2)
        info=ttk.Frame(self.root,padding=(10,3));info.pack(fill='x')
        ttk.Label(info,text='Title').pack(side='left')
        ttk.Entry(info,textvariable=self.title,width=21).pack(side='left',padx=(4,13))
        ttk.Label(info,text='BPM').pack(side='left')
        ttk.Entry(info,textvariable=self.bpm,width=7).pack(side='left',padx=4)
        ttk.Checkbutton(info,text='Snap',variable=self.snap).pack(side='left',padx=5)
        ttk.Combobox(info,textvariable=self.subdivision,values=('1','1/2','1/4','1/8','1/16'),width=6,state='readonly').pack(side='left')
        ttk.Label(info,text='Grid offset ms').pack(side='left',padx=(16,4))
        ttk.Entry(info,textvariable=self.offset,width=8).pack(side='left')
        ttk.Label(info,text='Selected time ms').pack(side='left',padx=(16,4))
        ttk.Entry(info,textvariable=self.time_input,width=10).pack(side='left')
        ttk.Button(info,text='Move Note',command=self.move_selected).pack(side='left',padx=3)
        controls=ttk.Frame(self.root,padding=(10,4));controls.pack(fill='x')
        ttk.Button(controls,text='▶ Play / Pause',command=self.toggle).pack(side='left')
        ttk.Button(controls,text='■ Stop',command=self.stop).pack(side='left',padx=4)
        ttk.Button(controls,text='◀ 5s',command=lambda:self.seek(self.cursor-5000)).pack(side='left',padx=3)
        ttk.Button(controls,text='5s ▶',command=lambda:self.seek(self.cursor+5000)).pack(side='left',padx=3)
        ttk.Button(controls,text='Zoom In',command=lambda:self.set_zoom(self.zoom/1.7)).pack(side='left',padx=(18,2))
        ttk.Button(controls,text='Zoom Out',command=lambda:self.set_zoom(self.zoom*1.7)).pack(side='left',padx=2)
        addbar=ttk.Frame(self.root,padding=(10,3));addbar.pack(fill='x')
        ttk.Label(addbar,text='Add Tap at playhead:').pack(side='left',padx=(0,8))
        for symbol,d in zip(MARKS,DIRS):
            ttk.Button(addbar,text=symbol+'  '+d.title(),command=lambda direction=d:self.add(self.cursor,direction)).pack(side='left',padx=3)
        ttk.Label(addbar,text='Keyboard ↑ → ↓ ← also adds notes · Space = play/pause').pack(side='left',padx=15)
        ttk.Label(controls,text='Double-click to add · Click to select · Drag note to move · Right-drag to pan · Wheel to zoom').pack(side='left',padx=15)
        self.canvas=tk.Canvas(self.root,bg='#111924',highlightthickness=0,cursor='crosshair')
        self.canvas.pack(fill='both',expand=True,padx=10,pady=5)
        self.canvas.bind('<Configure>',lambda e:self.redraw())
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<B1-Motion>',self.drag)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Double-Button-1>',self.double_click)
        self.canvas.bind('<Button-3>',self.right_down)
        self.canvas.bind('<B3-Motion>',self.right_drag)
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.canvas.bind('<Button-4>',lambda e:self.set_zoom(self.zoom/1.2,e.x))
        self.canvas.bind('<Button-5>',lambda e:self.set_zoom(self.zoom*1.2,e.x))
        self.progress=tk.Scale(self.root,from_=0,to=self.duration,orient='horizontal',showvalue=False,resolution=1)
        self.progress.pack(fill='x',padx=10)
        self.progress.bind('<ButtonRelease-1>',self.slider_released)
        ttk.Label(self.root,textvariable=self.status,padding=8).pack(fill='x')
        self.root.bind('<Control-s>',lambda e:self.save())
        self.root.bind('<Control-Shift-S>',lambda e:self.save_as())
        self.root.bind('<Control-z>',lambda e:self.undo())
        self.root.bind('<Control-y>',lambda e:self.redo())
        self.root.bind('<Delete>',lambda e:self.delete())
        self.root.bind('<space>',self.space)
        for key,d in [('Up','UP'),('Right','RIGHT'),('Down','DOWN'),('Left','LEFT')]:
            self.root.bind('<'+key+'>',lambda e,di=d:self.key_add(e,di))
        for key,d in [('u','UP'),('r','RIGHT'),('d','DOWN'),('l','LEFT')]:
            self.root.bind(key,lambda e,di=d:self.key_add(e,di))

    def eligible(self,event):
        return not isinstance(event.widget,(ttk.Entry,tk.Entry,ttk.Combobox))
    def space(self,event):
        if self.eligible(event):self.toggle()
    def key_add(self,event,d):
        if self.eligible(event):self.add(self.cursor,d)
    def confirm_unsaved(self):
        return not self.dirty or messagebox.askyesno('Unsaved changes','Discard unsaved chart changes?')
    def history(self):
        self.undo_stack.append(copy.deepcopy(self.notes))
        if len(self.undo_stack)>70:self.undo_stack.pop(0)
        self.redo_stack.clear()
    def changed(self):
        self.dirty=True
        self.redraw()
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.notes))
            self.notes=self.undo_stack.pop();self.selected=None;self.changed()
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.notes))
            self.notes=self.redo_stack.pop();self.selected=None;self.changed()
    def validate_note(self,n):
        d=str(n['direction']).upper()
        if d not in DIRS:raise ValueError('Unsupported direction: '+d)
        t=int(n['time_ms'])
        if t<0:raise ValueError('Negative note timestamp')
        return {'time_ms':t,'direction':d}
    def load(self,path):
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict) or not isinstance(data.get('notes'),list):
            raise ValueError('Expected JSON object containing a notes list')
        rows=[self.validate_note(n) for n in data['notes']]
        rows.sort(key=lambda n:n['time_ms'])
        duration=max(1,int(data.get('duration_ms',self.duration)),max([n['time_ms'] for n in rows],default=0)+1000)
        bpm=float(data.get('bpm',92))
        if not math.isfinite(bpm) or bpm<=0:raise ValueError('BPM must be positive')
        self.stop();self.notes=rows;self.duration=duration;self.bpm.set(str(bpm).rstrip('0').rstrip('.') if '.' in str(bpm) else str(bpm))
        self.title.set(str(data.get('title',Path(path).stem)))
        self.chart_path=Path(path);self.selected=None;self.dirty=False
        self.undo_stack.clear();self.redo_stack.clear();self.seek(0)
        self.progress.config(to=self.duration)
        self.status.set('Loaded '+str(self.chart_path)+' · '+str(len(rows))+' notes')
        self.redraw()
    def open_chart(self):
        if not self.confirm_unsaved():return
        name=filedialog.askopenfilename(filetypes=[('Rhythm Hold JSON','*.json')])
        if name:
            try:self.load(name)
            except Exception as e:messagebox.showerror('Open failed',str(e))
    def serialize(self):
        try:bpm=float(self.bpm.get())
        except ValueError:raise ValueError('Invalid BPM')
        if not math.isfinite(bpm) or bpm<=0:raise ValueError('BPM must be greater than 0')
        return {'title':self.title.get(),'duration_ms':int(self.duration),'bpm':bpm,
                'notes':sorted([self.validate_note(n) for n in self.notes],key=lambda n:n['time_ms'])}
    def save(self):
        if not self.chart_path:return self.save_as()
        try:
            doc=self.serialize()
            # Atomic replace; no backup destruction before serialization succeeds.
            temp=self.chart_path.with_name(self.chart_path.name+'.tmp')
            temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            os.replace(temp,self.chart_path)
            self.dirty=False;self.redraw();self.status.set('Saved '+str(self.chart_path))
        except Exception as e:messagebox.showerror('Save failed',str(e))
    def save_as(self):
        name=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Rhythm Hold JSON','*.json')],initialfile='chart.json')
        if name:self.chart_path=Path(name);self.save()
    def ms(self):
        return max(0,min(self.duration,int(self.cursor)))
    def snap_ms(self,t):
        if not self.snap.get():return int(round(t))
        try:
            bpm=float(self.bpm.get());division=int(self.subdivision.get().split('/')[1]) if '/' in self.subdivision.get() else 1
            offset=float(self.offset.get())
            if bpm<=0:return round(t)
            step=60000/bpm/division
            return max(0,int(round(offset+round((t-offset)/step)*step)))
        except (ValueError,ZeroDivisionError):return round(t)
    def add(self,t,d):
        self.history()
        n={'time_ms':max(0,self.snap_ms(t)),'direction':d}
        self.notes.append(n);self.notes.sort(key=lambda a:a['time_ms'])
        self.selected=n;self.changed()
    def delete(self):
        if self.selected is not None and self.selected in self.notes:
            self.history();self.notes.remove(self.selected);self.selected=None;self.changed()
    def move_selected(self):
        if self.selected is None:return
        try:t=int(self.time_input.get())
        except ValueError:
            messagebox.showerror('Invalid time','Enter a time in milliseconds');return
        self.history();self.selected['time_ms']=max(0,self.snap_ms(t));self.notes.sort(key=lambda a:a['time_ms']);self.changed()

    def x_for(self,t):
        return LEFT+(t-self.view_start)/self.zoom*self.plot_width()
    def t_for(self,x):
        return max(0,min(self.duration,int(self.view_start+(x-LEFT)/self.plot_width()*self.zoom)))
    def plot_width(self):return max(1,self.canvas.winfo_width()-LEFT-20)
    def lane(self,y):
        n=round((y-TOP)/STEP)
        return n if 0<=n<4 and abs(y-(TOP+n*STEP))<=20 else None
    def nearest(self,x,y):
        lane=self.lane(y)
        if lane is None:return None
        matches=[n for n in self.notes if n['direction']==DIRS[lane] and abs(self.x_for(n['time_ms'])-x)<10]
        return min(matches,key=lambda n:abs(self.x_for(n['time_ms'])-x)) if matches else None
    def click(self,e):
        self.selected=self.nearest(e.x,e.y)
        self.dragging=bool(self.selected)
        if self.selected:self.time_input.set(str(self.selected['time_ms']))
        else:self.seek(self.t_for(e.x),playing_restart=False)
        self.redraw()
    def drag(self,e):
        if self.selected and self.dragging:
            # Preview dragging without accumulating undo entries.
            if not hasattr(self,'drag_snapshot'):
                self.history();self.drag_snapshot=True
            self.selected['time_ms']=self.snap_ms(self.t_for(e.x))
            self.time_input.set(str(self.selected['time_ms']))
            self.changed()
    def release(self,e):
        self.dragging=False
        if hasattr(self,'drag_snapshot'):del self.drag_snapshot
        self.notes.sort(key=lambda n:n['time_ms'])
    def double_click(self,e):
        lane=self.lane(e.y)
        if lane is not None:self.add(self.t_for(e.x),DIRS[lane])
    def right_down(self,e):self.panning=True;self.pan_x=e.x;self.pan_start=self.view_start
    def right_drag(self,e):
        if self.panning:
            self.view_start=max(0,min(max(0,self.duration-self.zoom),int(self.pan_start-(e.x-self.pan_x)/self.plot_width()*self.zoom)))
            self.redraw()
    def wheel(self,e):self.set_zoom(self.zoom/(1.2 if e.delta>0 else 1/1.2),e.x)
    def set_zoom(self,z,anchor_x=None):
        anchor_x=anchor_x if anchor_x is not None else LEFT+self.plot_width()/2
        t=self.t_for(anchor_x)
        self.zoom=max(1000,min(max(1000,self.duration),int(z)))
        self.view_start=max(0,min(max(0,self.duration-self.zoom),int(t-(anchor_x-LEFT)/self.plot_width()*self.zoom)))
        self.redraw()
    def seek(self,t,playing_restart=True):
        self.cursor=max(0,min(self.duration,int(t)))
        if self.playing and playing_restart:self.start_audio(self.cursor)
        if self.cursor<self.view_start or self.cursor>self.view_start+self.zoom:
            self.view_start=max(0,min(max(0,self.duration-self.zoom),self.cursor-self.zoom//3))
        self.redraw()
    def slider_released(self,event):
        # User seek only; programmatic Scale.set must never restart audio.
        self.seek(self.progress.get())

    def import_audio(self):
        f=filedialog.askopenfilename(filetypes=[('Audio files','*.mid *.midi *.aac *.m4a *.mp3 *.wav *.ogg *.flac'),('All files','*.*')])
        if not f:return
        is_midi = Path(f).suffix.lower() in ('.mid', '.midi')
        if not is_midi and not shutil.which('ffmpeg'):
            messagebox.showerror('Missing FFmpeg','FFmpeg must be installed and available in PATH.');return
        self.stop()
        self.root.config(cursor='watch');self.root.update_idletasks()
        try:
            new_temp=tempfile.TemporaryDirectory(prefix='rhythm_chart_')
            wav=Path(new_temp.name)/'preview.wav'
            # Playback uses a WAV stream with an explicit mixer-compatible format.
            if is_midi:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
                from build_song import melody_segments, write_preview
                # Convert preview to the exact stereo format used by this studio.
                mono = Path(new_temp.name) / 'mono.wav'
                write_preview(mono, melody_segments(f)[0])
                with wave.open(str(mono), 'rb') as source:
                    frames = source.readframes(source.getnframes())
                samples = array.array('h');samples.frombytes(frames)
                stereo = array.array('h')
                for sample in samples:
                    stereo.extend((sample, sample, sample, sample))
                with wave.open(str(wav), 'wb') as output:
                    output.setnchannels(2);output.setsampwidth(2);output.setframerate(44100)
                    output.writeframes(stereo.tobytes())
            else:
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',f,'-vn','-ar','44100','-ac','2','-c:a','pcm_s16le',str(wav)],check=True,timeout=120)
            with wave.open(str(wav),'rb') as w:
                duration=int(w.getnframes()/w.getframerate()*1000)
                peak=[]
                block=512
                while True:
                    raw=w.readframes(block)
                    if not raw:break
                    samples=array.array('h');samples.frombytes(raw)
                    if not samples:break
                    peak.append(max(abs(min(samples)),abs(max(samples)))/32768)
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            # Keep decompressed 16-bit PCM in memory; avoid OGG seeking/decoding
            # on the playback path and expensive restarting of compressed music.
            pygame.mixer.init(frequency=44100,size=-16,channels=2,buffer=4096, allowedchanges=0)
            actual=pygame.mixer.get_init()
            if actual != (44100,-16,2):
                raise RuntimeError('Unexpected audio device format: '+str(actual))
            with wave.open(str(wav),'rb') as w:
                pcm_data=w.readframes(w.getnframes())
            self.channel=pygame.mixer.Channel(0)
            self.pcm_data=pcm_data
            self.sample_rate=44100
            self.active_sound=None
            if self.temp:self.temp.cleanup()
            self.temp=new_temp;self.peaks=peak
            self.duration=max(self.duration,duration) if self.notes else duration
            self.progress.config(to=self.duration)
            self.status.set('Audio loaded: '+Path(f).name+' · '+self.format_time(duration))
            self.redraw()
        except Exception as e:
            if 'new_temp' in locals():new_temp.cleanup()
            messagebox.showerror('Import audio failed',str(e))
        finally:self.root.config(cursor='')
    def start_audio(self,position):
        if self.pcm_data is None:return False
        import pygame
        self.channel.stop()
        bytes_per_frame=4  # 16-bit stereo, 2 channels
        total_frames=len(self.pcm_data)//bytes_per_frame
        start_frame=max(0,min(total_frames,int(position*self.sample_rate/1000)))
        if start_frame>=total_frames:return False
        # Package the selected segment as a real WAV stream, with explicit
        # sample rate / channels / bit depth. Avoid Sound(buffer=raw_pcm), whose
        # interpretation depends on SDL mixer format.
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(self.pcm_data[start_frame*bytes_per_frame:])
        stream.seek(0)
        self.active_sound=pygame.mixer.Sound(file=stream)
        self.channel.play(self.active_sound)
        self.paused=False
        self.play_offset=position
        self.play_started=time.monotonic()
        return True
    def toggle(self):
        if self.playing:
            self.playing=False
            if self.channel:self.channel.pause()
            self.paused=True
        else:
            if self.pcm_data is None:
                messagebox.showinfo('Load audio','Import an AAC/WAV/MP3 first to hear the music.');return
            try:
                if self.paused and self.channel and self.active_sound is not None:
                    self.channel.unpause()
                    self.paused=False
                    self.play_started=time.monotonic() - (self.cursor-self.play_offset)/1000
                    self.playing=True
                else:
                    self.playing=self.start_audio(self.cursor)
            except Exception as e:messagebox.showerror('Audio error',str(e));self.playing=False
        self.redraw()
    def stop(self):
        self.playing=False
        if self.channel:self.channel.stop()
        self.active_sound=None
        self.paused=False
    def tick(self):
        if self.playing:
            self.cursor=min(self.duration,int(self.play_offset+(time.monotonic()-self.play_started)*1000))
            if self.cursor>=self.duration or not self.channel.get_busy():self.playing=False
            if self.cursor>self.view_start+self.zoom*.87 or self.cursor<self.view_start:
                self.view_start=max(0,min(max(0,self.duration-self.zoom),int(self.cursor-self.zoom*.25)))
            self.redraw()
        self.root.after(80,self.tick)
    @staticmethod
    def format_time(ms):
        s=max(0,ms)//1000;return '%02d:%02d.%03d'%(s//60,s%60,max(0,ms)%1000)
    def redraw(self):
        c=self.canvas;c.delete('all')
        w=c.winfo_width();h=c.winfo_height()
        if w<100:return
        c.create_rectangle(0,0,w,h,fill='#111924',outline='')
        c.create_rectangle(LEFT,25,w-15,83,fill='#1b3040',outline='')
        if self.peaks:
            dur=max(1,self.duration)
            for x in range(LEFT,w-15,2):
                t=self.t_for(x)
                i=int(t/dur*len(self.peaks))
                j=min(len(self.peaks),max(i+1,int(self.t_for(x+2)/dur*len(self.peaks))))
                p=max(self.peaks[i:j],default=0) if i<len(self.peaks) else 0
                amp=p*26
                c.create_line(x,54-amp,x,54+amp,fill='#5eacbc')
        for i,d in enumerate(DIRS):
            y=TOP+i*STEP
            c.create_rectangle(LEFT,y-21,w-15,y+21,fill='#172333' if i%2==0 else '#1b293a',outline='')
            c.create_text(44,y,text=MARKS[i]+' '+d[:1],fill=LANE_COLORS[i],font=('Segoe UI',12,'bold'))
            c.create_line(LEFT,y,w-15,y,fill='#425166')
        # Ruler ticks: adaptive grid density.
        step=1000
        while step/self.zoom*self.plot_width()<65:step*=2
        first=int(self.view_start//step)*step
        for t in range(first,int(self.view_start+self.zoom)+step,step):
            x=self.x_for(t)
            if LEFT<=x<=w-15:
                c.create_line(x,22,x,TOP+3*STEP+26,fill='#283c50',dash=(2,5))
                c.create_text(x+3,13,text=self.format_time(t),anchor='w',fill='#a3b5c6',font=('Consolas',9))
        for n in self.notes:
            x=self.x_for(n['time_ms'])
            if not LEFT-15<=x<=w+15:continue
            idx=DIRS.index(n['direction']);y=TOP+idx*STEP
            if n is self.selected:
                c.create_oval(x-11,y-11,x+11,y+11,fill='#fff7cd',outline='#ffffff',width=2)
            else:c.create_oval(x-8,y-8,x+8,y+8,fill=LANE_COLORS[idx],outline='')
        x=self.x_for(self.cursor)
        if LEFT<=x<=w-15:c.create_line(x,21,x,TOP+3*STEP+30,fill='#ff7878',width=2)
        c.create_text(LEFT,TOP+3*STEP+45,anchor='w',fill='#adbccc',font=('Consolas',10),text='Playhead '+self.format_time(self.cursor)+'    Notes '+str(len(self.notes))+'    Zoom '+str(round(self.zoom/1000,2))+'s')
        self.root.title('Rhythm Chart Studio — '+self.title.get()+(' *' if self.dirty else ''))
        self.progress.set(self.cursor)
    def close(self):
        if not self.confirm_unsaved():return
        self.stop()
        if self.temp:self.temp.cleanup()
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk()
    Studio(root)
    root.mainloop()
