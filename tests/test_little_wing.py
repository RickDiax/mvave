import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'windows'))
spec = importlib.util.spec_from_file_location('lw', ROOT / 'windows/little_wing.py')
lw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lw)
RECIPE = json.loads((ROOT / 'windows/little_wing.json').read_text())


def fixture():
    raw = bytearray(448)
    raw[:20] = b'TESTE USB'.ljust(20, b'\0')
    raw[0x18:0x1A] = (90).to_bytes(2, 'little')
    raw[0x20:0x2B] = bytes(range(11))
    raw[lw.mk300.model_offset(3)] = 47
    raw[lw.mk300.model_offset(7)] = 11
    raw[lw.CONTROL_START:] = lw.EXPECTED_CONTROLS
    return bytes(raw)


class Pedal:
    def __init__(self):
        self.raw = fixture()
        self.writes = []
        self.committed = False

    def read_slot(self, slot):
        assert slot == 137
        return self.raw

    def write_target(self, raw):
        self.writes.append(raw)
        self.raw = raw

    def commit(self):
        self.committed = True


class LittleWingTests(unittest.TestCase):
    def test_controls_preserved_and_effects_initially_off(self):
        before = fixture()
        after = lw.build_image(before, RECIPE)
        self.assertEqual(len(after), 448)
        self.assertEqual(after[lw.CONTROL_START:], before[lw.CONTROL_START:])
        ps = lw.mk300.Preset(after)
        self.assertEqual(ps.name, 'LITTLE WING')
        self.assertEqual((ps.model(3), ps.model(7), ps.model(4), ps.model(5)), (47, 11, 42, 42))
        self.assertFalse(ps.enabled(3))
        self.assertFalse(ps.enabled(7))
        self.assertEqual(ps.knobs(3)[:2], [65, 50])
        self.assertEqual(ps.knobs(6)[:10], RECIPE['blocks']['EQ']['knobs'])

    def test_different_controls_refuse_write(self):
        d = Pedal()
        changed = bytearray(d.raw)
        changed[0x158] ^= 1
        d.raw = bytes(changed)
        with self.assertRaises(ValueError):
            lw.apply_recipe(d, RECIPE, {}, lambda _: None, apply=True)
        self.assertEqual(d.writes, [])

    def test_other_destination_name_refuses_write(self):
        d = Pedal()
        raw = bytearray(d.raw)
        raw[:20] = b'MY SOLO'.ljust(20, b'\0')
        d.raw = bytes(raw)
        with self.assertRaises(ValueError):
            lw.apply_recipe(d, RECIPE, {}, lambda _: None, apply=True)
        self.assertEqual(d.writes, [])

    def test_preview_and_backup(self):
        d = Pedal()
        copies = []
        r = {}
        lw.apply_recipe(d, RECIPE, r, lambda x: copies.append(dict(x)))
        self.assertEqual(d.writes, [])
        self.assertEqual(copies[0]['before_raw_hex'], fixture().hex())
        self.assertEqual(r['status'], 'preview_ready')

    def test_apply_verifies_once_and_reapplication_is_refused(self):
        d = Pedal()
        r = {}
        lw.apply_recipe(d, RECIPE, r, lambda _: None, apply=True)
        self.assertEqual(r['status'], 'little_wing_verified')
        self.assertEqual(r['after_raw_hex'], r['planned_image_hex'])
        self.assertEqual(len(d.writes), 1)
        with self.assertRaises(ValueError):
            lw.apply_recipe(d, RECIPE, {}, lambda _: None, apply=True)
        self.assertEqual(len(d.writes), 1)

    def test_out_of_range_is_refused(self):
        r = json.loads(json.dumps(RECIPE))
        r['blocks']['DS']['knobs'][0] = 200
        with self.assertRaises(ValueError):
            lw.build_image(fixture(), r)


if __name__ == '__main__':
    unittest.main()
