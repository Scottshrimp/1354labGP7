#!/usr/bin/env python3
"""Build a single Python Editor import file. Never opens serial or flashes hardware."""
import ast
import builtins
import base64
import re
from collections import Counter
import io
import keyword
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assembled_source():
    source = (ROOT / "src/microbit_main.py").read_text()
    # Reuse the current packed song; keep the original standalone project intact.
    song = (ROOT.parent / "standalone/src/microbit_main.py").read_text()
    begin, end = "# BEGIN GENERATED SONG", "# END GENERATED SONG"
    assets = song[song.index(begin) : song.index(end) + len(end)]
    # Base64 reduces source storage without requiring binascii on the board.
    assets = re.sub(
        r"unpack\('([0-9a-f]+)'\)",
        lambda m: "unpack("
        + repr(base64.b64encode(bytes.fromhex(m[1])).decode().rstrip("="))
        + ")",
        assets,
    )
    # Only these exact MIDI pitches are used; keep original integer frequencies.
    # A sparse table reduces source/storage while preserving indexing semantics.
    nodes = ast.parse(assets).body
    table = next(
        n
        for n in nodes
        if isinstance(n, ast.Assign) and n.targets[0].id == "FREQUENCIES"
    )
    values = ast.literal_eval(table.value)
    # A sparse dictionary retains the original MIDI pitch indices.
    # Derive used pitches from the existing packed melody using its LZ decoder.
    packed = bytes.fromhex(re.search(r"MELODY = unpack\('([0-9a-f]+)'\)", song)[1])
    decoded, i = bytearray(), 0
    while i < len(packed):
        value = packed[i]
        i += 1
        if value:
            decoded.append(value)
        else:
            size = packed[i]
            i += 1
            if not size:
                decoded.append(0)
            else:
                distance = packed[i] | (packed[i + 1] << 8)
                i += 2
                for _ in range(size):
                    decoded.append(decoded[-distance])
    frequencies = {pitch: values[pitch] for pitch in sorted(set(decoded[4::5]))}
    assets = re.sub(r"FREQUENCIES = .*", "FREQUENCIES = " + repr(frequencies), assets)
    assets = assets.replace("MELODY = unpack(", "MELODY_DATA = (")
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
    return connection + "\n" + protocol + "\n" + "\n".join(lines) + "\n"


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


def staged_deployment(compact):
    blocks = compilation_blocks(compact)
    # Short comment prefixes keep the single file within filesystem
    # capacity; the payload after BEGIN is never interpreted at boot.
    result = LOADER + "#~BEGIN\n"
    for index, block in enumerate(blocks):
        result += "".join("#" + line for line in block.splitlines(keepends=True))
        result += "#~END\n" if index == len(blocks) - 1 else "#~\n"
    return result


def deployment_payload(deployment):
    blocks, current = [], ""
    active = False
    for line in deployment.splitlines(keepends=True):
        if line == "#~BEGIN\n":
            active = True
            continue
        if not active:
            continue
        if line in ("#~\n", "#~END\n"):
            blocks.append(current)
            current = ""
        elif line.startswith("#"):
            current += line[1:]
    return blocks


def build():
    assembled = assembled_source()
    # Update only the generated song block in readable source as well.
    path = ROOT / "src/microbit_main.py"
    source = path.read_text()
    begin, end = "# BEGIN GENERATED SONG", "# END GENERATED SONG"
    assets = assembled[assembled.index(begin) : assembled.index(end) + len(end)]
    path.write_text(
        source[: source.index(begin)] + assets + source[source.index(end) + len(end) :]
    )
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
    target = ROOT / "deploy/main.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text(deployment)
    print(
        "Python Editor file:", target, "(" + str(len(deployment.encode())) + " bytes)"
    )


if __name__ == "__main__":
    build()
