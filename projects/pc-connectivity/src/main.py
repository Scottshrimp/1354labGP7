from microbit import *
from utime import ticks_ms, ticks_diff, ticks_add
import gc

FONT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-: >/"
FONT_ROWS = "7555726227717477171755711747177475771111757577571725755656563444365556746477464434553557557222711152556554444757755577752555265644255736565534216722225555755552557755525555222712470070002020000004212411244"


class OLED:
    def __init__(self, addr):
        self.addr = addr
        self.buf = bytearray(1024)
        self.previous = bytearray(1024)
        self.first_show = True
        for c in (
            0xAE,
            0xD5,
            0x80,
            0xA8,
            0x3F,
            0xD3,
            0x00,
            0x40,
            0x8D,
            0x14,
            0x20,
            0x02,
            0xA1,
            0xC8,
            0xDA,
            0x12,
            0x81,
            0xCF,
            0xD9,
            0xF1,
            0xDB,
            0x40,
            0xA4,
            0xA6,
            0xAF,
        ):
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
        for c in str(msg).upper():
            index = FONT_CHARS.find(c)
            if index < 0:
                index = FONT_CHARS.find(" ")
            for yy in range(5):
                row = ord(FONT_ROWS[index * 5 + yy]) - 48
                for xx in range(3):
                    if row & (1 << (2 - xx)):
                        for sy in range(scale):
                            for sx in range(scale):
                                self.px(x + (xx * scale) + sx, y + (yy * scale) + sy)
            x += 4 * scale

    def show(self):
        self.show_rect(0, 127, 0, 7)
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
                while (
                    x <= x1
                    and not self.first_show
                    and self.buf[base + x] == self.previous[base + x]
                ):
                    x += 1
                if x > x1:
                    break
                start = x
                last_dirty = x
                x += 1
                while x <= x1 and x - start < 28:
                    if self.first_show or self.buf[base + x] != self.previous[base + x]:
                        last_dirty = x
                    elif x - last_dirty > 6:
                        break
                    x += 1
                end = last_dirty + 1
                i2c.write(
                    self.addr, bytes((0, 0xB0 | page, start & 15, 0x10 | (start >> 4)))
                )
                i2c.write(self.addr, b"\x40" + self.buf[base + start : base + end])
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



def draw_hud(right, combo, score):
    if getattr(right, "hud_combo", None) is None:
        right.clear()
        right.text("COMBO", 23, 3, 2)
        right.line(8, 39, 119, 39)
        right.text("SCORE", 8, 48)
        right.text(
            str(combo), max(0, (128 - (4 * len(str(combo)) - 1) * 2) // 2), 22, 2
        )
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


# Wire protocol: one acknowledged command in flight, bounded ASCII frames.
# Chart records contain little-endian 24-bit milliseconds and one direction byte.
DPADS = (pin13, pin11, pin15, pin5)
MAX_NOTES = 2000
chart = bytearray()
count = duration = checksum = 0
state = 'IDLE'
round_id = 0
score = combo = best = misses = 0
start_at = 0
last_host = ticks_ms()
last_report = 0
last_frame = 0
last_seq = -1
last_reply = ''
rx = bytearray()
discard = False
pressed = [False] * 4
judged = bytearray()
feedback_until = None
last_digit = None


def feedback_off():
    global feedback_until
    pin9.write_digital(1)
    pin14.write_digital(1)
    pin16.write_digital(1)
    pin8.write_digital(0)
    feedback_until = None


def judgement_feedback(result, now):
    global feedback_until
    pin9.write_digital(0 if result in (1, 2) else 1)
    pin14.write_digital(0 if result in (0, 1) else 1)
    pin16.write_digital(1)
    pin8.write_digital(1 if result == 2 else 0)
    feedback_until = ticks_add(now, 130)


def show_digit(value):
    global last_digit
    if value != last_digit:
        display.show(str(value))
        last_digit = value


def send(line):
    uart.write(line + '\n')


def status():
    send('S,%s,%s,%s,%s,%s,%s' % (round_id, state, score, combo, best, misses))


def note_time(i):
    j = i * 4
    return chart[j] | (chart[j + 1] << 8) | (chart[j + 2] << 16)


def chart_checksum(data):
    a = b = 0
    for value in data:
        a = (a + value) % 255
        b = (b + a) % 255
    return (b << 8) | a


def command(line, now):
    global chart, count, duration, checksum, state, round_id, start_at
    global last_seq, last_reply, last_host, score, combo, best, misses, judged, last_digit
    p = line.split(',')
    if len(p) < 3 or p[0] != 'C':
        return
    try:
        seq = int(p[1])
    except ValueError:
        return
    try:
        if seq == last_seq:
            send(last_reply)
            last_host = now
            return
        action = p[2]
        result = 'OK'
        if action == 'PING' and len(p) == 3:
            result = str(now)
        elif action == 'CLOCK' and len(p) == 3:
            result = str(ticks_add(0, -1) + 1)
        elif action == 'BEGIN' and len(p) == 7 and state not in ('PLAY', 'START'):
            rid, n, length, check = [int(v) for v in p[3:]]
            if not 0 < n <= MAX_NOTES or not 0 < length < 16777216 or not 0 <= check <= 65535:
                raise ValueError()
            round_id, count, duration, checksum = rid, n, length, check
            chart = bytearray()
            judged = bytearray()
            state = 'LOAD'
            feedback_off()
            display.clear()
            last_digit = None
            score = combo = best = misses = 0
        elif action == 'DATA' and len(p) == 5 and state == 'LOAD':
            offset = int(p[3])
            if offset != len(chart) or len(p[4]) % 2 or len(p[4]) > 32:
                raise ValueError()
            part = bytearray()
            for j in range(0, len(p[4]), 2):
                part.append(int(p[4][j:j + 2], 16))
            if len(chart) + len(part) > count * 4:
                raise ValueError()
            chart.extend(part)
        elif action == 'END' and len(p) == 3 and state == 'LOAD':
            if len(chart) != count * 4 or chart_checksum(chart) != checksum:
                raise ValueError()
            previous = -1
            for i in range(count):
                stamp = note_time(i)
                if stamp < previous or stamp >= duration or chart[i * 4 + 3] > 3:
                    raise ValueError()
                previous = stamp
            judged = bytearray(count)
            state = 'READY'
            gc.collect()
        elif action == 'START' and len(p) == 5 and state == 'READY':
            if int(p[3]) != round_id:
                raise ValueError()
            target = int(p[4])
            if not 500 <= ticks_diff(target, now) <= 10000:
                raise ValueError()
            start_at = target
            state = 'START'
        elif action == 'STOP' and len(p) == 3:
            state = 'DONE'
            feedback_off()
        else:
            raise ValueError()
        last_host = now
    except (ValueError, IndexError, MemoryError):
        result = 'ERR'
    last_seq = seq
    last_reply = 'A,%s,%s' % (seq, result)
    # Report the final score before STOP's ACK, so it is received before ranking.
    status()
    send(last_reply)


def service(now):
    global rx, discard, state
    if uart.any():
        data = uart.read(64) or b''
        for c in data:
            if c == 10:
                if rx and not discard:
                    try:
                        command(rx.decode('ascii'), now)
                    except (UnicodeError, ValueError):
                        pass
                rx = bytearray()
                discard = False
            elif len(rx) >= 60 or c < 32 or c > 126:
                discard = True
            elif not discard:
                rx.append(c)
    if state in ('LOAD', 'READY', 'START', 'PLAY') and ticks_diff(now, last_host) > 4000:
        state = 'FAULT'
        feedback_off()
        status()


def render(elapsed):
    left.clear_band()
    left.circle(32, 35, 10)
    for i in range(count):
        if judged[i] and judged[i] != 3:
            continue
        dt = note_time(i) - elapsed
        if -1285 <= dt <= 3000:
            x = 32 + dt * 91 // 3000
            left.arrow(x, 35, chart[i * 4 + 3], 6)
        elif dt > 3000:
            break
    left.show_lane_region(0, 127)
    draw_hud(right, combo, score)


def update(now):
    global state, score, combo, best, misses, last_report, last_frame
    if feedback_until is not None and ticks_diff(now, feedback_until) >= 0:
        feedback_off()
    if state == 'START' and ticks_diff(now, start_at) >= 0:
        state = 'PLAY'
    if state not in ('START', 'PLAY'):
        return
    elapsed = ticks_diff(now, start_at)
    if elapsed >= duration + 500:
        state = 'DONE'
        feedback_off()
        status()
        return
    if elapsed < 0:
        show_digit(min(3, max(1, (-elapsed + 999) // 1000)))
    else:
        show_digit(combo % 10)
    for i in range(count):
        if not judged[i] and elapsed > note_time(i) + 400:
            judged[i] = 3
            misses += 1
            combo = 0
            judgement_feedback(2, now)
            show_digit(0)
        elif note_time(i) > elapsed + 400:
            break
    for direction in range(4):
        down = DPADS[direction].read_digital() == 0
        if down and not pressed[direction]:
            target, distance = -1, 401
            for i in range(count):
                if not judged[i] and chart[i * 4 + 3] == direction:
                    d = abs(elapsed - note_time(i))
                    if d < distance:
                        target, distance = i, d
                    if note_time(i) > elapsed + 400:
                        break
            if target >= 0:
                judged[target] = 1
                result = 0 if distance <= 220 else 1
                score += 100 if result == 0 else 50
                combo += 1
                best = max(best, combo)
                judgement_feedback(result, now)
                show_digit(combo % 10)
        pressed[direction] = down
    if ticks_diff(now, last_frame) >= 40:
        render(elapsed)
        last_frame = now
    if ticks_diff(now, last_report) >= 250:
        status()
        last_report = now


for button in DPADS:
    button.set_pull(button.PULL_UP)
feedback_off()
display.clear()
i2c.init(freq=400000)
left = OLED(0x3C)
right = OLED(0x3D)
left.clear()
left.line(1, 18, 126, 18)
left.line(1, 52, 126, 52)
left.circle(32, 35, 10)
left.show()
right.hud_combo = None
draw_hud(right, 0, 0)
uart.init(baudrate=115200)
while True:
    now = ticks_ms()
    service(now)
    update(now)
    sleep(2)
