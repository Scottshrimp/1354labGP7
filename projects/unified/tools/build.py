#!/usr/bin/env python3
"""Build a single Python Editor import file. Never opens serial or flashes hardware."""
import ast
import base64
import builtins
import importlib.util
import io
import json
import keyword
import struct
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDALONE_ROOT = ROOT.parent / "standalone"
# End on a D before a pause in the original arrangement to fit both songs.
MEGALOVANIA_END_MS = 114770


def standalone_builder():
    spec = importlib.util.spec_from_file_location(
        "standalone_build_song", STANDALONE_ROOT / "src/tools/build_song.py"
    )
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    return converter


def song_assets():
    converter = standalone_builder()

    source = STANDALONE_ROOT / "music/megalovania"
    segments, *_ = converter.melody_segments(source / "source.mid")
    original_chart = json.loads((source / "chart.json").read_text(encoding="utf-8-sig"))
    duration = max(segments[-1][1] + 600, original_chart["duration_ms"])
    notes = original_chart["notes"]
    if MEGALOVANIA_END_MS is not None:
        segments = [segment for segment in segments if segment[1] <= MEGALOVANIA_END_MS]
        last_note_end = segments[-1][1]
        duration = last_note_end + 600
        notes = [row for row in notes if row["time_ms"] < last_note_end]
    songs = [
        {
            "title": "MEGALOVANIA",
            "duration_ms": duration,
            "melody": [(start, end - start, pitch) for start, end, pitch in segments],
            "notes": notes,
        }
    ]
    songs.extend(
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "music").glob("*.json"))
    )
    return pack_song_assets(songs, converter)


def pack_song_assets(songs, converter):
    pitches = set()
    packed_songs = []

    def encoded(data):
        return base64.b64encode(converter.compress(data)).decode().rstrip("=")

    for song in songs:
        title, duration = song["title"], song["duration_ms"]
        music, chart = bytearray(), bytearray()
        previous = end = 0
        for start, length, pitch in song["melody"]:
            if not (end <= start < start + length <= duration and 0 <= pitch < 128):
                raise ValueError(
                    f"Invalid melody event for {title}: {(start, length, pitch)}"
                )
            music.extend(struct.pack("<HHB", start - previous, length, pitch))
            previous, end = start, start + length
            pitches.add(pitch)
        previous = 0
        for row in sorted(song["notes"], key=lambda row: row["time_ms"]):
            stamp = row["time_ms"]
            if not 0 <= stamp < duration or (chart and stamp - previous < 1000):
                raise ValueError(f"Invalid Gentle chart time for {title}: {stamp}")
            direction = converter.DIRECTIONS.index(row["direction"])
            chart.extend(struct.pack("<HB", stamp - previous, direction))
            previous = stamp
        if not music or not chart:
            raise ValueError(f"Missing melody or chart for {title}")
        packed_songs.append((title, duration, encoded(music), encoded(chart)))

    first_pitch = min(pitches)
    frequencies = tuple(
        round(440 * 2 ** ((pitch - 69) / 12))
        for pitch in range(first_pitch, max(pitches) + 1)
    )
    return (
        "# BEGIN GENERATED SONG\n"
        + "SONGS = (\n"
        + "".join(f"    {song!r},\n" for song in packed_songs)
        + ")\n"
        + f"FIRST_PITCH = {first_pitch}\n"
        + f"FREQUENCIES = {frequencies!r}\n"
        + "# END GENERATED SONG"
    )


def assembled_source(assets=None):
    source = (ROOT / "src/microbit_main.py").read_text()
    begin, end = "# BEGIN GENERATED SONG", "# END GENERATED SONG"
    if assets is None:
        assets = song_assets()
    source = (
        source[: source.index(begin)] + assets + source[source.index(end) + len(end) :]
    )
    lines = [
        line
        for line in source.splitlines()
        if not line.startswith(("from connection import ", "from protocol import "))
    ]
    connection = (ROOT / "connection.py").read_text()
    # These desktop-facing helpers have no callers in the board adapter.
    start, end = connection.index("    @property"), connection.index(
        "    def attach_host"
    )
    connection = connection[:start] + connection[end:]
    start, end = connection.index("    def disconnect"), connection.index(
        "    def poll"
    )
    connection = connection[:start] + connection[end:]
    protocol = (ROOT / "protocol.py").read_text()
    start, end = protocol.index("def encode_line"), protocol.index("class LineFramer")
    protocol = protocol[:start] + protocol[end:]
    source = "\n".join(lines) + "\n"
    decoder, game = source.split("FRAME_MS =", 1)
    return decoder + connection + "\n" + protocol + "\nFRAME_MS =" + game


def compact_tree(tree):
    """Shorten bound identifiers consistently; preserve hardware API attributes.

    Native import names and keyword arguments keep their original spellings.
    This is a build-only transform; readable source is always the editing target.
    """
    reserved = set(dir(builtins)) | set(keyword.kwlist)
    bindings = set()
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            reserved.update(
                alias.asname or alias.name.split(".")[0] for alias in node.names
            )
        if isinstance(node, ast.keyword) and node.arg:
            reserved.add(node.arg)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bindings.add(node.id)
        if isinstance(node, ast.arg):
            bindings.add(node.arg)
        if isinstance(node, ast.ClassDef):
            methods.update(n.name for n in node.body if isinstance(n, ast.FunctionDef))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            bindings.add(node.name)
    reserved.update(methods)
    # Only attributes owned by our classes can be shortened. Hardware methods
    # such as music.stop/display.show retain their public API names.
    attrs = {
        n.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)
    }
    attrs.update(methods - {"__init__", "show", "stop"})
    string_attrs = {
        n.args[1].value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id in ("getattr", "setattr", "hasattr")
        and len(n.args) > 1
        and isinstance(n.args[1], ast.Constant)
    }
    native_attrs = set().union(
        *(set(dir(t)) for t in (str, bytes, bytearray, list, dict, tuple))
    )
    native_attrs.update(
        n.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute)
        and isinstance(n.value, ast.Name)
        and n.value.id in ("music", "display", "i2c", "uart")
    )
    attrs -= string_attrs | native_attrs
    counts = Counter(n.id for n in ast.walk(tree) if isinstance(n, ast.Name))
    counts.update(n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute))
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    candidates = list(alphabet) + [a + b for a in alphabet for b in alphabet]
    names = iter(
        name
        for name in candidates
        if name not in reserved and name not in bindings and name not in attrs
    )
    mapping = {
        name: next(names)
        for name in sorted(bindings - reserved, key=lambda n: (-counts[n], n))
    }
    attr_mapping = {
        name: next(names) for name in sorted(attrs, key=lambda n: (-counts[n], n))
    }

    class Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = mapping.get(node.id, node.id)
            return node

        def visit_Attribute(self, node):
            node.attr = attr_mapping.get(node.attr, node.attr)
            return self.generic_visit(node)

        def visit_arg(self, node):
            node.arg = mapping.get(node.arg, node.arg)
            return self.generic_visit(node)

        def visit_Global(self, node):
            node.names = [mapping.get(name, name) for name in node.names]
            return node

        visit_Nonlocal = visit_Global

        def visit_FunctionDef(self, node):
            node.name = attr_mapping.get(node.name, mapping.get(node.name, node.name))
            return self.generic_visit(node)

        visit_ClassDef = visit_FunctionDef

    tree = Rename().visit(tree)
    # Drop optional whitespace but retain token boundaries and one-space indents.
    output = []
    depth = 0
    previous = None
    for token in tokenize.generate_tokens(
        io.StringIO(ast.unparse(tree) + "\n").readline
    ):
        kind, value = token.type, token.string
        if kind == tokenize.INDENT:
            depth += 1
            continue
        if kind == tokenize.DEDENT:
            depth -= 1
            continue
        if kind in (tokenize.NEWLINE, tokenize.NL):
            if previous is not None:
                output.append("\n")
            previous = None
            continue
        if kind in (tokenize.ENDMARKER, tokenize.ENCODING):
            continue
        if previous is None:
            output.append(" " * depth)
        elif previous in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING) and kind in (
            tokenize.NAME,
            tokenize.NUMBER,
            tokenize.STRING,
        ):
            output.append(" ")
        output.append(value)
        previous = kind
    compact = "".join(output)
    if ast.dump(ast.parse(compact)) != ast.dump(tree):
        raise ValueError("Whitespace compaction changed program semantics")
    # Rename is reversible: verify the AST against the original apart from docs.
    reverse = {value: key for key, value in mapping.items()}
    mapping.clear()
    mapping.update(reverse)
    reverse_attrs = {value: key for key, value in attr_mapping.items()}
    attr_mapping.clear()
    attr_mapping.update(reverse_attrs)
    restored = Rename().visit(ast.parse(compact))
    return compact, restored


# The payload is stored as comments, so the boot compiler only parses this tiny
# loader. Read and compile one bounded block at a time, collecting between them.
# Nothing is extracted to flash: the only deployed file remains main.py.
LOADER = r"""# Unified RAM2: bounded compilation, one deployment file.
import gc

def _rh_boot():
    with open('main.py') as _rh_file:
        _rh_code = ''
        while True:
            _rh_line = _rh_file.readline()
            if _rh_line == '#~BEGIN\n':
                break
            if not _rh_line:
                raise ValueError('Missing payload')
        while True:
            _rh_line = _rh_file.readline()
            if not _rh_line:
                break
            if _rh_line in ('#~\n', '#~END\n'):
                if _rh_line == '#~END\n':
                    _rh_file.close()
                gc.collect()
                if _rh_code.startswith('@'):
                    _rh_code = _rh_unpack(_rh_code[1:].replace('\n', '')).decode('ascii')
                exec(_rh_code, globals())
                _rh_code = ''
                gc.collect()
            elif _rh_line.startswith('#'):
                _rh_code += _rh_line[1:]

_rh_boot()
"""


def compilation_blocks(compact, limit=2400):
    """Keep top-level statements intact and compile the main loop last."""
    lines = compact.splitlines(keepends=True)
    tree = ast.parse(compact)
    blocks, current = [], ""
    for node in tree.body:
        start = min(
            [node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]
        )
        text = "".join(lines[start - 1 : node.end_lineno])
        if current and (
            len(current) + len(text) > limit or isinstance(node, ast.While)
        ):
            blocks.append(current)
            current = ""
        current += text
    if current:
        blocks.append(current)
    reconstructed = ast.Module(
        body=[node for block in blocks for node in ast.parse(block).body],
        type_ignores=[],
    )
    if ast.dump(reconstructed) != ast.dump(tree):
        raise ValueError("Compilation blocks changed program structure")
    return blocks


def compress_source(block):
    """Pack ASCII literals and two-byte references within one source block."""
    data = block.encode("ascii")
    output = bytearray()
    index = 0
    while index < len(data):
        for size in range(min(10, len(data) - index), 2, -1):
            match = data.rfind(data[index:index + size], max(0, index - 4095), index)
            if match != -1:
                distance = index - match
                output.extend((128 | ((size - 3) << 4) | (distance >> 8), distance & 255))
                index += size
                break
        else:
            output.append(data[index])
            index += 1
    return output


def staged_deployment(compact):
    blocks = compilation_blocks(compact)
    # Keep the first block readable so it can bootstrap the shared decoder.
    result = LOADER + "#~BEGIN\n"
    for index, block in enumerate(blocks):
        plain = "".join("#" + line for line in block.splitlines(keepends=True))
        if index and block.isascii():
            encoded = "@" + base64.b64encode(compress_source(block)).decode().rstrip("=")
            packed = "".join("#" + encoded[i:i + 76] + "\n" for i in range(0, len(encoded), 76))
            if len(packed) < len(plain):
                plain = packed
        result += plain
        result += "#~END\n" if index == len(blocks) - 1 else "#~\n"
    return result


def deployment_payload(deployment):
    decoder = {}
    blocks, current = [], ""
    active = False
    for line in deployment.splitlines(keepends=True):
        if line == "#~BEGIN\n":
            active = True
            continue
        if not active:
            continue
        if line in ("#~\n", "#~END\n"):
            if not blocks:
                # Execute only the startup decoder definitions, without hardware imports.
                tree = ast.parse(current)
                bindings = []
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        bindings.append(node)
                    elif isinstance(node, ast.Assign):
                        bindings.append(node)
                        break
                exec(compile(ast.Module(bindings, []), "<decoder>", "exec"), decoder)
                unpack = decoder["_rh_unpack"]
            if current.startswith("@"):
                current = unpack(current[1:].replace("\n", "")).decode("ascii")
            blocks.append(current)
            current = ""
        elif line.startswith("#"):
            current += line[1:]
    return blocks


def compile_deployment(assembled):
    tree = ast.parse(assembled)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                body.pop(0)
    original = ast.dump(tree)
    compact, restored = compact_tree(tree)
    if ast.dump(restored) != original:
        raise ValueError("Identifier shortening changed program structure")
    deployment = staged_deployment(compact)
    if len(deployment.encode()) > 20000:
        raise ValueError(
            "Unified deployment exceeds the 20 KB single-file source budget"
        )
    return deployment


def build():
    assembled = assembled_source()
    deployment = compile_deployment(assembled)
    # Keep the readable source and deployment in sync after validation.
    path = ROOT / "src/microbit_main.py"
    source = path.read_text()
    begin, end = "# BEGIN GENERATED SONG", "# END GENERATED SONG"
    assets = assembled[assembled.index(begin) : assembled.index(end) + len(end)]
    path.write_text(
        source[: source.index(begin)] + assets + source[source.index(end) + len(end) :]
    )
    target = ROOT / "deploy/main.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text(deployment)
    print(
        "Python Editor file:", target, "(" + str(len(deployment.encode())) + " bytes)"
    )


if __name__ == "__main__":
    build()
