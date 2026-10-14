"""MK300 Studio: preset editing and serialized USB operations for Windows."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mvave import protocol as p
from mvave.devices import mk300 as profile

CATALOG = json.loads((Path(__file__).parent / 'catalog.json').read_text(encoding='utf-8'))
MODELS = {b['name']: {m['index']: m for m in b['models']} for b in CATALOG['blocks']}
CONTROL_START = 0x14A


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(raw):
    ps = profile.Preset(raw)
    if sorted(ps.chain) != list(range(11)) or not 0 <= ps.volume <= 100:
        raise ValueError('Formato inesperado do preset. Operacao interrompida.')
    if any(raw[profile.enabled_offset(i)] not in (0, 1) for i in range(11)):
        raise ValueError('Estado de bloco inesperado.')
    return ps


def decode(raw):
    ps = validate(raw)
    return {'raw_hex': raw.hex(), 'sha256': digest(raw), 'name': ps.name,
            'volume': ps.volume, 'bpm': ps.bpm, 'pan': ps.pan,
            'chain': [profile.BLOCKS[i] for i in ps.chain],
            'blocks': {name: {'model_index': ps.model(i), 'enabled': ps.enabled(i),
                              'knobs': ps.knobs(i)} for i, name in enumerate(profile.BLOCKS)}}


def encode(raw_hex, draft):
    before = bytes.fromhex(raw_hex)
    original = validate(before)
    image = bytearray(before)
    name = str(draft['name']).strip()
    if not name or len(name) > 20 or any(ord(x) < 32 or ord(x) > 126 for x in name):
        raise ValueError('Use um nome de 1 a 20 caracteres sem acentos.')
    image[:20] = name.encode('ascii').ljust(20, b'\0')

    def number(off, value, lo, hi):
        if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
            raise ValueError(f'Parametro fora da faixa: {value!r}.')
        image[off:off + 2] = (value & 0xFFFF).to_bytes(2, 'little')

    number(profile.OFF_VOL, draft['volume'], 0, 100)
    number(profile.OFF_BPM, draft['bpm'], 40, 240)
    number(profile.OFF_PAN, draft['pan'], -100, 100)
    if sorted(draft['chain']) != sorted(profile.BLOCKS):
        raise ValueError('Cadeia invalida: cada bloco precisa aparecer uma vez.')
    image[profile.OFF_CHAIN:profile.OFF_CHAIN + 11] = bytes(profile.BLOCK_ID[x] for x in draft['chain'])
    if set(draft['blocks']) != set(profile.BLOCKS):
        raise ValueError('Lista de blocos incompleta.')
    for i, block in enumerate(profile.BLOCKS):
        settings = draft['blocks'][block]
        model = settings['model_index']
        if isinstance(model, bool) or not isinstance(model, int):
            raise ValueError('Indice de modelo invalido.')
        md = MODELS[block].get(model)
        if md is None and model != original.model(i):
            raise ValueError(f'Modelo nao catalogado: {block} {model}.')
        image[profile.model_offset(i)] = model
        if type(settings['enabled']) is not bool:
            raise ValueError('Ativacao invalida.')
        image[profile.enabled_offset(i)] = int(settings['enabled'])
        values = settings['knobs']
        if len(values) != 12:
            raise ValueError('Cada bloco exige 12 valores brutos.')
        params = md['parameters'] if md else []
        for k, value in enumerate(values):
            old = original.knob(i, k)
            if model == original.model(i) and value == old:
                continue  # preserve nonstandard/unknown existing values without guessing
            if k >= len(params):
                if value != 0:
                    raise ValueError('Parametros nao catalogados devem ser preservados ou zerados.')
                number(profile.knob_offset(i, k), value, 0, 0)
                continue
            param = params[k]
            if param.get('readonly'):
                if model != original.model(i) or value != old:
                    raise ValueError(f"Ajuste {block}/{param['name']} na pedaleira e leia novamente.")
            number(profile.knob_offset(i, k), value, param['min'], param['max'])
    if image[CONTROL_START:] != before[CONTROL_START:]:
        raise AssertionError('Controles alterados indevidamente.')
    validate(bytes(image))
    return bytes(image)


class Midi:
    def __init__(self, input_name, output_name):
        import mido
        self.mido = mido
        mido.set_backend('mido.backends.rtmidi')
        self.mi = mido.open_input(input_name)
        try:
            self.mo = mido.open_output(output_name)
        except Exception:
            self.mi.close()
            raise

    def close(self):
        self.mi.close()
        self.mo.close()

    def send(self, raw):
        for _ in self.mi.iter_pending():
            pass
        self.mo.send(self.mido.Message('sysex', data=raw[1:-1]))

    def read(self, field, length, space, timeout=3):
        self.send(p.read(field, length, space))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for msg in self.mi.iter_pending():
                if msg.type != 'sysex':
                    continue
                try:
                    f = p.parse(bytes(msg.bytes()))
                except (ValueError, IndexError):
                    continue
                if (f.cls, f.field, f.length, f.space) == (p.CLS_READ, field, length, space) and len(f.payload) == length:
                    return f.payload
            time.sleep(0.005)
        raise TimeoutError('Sem resposta MIDI. Feche M-EFCS/DAW e confira as portas e o cabo USB.')

    def slot(self, n):
        if type(n) is not int or not 1 <= n <= 160:
            raise ValueError('Posicao precisa estar entre 1 e 160.')
        return self.read((n - 1) * profile.SIZE, profile.SIZE, p.SPACE_BANK)

    def write(self, raw):
        self.send(raw)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            for msg in self.mi.iter_pending():
                if msg.type == 'sysex' and p.is_ack(bytes(msg.bytes())):
                    return
            time.sleep(0.005)
        raise TimeoutError('Sem confirmacao de escrita; pode haver alteracao parcial. Leia o destino antes de tentar novamente.')

    def save(self, slot, raw, expected_sha, backup_dir):
        validate(raw)
        before = self.slot(slot)
        if digest(before) != expected_sha:
            raise ValueError('O destino mudou desde a previa. Leia novamente antes de gravar.')
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f'{datetime.now():%Y%m%d_%H%M%S_%f}_slot{slot:03d}.json'
        record = {'format': 'mk300-studio-1', 'slot': slot, 'status': 'backup_before_write',
                  'before_raw_hex': before.hex(), 'planned_raw_hex': raw.hex()}

        def persist():
            tmp = backup.with_suffix('.tmp')
            tmp.write_text(json.dumps(record, indent=2), encoding='utf-8')
            tmp.replace(backup)

        persist()  # a failed local backup prevents any USB write
        try:
            record['status'] = 'write_started'
            persist()
            self.write(p.write_preset_image(slot - 1, raw))
            self.write(p.COMMIT)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    after = self.slot(slot)
                except TimeoutError:
                    continue
                if after == raw:
                    record.update(status='verified', after_raw_hex=after.hex())
                    persist()
                    return {'verified': True, 'slot': slot, 'backup': backup.name}
                time.sleep(0.25)
            raise TimeoutError('Gravacao sem leitura de retorno correspondente. Confira o destino; nao repita automaticamente.')
        except Exception as e:
            record.update(status='uncertain', error=str(e))
            persist()
            raise


class Library:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def list(self):
        result = []
        for path in self.folder.glob('*.json'):
            try:
                r = json.loads(path.read_text(encoding='utf-8'))
                validate(bytes.fromhex(r['raw_hex']))
                result.append({'id': path.stem, 'name': r['name'], 'updated_at': r['updated_at']})
            except (ValueError, KeyError):
                continue
        return sorted(result, key=lambda r: r['updated_at'], reverse=True)

    def save(self, raw):
        ps = validate(raw)
        key = uuid.uuid4().hex
        r = {'format': 'mk300-studio-1', 'name': ps.name, 'raw_hex': raw.hex(),
             'updated_at': datetime.now().isoformat()}
        tmp = self.folder / f'{key}.tmp'
        tmp.write_text(json.dumps(r, indent=2), encoding='utf-8')
        tmp.replace(self.folder / f'{key}.json')
        return key

    def get(self, key):
        if not isinstance(key, str) or len(key) != 32 or any(x not in '0123456789abcdef' for x in key):
            raise ValueError('Identificador de timbre invalido.')
        r = json.loads((self.folder / f'{key}.json').read_text(encoding='utf-8'))
        return decode(bytes.fromhex(r['raw_hex']))
