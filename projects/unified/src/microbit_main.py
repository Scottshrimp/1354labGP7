from microbit import *
import music
import gc
from utime import ticks_ms, ticks_diff, ticks_add
from random import getrandbits
from connection import ModeSupervisor, PC, STANDALONE
from protocol import LineFramer


def decode64(text):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    data = bytearray()
    value = bits = 0
    for char in text:
        value = (value << 6) | alphabet.index(char)
        bits += 6
        if bits >= 8:
            bits -= 8
            data.append((value >> bits) & 255)
            value &= (1 << bits) - 1
    return data


def unpack(text):
    source = decode64(text)
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
                distance = source[i] | (source[i + 1] << 8)
                i += 2
                for _ in range(length):
                    output.append(output[-distance])
    return output


LEAD_MS = 3000
PERFECT_MS = 220
GOOD_MS = 400
FRAME_MS = 20
USE_RGB = True
# BEGIN GENERATED SONG
SONG_LENGTH_MS = 159196
MELODY_DATA = ('AAAAAHUAAD6CAAB2AAA+gwAA6wAASgUBYAFFhwHrAABEBQHrAABDAAQFAEEFAQAHIwBBgwAAdQAAQ4IAAHUAADwABA8APAAgMgB1AABBAAQoAEMABDcAOwAECgA7ACwyADoABAoAOgAsMgAAHMgA6gAAQQQBAAUeAAAMMgAAHMgAABYyAAAcyAAAFjIAAAjIAOoAAEoEAWEBRYgAITIASgAECgBKAAQyAFYABDIAUQAEMgBQAAQtAE8EAesAAE0FAQAFHgB1AABNAAQoAE8ABAoASAAECgBIACwyAEcABDsBR4IAAOsAAFYFACYyAEYABDIARgAMMgDqAABQAAQtAE8ABM0AABQyAEoABDIASgAlMgB1AABPAAfDAAAFzQAAKjIARwAHzQAABTIAYAFRAASQAVAABC0AABkyAEYAB80AABkyAAAHgQFNAAQoAAAFMgAABUYATQAE9AFNAAQiAU0AByIBAAUDAksCSowCAAdpAE0ABIEBAAUeAAAFSwBQAAQUAAAFCQEABRMBAAiHAGABT4cABC0AABYyAOsAAFEABIIAVAAJmwBWAAQUAFYABBQAVgAERgBRAARGAFaCAAAhBFSWBHYABC0AAAUUAOoAAFEABEYAUQAHQQAABVAASwJPjAIABSMAdQAAUQAE8AAADR4AAAcKAAAFWgAABR4AAAUUAAAFbgAACiMAAAXwAFQADIEB6wAATAAEBQBGAAQ3AAAFdgJKAAcZACEEVKoIAAdoAQAPQAFQAApKAQAHFwI6AABQQQAAOgAAT0EAADsAAE1CAAA6AABKQQAEHQEFAasDT5YEAAUJAQAFlgAABQkBAAUKAAAURgB1AABMAAS5AAAFlgAACtIAVAAEBQBVAAdPAXUAAFAACY8CTQAENgEABV8AQQAJfwNFAAfMAdYBTAoC1gFKAAQFAEwKAtUBTQkC1gFPAAcPAKsDURMABG0BAARGAAAKUABOAASCAAAF2wFMAAQPAEsAB+UBNgNJkQMhBEupCAAKqgAACg4BAA+RAAAFMgAACg4BOgAATQAEEwFKQgAEHgAEAawACQ4BAAd9AAAIDgEAFEYAABkOAeoAAFUABOYAAAVGAAANRQEABQ4BAAWDBAAHVQVFAAfMAQAKDgHVAUwABAkBTQAEDwBPAAcPAKwDURQEABGVAU4ACYwAAAgOAQAF+gAACA4BlgSBBToeBtUBQQAEQQBAFASrAz4TBFYHQU4QgAU6HQbWAUEKAA0ZAD5OEAAHGQU+AATXAABOmgYADDIAACaaBgAyMgAAKJoGABYyAAAuYgeIAbAAAE2wAARNA1UABAgCAAQtAEgABCMATAAE/gFKAARjBkUACScGSgAtLQAABIIARgAJ8gMABTcFAAgPAAAFBQDqAABGAAQyAEYACSgASAAEFABIAAQUAEgABBQASAAHFAAAFhkASgAJcwAABWkAAAVMBEkABBQASQAElAJJAASyAkkABBkASQAYQQBHAAQUAEcABC0ARwAELQBHAAQZAAAFFABGAAQUAEYABBQAAAqbAAAIrwAADxkAAAVVAAAFUAAACloAAAoUAAARGQBKAAQZAEoAB1kGAArDAAAHvgAACBkAABQUAAAgLQAACKUAAAWbAAAKqgAAFhkAAA2bAAAPrwAAB9EBAAVJBwAIaAEAEW4AAAVUAQAFBQBJAAQtAEkABC0AAAhoAQARQQBHAAdtAQAFBQAAB3EHAAUPAAAcHAIAERkAABRaAAAXtAAAMvwDADIyAAAFlwkABaEJACoyADwAB50DACouBAAyXgsALjIA')
CHART = unpack('JwgAABMEAAAUBAETBAEUBAITBAIUBAMTBAMUBAAKGABiFAAWGAAABRUAAgAFFQADYRQAAAAFGwABAAUbAAAKGAAABS0AAAcYAGEAF0gAAAx4AGIUAByQAAAJSAAAFWAAABWQAAAz2AAADDAAACfYAAAMGAATBAAA')
FREQUENCIES = {58: 233, 59: 247, 60: 262, 62: 294, 64: 330, 65: 349, 67: 392, 68: 415, 69: 440, 70: 466, 71: 494, 72: 523, 73: 554, 74: 587, 75: 622, 76: 659, 77: 698, 78: 740, 79: 784, 80: 831, 81: 880, 84: 1047, 85: 1109, 86: 1175}
# END GENERATED SONG
MELODY = None


def load_melody():
    global MELODY
    if MELODY is None:
        gc.collect()
        MELODY = unpack(MELODY_DATA)
        gc.collect()


DPADS = (pin13, pin11, pin15, pin5)
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
screen_state = "MENU"


def u16(data, offset):
    return data[offset] | (data[offset + 1] << 8)


class Melody:
    """Consume packed events on the same millisecond clock as the chart."""

    def __init__(self):
        load_melody()
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


def judgement_feedback(j, now):
    led_judge(j)
    pin8.write_digital(1 if j == 2 else 0)
    return ticks_add(now, 130), 0


# RH1 stop-and-wait transport. Only this module reads/writes the board UART.
def new_nonce():
    # micro:bit getrandbits only supports 1..30 bits per call.
    return "%04x%04x" % (getrandbits(16), getrandbits(16))


supervisor = ModeSupervisor(ticks_diff=ticks_diff)
framer = LineFramer()
nonce = new_nonce()
last_hello = ticks_add(ticks_ms(), -1000)
expected_seq = 0
catalog = []
catalog_count = 0
menu_index = 0
round_id = 0
song_length = 0
note_count = 0
next_note = 0
chart_ended = False
synced = False
sync_at = 0
data_at = 0
last_need = 0
last_screen = ""
events = []
event_seq = 0
event_at = 0
sent_event = -1
last_gc = ticks_ms()


def wire(*fields):
    line = ",".join(str(value) for value in fields)
    if len(line) <= 60:
        uart.write(line + "\n")


def send_event(command, *values):
    global event_seq
    if supervisor.lease.session:
        if command == "NEED" and any(e[1] == "NEED" for e in events):
            return
        events.append((event_seq, command) + values)
        event_seq = (event_seq + 1) % 65536


def outputs_off():
    global MELODY
    music.stop(pin12)
    MELODY = None
    led_off()
    pin8.write_digital(0)


def return_to_menu(stop):
    global screen_state, queue, last_screen
    if stop and supervisor.mode == PC:
        send_event("STOP", round_id)
    outputs_off()
    queue = []
    supervisor.set_phase("menu", ticks_ms())
    screen_state = "MENU"
    last_screen = ""


def apply_actions(actions):
    global nonce, catalog, queue, screen_state, last_screen, menu_index
    if "enter_standalone" in actions or "enter_pc" in actions:
        outputs_off()
        queue = []
        screen_state = "MENU"
        last_screen = ""
        menu_index = 0
    if "enter_standalone" in actions:
        catalog = []
    if supervisor.lease.session is None:
        framer.reset()
        events[:] = []
        nonce = new_nonce()


def command(parts, now):
    global catalog, catalog_count, song_length, note_count, next_note
    global chart_ended, screen_state, synced, sync_at, data_at, last_screen
    kind = parts[0]
    if kind == "EA" and len(parts) == 2:
        if events and int(parts[1]) == events[0][0]:
            events.pop(0)
        return
    if kind == "HB" and len(parts) == 1:
        return
    if kind == "CATBEGIN" and len(parts) == 2 and not supervisor.host_ready:
        count = int(parts[1])
        if not 1 <= count <= 12:
            raise ValueError()
        catalog = []
        catalog_count = count
        return
    if kind == "CAT" and len(parts) == 3 and not supervisor.host_ready:
        index = int(parts[1])
        if index != len(catalog) or index >= catalog_count:
            raise ValueError()
        catalog.append((index, parts[2][:18]))
        return
    if (
        kind == "READY"
        and len(parts) == 1
        and len(catalog) == catalog_count
        and catalog_count
    ):
        apply_actions(supervisor.mark_host_ready(supervisor.lease.session, now))
        return
    if kind == "BYE" and len(parts) == 1:
        # Expiry is applied after ACK so the sender can close cleanly.
        supervisor.lease.last_seen_ms = ticks_add(now, -3000)
        return
    if supervisor.mode != PC or len(parts) < 2:
        raise ValueError()
    if (
        int(parts[1]) != round_id
        or screen_state == "MENU"
        or supervisor.phase == "results"
    ):
        return  # An already-sent old-round frame may arrive after cancellation.
    if kind == "BEGIN" and len(parts) == 4 and screen_state == "LOADING":
        duration, count = int(parts[2]), int(parts[3])
        if not 0 < duration <= 3600000 or not 0 < count <= 10000:
            raise ValueError()
        song_length, note_count, next_note = duration, count, 0
        chart_ended = False
        data_at = now
    elif (
        kind == "N" and len(parts) == 5 and screen_state in ("LOADING", "ARMED", "PLAY")
    ):
        index, stamp, direction = int(parts[2]), int(parts[3]), int(parts[4])
        if (
            index != next_note
            or index >= note_count
            or len(queue) >= 48
            or not 0 <= stamp < song_length
            or not 0 <= direction < 4
            or (queue and stamp < queue[-1][0])
        ):
            raise ValueError()
        queue.append([stamp, direction, 0, None])
        next_note += 1
        data_at = now
    elif kind == "END" and len(parts) == 2 and next_note == note_count:
        chart_ended = True
    elif kind == "ARM" and len(parts) == 2 and screen_state == "LOADING" and next_note:
        screen_state = "ARMED"
        supervisor.set_phase("ready", now)
    elif kind == "SYNC" and len(parts) == 2 and screen_state == "PLAY" and not synced:
        sync_at = ticks_add(now, 2700)
        synced = True
        send_event("SYNCED", round_id)
    elif kind == "ERROR" and len(parts) == 2:
        return_to_menu(True)
    else:
        raise ValueError()


def receive(line, now):
    global expected_seq, event_seq, sent_event, catalog, catalog_count, menu_index
    parts = line.split(",")
    if (
        len(parts) == 4
        and parts[:2] == ["RH1", "ATTACH"]
        and parts[2] == nonce
        and len(parts[3]) == 8
        and all(c in "0123456789abcdef" for c in parts[3])
    ):
        session = nonce + parts[3]
        fresh = supervisor.lease.session is None
        if supervisor.attach_host(session, now):
            if fresh:
                expected_seq = event_seq = 0
                sent_event = -1
                catalog = []
                catalog_count = 0
                menu_index = 0
                events[:] = []
            wire("RH1", "ACCEPT", session)
        return
    if len(parts) < 4 or parts[0] != "RH1" or parts[1] != supervisor.lease.session:
        return
    try:
        seq = int(parts[2])
        if seq == (expected_seq - 1) % 65536:
            wire("RH1", parts[1], "A", seq, "OK")
            return
        if seq != expected_seq:
            return
        command(parts[3:], now)
        supervisor.heartbeat(parts[1], now)
        expected_seq = (expected_seq + 1) % 65536
        wire("RH1", parts[1], "A", seq, "OK")
    except (ValueError, IndexError):
        wire("RH1", parts[1], "A", parts[2], "BAD")


def service():
    global nonce, last_hello, event_at, sent_event, last_gc
    now = ticks_ms()
    had_session = supervisor.lease.session is not None
    actions = supervisor.poll(now)
    if actions or (had_session and supervisor.lease.session is None):
        apply_actions(actions)
    if ticks_diff(now, last_gc) >= 1000:
        gc.collect()
        last_gc = now
    # Avoid allocating an empty receive list on every idle poll.
    if uart.any():
        for line in framer.feed(uart.read(64)):
            receive(line, now)
    if events and (events[0][0] != sent_event or ticks_diff(now, event_at) >= 600):
        wire("RH1", supervisor.lease.session, "E", *events[0])
        sent_event = events[0][0]
        event_at = now
    if supervisor.lease.session is None and ticks_diff(now, last_hello) >= 800:
        wire("RH1", "HELLO", nonce)
        last_hello = now


def request_notes(now):
    global last_need
    if not chart_ended and len(queue) < 32 and ticks_diff(now, last_need) >= 500:
        send_event("NEED", round_id, next_note, 44 - len(queue))
        last_need = now


def play(left, right):
    global screen_state, queue, MELODY
    pc = supervisor.mode == PC
    supervisor.set_phase("playing", ticks_ms())
    lead, perfect, good_window = (1700, 100, 210) if pc else (3000, 220, 400)
    duration = song_length if pc else SONG_LENGTH_MS
    screen_state = "PLAY"
    combo = 0
    score = 0
    best_combo = 0
    perf = 0
    good = 0
    miss = 0
    if not pc:
        queue = []
    chart = None if pc else ChartReader()
    if chart:
        chart.fill()
    melody = None if pc else Melody()
    paused_at = 0
    paused = False
    last_inputs = [False] * 4
    feedback_until = ticks_ms()
    last_frame = ticks_add(ticks_ms(), -FRAME_MS)
    last_joy = joy_direction(center_x, center_y)
    hud_dirty = False
    last_led = -1
    progress = Image(5, 5)
    left.clear()
    left.line(1, 18, 126, 18)
    left.line(1, 52, 126, 52)
    left.circle(32, 35, 10)
    left.show()
    right.hud_combo = None
    draw_hud(right, 0, 0)
    # Leave time to see the first cue before music begins.
    if pc:
        send_event("START", round_id)
        deadline = ticks_add(ticks_ms(), 8000)
        while not synced:
            service()
            if supervisor.mode != PC or ticks_diff(ticks_ms(), deadline) >= 0:
                return_to_menu(True)
                return
            sleep(2)
        t0 = sync_at
    else:
        t0 = ticks_add(ticks_ms(), 3500)
    display.show("3")
    countdown = 3
    while True:
        service()
        if pc and supervisor.mode != PC:
            return
        now = ticks_ms()
        d = joy_direction(center_x, center_y)
        if d != -1 and last_joy == -1:
            if not paused and d == 3:
                paused = True
                paused_at = now
                supervisor.set_phase("paused", now)
                if pc:
                    send_event("PAUSE", round_id)
                else:
                    melody.stop()
                led_off()
                pin8.write_digital(0)
                menu_draw(
                    right,
                    "PAUSED",
                    ("LS RIGHT RESUME", "LS DOWN EXIT"),
                    0,
                    "LS R / LS DOWN",
                )
            elif paused and d == 1:
                paused = False
                t0 = ticks_add(t0, ticks_diff(now, paused_at))
                supervisor.set_phase("playing", now)
                if pc:
                    send_event("RESUME", round_id)
                right.hud_combo = None
                draw_hud(right, combo, score)
                last_frame = ticks_add(now, -FRAME_MS)
            elif paused and d == 2:
                return_to_menu(pc)
                return
        last_joy = d
        if paused:
            sleep(18)
            continue
        elapsed = ticks_diff(now, t0)
        if elapsed >= duration + 900:
            break
        if pc:
            request_notes(now)
            if (
                not chart_ended
                and not any(n[2] == 0 for n in queue)
                and ticks_diff(now, data_at) > 4000
            ):
                send_event("STARVED", round_id)
                return_to_menu(True)
                return
        else:
            melody.update(elapsed)
            chart.fill()
        if elapsed < 0:
            digit = min(3, max(1, (-elapsed + 999) // 1000))
            if digit != countdown:
                display.show(str(digit))
                countdown = digit
        elif countdown:
            countdown = 0
        if ticks_diff(now, feedback_until) >= 0:
            led_off()
            pin8.write_digital(0)

        for n in queue:
            if n[2] == 0 and elapsed > n[0] + good_window:
                n[2] = 3
                miss += 1
                combo = 0
                hud_dirty = True
                feedback_until, _ = judgement_feedback(2, now)
        for j in range(4):
            down = DPADS[j].read_digital() == 0
            if down and not last_inputs[j]:
                target = None
                dist = good_window + 1
                for n in queue:
                    e = abs(elapsed - n[0])
                    if n[2] == 0 and (pc or n[1] == j) and e < dist:
                        target = n
                        dist = e
                if target is not None:
                    if target[1] != j:
                        r = 2
                    elif dist <= perfect:
                        r = 0
                    else:
                        r = 1
                    feedback_until, _ = judgement_feedback(r, now)
                    if r == 2:
                        target[2] = 3
                        miss += 1
                        combo = 0
                    else:
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
        if ticks_diff(now, last_frame) >= FRAME_MS:
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
                    if dt <= lead:
                        x = 32 + (dt * 91) // lead
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
            draw_hud(right, combo, score)
            hud_dirty = False
        # The song clock excludes countdown and paused time, in both modes.
        if elapsed >= 0:
            filled = min(25, elapsed * 25 // duration)
            if filled != last_led:
                for index in range(25):
                    progress.set_pixel(
                        index % 5, index // 5, 9 if index < filled else 0
                    )
                display.show(progress)
                last_led = filled
        sleep(1)
    if pc:
        send_event("DONE", round_id, score, miss)
    else:
        melody.stop()
        MELODY = None
        gc.collect()
    supervisor.set_phase("results", ticks_ms())
    led_off()
    pin8.write_digital(0)
    left.clear()
    left.text("FINISH", 29, 14, 2)
    left.show()
    menu_draw(
        right,
        "RESULT",
        (
            "SCORE " + str(score),
            "BEST " + str(best_combo),
            "P" + str(perf) + " G" + str(good),
            "MISS " + str(miss),
        ),
        0,
        "LS LEFT MENU",
    )
    previous = -1
    while True:
        service()
        if pc and supervisor.mode != PC:
            return
        d = joy_direction(center_x, center_y)
        if d == 3 and previous == -1:
            break
        previous = d
        sleep(25)
    return_to_menu(False)


for button in DPADS:
    button.set_pull(button.PULL_UP)
outputs_off()
i2c.init(freq=400000)
left = OLED(0x3C)
right = OLED(0x3D)
uart.init(baudrate=115200)
gc.collect()
center_x = pin0.read_analog()
center_y = pin1.read_analog()
previous = joy_direction(center_x, center_y)
last_action = ticks_ms()

while True:
    service()
    now = ticks_ms()
    direction = joy_direction(center_x, center_y)
    screen_key = supervisor.mode + screen_state
    if screen_key != last_screen:
        gc.collect()
        if screen_state == "MENU":
            if supervisor.mode == PC:
                menu_draw(
                    right,
                    "PC SONGS",
                    [s[1] for s in catalog],
                    menu_index,
                    "LS RIGHT SELECT",
                )
            else:
                menu_draw(
                    right,
                    "MEGALOVANIA",
                    ("STANDALONE", "LS RIGHT START"),
                    0,
                    "P12 SPEAKER",
                )
            left.clear()
            left.text("READY", 24, 20, 2)
            left.show()
            display.show(Image.HAPPY)
        elif screen_state == "LOADING":
            menu_draw(right, "PC LOADING", ("WAIT FOR CHART",), 0, "")
        elif screen_state == "ARMED":
            menu_draw(right, "PC READY", ("LS RIGHT PLAY", "LS LEFT CANCEL"), 0, "")
        last_screen = screen_key
    if direction != -1 and previous == -1 and ticks_diff(now, last_action) > 200:
        last_action = now
        if screen_state == "MENU":
            if supervisor.mode == PC:
                if direction == 0:
                    menu_index = (menu_index - 1) % len(catalog)
                    last_screen = ""
                elif direction == 2:
                    menu_index = (menu_index + 1) % len(catalog)
                    last_screen = ""
                elif direction == 1:
                    queue = []
                    chart_ended = False
                    synced = False
                    next_note = note_count = 0
                    round_id = (round_id + 1) % 65536
                    supervisor.set_phase("loading", now)
                    screen_state = "LOADING"
                    data_at = now
                    send_event("SELECT", round_id, menu_index)
            elif direction == 1:
                play(left, right)
                last_screen = ""
                direction = joy_direction(center_x, center_y)
        elif screen_state == "ARMED":
            if direction == 1:
                play(left, right)
                last_screen = ""
                direction = joy_direction(center_x, center_y)
            elif direction == 3:
                return_to_menu(True)
    if screen_state == "LOADING" and ticks_diff(now, data_at) > 12000:
        return_to_menu(True)
    previous = direction
    sleep(12)
