import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import automation as a
import core


def fixture():
    r = bytearray(448)
    r[:20] = b'TESTE USB'.ljust(20, b'\0')
    r[24:26] = (80).to_bytes(2, 'little')
    r[26:28] = (80).to_bytes(2, 'little')
    r[32:43] = bytes(range(11))
    r[330:] = bytes(i % 256 for i in range(118))
    return bytes(r)


def recipe():
    r = {key: copy.deepcopy(core.decode(fixture())[key]) for key in ('name','volume','bpm','pan','chain')}
    r['name'] = 'AUTO TONE'
    r['blocks'] = {b:{'enabled':False} for b in core.profile.BLOCKS}
    r['blocks']['DS'] = {'enabled':True,'model_index':47,'parameters':{'Fuzz':25,'Level':35}}
    return r


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime(2026, 10, 14, 22, 0, tzinfo=timezone.utc)
        self.raw = fixture()
        self.writes = []
        self.opens = []
        self.fail = False
        self.doc = {'format':'mk300-tone-inbox-2', 'job':None}
        owner = self
        class Pedal:
            def __init__(self, input_name, output_name):
                owner.opens.append((input_name, output_name))
            def slot(self, slot):
                assert slot == 137
                return owner.raw
            def write(self, frame):
                # Use the production save logic; only the device transport is simulated.
                owner.writes.append(frame)
                record = json.loads((Path(owner.temp.name)/'automation.json').read_text())
                assert record['phase'] == 'writing' and record['last_job_id'] in record['seen']
                assert list((Path(owner.temp.name)/'backups').glob('*.json'))
                if owner.fail:
                    raise TimeoutError('ACK lost')
                parsed = core.p.parse(frame)
                if parsed.space == core.p.SPACE_BANK:
                    assert parsed.field == 136 * 448
                    owner.raw = parsed.payload
                else:
                    assert frame == core.p.COMMIT
            save = core.Midi.save
            def close(self):
                pass
        self.receiver = a.Receiver(self.temp.name, threading.Lock(), fetcher=lambda:self.doc,
                                   midi_factory=Pedal, clock=lambda:self.now)
        self.doc['channel_id'] = self.receiver.channel_id
        self.receiver.enable('USB-Midi 0','USB-Midi 1',137)
        self.now += timedelta(seconds=5)

    def job(self, key='a'*32):
        return {'format':'mk300-tone-job-2','channel_id':self.receiver.channel_id,'id':key,'created_at':self.now.isoformat(),
                'expires_at':(self.now+timedelta(hours=1)).isoformat(),
                'catalog_sha256':a.CATALOG_SHA256, 'recipe':recipe(), 'request':'test', 'sources':[], 'notes':[]}

    def deliver(self, job):
        self.doc['job'] = job
        self.receiver.poll_once()

    def test_end_to_end_compiles_backs_up_saves_verifies_and_deduplicates(self):
        self.deliver(self.job())
        self.assertEqual(self.receiver.state['phase'], 'verified')
        self.assertEqual(len(self.writes), 2)
        self.assertEqual(core.decode(self.raw)['blocks']['DS']['knobs'][:2], [25,35])
        self.assertEqual(self.raw[330:], fixture()[330:])
        self.assertEqual(len(core.Library(Path(self.temp.name)/'timbres').list()), 1)
        self.receiver.poll_once()
        self.assertEqual(len(self.writes), 2)
        next_job = self.job('b'*32)
        next_job['recipe']['name'] = 'SECOND TONE'
        self.deliver(next_job)
        self.assertEqual(len(self.writes), 4)
        self.assertEqual(core.decode(self.raw)['name'], 'SECOND TONE')

    def test_external_destination_change_pauses_without_write(self):
        raw = bytearray(self.raw)
        raw[24] = 50
        self.raw = bytes(raw)
        self.deliver(self.job())
        self.assertFalse(self.receiver.enabled)
        self.assertIn('mudou', self.receiver.state['message'])
        self.assertFalse(self.writes)

    def test_invalid_recipe_or_catalog_never_writes(self):
        for change in ('range', 'field', 'parameter', 'catalog', 'controls'):
            with self.subTest(change=change):
                self.receiver.enabled = True
                job = self.job()
                if change == 'range': job['recipe']['blocks']['DS']['parameters']['Fuzz'] = 1000
                if change == 'field': job['slot'] = 142
                if change == 'parameter': job['recipe']['blocks']['DS']['parameters']['command'] = 1
                if change == 'catalog': job['catalog_sha256'] = 'wrong'
                if change == 'controls': job['recipe']['controls'] = 'changed'
                self.deliver(job)
                self.assertFalse(self.writes)
                self.assertFalse(self.receiver.enabled)

    def test_old_and_expired_requests_are_skipped(self):
        old = self.job()
        old['created_at'] = (self.now-timedelta(hours=2)).isoformat()
        self.deliver(old)
        expired = self.job('b'*32)
        expired['expires_at'] = (self.now-timedelta(seconds=1)).isoformat()
        self.deliver(expired)
        self.assertFalse(self.writes)
        self.assertTrue(self.receiver.enabled)

    def test_uncertain_write_is_not_retried_even_after_restart(self):
        self.fail = True
        self.deliver(self.job())
        self.assertFalse(self.receiver.enabled)
        self.assertEqual(len(self.writes), 1)
        self.receiver.poll_once()
        self.assertEqual(len(self.writes), 1)
        recovered = a.Receiver(self.temp.name, threading.Lock(), fetcher=lambda:self.doc,
                               midi_factory=self.receiver.midi_factory, clock=lambda:self.now)
        self.assertFalse(recovered.enabled)
        self.assertIn('a'*32, recovered.state['seen'])
        recovered.enable('USB-Midi 0','USB-Midi 1',137)
        recovered.poll_once()
        self.assertEqual(len(self.writes), 1)

    def test_disk_failure_prevents_any_write(self):
        with patch.object(self.receiver, 'persist', side_effect=OSError('disk full')):
            # pause may also fail to persist, but must disable the receiver first
            with self.assertRaises(OSError):
                self.deliver(self.job())
        self.assertFalse(self.writes)
        self.assertFalse(self.receiver.enabled)

    def test_no_network_retries_only_download(self):
        calls = len(self.opens)
        def fail():
            raise TimeoutError('offline')
        self.receiver.fetcher = fail
        self.receiver.poll_once()
        self.receiver.poll_once()
        self.assertEqual(len(self.opens), calls)
        self.assertTrue(self.receiver.enabled)

    def test_pause_during_download_blocks_execution(self):
        def fetch():
            self.receiver.pause()
            return {'format':'mk300-tone-inbox-2','channel_id':self.receiver.channel_id,'job':self.job()}
        self.receiver.fetcher = fetch
        self.receiver.poll_once()
        self.assertFalse(self.writes)

    def test_arming_ignores_current_published_job_and_never_writes(self):
        self.doc['job'] = self.job()
        self.doc['channel_id'] = self.receiver.channel_id
        self.receiver.enable('USB-Midi 0','USB-Midi 1',137)
        self.receiver.poll_once()
        self.assertFalse(self.writes)
        self.assertEqual(self.receiver.state['phase'], 'waiting')

    def test_catalog_checksum_file_matches_receiver(self):
        path = Path(__file__).resolve().parents[1] / 'automation/catalog.sha256'
        self.assertEqual(path.read_text().strip(), a.CATALOG_SHA256)

    def test_download_is_bounded_and_only_accepts_fixed_source(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return a.inbox_url('RickDiax/mvave','a'*32) + '?poll=1'
            def read(self, limit):
                self.limit = limit
                return json.dumps({'format':'mk300-tone-inbox-2','channel_id':'a'*32,'job':None}).encode()
        response = Response()
        with patch.object(a, 'urlopen', return_value=response):
            self.assertIsNone(a.fetch_inbox('RickDiax/mvave','a'*32)['job'])
        self.assertEqual(response.limit, 100001)
        response.geturl = lambda: 'https://example.com/recipe.json'
        with patch.object(a, 'urlopen', return_value=response):
            with self.assertRaises(ValueError):
                a.fetch_inbox('RickDiax/mvave','a'*32)

    def test_future_dated_job_pauses_without_write(self):
        job = self.job()
        job['created_at'] = (self.now+timedelta(hours=1)).isoformat()
        job['expires_at'] = (self.now+timedelta(hours=2)).isoformat()
        self.deliver(job)
        self.assertFalse(self.writes)
        self.assertFalse(self.receiver.enabled)

    def test_other_computer_job_never_opens_usb_or_writes(self):
        calls = len(self.opens)
        job = self.job()
        job['channel_id'] = '0' * 32
        self.deliver(job)
        self.assertFalse(self.writes)
        self.assertEqual(len(self.opens), calls)
        self.assertFalse(self.receiver.enabled)

    def test_other_computer_inbox_is_rejected(self):
        self.doc.update(channel_id='0' * 32, job=self.job())
        self.receiver.poll_once()
        self.assertFalse(self.writes)
        self.assertFalse(self.receiver.enabled)

    def test_installations_have_separate_persistent_channels(self):
        with tempfile.TemporaryDirectory() as other_folder:
            other = a.Receiver(other_folder, threading.Lock(), fetcher=lambda:self.doc)
            self.assertNotEqual(other.channel_id, self.receiver.channel_id)
        restarted = a.Receiver(self.temp.name, threading.Lock(), fetcher=lambda:self.doc)
        self.assertEqual(restarted.channel_id, self.receiver.channel_id)
        self.assertFalse(restarted.enabled)
        self.assertEqual(restarted.settings['slot'], 137)

    def test_repository_change_preserves_channel_and_pauses_receiver(self):
        channel = self.receiver.channel_id
        state = self.receiver.configure({'repository':'AnotherUser/mvave','slot':12,'input':'In','output':'Out','instrument':'Humbucker guitar'})
        self.assertFalse(state['enabled'])
        self.assertEqual(self.receiver.channel_id, channel)
        self.assertEqual(self.receiver.settings['repository'], 'AnotherUser/mvave')
        self.assertEqual(self.receiver.settings['instrument'], 'Humbucker guitar')
        self.assertFalse(self.writes)

    def test_repository_and_channel_cannot_escape_github_path(self):
        for repo in ['https://evil.test/x', '../mvave', 'Owner/..', 'Owner/repo/extra', 'Owner/repo?x=1', 'Owner/repo#anchor']:
            with self.assertRaises(ValueError):
                a.inbox_url(repo, self.receiver.channel_id)
        with self.assertRaises(ValueError):
            a.inbox_url('Owner/repo', '../inbox')

    def test_missing_channel_waits_without_using_shared_inbox(self):
        from urllib.error import HTTPError
        error = HTTPError('test', 404, 'not found', None, None)
        with patch.object(a, 'urlopen', side_effect=error) as request:
            document = a.fetch_inbox('Other/mvave', self.receiver.channel_id)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(document['channel_id'], self.receiver.channel_id)
        self.assertIsNone(document['job'])
        self.assertIn('/channels/' + self.receiver.channel_id + '.json', request.call_args[0][0].full_url)


if __name__ == '__main__':
    unittest.main()
