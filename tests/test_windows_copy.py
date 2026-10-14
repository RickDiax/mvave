import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mk300_copy', ROOT / 'windows/copiar_teste.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def preset(name):
    b = bytearray(448)
    b[:20] = name.encode('ascii').ljust(20, b'\0')
    b[0x18:0x1A] = (90).to_bytes(2, 'little')
    b[0x1A:0x1C] = (80).to_bytes(2, 'little')
    b[0x20:0x2B] = bytes(range(11))
    b[0x14A:] = bytes((i % 256 for i in range(448 - 0x14A)))
    return bytes(b)


class FakePedal:
    def __init__(self, name='USER PRESET', mismatch=False):
        self.source = preset('Belief')
        self.target = preset(name)
        self.writes = []
        self.reads = []
        self.mismatch = mismatch
        self.committed = False

    def read_slot(self, slot):
        self.reads.append(slot)
        return self.source if slot == 142 else self.target

    def write_target(self, image):
        self.writes.append(image)
        if not self.mismatch:
            self.target = image

    def commit(self):
        self.committed = True


class CopyTests(unittest.TestCase):
    def test_preview_never_writes(self):
        d = FakePedal()
        r = {}
        c.copy_test(d, r, lambda _: None)
        self.assertEqual(d.writes, [])
        self.assertFalse(d.committed)
        self.assertEqual(r['status'], 'preview_ready')

    def test_named_destination_is_preserved(self):
        d = FakePedal('My Solo')
        backups = []
        with self.assertRaises(ValueError):
            c.copy_test(d, {}, lambda r: backups.append(dict(r)), apply=True)
        self.assertEqual(d.writes, [])
        self.assertIn('target_before_raw_hex', backups[0])

    def test_wrong_source_is_preserved(self):
        d = FakePedal()
        d.source = preset('Other')
        with self.assertRaises(ValueError):
            c.copy_test(d, {}, lambda _: None, apply=True)
        self.assertEqual(d.writes, [])

    def test_copy_preserves_unknown_fields_and_source(self):
        d = FakePedal('USER PRESET 137')
        original = d.source
        backups = []
        r = {}
        c.copy_test(d, r, lambda r: backups.append(dict(r)), apply=True)
        self.assertEqual(d.source, original)
        self.assertEqual(d.target[20:], original[20:])
        self.assertEqual(d.target[:20], b'TESTE USB'.ljust(20, b'\0'))
        self.assertEqual(r['status'], 'copy_verified')
        self.assertEqual(backups[0]['target_before_raw_hex'], preset('USER PRESET 137').hex())
        self.assertEqual(d.reads, [142, 137, 137])
        self.assertEqual(len(d.writes), 1)

    def test_readback_mismatch_does_not_retry_write(self):
        d = FakePedal(mismatch=True)
        with self.assertRaises(TimeoutError):
            c.copy_test(d, {}, lambda _: None, apply=True, verify_timeout=0)
        self.assertEqual(len(d.writes), 1)
        self.assertTrue(d.committed)

    def test_no_loose_prefix_match(self):
        with self.assertRaises(ValueError):
            c.prepare_image(preset('Belief'), preset('USER PRESET SOLO'))

    def test_transport_rejects_writes_to_source_and_global(self):
        transport = c.ReadTransport(None, None, None)
        for frame in (c.p.write_preset_image(141, preset('Belief')),
                      c.p.write_u8(0x3D, 2, c.p.SPACE_STATUS), c.p.load_preset(136)):
            with self.subTest(frame=frame[:20].hex()), self.assertRaises(ValueError):
                transport._write(frame, 0)

    def test_target_frame_has_correct_offset_and_preserves_image(self):
        transport = c.ReadTransport(None, None, None)
        sent = []
        transport._write = lambda f, t: sent.append(f)
        image = c.prepare_image(preset('Belief'), preset('USER PRESET'))
        transport.write_target(image)
        transport.commit()
        f = c.p.parse(sent[0])
        self.assertEqual((f.field, f.space, f.length, f.payload), (136 * 448, c.p.SPACE_BANK, 448, image))
        self.assertEqual(sent[1], c.p.COMMIT)


if __name__ == '__main__':
    unittest.main()
