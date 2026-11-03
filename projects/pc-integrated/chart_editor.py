"""Rhythm Hold chart editor: AAC playback, waveform, tap-only chart editing."""
import json, math, shutil, subprocess, tempfile, wave, tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

DIRECTIONS = ('UP','RIGHT','DOWN','LEFT')

class Editor:
    def __init__(self, root):
        self.root=root;root.title('Rhythm Hold - Chart Editor - Tap Only')
        self.notes=[];self.path=None;self.audio_path=None;self.audio_wav=None;self.audio_preview=None
        self.duration=156565;self.bpm=92.0;self.selected=None
        self.cursor=tk.DoubleVar(value=0)
        self.snap=tk.BooleanVar(value=True);self.zoom=tk.DoubleVar(value=15)
        self.waveform=[];self.playing=False;self.play_start=0
        self.pg=None;self.audio_offset=0
        top=ttk.Frame(root);top.pack(fill='x',padx=8,pady=6)
        for name,fn in [('Open Chart',self.open),('Import AAC',self.import_audio),('Save',self.save),('Save As',self.save_as),('Delete',self.delete)]:
            ttk.Button(top,text=name,command=fn).pack(side='left',padx=3)
        ttk.Button(top,text='Play / Pause [Space]',command=self.toggle_play).pack(side='left',padx=7)
        ttk.Button(top,text='Stop',command=self.stop).pack(side='left')
        ttk.Label(top,text='Zoom window (seconds)').pack(side='left',padx=(18,3))
        ttk.Combobox(top,textvariable=self.zoom,values=(5,10,15,30,60,120,180),width=5,state='readonly').pack(side='left')
        form=ttk.Frame(root);form.pack(fill='x',padx=8,pady=5)
        ttk.Label(form,text='Time ms').pack(side='left')
        self.entry=ttk.Entry(form,width=9);self.entry.pack(side='left',padx=5)
        ttk.Label(form,text='BPM').pack(side='left')
        self.bpmvar=tk.DoubleVar(value=self.bpm)
        ttk.Entry(form,textvariable=self.bpmvar,width=6).pack(side='left',padx=3)
        ttk.Checkbutton(form,text='Snap 1/4 beat',variable=self.snap).pack(side='left',padx=6)
        for k in DIRECTIONS:
            ttk.Button(form,text=k,command=lambda d=k:self.add(d)).pack(side='left',padx=2)
        self.canvas=tk.Canvas(root,height=335,bg='#111927',highlightthickness=0)
        self.canvas.pack(fill='both',expand=True,padx=8,pady=5)
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<Configure>',lambda e:self.redraw())
        self.slider=ttk.Scale(root,variable=self.cursor,from_=0,to=self.duration,command=lambda _:self.redraw())
        self.slider.pack(fill='x',padx=12)
        self.status=ttk.Label(root,text='Load audio or chart to begin');self.status.pack(fill='x',padx=10,pady=7)
        root.bind('<space>',lambda e:self.toggle_play())
        root.bind('<Delete>',lambda e:self.delete())
        root.bind('<Control-s>',lambda e:self.save())
        for key,d in zip(('u','r','d','l'),DIRECTIONS):root.bind(key,lambda e,k=d:self.add(k))
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(40,self.tick)
        self.redraw()
    def get_bpm(self):
        try:return max(1,float(self.bpmvar.get()))
        except:return 92.0
    def snap_time(self,t):
        if self.snap.get():
            step=60000/self.get_bpm()/4
            return round(t/step)*step
        return t
    def visible(self):
        window=min(self.duration,max(1000,self.zoom.get()*1000))
        start=max(0,min(self.duration-window,self.cursor.get()-window/2))
        return start,window
    def coordinates(self,ms):
        start,window=self.visible();w=max(100,self.canvas.winfo_width()-95)
        return 63+(ms-start)/window*w
    def add(self,d):
        try:t=float(self.entry.get())
        except:t=self.cursor.get()
        t=max(0,int(self.snap_time(t)))
        n={'time_ms':t,'direction':d}
        self.notes.append(n);self.notes.sort(key=lambda n:n['time_ms'])
        self.selected=self.notes.index(n);self.cursor.set(t);self.redraw()
    def click(self,e):
        start,window=self.visible();w=max(100,self.canvas.winfo_width()-95)
        t=max(0,int(start+max(0,e.x-63)/w*window))
        lane=min(3,max(0,round((e.y-125)/42)))
        candidates=[(abs(n['time_ms']-t),i) for i,n in enumerate(self.notes) if DIRECTIONS.index(n['direction'].upper())==lane]
        if candidates and min(candidates)[0] < window*10/w:
            self.selected=min(candidates)[1];n=self.notes[self.selected]
            t=n['time_ms'];
        else:self.selected=None
        self.cursor.set(t);self.entry.delete(0,'end');self.entry.insert(0,str(t));self.redraw()
    def delete(self):
        if self.selected is not None and self.selected<len(self.notes):
            self.notes.pop(self.selected);self.selected=None;self.redraw()
    def open(self):
        f=filedialog.askopenfilename(filetypes=[('Chart JSON','*.json')])
        if not f:return
        try:
            data=json.loads(Path(f).read_text(encoding='utf-8'))
            self.notes=[{'time_ms':int(n['time_ms']),'direction':n['direction']} for n in data['notes']];self.duration=int(data.get('duration_ms',156565))
            self.bpmvar.set(float(data.get('bpm',92)));self.path=Path(f)
            self.slider.configure(to=self.duration);self.selected=None
            self.cursor.set(0);self.redraw()
        except Exception as ex:messagebox.showerror('Open chart',str(ex))
    def import_audio(self):
        f=filedialog.askopenfilename(filetypes=[('Audio','*.aac *.wav *.mp3 *.m4a *.ogg'),('All files','*.*')])
        if not f:return
        try:
            import pygame
            self.pg=pygame
            if not pygame.mixer.get_init():pygame.mixer.init(frequency=22050,size=-16,channels=1,buffer=1024)
            if not shutil.which('ffmpeg'):raise RuntimeError('FFmpeg must be installed and on PATH')
            if not self.audio_wav:
                tmp=Path(tempfile.mkdtemp(prefix='rhythm_editor_'))
                self.audio_wav=tmp/'preview.wav';self.audio_preview=tmp/'preview.ogg'
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',f,'-ac','1','-ar','22050',str(self.audio_wav)],check=True)
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',f,'-ac','1','-c:a','libvorbis','-q:a','4',str(self.audio_preview)],check=True)
            pygame.mixer.music.load(str(self.audio_preview))
            self.audio_path=Path(f)
            with wave.open(str(self.audio_wav),'rb') as w:
                length=w.getnframes()/w.getframerate()
                self.duration=int(length*1000)
                n=w.getnframes();stride=max(1,int(w.getframerate()/80))
                peaks=[];block=4096;values=[]
                while True:
                    raw=w.readframes(block)
                    if not raw:break
                    import array
                    a=array.array('h');a.frombytes(raw)
                    values.extend(a)
                    while len(values)>=stride:
                        seg=values[:stride];del values[:stride]
                        peaks.append(max(abs(v) for v in seg)/32768)
                self.waveform=peaks
            self.slider.configure(to=self.duration);self.cursor.set(0);self.redraw()
        except Exception as ex:messagebox.showerror('Import audio',str(ex))
    def toggle_play(self):
        if not self.pg or not self.audio_wav:
            messagebox.showinfo('Audio','Import AAC (or other audio) first.');return
        import time
        if self.playing:
            self.pg.mixer.music.stop();self.audio_offset=self.cursor.get();self.playing=False
        else:
            if False:pass
            else:self.pg.mixer.music.play(start=self.cursor.get()/1000)
            self.play_start=time.monotonic()-self.cursor.get()/1000;self.playing=True
    def stop(self):
        if self.pg:self.pg.mixer.music.stop()
        self.playing=False
    def tick(self):
        if self.playing:
            import time
            t=(time.monotonic()-self.play_start)*1000
            if t>=self.duration:self.stop()
            else:self.cursor.set(t);self.redraw()
        self.root.after(40,self.tick)
    def save(self):
        if self.path is None:return self.save_as()
        document={'duration_ms':self.duration,'bpm':self.get_bpm(),'notes':self.notes}
        self.path.write_text(json.dumps(document,indent=2,ensure_ascii=False),encoding='utf-8')
        self.status.configure(text='Saved: '+str(self.path))
    def save_as(self):
        f=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if f:self.path=Path(f);self.save()
    def redraw(self):
        c=self.canvas;c.delete('all');w=max(200,c.winfo_width())
        start,window=self.visible()
        c.create_text(8,10,anchor='nw',fill='#b7c6da',text='Waveform / {} - {}'.format(round(start/1000,1),round((start+window)/1000,1)))
        mid=60
        if self.waveform:
            left=max(0,int(start/1000*80));right=min(len(self.waveform),int((start+window)/1000*80)+1)
            for idx in range(left,right):
                x=self.coordinates(idx*12.5)
                if 63<=x<=w-25:
                    strength=self.waveform[idx]
                    c.create_line(x,mid-strength*30,x,mid+strength*30,fill='#4d9cb3')
        c.create_line(63,mid,w-25,mid,fill='#506078')
        for lane,d in enumerate(DIRECTIONS):
            y=125+lane*42
            c.create_text(28,y,text=d,fill='#e2ecf5')
            c.create_line(63,y,w-25,y,fill='#34465c')
        tick=1000 if window<=20000 else (5000 if window<=60000 else 10000)
        first=int(start//tick)*tick
        for t in range(first,int(start+window)+1,tick):
            x=self.coordinates(t)
            c.create_line(x,94,x,275,fill='#293b50')
            c.create_text(x,99,text=str(round(t/1000,1))+'s',fill='#95a9c0',anchor='n')
        for i,n in enumerate(self.notes):
            x=self.coordinates(n['time_ms']);y=125+DIRECTIONS.index(n['direction'].upper())*42
            if x < 49 or x > w+5:continue
            color='#ffdc75' if i==self.selected else '#84e0cc'
            c.create_oval(x-7,y-7,x+7,y+7,fill=color,outline='#182431')
        x=self.coordinates(self.cursor.get())
        c.create_line(x,30,x,285,fill='#ff777e',width=2)
        c.create_text(10,295,anchor='nw',fill='#b7c6da',text='Click a lane to select time/note. U/R/D/L inserts a note. Tap notes only.')
        self.status.configure(text='{} notes | Cursor {:.3f}s | BPM {:.2f} | {}'.format(len(self.notes),self.cursor.get()/1000,self.get_bpm(),self.path or 'Unsaved'))
    def close(self):
        self.stop();self.root.destroy()

if __name__=='__main__':
    r=tk.Tk();r.geometry('1100x540');Editor(r);r.mainloop()
