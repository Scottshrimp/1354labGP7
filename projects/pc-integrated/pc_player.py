#!/usr/bin/env python3
"""PC dependency only: catalog, chart streaming, audio transport. Board owns all controls."""
import argparse,json,subprocess,time,shutil
from pathlib import Path
import serial,pygame

ROOT=Path(__file__).resolve().parent
BATCH=12
DIRECTION={'UP':0,'RIGHT':1,'DOWN':2,'LEFT':3}

def load_songs():
    songs=[]
    for file in sorted((ROOT/'songs').glob('*/song.json')):
        doc=json.loads(file.read_text(encoding='utf-8'))
        audio=file.parent/doc['audio']
        if audio.is_file():songs.append((file.parent,doc))
    return songs

def notes_for(folder,doc):
    p=folder/doc['chart']
    c=json.loads(p.read_text(encoding='utf-8'))
    rows=[]
    for n in c['notes']:
        rows.append((int(n['time_ms']),DIRECTION[n['direction'].upper()],0))
    return sorted(rows),int(c.get('duration_ms',doc['duration_ms']))

def wav_for(folder,doc):
    audio=folder/doc['audio']
    wav=folder/'cache.wav'
    if not wav.exists() or wav.stat().st_mtime<audio.stat().st_mtime:
        if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg missing in PATH')
        print('Preparing WAV for',doc['title'],flush=True)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(audio),'-ar','44100','-ac','2',str(wav)],check=True)
    return wav

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--port',default='COM3')
    ap.add_argument('--offset-ms',type=int,default=0,help='Positive makes audio later than notes')
    args=ap.parse_args()
    songs=load_songs()
    if not songs:raise SystemExit('No valid songs/*/song.json + audio files')
    pygame.mixer.pre_init(44100,-16,2,512)
    pygame.init()
    print('Listening for Gamepad on',args.port,' | Songs:',len(songs),flush=True)
    with serial.Serial(args.port,115200,timeout=0.04,write_timeout=2) as link:
        time.sleep(2.0)
        link.reset_input_buffer()
        def send(line):
            link.write((line+'\n').encode('ascii'))
            link.flush()
        def send_catalog():
            for i,(_,s) in enumerate(songs[:12]):
                title=''.join(ch for ch in s['title'].upper() if ch.isascii() and (ch.isalnum() or ch in ' -_'))[:18]
                send('CAT,{},{}'.format(i,title))
                time.sleep(0.045)
            send('CATDONE')
        # Board may have printed HELLO before serial is open; catalog is authoritative.
        send_catalog()
        current=None;cursor=0;state='MENU';audio_at=None
        while True:
            line=link.readline().decode('ascii','replace').strip()
            if line:
                print('Board:',line,flush=True)
                if line=='HELLO':
                    if current is None:send_catalog()
                elif line.startswith('SELECT,'):
                    try:
                        _,si=line.split(',');si=int(si)
                        folder,doc=songs[si]
                        notes,duration=notes_for(folder,doc)
                        wav=wav_for(folder,doc)
                        pygame.mixer.music.load(str(wav))
                        current=notes;cursor=0;state='READY';audio_at=None
                        send('META,{}'.format(duration))
                        time.sleep(0.06)
                        def batch(k):
                            nonlocal cursor
                            if current is None:return
                            for t,d,hold in current[cursor:cursor+k]:
                                send('N,{},{},{}'.format(t,d,hold))
                                time.sleep(0.022)
                            cursor=min(cursor+k,len(current))
                            if cursor==len(current):send('END')
                        batch(24)
                        time.sleep(0.12)
                        send('ARMED')
                        print('Ready: {} / {} notes'.format(doc['title'],len(notes)),flush=True)
                    except (ValueError,IndexError,KeyError,OSError) as e:
                        print('Selection failed:',e,flush=True);send('ERR');current=None
                elif line=='START' and current is not None:
                    # Board waits for SYNC before starting its local timeline.
                    send('SYNC')
                    state='SYNCING'
                elif line=='SYNCED' and current is not None:
                    # Device starts counting at SYNC; receive latency is small and measurable.
                    audio_at=time.perf_counter()+2.7+args.offset_ms/1000.0
                    state='PLAY'
                    print('Synchronized start, audio offset:',args.offset_ms,'ms',flush=True)
                elif line=='SYNC_TIMEOUT':
                    print('Board synchronization timed out',flush=True)
                elif line=='NEED' and current is not None and state in ('PLAY','PAUSED'):
                    batch(12)
                elif line=='PAUSE':
                    pygame.mixer.music.pause()
                    state='PAUSED'
                elif line=='RESUME':
                    pygame.mixer.music.unpause()
                    state='PLAY'
                elif line=='STOP':
                    pygame.mixer.music.stop();current=None;state='MENU';audio_at=None
                elif line.startswith('DONE,'):
                    pygame.mixer.music.stop()
                    print('Result:',line,flush=True)
                    current=None;state='MENU';audio_at=None
            if audio_at is not None and time.perf_counter()>=audio_at:
                pygame.mixer.music.play();audio_at=None
                print('Audio playback started',flush=True)
            time.sleep(0.002)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nPC host stopped')
