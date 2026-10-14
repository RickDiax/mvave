import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mk300_windows_diagnostic', ROOT / 'windows/diagnostico.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Message:
    def __init__(self, kind, data):
        self.type = kind
        self.data = data

    def bytes(self):
        return bytes([0xF0, *self.data, 0xF7])


class Input:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        queue, self.queue = self.queue, []
        return iter(queue)


class Output:
    def __init__(self, mi, replies):
        self.mi, self.replies, self.sent = mi, replies, []

    def send(self, message):
        self.sent.append(message)
        self.mi.queue.extend(Message('sysex', f[1:-1]) for f in self.replies)


class DiagnosticTests(unittest.TestCase):
    def test_separate_windows_port_names(self):
        self.assertEqual(d.choose_port(['MK-300 0', 'Other']), 'MK-300 0')
        self.assertEqual(d.choose_port(['MK-300 1', 'Other']), 'MK-300 1')
        with self.assertRaises(ValueError):
            d.choose_port(['MK-300 0', 'MK-300 1'])
        with self.assertRaises(ValueError):
            d.choose_port(['Other'])
        self.assertEqual(d.choose_port(['Explicit device'], 'Explicit device'), 'Explicit device')

    def test_queries_are_reads_and_invalid_replies_are_ignored(self):
        for length, space in [(86, d.p.SPACE_STATUS), (448, d.p.SPACE_PRESET)]:
            with self.subTest(length=length):
                payload = bytes(length)
                good = d.p.build(d.p.CLS_READ, d.p.CMD_READ, 0, length, space, payload)
                bad = bytearray(good)
                bad[-2] ^= 1
                unrelated = d.p.build(d.p.CLS_WRITE, d.p.CMD_READ, 0, length, space, payload)
                mi = Input()
                mo = Output(mi, [bytes(bad), unrelated, good])
                self.assertEqual(d.read_only_query(mi, mo, Message, 0, length, space), payload)
                self.assertEqual(len(mo.sent), 1)
                request = d.p.parse(mo.sent[0].bytes())
                self.assertEqual((request.cls, request.cmd, request.payload),
                                 (d.p.CLS_READ, d.p.CMD_READ, b''))

    def test_unexpected_query_sends_nothing(self):
        mi = Input()
        mo = Output(mi, [])
        with self.assertRaises(ValueError):
            d.read_only_query(mi, mo, Message, 0, 1, d.p.SPACE_COMMAND)
        self.assertEqual(mo.sent, [])

    def test_timeout_does_not_trigger_write_or_retry(self):
        mi = Input()
        mo = Output(mi, [])
        with self.assertRaises(TimeoutError):
            d.read_only_query(mi, mo, Message, 0, 86, d.p.SPACE_STATUS, timeout=0)
        self.assertEqual(len(mo.sent), 1)
        self.assertEqual(d.p.parse(mo.sent[0].bytes()).cls, d.p.CLS_READ)

    def test_preset_layout_is_checked(self):
        raw = bytearray(448)
        raw[:4] = b'TEST'
        raw[0x18:0x1A] = (60).to_bytes(2, 'little')
        raw[0x1A:0x1C] = (120).to_bytes(2, 'little')
        raw[0x20:0x2B] = bytes(range(11))
        result = d.describe_preset(bytes(raw))
        self.assertEqual((result['name'], result['volume'], result['bpm']), ('TEST', 60, 120))
        raw[0x20] = 255
        with self.assertRaises(ValueError):
            d.describe_preset(bytes(raw))


if __name__ == '__main__':
    unittest.main()
