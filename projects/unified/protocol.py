"""Bounded ASCII line framing for the RH1 serial protocol.

Command validation, handshakes, acknowledgments and serial I/O are handled by
the board adapter and pc_host.py.
"""

PROTOCOL_PREFIX = "RH1"
MAX_LINE_BYTES = 60


def encode_line(*fields):
    values = [str(field) for field in fields]
    if not values or any(not value or "," in value for value in values):
        raise ValueError("Protocol fields must be nonempty and cannot contain commas")
    line = ",".join(values)
    if any(ord(char) < 32 or ord(char) > 126 for char in line):
        raise ValueError("Protocol fields must contain printable ASCII")
    if len(line) > MAX_LINE_BYTES:
        raise ValueError("Protocol line is too long")
    return line.encode("ascii") + b"\n"


class LineFramer:
    def __init__(self, max_line_bytes=MAX_LINE_BYTES):
        if not 1 <= max_line_bytes <= MAX_LINE_BYTES:
            raise ValueError("Line limit must be between 1 and 60 bytes")
        self.max_line_bytes = max_line_bytes
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.discarding = False
        self.carriage_return = False

    def feed(self, data):
        lines = []
        for value in data or b"":
            if value == 10:
                if not self.discarding and self.buffer:
                    lines.append(self.buffer.decode("ascii"))
                self.reset()
            elif self.discarding:
                continue
            elif value == 13:
                if self.carriage_return:
                    self.buffer = bytearray()
                    self.discarding = True
                self.carriage_return = True
            elif (
                self.carriage_return
                or value < 32
                or value > 126
                or len(self.buffer) >= self.max_line_bytes
            ):
                # Discard through the next newline, never reinterpret a suffix.
                self.buffer = bytearray()
                self.discarding = True
            else:
                self.buffer.append(value)
        return lines
