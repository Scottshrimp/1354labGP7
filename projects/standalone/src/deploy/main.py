from microbit import *
import music

def unhexlify(text):
 data = bytearray(len(text) // 2)
 for i in range(len(data)):
  data[i] = int(text[i * 2:i * 2 + 2], 16)
 return bytes(data)

def unpack(text):
 source = unhexlify(text)
 output = bytearray()
 i = 0
 while i < len(source):
  value = source[i]
  i += 1
  if value:
   output.append(value)
  else:
   length = source[i]
   i += 1
   if length == 0:
    output.append(0)
   else:
    distance = source[i] | source[i + 1] << 8
    i += 2
    for _ in range(length):
     output.append(output[-distance])
 return bytes(output)
LEAD_MS = 3000
PERFECT_MS = 220
GOOD_MS = 400
FRAME_MS = 20
USE_RGB = True
SONG_LENGTH_MS = 159196
MELODY = unpack('000000007500003e8200007600003e830000eb00004a05016001458701eb0000440501eb000043000405004105010007230041830000750000438200007500003c00040f003c00203200750000410004280043000437003b00040a003b002c32003a00040a003a002c3200001cc800ea000041040100051e00000c3200001cc80000163200001cc800001632000008c800ea00004a040161014588002132004a00040a004a00043200560004320051000432005000042d004f0401eb00004d050100051e007500004d000428004f00040a004800040a0048002c32004700043b0147820000eb0000560500263200460004320046000c3200ea00005000042d004f0004cd00001432004a000432004a002532007500004f0007c3000005cd00002a3200470007cd0000053200600151000490015000042d0000193200460007cd0000193200000781014d0004280000053200000546004d0004f4014d000422014d00072201000503024b024a8c02000769004d0004810100051e0000054b00500004140000050901000513010008870060014f8700042d0000163200eb000051000482005400099b0056000414005600041400560004460051000446005682000021045496047600042d0000051400ea000051000446005100074100000550004b024f8c0200052300750000510004f000000d1e0000070a0000055a0000051e000005140000056e00000a23000005f00054000c8101eb00004c000405004600043700000576024a00071900210454aa0800076801000f400150000a4a01000717023a0000504100003a00004f4100003b00004d4200003a00004a4100041d010501ab034f960400050901000596000005090100050a00001446007500004c0004b90000059600000ad20054000405005500074f017500005000098f024d0004360100055f004100097f03450007cc01d6014c0a02d6014a000405004c0a02d5014d0902d6014f00070f00ab03511300046d0100044600000a50004e000482000005db014c00040f004b0007e501360349910321044ba908000aaa00000a0e01000f910000053200000a0e013a00004d000413014a4200041e000401ac00090e0100077d0000080e010014460000190e01ea0000550004e60000054600000d450100050e010005830400075505450007cc01000a0e01d5014c000409014d00040f004f00070f00ac03511404001195014e00098c0000080e010005fa0000080e01960481053a1e06d5014100044100401404ab033e13045607414e1080053a1d06d601410a000d19003e4e10000719053e0004d700004e9a06000c320000269a060032320000289a0600163200002e62078801b000004db000044d03550004080200042d0048000423004c0004fe014a0004630645000927064a002d2d0000048200460009f2030005370500080f0000050500ea0000460004320046000928004800041400480004140048000414004800071400001619004a000973000005690000054c0449000414004900049402490004b2024900041900490018410047000414004700042d004700042d0047000419000005140046000414004600041400000a9b000008af00000f19000005550000055000000a5a00000a1400001119004a000419004a00075906000ac3000007be00000819000014140000202d000008a50000059b00000aaa0000161900000d9b00000faf000007d101000549070008680100116e0000055401000505004900042d004900042d0000086801001141004700076d01000505000007710700050f00001c1c020011190000145a000017b4000032fc0300323200000597090005a109002a32003c00079d03002a2e0400325e0b002e3200')
CHART = unpack('27080000130400001404011304011404021304021404031304031404000a1800621400161800000515000200051500036114000000051b000100051b00000a180000052d00000718006100174800000c78006214001c90000009480000156000001590000033d800000c30000027d800000c180013040000')
FREQUENCIES = (8, 9, 9, 10, 10, 11, 12, 12, 13, 14, 15, 15, 16, 17, 18, 19, 21, 22, 23, 24, 26, 28, 29, 31, 33, 35, 37, 39, 41, 44, 46, 49, 52, 55, 58, 62, 65, 69, 73, 78, 82, 87, 92, 98, 104, 110, 117, 123, 131, 139, 147, 156, 165, 175, 185, 196, 208, 220, 233, 247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 523, 554, 587, 622, 659, 698, 740, 784, 831, 880, 932, 988, 1047, 1109, 1175, 1245, 1319, 1397, 1480, 1568, 1661, 1760, 1865, 1976, 2093, 2217, 2349, 2489, 2637, 2794, 2960, 3136, 3322, 3520, 3729, 3951, 4186, 4435, 4699, 4978, 5274, 5588, 5920, 6272, 6645, 7040, 7459, 7902, 8372, 8870, 9397, 9956, 10548, 11175, 11840, 12544)
DPADS = (pin13, pin11, pin15, pin5)

class OLED:

 def __init__(self, addr):
  self.addr = addr
  self.buf = bytearray(1024)
  self.previous = bytearray(1024)
  self.first_show = True
  for c in (174, 213, 128, 168, 63, 211, 0, 64, 141, 20, 32, 2, 161, 200, 218, 18, 129, 207, 217, 241, 219, 64, 164, 166, 175):
   i2c.write(addr, bytes((0, c)))

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

 def circle(self, cx, cy, radius):
  x = radius
  y = 0
  err = 1 - radius
  while x >= y:
   self.px(cx + x, cy + y)
   self.px(cx + y, cy + x)
   self.px(cx - y, cy + x)
   self.px(cx - x, cy + y)
   self.px(cx - x, cy - y)
   self.px(cx - y, cy - x)
   self.px(cx + y, cy - x)
   self.px(cx + x, cy - y)
   y += 1
   if err < 0:
    err += 2 * y + 1
   else:
    x -= 1
    err += 2 * (y - x) + 1

 def arrow(self, cx, cy, direction, radius=8):
  r = radius
  if direction == 0:
   self.line(cx, cy - r, cx - r, cy + 3)
   self.line(cx, cy - r, cx + r, cy + 3)
   self.line(cx, cy - r, cx, cy + r)
  elif direction == 1:
   self.line(cx + r, cy, cx - 3, cy - r)
   self.line(cx + r, cy, cx - 3, cy + r)
   self.line(cx - r, cy, cx + r, cy)
  elif direction == 2:
   self.line(cx, cy + r, cx - r, cy - 3)
   self.line(cx, cy + r, cx + r, cy - 3)
   self.line(cx, cy - r, cx, cy + r)
  else:
   self.line(cx - r, cy, cx + 3, cy - r)
   self.line(cx - r, cy, cx + 3, cy + r)
   self.line(cx - r, cy, cx + r, cy)

 def text(self, msg, x, y, scale=1):
  font = {'0': (7, 5, 5, 5, 7), '1': (2, 6, 2, 2, 7), '2': (7, 1, 7, 4, 7), '3': (7, 1, 7, 1, 7), '4': (5, 5, 7, 1, 1), '5': (7, 4, 7, 1, 7), '6': (7, 4, 7, 5, 7), '7': (7, 1, 1, 1, 1), '8': (7, 5, 7, 5, 7), '9': (7, 5, 7, 1, 7), 'A': (2, 5, 7, 5, 5), 'B': (6, 5, 6, 5, 6), 'C': (3, 4, 4, 4, 3), 'D': (6, 5, 5, 5, 6), 'E': (7, 4, 6, 4, 7), 'F': (7, 4, 6, 4, 4), 'G': (3, 4, 5, 5, 3), 'H': (5, 5, 7, 5, 5), 'I': (7, 2, 2, 2, 7), 'J': (1, 1, 1, 5, 2), 'K': (5, 5, 6, 5, 5), 'L': (4, 4, 4, 4, 7), 'M': (5, 7, 7, 5, 5), 'N': (5, 7, 7, 7, 5), 'O': (2, 5, 5, 5, 2), 'P': (6, 5, 6, 4, 4), 'Q': (2, 5, 5, 7, 3), 'R': (6, 5, 6, 5, 5), 'S': (3, 4, 2, 1, 6), 'T': (7, 2, 2, 2, 2), 'U': (5, 5, 5, 5, 7), 'V': (5, 5, 5, 5, 2), 'W': (5, 5, 7, 7, 5), 'X': (5, 5, 2, 5, 5), 'Y': (5, 5, 2, 2, 2), 'Z': (7, 1, 2, 4, 7), '-': (0, 0, 7, 0, 0), ':': (0, 2, 0, 2, 0), ' ': (0, 0, 0, 0, 0), '>': (4, 2, 1, 2, 4), '/': (1, 1, 2, 4, 4)}
  for c in str(msg).upper():
   glyph = font.get(c, font[' '])
   for yy in range(5):
    for xx in range(3):
     if glyph[yy] & 1 << 2 - xx:
      for sy in range(scale):
       for sx in range(scale):
        self.px(x + xx * scale + sx, y + yy * scale + sy)
   x += 4 * scale

 def show(self):
  for page in range(8):
   base = page * 128
   x = 0
   while x < 128:
    while x < 128 and (not self.first_show) and (self.buf[base + x] == self.previous[base + x]):
     x += 1
    if x >= 128:
     break
    start = x
    last_dirty = x
    x += 1
    while x < 128 and x - start < 28:
     if self.first_show or self.buf[base + x] != self.previous[base + x]:
      last_dirty = x
     elif x - last_dirty > 6:
      break
     x += 1
    end = last_dirty + 1
    i2c.write(self.addr, bytes((0, 176 | page, start & 15, 16 | start >> 4)))
    i2c.write(self.addr, b'@' + self.buf[base + start:base + end])
    for k in range(start, end):
     self.previous[k + base] = self.buf[k + base]
    if x < end:
     x = end
  self.first_show = False

 def show_lane_region(self, x0, x1):
  if x0 <= x1:
   self.show_rect(x0, x1, 3, 5)

 def show_rect(self, x0, x1, page0, page1):
  x0 = max(0, x0)
  x1 = min(127, x1)
  for page in range(page0, page1 + 1):
   base = page * 128
   x = x0
   while x <= x1:
    while x <= x1 and self.buf[base + x] == self.previous[base + x]:
     x += 1
    if x > x1:
     break
    start = x
    last_dirty = x
    x += 1
    while x <= x1 and x - start < 28:
     if self.buf[base + x] != self.previous[base + x]:
      last_dirty = x
     elif x - last_dirty > 6:
      break
     x += 1
    end = last_dirty + 1
    i2c.write(self.addr, bytes((0, 176 | page, start & 15, 16 | start >> 4)))
    i2c.write(self.addr, b'@' + self.buf[base + start:base + end])
    for k in range(start, end):
     self.previous[base + k] = self.buf[base + k]
    if x < end:
     x = end

 def erase_pages(self, x0, x1, p0, p1):
  for page in range(p0, p1 + 1):
   base = page * 128
   for x in range(x0, x1 + 1):
    self.buf[base + x] = 0

 def clear_band(self):
  for page in (3, 4, 5):
   base = page * 128
   for x in range(128):
    self.buf[base + x] = 0

def led_off():
 if USE_RGB:
  pin9.write_digital(1)
  pin14.write_digital(1)
  pin16.write_digital(1)

def led_judge(result):
 if not USE_RGB:
  return
 pin9.write_digital(0 if result in (1, 2) else 1)
 pin14.write_digital(0 if result in (0, 1) else 1)
 pin16.write_digital(1)
queue = []
screen_state = 'MENU'

def u16(data, offset):
 return data[offset] | data[offset + 1] << 8

class Melody:

 def __init__(self):
  self.index = 0
  self.next_at = u16(MELODY, 0) if MELODY else SONG_LENGTH_MS
  self.end_at = -1
  self.pitch = 0
  self.sounding = False

 def stop(self):
  music.stop(pin12)
  self.sounding = False

 def update(self, elapsed):
  if elapsed < 0:
   return
  changed = False
  while self.index < len(MELODY) and elapsed >= self.next_at:
   self.end_at = self.next_at + u16(MELODY, self.index + 2)
   self.pitch = MELODY[self.index + 4]
   self.index += 5
   if self.index < len(MELODY):
    self.next_at += u16(MELODY, self.index)
   changed = True
  if elapsed < self.end_at:
   if changed or not self.sounding:
    music.pitch(FREQUENCIES[self.pitch], duration=-1, pin=pin12, wait=False)
    self.sounding = True
  elif self.sounding:
   self.stop()

class ChartReader:

 def __init__(self):
  self.index = 0
  self.time_ms = 0

 def fill(self):
  while len(queue) < 12 and self.index < len(CHART):
   self.time_ms += u16(CHART, self.index)
   queue.append([self.time_ms, CHART[self.index + 2], 0, None])
   self.index += 3

def joy_direction(cx, cy):
 x = pin0.read_analog() - cx
 y = pin1.read_analog() - cy
 if abs(x) < 230 and abs(y) < 230:
  return -1
 if abs(x) >= abs(y):
  return 1 if x > 0 else 3
 return 0 if y > 0 else 2

def invert_strip(oled, y0, h):
 for y in range(y0, y0 + h):
  a = (y >> 3) * 128
  mask = 1 << (y & 7)
  for x in range(6, 122):
   oled.buf[a + x] ^= mask

def menu_draw(right, heading, options, index, footer):
 right.hud_combo = None
 right.clear()
 right.text(heading[:18], 4, 2)
 for i in range(min(4, len(options))):
  shown = max(0, min(index - 2, len(options) - 4)) if len(options) > 4 else 0
  k = shown + i
  if k >= len(options):
   break
  y = 16 + i * 9
  right.text(options[k][:25], 10, y)
  if k == index:
   invert_strip(right, y - 1, 8)
 right.text(footer[:28], 3, 57)
 right.show()

def draw_hud(right, combo, score):
 if getattr(right, 'hud_combo', None) is None:
  right.clear()
  right.text('COMBO', 23, 3, 2)
  right.line(8, 39, 119, 39)
  right.text('SCORE', 8, 48)
  right.text(str(combo), max(0, (128 - (4 * len(str(combo)) - 1) * 2) // 2), 22, 2)
  right.text(str(score), 40, 48)
  right.show()
 else:
  if combo != right.hud_combo:
   right.erase_pages(0, 127, 2, 3)
   cs = str(combo)
   right.text(cs, max(0, (128 - (4 * len(cs) - 1) * 2) // 2), 22, 2)
   right.show_rect(0, 127, 2, 3)
  if score != right.hud_score:
   right.erase_pages(40, 127, 6, 6)
   right.text(str(score), 40, 48)
   right.show_rect(40, 127, 6, 6)
 right.hud_combo = combo
 right.hud_score = score

def judgement_feedback(j, now):
 led_judge(j)
 pin8.write_digital(1 if j == 2 else 0)
 return (now + 130, 0)

def play(left, right):
 global screen_state, queue
 screen_state = 'PLAY'
 combo = 0
 score = 0
 best_combo = 0
 perf = 0
 good = 0
 miss = 0
 queue = []
 chart = ChartReader()
 chart.fill()
 melody = Melody()
 paused_at = 0
 paused = False
 last_inputs = [False] * 4
 feedback_until = 0
 last_frame = -FRAME_MS
 last_joy = joy_direction(center_x, center_y)
 hud_dirty = False
 left.clear()
 left.line(1, 18, 126, 18)
 left.line(1, 52, 126, 52)
 left.circle(32, 35, 10)
 left.show()
 right.hud_combo = None
 draw_hud(right, 0, 0)
 t0 = running_time() + 3500
 display.show('3')
 countdown = 3
 while True:
  now = running_time()
  d = joy_direction(center_x, center_y)
  if d != -1 and last_joy == -1:
   if not paused and d == 3:
    paused = True
    paused_at = now
    melody.stop()
    led_off()
    pin8.write_digital(0)
    menu_draw(right, 'PAUSED', ('LS RIGHT RESUME', 'LS DOWN EXIT'), 0, 'LS R / LS DOWN')
    display.show(Image.SQUARE)
   elif paused and d == 1:
    paused = False
    t0 += now - paused_at
    right.hud_combo = None
    draw_hud(right, combo, score)
    display.show(str(combo % 10))
    last_frame = -FRAME_MS
   elif paused and d == 2:
    melody.stop()
    led_off()
    pin8.write_digital(0)
    screen_state = 'MENU'
    return
  last_joy = d
  if paused:
   sleep(18)
   continue
  elapsed = now - t0
  if elapsed >= SONG_LENGTH_MS + 900:
   break
  melody.update(elapsed)
  chart.fill()
  if elapsed < 0:
   digit = min(3, max(1, (-elapsed + 999) // 1000))
   if digit != countdown:
    display.show(str(digit))
    countdown = digit
  elif countdown:
   display.show('0')
   countdown = 0
  if now >= feedback_until:
   led_off()
   pin8.write_digital(0)
  for n in queue:
   if n[2] == 0 and elapsed > n[0] + GOOD_MS:
    n[2] = 3
    miss += 1
    combo = 0
    hud_dirty = True
    feedback_until, _ = judgement_feedback(2, now)
  for j in range(4):
   down = DPADS[j].read_digital() == 0
   if down and (not last_inputs[j]):
    target = None
    dist = GOOD_MS + 1
    for n in queue:
     e = abs(elapsed - n[0])
     if n[2] == 0 and n[1] == j and (e < dist):
      target = n
      dist = e
    if target is not None:
     if dist <= PERFECT_MS:
      r = 0
     else:
      r = 1
     feedback_until, _ = judgement_feedback(r, now)
     target[2] = 1 if r == 0 else 2
     if r == 0:
      perf += 1
      score += 100
     else:
      good += 1
      score += 50
     combo += 1
     best_combo = max(best_combo, combo)
     hud_dirty = True
   last_inputs[j] = down
  if now - last_frame >= FRAME_MS:
   last_frame = now
   left.clear_band()
   left.circle(32, 35, 10)
   lo = 128
   hi = -1
   for n in queue:
    old = n[3]
    new = None
    if n[2] in (0, 3):
     dt = n[0] - elapsed
     if dt <= LEAD_MS:
      x = 32 + dt * 91 // LEAD_MS
      if x >= -7:
       new = x
       left.arrow(x, 35, n[1], 6)
      elif n[2] == 3:
       n[2] = 5
    if old is not None:
     lo = min(lo, old - 8)
     hi = max(hi, old + 8)
    if new is not None:
     lo = min(lo, new - 8)
     hi = max(hi, new + 8)
    n[3] = new
   left.show_lane_region(lo, hi)
   while queue and queue[0][0] < elapsed - 1600:
    queue.pop(0)
  if hud_dirty:
   display.show(str(combo % 10))
   draw_hud(right, combo, score)
   hud_dirty = False
  sleep(1)
 melody.stop()
 led_off()
 pin8.write_digital(0)
 left.clear()
 left.text('FINISH', 29, 14, 2)
 left.show()
 menu_draw(right, 'RESULT', ('SCORE ' + str(score), 'BEST ' + str(best_combo), 'P' + str(perf) + ' G' + str(good), 'MISS ' + str(miss)), 0, 'LS LEFT MENU')
 previous = -1
 while True:
  d = joy_direction(center_x, center_y)
  if d == 3 and previous == -1:
   break
  previous = d
  sleep(25)
 screen_state = 'MENU'
for b in DPADS:
 b.set_pull(b.PULL_UP)
led_off()
i2c.init(freq=400000)
left = OLED(60)
right = OLED(61)
pin8.write_digital(0)
music.stop(pin12)
center_x = pin0.read_analog()
center_y = pin1.read_analog()
previous = joy_direction(center_x, center_y)
last_action = 0
last_screen = ''
while True:
 now = running_time()
 d = joy_direction(center_x, center_y)
 if screen_state != last_screen:
  if screen_state == 'MENU':
   menu_draw(right, 'MEGALOVANIA', ('GENTLE MODE', 'LS RIGHT START'), 0, 'P12 SPEAKER')
   left.clear()
   left.text('READY', 24, 20, 2)
   left.show()
   display.show(Image.HAPPY)
  last_screen = screen_state
 if d != -1 and previous == -1 and (now - last_action > 200):
  last_action = now
  if screen_state == 'MENU' and d == 1:
   play(left, right)
   last_screen = ''
   d = joy_direction(center_x, center_y)
 previous = d
 sleep(12)
