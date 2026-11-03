#!/usr/bin/env python3
"""Convert the supplied standard MIDI and editor JSON into a compact board bundle."""
import argparse
import bisect
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'src'
SONG = ROOT / 'music' / 'megalovania'
DIRECTIONS = ('UP', 'RIGHT', 'DOWN', 'LEFT')


def read_midi(path):
    data = path.read_bytes()
    if data[:4] != b'MThd':
        raise ValueError('Not a MIDI file')
    header_size = int.from_bytes(data[4:8], 'big')
    fmt, count, division = struct.unpack('>HHH', data[8:14])
    if fmt not in (0, 1) or division & 0x8000:
        raise ValueError('Only synchronous PPQN MIDI types 0 and 1 are supported')
    pos = 8 + header_size
    tracks, tempos = [], [(0, 500000)]
    for track_id in range(count):
        if data[pos:pos + 4] != b'MTrk':
            raise ValueError('Missing track chunk')
        length = int.from_bytes(data[pos + 4:pos + 8], 'big')
        chunk = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        i, tick, status = 0, 0, None
        active, notes, names, programs = {}, [], [], set()

        def vlq():
            nonlocal i
            value = 0
            while True:
                b = chunk[i]
                i += 1
                value = (value << 7) | (b & 127)
                if b < 128:
                    return value

        while i < len(chunk):
            tick += vlq()
            if chunk[i] >= 128:
                status = chunk[i]
                i += 1
            if status == 255:
                kind = chunk[i]
                i += 1
                n = vlq()
                value = chunk[i:i + n]
                i += n
                if kind == 81:
                    tempos.append((tick, int.from_bytes(value, 'big')))
                elif kind in (3, 4):
                    names.append(value.decode('utf-8', 'replace'))
                status = None
                continue
            if status in (240, 247):
                n = vlq()
                i += n
                status = None
                continue
            if status is None:
                raise ValueError('Invalid running status')
            kind, channel = status >> 4, status & 15
            n = 1 if kind in (12, 13) else 2
            values = chunk[i:i + n]
            i += n
            if kind == 12:
                programs.add(values[0])
            if kind == 9 and values[1] > 0:
                active.setdefault((channel, values[0]), []).append((tick, values[1]))
            elif kind == 8 or (kind == 9 and values[1] == 0):
                key = (channel, values[0])
                if active.get(key):
                    start, velocity = active[key].pop(0)
                    if channel != 9 and tick > start:
                        notes.append((start, tick, values[0], velocity))
        tracks.append({'id': track_id, 'names': names, 'programs': sorted(programs), 'notes': notes})
    tempo_map = sorted(dict(tempos).items())
    ticks, times, rates = [], [], []
    elapsed, previous, rate = 0.0, 0, 500000
    for tick, next_rate in tempo_map:
        elapsed += (tick - previous) * rate / division / 1000
        ticks.append(tick)
        times.append(elapsed)
        rates.append(next_rate)
        previous, rate = tick, next_rate

    def milliseconds(tick):
        index = bisect.bisect_right(ticks, tick) - 1
        return round(times[index] + (tick - ticks[index]) * rates[index] / division / 1000)

    return tracks, milliseconds, tempo_map, division


def melody_segments(path):
    tracks, ms, tempos, division = read_midi(Path(path))
    # This supplied MIDI has a lead on track 3 and accompaniment on track 4.
    lead = tracks[3]['notes']
    if not lead:
        raise ValueError('Expected melody on track 3')
    # Short gaps preserve repeated-note attacks instead of merging them into a drone.
    voiced = [(ms(a), ms(a) + max(1, round((ms(b) - ms(a)) * 0.90)), pitch, velocity)
              for a, b, pitch, velocity in lead]
    boundaries = sorted({t for a, b, pitch, velocity in voiced for t in (a, b)})
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        sounding = [n for n in voiced if n[0] <= start < n[1]]
        if sounding:
            pitch = max(n[2] for n in sounding)
            segments.append((start, end, pitch))
    return segments, lead, ms, tempos, division


def write_preview(path, segments):
    """Create a temporary mono WAV for the existing editor's audio preview."""
    import array
    import math
    import wave
    rate = 22050
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        cursor = 0
        for start, end, pitch in segments:
            begin, finish = round(start * rate / 1000), round(end * rate / 1000)
            if begin > cursor:
                output.writeframesraw(b'\x00\x00' * (begin - cursor))
            frequency = 440 * 2 ** ((pitch - 69) / 12)
            length = finish - begin
            samples = array.array('h', (int(8000 * min(1, i / 90, (length - i) / 90)
                                       * math.sin(2 * math.pi * frequency * i / rate))
                                       for i in range(length)))
            import sys
            if sys.byteorder != 'little':
                samples.byteswap()
            output.writeframesraw(samples.tobytes())
            cursor = finish


def compress(data):
    """Small LZ backreferences; the board decoder needs only bytearray."""
    data = bytes(data)
    output = bytearray()
    index = 0
    while index < len(data):
        length, distance = 0, 0
        for size in range(4, min(255, len(data) - index) + 1):
            match = data.rfind(data[index:index + size], max(0, index - 65535), index)
            if match < 0:
                break
            length, distance = size, index - match
        if length:
            output.extend((0, length, distance & 255, distance >> 8))
            index += length
        else:
            value = data[index]
            output.extend((0, 0) if value == 0 else (value,))
            index += 1
    return bytes(output)


def write_deployment(source):
    import ast
    tree = ast.parse(source)
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                body.pop(0)
    compact = ast.unparse(tree)
    compact = '\n'.join(' ' * ((len(line) - len(line.lstrip())) // 4)
                        + line.lstrip() for line in compact.splitlines()) + '\n'
    if ast.dump(ast.parse(compact)) != ast.dump(tree):
        raise ValueError('Deployment changed program semantics')
    if len(compact.encode()) > 18000:
        raise ValueError('Deployment exceeds conservative flash budget')
    destination = GAME / 'deploy' / 'main.py'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(compact)
    print('Flash file:', destination.relative_to(ROOT), len(compact.encode()), 'bytes')


def build(make_chart=False):
    segments, lead, ms, tempos, division = melody_segments(SONG / 'source.mid')
    duration = max(n[1] for n in segments) + 600
    chart_path = SONG / 'chart.json'
    if make_chart:
        notes = []
        pattern = ('UP', 'UP', 'RIGHT', 'RIGHT', 'DOWN', 'DOWN', 'LEFT', 'LEFT')
        # Four MIDI quarter notes = about 1.04 seconds; 12 cues then 4 rests.
        for index, tick in enumerate(range(division * 8, max(n[1] for n in lead), division * 4)):
            if index % 16 < 12 and ms(tick) < duration - 1500:
                notes.append({'time_ms': ms(tick), 'direction': pattern[len(notes) % len(pattern)]})
        chart = {'title': 'MEGALOVANIA - Gentle', 'duration_ms': duration,
                 'bpm': round(60000000 / tempos[0][1] / 2, 3), 'notes': notes}
        chart_path.write_text(json.dumps(chart, indent=2) + '\n', encoding='utf-8')
    chart = json.loads(chart_path.read_text(encoding='utf-8-sig'))
    chart_rows = sorted(chart['notes'], key=lambda n: n['time_ms'])
    duration = max(duration, int(chart['duration_ms']))
    packed_chart, previous = bytearray(), 0
    for row in chart_rows:
        time_ms = row['time_ms']
        if not isinstance(time_ms, int) or time_ms < 0 or time_ms >= duration:
            raise ValueError('Chart timestamps must be nonnegative integers within the song')
        if previous and time_ms - previous < 1000:
            raise ValueError('Gentle chart requires at least 1000 ms between cues')
        packed_chart.extend(struct.pack('<HB', time_ms - previous, DIRECTIONS.index(row['direction'])))
        previous = time_ms
    packed_music, previous = bytearray(), 0
    for start, end, pitch in segments:
        packed_music.extend(struct.pack('<HHB', start - previous, end - start, pitch))
        previous = start
    frequencies = tuple(round(440 * 2 ** ((pitch - 69) / 12)) for pitch in range(128))
    block = ('# BEGIN GENERATED SONG\n'
             + 'SONG_LENGTH_MS = ' + str(duration) + '\n'
             + 'MELODY = unpack(' + repr(compress(packed_music).hex()) + ')' + '\n'
             + 'CHART = unpack(' + repr(compress(packed_chart).hex()) + ')' + '\n'
             + 'FREQUENCIES = ' + repr(frequencies) + '\n'
             + '# END GENERATED SONG')
    main_path = GAME / 'microbit_main.py'
    main = main_path.read_text()
    a, b = main.index('# BEGIN GENERATED SONG'), main.index('# END GENERATED SONG')
    main = main[:a] + block + main[b + len('# END GENERATED SONG'):]
    main_path.write_text(main)
    write_deployment(main)
    (SONG / 'song.json').write_text(json.dumps({
        'title': 'MEGALOVANIA - Gentle', 'audio': 'source.mid', 'chart': 'chart.json',
        'duration_ms': duration, 'playback': 'on-device single-voice melody',
        'melody_track': 3}, indent=2) + '\n')
    print('Built:', len(segments), 'melody segments;', len(chart_rows), 'cues;',
          duration / 1000, 'seconds; board script', len(main.encode()), 'bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-chart', action='store_true', help='Replace chart with the default gentle chart')
    build(parser.parse_args().make_chart)
