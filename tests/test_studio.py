import copy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
import core
import server


def fixture():
    raw = bytearray(448)
    raw[:20] = b'TESTE USB'.ljust(20, b'\0')
    raw[0x18:0x1A] = (80).to_bytes(2, 'little')
    raw[0x1A:0x1C] = (80).to_bytes(2, 'little')
    raw[0x20:0x2B] = bytes(range(11))
    raw[core.CONTROL_START:] = bytes((i * 19) % 256 for i in range(448-core.CONTROL_START))
    return bytes(raw)


class StudioTests(unittest.TestCase):
    def test_roundtrip_retains_every_byte(self):
        raw = fixture()
        self.assertEqual(core.encode(raw.hex(), core.decode(raw)), raw)

    def test_edit_preserves_controls_and_unmapped_bytes(self):
        raw = fixture()
        draft = core.decode(raw)
        draft['name'] = 'MY SOUND'
        draft['blocks']['DS'].update(model_index=47, enabled=True, knobs=[25, 35]+[0]*10)
        draft['chain'][3], draft['chain'][7] = draft['chain'][7], draft['chain'][3]
        after = core.encode(raw.hex(), draft)
        self.assertEqual(after[core.CONTROL_START:], raw[core.CONTROL_START:])
        self.assertEqual(after[20:24], raw[20:24])
        self.assertEqual(core.decode(after)['blocks']['DS']['knobs'][:2], [25, 35])

    def test_reject_bad_chain_unknown_model_and_range(self):
        base = core.decode(fixture())
        for mutate in [lambda d: d['chain'].__setitem__(0, 'AMP'),
                       lambda d: d['blocks']['DS'].__setitem__('model_index', 255),
                       lambda d: d.__setitem__('volume', 101),
                       lambda d: d.__setitem__('name', '<\n>'),
                       lambda d: d['blocks']['DS']['knobs'].__setitem__(0, 999)]:
            d = copy.deepcopy(base)
            mutate(d)
            with self.assertRaises(ValueError):
                core.encode(base['raw_hex'], d)

    def test_unknown_current_model_is_preserved(self):
        raw = bytearray(fixture())
        raw[core.profile.model_offset(3)] = 250
        self.assertEqual(core.encode(raw.hex(), core.decode(bytes(raw))), bytes(raw))

    def test_library_and_backup_restoration(self):
        with tempfile.TemporaryDirectory() as folder:
            library = core.Library(folder)
            key = library.save(fixture())
            self.assertEqual(library.get(key)['raw_hex'], fixture().hex())
            self.assertEqual(len(library.list()), 1)
            with self.assertRaises(ValueError):
                library.get('../server.py')
        restored = server.dispatch('/api/import', {'document': {'format':'mk300-studio-1','before_raw_hex':fixture().hex()}})
        self.assertEqual(restored['raw_hex'], fixture().hex())
        with self.assertRaises(ValueError):
            server.dispatch('/api/import', {'document':{'format':'other'}})


class SaveTests(unittest.TestCase):
    def setup_pedal(self, folder, fail=False):
        pedal = object.__new__(core.Midi)
        pedal.slot = lambda slot: self.raw
        self.raw = fixture()
        self.writes = []
        def write(frame):
            records = list(Path(folder).glob('*.json'))
            self.assertEqual(len(records), 1)  # backup exists before the first send
            record = json.loads(records[0].read_text())
            self.assertEqual(record['before_raw_hex'], fixture().hex())
            self.writes.append(frame)
            if fail:
                raise TimeoutError('simulated ACK failure')
            self.raw = self.planned
        pedal.write = write
        return pedal

    def test_success_and_destination_concurrency_guard(self):
        self.planned = core.encode(fixture().hex(), {**core.decode(fixture()), 'name':'NEW PRESET'})
        with tempfile.TemporaryDirectory() as folder:
            pedal = self.setup_pedal(folder)
            with self.assertRaises(ValueError):
                pedal.save(137, self.planned, 'changed', Path(folder))
            self.assertFalse(self.writes)
            self.assertFalse(list(Path(folder).glob('*.json')))
            result = pedal.save(137, self.planned, core.digest(fixture()), Path(folder))
            self.assertTrue(result['verified'])
            self.assertEqual(len(self.writes), 2)
            self.assertEqual(self.writes[-1], core.p.COMMIT)
            self.assertEqual(json.loads((Path(folder)/result['backup']).read_text())['status'], 'verified')

    def test_uncertain_write_keeps_original_and_never_retries(self):
        self.planned = fixture()
        with tempfile.TemporaryDirectory() as folder:
            pedal = self.setup_pedal(folder, fail=True)
            with self.assertRaises(TimeoutError):
                pedal.save(137, fixture(), core.digest(fixture()), Path(folder))
            self.assertEqual(len(self.writes), 1)
            r = json.loads(next(Path(folder).glob('*.json')).read_text())
            self.assertEqual(r['status'], 'uncertain')
            self.assertEqual(r['before_raw_hex'], fixture().hex())

    def test_failed_backup_prevents_usb_write(self):
        self.planned = fixture()
        with tempfile.TemporaryDirectory() as folder:
            pedal = self.setup_pedal(folder)
            with patch.object(Path, 'write_text', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    pedal.save(137, fixture(), core.digest(fixture()), Path(folder))
            self.assertFalse(self.writes)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, **headers):
        connection = HTTPConnection('127.0.0.1', self.http.server_port)
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        r = connection.getresponse()
        data = r.read()
        connection.close()
        return r.status, data

    def test_html_and_authenticated_preview(self):
        status, html = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(server.TOKEN.encode(), html)
        self.assertNotIn(b'__APP_TOKEN__', html)
        status, data = self.request('POST', '/api/preview', {'raw_hex':fixture().hex(), 'draft':core.decode(fixture())}, **{'Content-Type':'application/json','X-Studio-Token':server.TOKEN})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['raw_hex'], fixture().hex())

    def test_foreign_origin_host_and_missing_token_refused(self):
        for headers in [{}, {'Host':'evil.test'}, {'X-Studio-Token':server.TOKEN,'Origin':'https://evil.test'}]:
            status, _ = self.request('POST', '/api/save', {}, **headers)
            self.assertEqual(status, 403)

    def test_invalid_json_and_size_are_handled(self):
        status, _ = self.request('POST', '/api/import', {}, **{'Content-Type':'text/plain','X-Studio-Token':server.TOKEN})
        self.assertEqual(status, 415)
        status, _ = self.request('POST', '/api/import', {'x':'a'*200001}, **{'Content-Type':'application/json','X-Studio-Token':server.TOKEN})
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
