from microbit import *
OLED_W = 128
OLED_H = 64
BPM = 80
BEAT_MS = 60000 // BPM
LEAD_MS = 1700
PERFECT_MS = 100
GOOD_MS = 210
FRAME_MS = 20
RIGHT_FRAME_MS = 180
USE_RGB = True
SONG_LENGTH_MS = 156565
DPADS = (pin13, pin11, pin15, pin5)
ARROWS = ('U','R','D','L')
class OLED:
    def __init__(self, addr):
        self.addr = addr
        self.buf = bytearray(1024)
        self.previous = bytearray(1024)
        self.first_show = True
        for c in (0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00,
                  0x40, 0x8D, 0x14, 0x20, 0x02, 0xA1, 0xC8,
                  0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB,
                  0x40, 0xA4, 0xA6, 0xAF):
            i2c.write(addr, bytes((0x00, c)))
    def clear(self):
        for i in range(1024):
            self.buf[i] = 0
    def px(self, x, y):
        if 0 <= x < 128 and 0 <= y < 64:
            self.buf[x + (y >> 3) * 128] |= 1 << (y & 7)
    def line(self, x0, y0, x1, y1):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        e = dx + dy
        while True:
            self.px(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * e
            if e2 >= dy:
                e += dy
                x0 += sx
            if e2 <= dx:
                e += dx
                y0 += sy
    def rect(self, x, y, w, h):
        self.line(x, y, x+w-1, y)
        self.line(x, y+h-1, x+w-1, y+h-1)
        self.line(x, y, x, y+h-1)
        self.line(x+w-1, y, x+w-1, y+h-1)
    def circle(self, cx, cy, radius):
        x = radius
        y = 0
        err = 1-radius
        while x >= y:
            self.px(cx+x, cy+y)
            self.px(cx+y, cy+x)
            self.px(cx-y, cy+x)
            self.px(cx-x, cy+y)
            self.px(cx-x, cy-y)
            self.px(cx-y, cy-x)
            self.px(cx+y, cy-x)
            self.px(cx+x, cy-y)
            y += 1
            if err < 0:
                err += 2*y + 1
            else:
                x -= 1
                err += 2*(y-x) + 1
    def arrow(self, cx, cy, direction, radius=8):
        r = radius
        if direction == 0:
            self.line(cx, cy-r, cx-r, cy+3)
            self.line(cx, cy-r, cx+r, cy+3)
            self.line(cx, cy-r, cx, cy+r)
        elif direction == 1:
            self.line(cx+r, cy, cx-3, cy-r)
            self.line(cx+r, cy, cx-3, cy+r)
            self.line(cx-r, cy, cx+r, cy)
        elif direction == 2:
            self.line(cx, cy+r, cx-r, cy-3)
            self.line(cx, cy+r, cx+r, cy-3)
            self.line(cx, cy-r, cx, cy+r)
        else:
            self.line(cx-r, cy, cx+3, cy-r)
            self.line(cx-r, cy, cx+3, cy+r)
            self.line(cx-r, cy, cx+r, cy)
    def text(self, msg, x, y, scale=1):
        font = {
          '0':(7,5,5,5,7),'1':(2,6,2,2,7),'2':(7,1,7,4,7),
          '3':(7,1,7,1,7),'4':(5,5,7,1,1),'5':(7,4,7,1,7),
          '6':(7,4,7,5,7),'7':(7,1,1,1,1),'8':(7,5,7,5,7),
          '9':(7,5,7,1,7),'A':(2,5,7,5,5),'B':(6,5,6,5,6),
          'C':(3,4,4,4,3),'D':(6,5,5,5,6),'E':(7,4,6,4,7),
          'F':(7,4,6,4,4),'G':(3,4,5,5,3),'H':(5,5,7,5,5),
          'I':(7,2,2,2,7),'J':(1,1,1,5,2),'K':(5,5,6,5,5),
          'L':(4,4,4,4,7),'M':(5,7,7,5,5),'N':(5,7,7,7,5),
          'O':(2,5,5,5,2),'P':(6,5,6,4,4),'Q':(2,5,5,7,3),
          'R':(6,5,6,5,5),'S':(3,4,2,1,6),'T':(7,2,2,2,2),
          'U':(5,5,5,5,7),'V':(5,5,5,5,2),'W':(5,5,7,7,5),
          'X':(5,5,2,5,5),'Y':(5,5,2,2,2),'Z':(7,1,2,4,7),
          '-':(0,0,7,0,0),':':(0,2,0,2,0),' ':(0,0,0,0,0),
          '>':(4,2,1,2,4),'/':(1,1,2,4,4)}
        for c in str(msg).upper():
            glyph = font.get(c, font[' '])
            for yy in range(5):
                for xx in range(3):
                    if glyph[yy] & (1 << (2-xx)):
                        for sy in range(scale):
                            for sx in range(scale):
                                self.px(x + (xx*scale)+sx, y+(yy*scale)+sy)
            x += 4*scale
    def show(self):
        for page in range(8):
            base = page * 128
            x = 0
            while x < 128:
                while x < 128 and not self.first_show and self.buf[base+x] == self.previous[base+x]:
                    x += 1
                if x >= 128:
                    break
                start = x
                last_dirty = x
                x += 1
                while x < 128 and x - start < 28:
                    if self.first_show or self.buf[base+x] != self.previous[base+x]:
                        last_dirty = x
                    elif x - last_dirty > 6:
                        break
                    x += 1
                end = last_dirty + 1
                i2c.write(self.addr, bytes((0, 0xB0 | page, start & 15, 0x10 | (start >> 4))))
                i2c.write(self.addr, b'\x40' + self.buf[base+start:base+end])
                for k in range(start, end):
                    self.previous[k+base] = self.buf[k+base]
                if x < end:
                    x = end
        self.first_show = False
    def show_lane_region(self, x0, x1):
        if x0 > x1:
            return
        x0 = max(0, x0)
        x1 = min(127, x1)
        for page in (3, 4, 5):
            base = page * 128
            x = x0
            while x <= x1:
                while x <= x1 and self.buf[base+x] == self.previous[base+x]:
                    x += 1
                if x > x1:
                    break
                start = x
                last_dirty = x
                x += 1
                while x <= x1 and x - start < 28:
                    if self.buf[base+x] != self.previous[base+x]:
                        last_dirty = x
                    elif x - last_dirty > 6:
                        break
                    x += 1
                end = last_dirty + 1
                i2c.write(self.addr, bytes((0, 0xB0 | page,
                                              start & 15, 0x10 | (start >> 4))))
                i2c.write(self.addr, b'\x40' + self.buf[base+start:base+end])
                for k in range(start, end):
                    self.previous[base+k] = self.buf[base+k]
                if x < end:
                    x = end
    def show_rect(self, x0, x1, page0, page1):
        x0 = max(0, x0)
        x1 = min(127, x1)
        for page in range(page0, page1 + 1):
            base = page * 128
            x = x0
            while x <= x1:
                while x <= x1 and self.buf[base+x] == self.previous[base+x]:
                    x += 1
                if x > x1:
                    break
                start = x
                last_dirty = x
                x += 1
                while x <= x1 and x-start < 28:
                    if self.buf[base+x] != self.previous[base+x]:
                        last_dirty = x
                    elif x-last_dirty > 6:
                        break
                    x += 1
                end = last_dirty + 1
                i2c.write(self.addr, bytes((0, 0xB0 | page,
                                             start & 15, 0x10 | (start >> 4))))
                i2c.write(self.addr, b'\x40' + self.buf[base+start:base+end])
                for k in range(start, end):
                    self.previous[base+k] = self.buf[base+k]
                if x < end:
                    x = end
    def erase_pages(self, x0, x1, p0, p1):
        for page in range(p0, p1+1):
            base = page * 128
            for x in range(x0, x1+1):
                self.buf[base+x] = 0
    def clear_band(self):
        for page in (3, 4, 5):
            base = page * 128
            for x in range(128):
                self.buf[base+x] = 0
def led_off():
    if USE_RGB:
        pin9.write_analog(1023)
        pin14.write_analog(1023)
        pin16.write_analog(1023)
def led_judge(result):
    if not USE_RGB:return
    pin9.write_analog(768 if result in (1,2) else 1023)
    pin14.write_analog(768 if result in (0,1) else 1023)
    pin16.write_analog(1023)
DPADS = (pin13, pin11, pin15, pin5)
queue = []
rx = bytearray()
catalog = []
menu_index = 0
screen_state = 'CONNECT'
end_of_chart = False
song_length = 156565
sync_requested=False
def joy_direction(cx, cy):
    x = pin0.read_analog() - cx
    y = pin1.read_analog() - cy
    if abs(x) < 230 and abs(y) < 230: return -1
    if abs(x) >= abs(y): return 1 if x > 0 else 3
    return 0 if y > 0 else 2
def invert_strip(oled, y0, h):
    for y in range(y0,y0+h):
        a=(y>>3)*128
        mask=1<<(y&7)
        for x in range(6,122):oled.buf[a+x] ^= mask
def menu_draw(right, heading, options, index, footer):
    right.hud_combo=None
    right.clear()
    right.text(heading[:18], 4, 2)
    for i in range(min(4,len(options))):
        shown = max(0,min(index-2,len(options)-4)) if len(options)>4 else 0
        k = shown+i
        if k>=len(options): break
        y=16+i*9
        right.text(options[k][:25], 10, y)
        if k==index: invert_strip(right,y-1,8)
    right.text(footer[:28], 3, 57)
    right.show()
def draw_hud(right,combo,score):
    if getattr(right,'hud_combo',None) is None:
        right.clear()
        right.text('COMBO',23,3,2)
        right.line(8,39,119,39)
        right.text('SCORE',8,48)
        right.text(str(combo),max(0,(128-(4*len(str(combo))-1)*2)//2),22,2)
        right.text(str(score),40,48)
        right.show()
    else:
        if combo != right.hud_combo:
            right.erase_pages(0,127,2,3)
            cs=str(combo)
            right.text(cs,max(0,(128-(4*len(cs)-1)*2)//2),22,2)
            right.show_rect(0,127,2,3)
        if score != right.hud_score:
            right.erase_pages(40,127,6,6)
            right.text(str(score),40,48)
            right.show_rect(40,127,6,6)
    right.hud_combo=combo
    right.hud_score=score
def send(s): print(s)
def poll_messages(limit=96):
    global rx,end_of_chart,song_length,screen_state,catalog,sync_requested
    lines=[]
    count=0
    while uart.any() and count<limit:
        b=uart.read(1)
        if not b: break
        count+=1
        if b==b'\n':
            line=bytes(rx)
            rx=bytearray()
            try:
                parts=line.decode('ascii').split(',')
                k=parts[0]
                if k=='CAT' and len(parts)>=3:
                    idx=int(parts[1]);name=parts[2][:18]
                    if idx<len(catalog):catalog[idx]=(idx,name)
                    elif len(catalog)<12:catalog.append((idx,name))
                elif k=='META':song_length=int(parts[1])
                elif k=='N' and len(parts)==4 and len(queue)<48:
                    queue.append([int(parts[1]),int(parts[2]),0,None])
                elif k=='ARMED':screen_state='ARMED'
                elif k=='END':end_of_chart=True
                elif k=='SYNC':sync_requested=True
                elif k=='PING':send('PONG')
                elif k=='CATDONE':
                    if screen_state=='CONNECT':screen_state='MENU'
                elif k=='ERR':screen_state='ERROR'
                lines.append(k)
            except (ValueError,IndexError):pass
        elif b!=b'\r':
            if len(rx)<60:rx.append(b[0])
            else:rx=bytearray()
    return lines
def judgement_feedback(j,now):
    led_judge(j)
    return now+130,0
def play(left,right):
    global screen_state,end_of_chart, sync_requested
    screen_state='PLAY'
    combo=0;score=0;best_combo=0
    perf=0;good=0;miss=0
    t0=None
    paused_at=0;paused=False
    last_inputs=[False]*4
    feedback_until=0
    last_frame=-FRAME_MS
    last_need=0
    last_joy=-1
    hud_dirty=False
    left.clear();left.line(1,18,126,18);left.line(1,52,126,52);left.circle(32,35,10);left.show()
    right.hud_combo=None;draw_hud(right,0,0)
    # Ask PC to arm audio, then wait for a single shared synchronization event.
    sync_requested=False
    send('START')
    display.show('0')
    sync_deadline=running_time()+8000
    while not sync_requested:
        poll_messages()
        if running_time() >= sync_deadline:
            send('SYNC_TIMEOUT')
            screen_state='MENU'
            return
        sleep(2)
    # PC and board now use the same SYNC event to anchor their countdown.
    t0=running_time()+2700
    send('SYNCED')
    while True:
        now=running_time()
        poll_messages()
        d=joy_direction(center_x,center_y)
        if d!=-1 and last_joy==-1:
            if not paused and d==3:
                paused=True;paused_at=now;send('PAUSE')
                menu_draw(right,'PAUSED',('LS RIGHT RESUME','LS DOWN EXIT'),0,'LS R / LS DOWN')
                display.show(Image.SQUARE)
            elif paused and d==1:
                paused=False;t0+=now-paused_at;send('RESUME')
                right.hud_combo=None;draw_hud(right,combo,score)
                display.show(str(combo%10))
                last_frame=-FRAME_MS
            elif paused and d==2:
                send('STOP');screen_state='MENU';return
        last_joy=d
        if paused:
            sleep(18)
            continue
        elapsed=now-t0
        if elapsed>=song_length+900:break
        if len(queue)<20 and not end_of_chart and now>=last_need:
            send('NEED');last_need=now+800
        if now>=feedback_until:led_off()

        for n in queue:
            if n[2]==0 and elapsed>n[0]+GOOD_MS:
                n[2]=3;miss+=1;combo=0;hud_dirty=True
                feedback_until,_=judgement_feedback(2,now)
        for j in range(4):
            down=DPADS[j].read_digital()==0
            if down and not last_inputs[j]:
                target=None;dist=GOOD_MS+1
                for n in queue:
                    e=abs(elapsed-n[0])
                    if n[2]==0 and e<dist:target=n;dist=e
                if target is not None:
                    if target[1]!=j: r=2
                    elif dist<=PERFECT_MS:r=0
                    else:r=1
                    feedback_until,_=judgement_feedback(r,now)
                    if r==2:
                        target[2]=3;miss+=1;combo=0
                    else:
                        target[2]=1 if r==0 else 2
                        if r==0:perf+=1;score+=100
                        else:good+=1;score+=50
                        combo+=1;best_combo=max(best_combo,combo)
                    hud_dirty=True
            last_inputs[j]=down
        if now-last_frame>=FRAME_MS:
            last_frame=now
            left.clear_band();left.circle(32,35,10)
            lo=128;hi=-1
            for n in queue:
                old=n[3];new=None
                if n[2] in (0,3):
                    dt=n[0]-elapsed
                    if dt<=LEAD_MS:
                        x=32+(dt*91)//LEAD_MS
                        if x>=-7:
                            new=x
                            left.arrow(x,35,n[1],6)
                        elif n[2]==3:n[2]=5
                if old is not None:lo=min(lo,old-8);hi=max(hi,old+8)
                if new is not None:lo=min(lo,new-8);hi=max(hi,new+8)
                n[3]=new
            left.show_lane_region(lo,hi)
            while queue and queue[0][0]<elapsed-1600:queue.pop(0)
        if hud_dirty:
            display.show(str(combo%10))
            draw_hud(right,combo,score);hud_dirty=False
        sleep(1)
    led_off()
    send('DONE,{},{},{},{},{}'.format(score,best_combo,perf,good,miss))
    left.clear();left.text('FINISH',29,14,2);left.show()
    menu_draw(right,'RESULT',('SCORE '+str(score),'BEST '+str(best_combo),'P'+str(perf)+' G'+str(good),'MISS '+str(miss)),0,'LS LEFT MENU')
    previous=-1
    while True:
        poll_messages()
        d=joy_direction(center_x,center_y)
        if d==3 and previous==-1:break
        previous=d;sleep(25)
    screen_state='MENU'
for b in DPADS:b.set_pull(b.PULL_UP)
led_off()
i2c.init(freq=400000)
left=OLED(0x3C);right=OLED(0x3D)
uart.init(baudrate=115200)
center_x=pin0.read_analog();center_y=pin1.read_analog()
right.clear();right.text('CONNECT PC',12,18,2);right.show()
send('HELLO')
previous=-1
last_action=0
last_screen=''
while True:
    poll_messages()
    now=running_time()
    d=joy_direction(center_x,center_y)
    if screen_state!=last_screen:
        if screen_state=='MENU':menu_draw(right,'SONGS',[s[1] for s in catalog],menu_index,'LS RIGHT SELECT')
        elif screen_state=='LOADING':menu_draw(right,'LOADING',('WAIT FOR CHART',),0,'')
        elif screen_state=='ARMED':menu_draw(right,'READY',('LS RIGHT PLAY',),0,'')
        elif screen_state=='ERROR':menu_draw(right,'PC ERROR',('CHECK HOST',),0,'')
        last_screen=screen_state
    if d!=-1 and previous==-1 and now-last_action>200:
        last_action=now
        if screen_state=='MENU' and catalog:
            if d==0:menu_index=(menu_index-1)%len(catalog);last_screen=''
            elif d==2:menu_index=(menu_index+1)%len(catalog);last_screen=''
            elif d==1:
                queue=[];end_of_chart=False
                send('SELECT,{}'.format(catalog[menu_index][0]))
                screen_state='LOADING'
        elif screen_state=='ARMED':
            if d==1:play(left,right);last_screen=''
            elif d==3:send('STOP');screen_state='MENU'
    previous=d
    sleep(12)
