"""ChatGPT -> repository inbox -> local, bounded preset writes. No remote code execution."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.request import Request, urlopen

from core import MODELS, Library, Midi, decode, digest, encode, profile

INBOX_URL = 'https://raw.githubusercontent.com/RickDiax/mvave/main/automation/inbox.json'
CATALOG_SHA256 = hashlib.sha256((Path(__file__).parent / 'catalog.json').read_bytes()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value):
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Data do pedido precisa conter fuso horario.')
    return d


def fetch_inbox():
    # Only this fixed repository can supply recipes; no arbitrary callback/download URLs.
    req = Request(INBOX_URL + '?poll=' + str(int(time.time() // 15)),
                  headers={'User-Agent': 'MK300-Studio/2', 'Cache-Control': 'no-cache'})
    with urlopen(req, timeout=8) as response:
        if response.geturl().split('?')[0] != INBOX_URL:
            raise ValueError('Redirecionamento da caixa de entrada recusado.')
        data = response.read(100001)
    if len(data) > 100000:
        raise ValueError('Pedido excede 100 KB.')
    result = json.loads(data)
    if not isinstance(result, dict) or result.get('format') != 'mk300-tone-inbox-1':
        raise ValueError('Formato de caixa de entrada desconhecido.')
    return result


def compile_recipe(raw, recipe):
    """Recipes describe sound, never ports, slot numbers, controllers, globals or commands."""
    allowed = {'name', 'volume', 'bpm', 'pan', 'chain', 'blocks'}
    if set(recipe) != allowed or set(recipe['blocks']) != set(profile.BLOCKS):
        raise ValueError('Receita incompleta ou com campos nao permitidos.')
    draft = decode(raw)
    for key in allowed - {'blocks'}:
        draft[key] = recipe[key]
    for block, settings in recipe['blocks'].items():
        if not isinstance(settings, dict) or not set(settings) <= {'enabled', 'model_index', 'parameters'} or 'enabled' not in settings:
            raise ValueError(f'Configuracao invalida de {block}.')
        dst = draft['blocks'][block]
        dst['enabled'] = settings['enabled']
        index = settings.get('model_index', dst['model_index'])
        if type(index) is not int:
            raise ValueError('Indice de modelo precisa ser inteiro.')
        model = MODELS[block].get(index)
        if model is None and ('model_index' in settings or settings.get('parameters')):
            raise ValueError(f'Modelo desconhecido em {block}.')
        if index != dst['model_index']:
            dst['model_index'] = index
            dst['knobs'] = [p['default'] for p in model['parameters']]
            dst['knobs'] += [0] * (12 - len(dst['knobs']))
        params = settings.get('parameters', {})
        if not isinstance(params, dict):
            raise ValueError('Parametros precisam ser um objeto por nome.')
        names = {p['name']: i for i, p in enumerate(model['parameters'])} if model else {}
        for name, value in params.items():
            if name not in names:
                raise ValueError(f'Parametro desconhecido: {block}/{name}.')
            dst['knobs'][names[name]] = value
    return encode(raw.hex(), draft)


class Receiver:
    def __init__(self, folder, lock, fetcher=fetch_inbox, midi_factory=Midi, clock=utcnow):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / 'automation.json'
        self.lock, self.fetcher, self.midi_factory, self.clock = lock, fetcher, midi_factory, clock
        self.enabled = False  # arming requires a successful local read each program session
        self.config = None
        self.epoch = 0
        self.stop_event = threading.Event()
        self.thread = None
        self.state = {'phase': 'paused', 'message': 'Ative a recepcao antes de pedir um timbre no ChatGPT.', 'seen': []}
        if self.path.exists():
            old = json.loads(self.path.read_text(encoding='utf-8'))
            self.state.update(old)
            self.state.update(phase='paused', message='Recepcao pausada ao reiniciar. Confira o destino e ative novamente.')

    def persist(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def status(self):
        return {**{k: v for k, v in self.state.items() if k != 'seen'}, 'enabled': self.enabled,
                'slot': self.config['slot'] if self.config else None, 'catalog_sha256': CATALOG_SHA256}

    def enable(self, input_name, output_name, slot):
        self.enabled = False
        self.epoch += 1
        if type(slot) is not int or not 1 <= slot <= 160:
            raise ValueError('Escolha a posicao reservada entre 1 e 160.')
        # Check reachability before reading and authorizing this destination.
        document = self.fetcher()
        midi = self.midi_factory(input_name, output_name)
        try:
            raw = midi.slot(slot)
            current = decode(raw)
        finally:
            midi.close()
        self.config = {'input': input_name, 'output': output_name, 'slot': slot,
                       'expected_sha': digest(raw), 'armed_at': self.clock()}
        prior = document.get('job')
        if isinstance(prior, dict) and isinstance(prior.get('id'), str):
            self.remember(prior['id'])  # activating never replays an old published request
        self.state.update(phase='waiting', message=f'Recebendo novos pedidos do ChatGPT na posicao {slot}: {current["name"]}.',
                          destination_name=current['name'])
        self.persist()  # failure prevents arming
        self.enabled = True
        self.epoch += 1
        return self.status()

    def remember(self, key):
        if key not in self.state['seen']:
            self.state['seen'].append(key)

    def pause(self, message='Recepcao pausada.'):
        self.enabled = False
        self.epoch += 1
        self.state.update(phase='paused', message=message)
        self.persist()
        return self.status()

    def consume(self, document):
        # Called under the shared USB lock. Never retries a job after writing has begun.
        if not self.enabled:
            return
        if document.get('format') != 'mk300-tone-inbox-1':
            raise ValueError('Caixa de entrada invalida.')
        job = document.get('job')
        if job is None:
            return
        if not isinstance(job, dict):
            raise ValueError('Pedido invalido.')
        key = job.get('id')
        if not isinstance(key, str) or len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Identificador de pedido invalido.')
        if key in self.state['seen']:
            return
        now = self.clock()
        created = stamp(job['created_at'])
        expires = stamp(job['expires_at'])
        if created < self.config['armed_at'] or expires <= now:
            self.remember(key)
            self.state.update(message='Pedido antigo/expirado ignorado. Peca um novo timbre com a recepcao ativa.')
            self.persist()
            return
        if (created - now).total_seconds() > 300 or not 0 < (expires - created).total_seconds() <= 86400:
            raise ValueError('Prazo do pedido invalido. Confira o relogio do computador.')
        if job.get('format') != 'mk300-tone-job-1' or job.get('catalog_sha256') != CATALOG_SHA256:
            raise ValueError('Pedido e Studio usam formatos/catalogos diferentes. Atualize o Studio.')
        if set(job) - {'id','format','created_at','expires_at','catalog_sha256','recipe','request','sources','notes'}:
            raise ValueError('Campos extras no pedido recusados.')
        midi = self.midi_factory(self.config['input'], self.config['output'])
        try:
            slot = self.config['slot']
            before = midi.slot(slot)
            if digest(before) != self.config['expected_sha']:
                raise ValueError('A posicao reservada mudou fora da automacao. Confira e ative a recepcao novamente.')
            raw = compile_recipe(before, job['recipe'])
            # Keep a ready-to-import copy and source evidence locally before writing.
            receipt = self.folder / 'recebidos' / (key + '.json')
            receipt.parent.mkdir(parents=True, exist_ok=True)
            received = {'job':job, 'format':'mk300-studio-1', 'raw_hex':raw.hex(), 'slot':slot, 'verified':False}
            receipt.write_text(json.dumps(received, ensure_ascii=False, indent=2), encoding='utf-8')
            Library(self.folder / 'timbres').save(raw)
            self.remember(key)
            self.state.update(phase='writing', last_job_id=key, last_result=None, last_name=decode(raw)['name'], message=f'Gravando {decode(raw)["name"]} na posicao {slot}...')
            self.persist()  # durable at-most-once marker before first USB write
            result = midi.save(slot, raw, self.config['expected_sha'], self.folder / 'backups')
            if result.get('verified') is not True:
                raise ValueError('Gravacao sem confirmacao de retorno.')
            self.config['expected_sha'] = digest(raw)
            received['verified'] = True
            receipt.write_text(json.dumps(received, ensure_ascii=False, indent=2), encoding='utf-8')
            self.state.update(phase='verified', last_result=result, destination_name=decode(raw)['name'],
                              message=f'{decode(raw)["name"]} gravado e verificado na posicao {slot}. Selecione outra posicao e volte para ouvir.')
            self.persist()
        finally:
            midi.close()

    def poll_once(self):
        with self.lock:
            if not self.enabled:
                return
            epoch = self.epoch
        try:
            document = self.fetcher()
        except Exception as e:
            with self.lock:
                if self.enabled and self.epoch == epoch:
                    self.state.update(message='Sem acesso a caixa de entrada; tentando novamente: ' + str(e))
            return  # network retry is safe; there was no USB action
        with self.lock:
            if not self.enabled or self.epoch != epoch:
                return
            try:
                self.consume(document)
            except Exception as e:
                self.pause('Automacao pausada: ' + str(e) + ' Confira a posicao antes de reativar.')

    def start(self):
        def work():
            while not self.stop_event.wait(15):
                self.poll_once()
        self.thread = threading.Thread(target=work, name='mk300-inbox', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
