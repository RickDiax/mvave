"""Local-only MK300 Studio web interface. No external hosting or USB in the cloud."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import webbrowser

from core import CATALOG, CONTROL_START, MODELS, Library, Midi, decode, encode, validate
from automation import Receiver

FOLDER = Path(__file__).resolve().parent
ASSETS = {
    '/assets/brand.svg': ('brand.svg', 'image/svg+xml'),
    '/assets/icons.svg': ('icons.svg', 'image/svg+xml'),
    '/assets/preset.svg': ('preset.svg', 'image/svg+xml'),
    '/assets/mk300-studio.ico': ('mk300-studio.ico', 'image/x-icon'),
    '/favicon.ico': ('mk300-studio.ico', 'image/x-icon'),
    '/assets/mk300-studio-192.png': ('mk300-studio-192.png', 'image/png'),
}
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
DATA = Path(os.environ.get('LOCALAPPDATA') or str(Path.home())) / 'MK300Studio'
LIBRARY = Library(DATA / 'timbres')
RECEIVER = Receiver(DATA, LOCK)


def ports():
    try:
        import mido
        mido.set_backend('mido.backends.rtmidi')
        return {'inputs': mido.get_input_names(), 'outputs': mido.get_output_names()}
    except Exception as e:
        return {'inputs': [], 'outputs': [], 'error': str(e)}


def dispatch(route, body):
    if route == '/api/automation-latest':
        key = RECEIVER.state.get('last_job_id')
        if not key:
            raise ValueError('Nenhum pedido recebido ainda.')
        r = json.loads((DATA / 'recebidos' / (key + '.json')).read_text(encoding='utf-8'))
        result = decode(bytes.fromhex(r['raw_hex']))
        result.update(slot=r['slot'], verified=r.get('verified', False))
        return result
    if route == '/api/automation-enable':
        return RECEIVER.enable(body['input'], body['output'], body['slot'])
    if route == '/api/automation-disable':
        return RECEIVER.pause()
    if route == '/api/preview':
        return decode(encode(body['raw_hex'], body['draft']))
    if route == '/api/import':
        document = body['document']
        if document.get('format') != 'mk300-studio-1':
            raise ValueError('Importe um arquivo exportado pelo MK300 Studio, nao um snapshot M-EFCS.')
        return decode(bytes.fromhex(document.get('raw_hex') or document['before_raw_hex']))
    if route == '/api/library-save':
        raw = encode(body['raw_hex'], body['draft'])
        return {'id': LIBRARY.save(raw), 'items': LIBRARY.list()}
    if route == '/api/library-get':
        return LIBRARY.get(body['id'])
    if route == '/api/export':
        raw = encode(body['raw_hex'], body['draft'])
        return {'format': 'mk300-studio-1', 'name': decode(raw)['name'], 'raw_hex': raw.hex()}
    if route == '/api/recipe':
        # Built-in recipe applies only to a loaded preset: it inherits controls and unknown bytes.
        draft = body['draft']
        recipe = json.loads((FOLDER.parent / 'windows/little_wing.json').read_text(encoding='utf-8'))
        recipe['blocks']['DS']['knobs'] = [25, 35]  # incorporates the user's fuzz feedback
        draft.update(name=recipe['name'], volume=recipe['preset_volume'], bpm=recipe['bpm'], pan=recipe['pan'], chain=recipe['chain'])
        for block, settings in recipe['blocks'].items():
            dst = draft['blocks'][block]
            dst['enabled'] = settings['enabled']
            if 'model_index' in settings:
                model = settings['model_index']
                tail = dst['knobs'][:] if dst['model_index'] == model else [0] * 12
                count = len(MODELS[block][model]['parameters'])
                values = settings['knobs'][:count]
                tail[:len(values)] = values
                dst.update(model_index=model, knobs=tail)
        return decode(encode(body['raw_hex'], draft))
    if route not in ('/api/current', '/api/read-slot', '/api/save', '/api/controls'):
        raise ValueError('Operacao desconhecida.')
    midi = Midi(body['input'], body['output'])
    try:
        if route == '/api/current':
            status = midi.read(0, 86, 2)
            if status[0] >= 160:
                raise ValueError('Indice atual inesperado.')
            r = decode(midi.read(0, 448, 1))
            r.update(slot=status[0] + 1, edit_buffer=True)
            return r
        slot = body['slot']
        if route == '/api/controls':
            source = midi.slot(slot)
            before = bytes.fromhex(body['raw_hex'])
            validate(before)
            validate(source)
            base = before[:CONTROL_START] + source[CONTROL_START:]
            return decode(encode(base.hex(), body['draft']))
        if route == '/api/read-slot':
            r = decode(midi.slot(slot))
            r.update(slot=slot, edit_buffer=False)
            return r
        raw = encode(body['raw_hex'], body['draft'])
        return midi.save(slot, raw, body['expected_sha'], DATA / 'backups')
    finally:
        midi.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def headers_ok(self):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        return self.headers.get('Host') in allowed

    def reply(self, status, data, kind='application/json; charset=utf-8'):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8') if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.headers_ok():
            return self.reply(403, {'error': 'Host recusado.'})
        if self.path in ASSETS:
            name, kind = ASSETS[self.path]
            return self.reply(200, (FOLDER / 'assets' / name).read_bytes(), kind)
        if self.path == '/':
            html = (FOLDER / 'index.html').read_text(encoding='utf-8').replace('__APP_TOKEN__', TOKEN)
            return self.reply(200, html.encode('utf-8'), 'text/html; charset=utf-8')
        if self.path == '/api/bootstrap' and self.headers.get('X-Studio-Token') == TOKEN:
            return self.reply(200, {'catalog': CATALOG, 'ports': ports(), 'library': LIBRARY.list(), 'data_folder': str(DATA), 'automation': RECEIVER.status()})
        if self.path == '/api/automation-status' and self.headers.get('X-Studio-Token') == TOKEN:
            with LOCK:
                state = RECEIVER.status()
            return self.reply(200, state)
        return self.reply(404, {'error': 'Nao encontrado.'})

    def do_POST(self):
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        if not self.headers_ok() or self.headers.get('X-Studio-Token') != TOKEN \
                or (origin is not None and origin != f'http://{host}'):
            return self.reply(403, {'error': 'Requisicao externa recusada.'})
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, {'error': 'JSON obrigatorio.'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if not 0 < n <= 200000:
                raise ValueError('Tamanho de requisicao invalido.')
            body = json.loads(self.rfile.read(n))
            # Protect device access and file mutations from concurrent requests.
            with LOCK:
                r = dispatch(self.path, body)
            self.reply(200, r)
        except Exception as e:
            self.reply(400, {'error': str(e)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    url = f'http://127.0.0.1:{server.server_port}'
    print('MK300 Studio:', url, flush=True)
    print('Mantenha esta janela aberta. Feche com Ctrl+C ao terminar.', flush=True)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    RECEIVER.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        RECEIVER.stop()
        server.server_close()


if __name__ == '__main__':
    main()
