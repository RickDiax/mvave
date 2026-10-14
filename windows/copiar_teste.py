"""Copy the STORED Belief [142] to USER PRESET [137], preserving unknown bytes.

Default: preview only. --apply writes just slot 137, commits and verifies by read-back.
Does not load a preset or change globals. USB names can differ on Windows.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mvave import protocol as p
from mvave.devices import mk300

SOURCE = 142
TARGET = 137
NAME = 'TESTE USB'


class ReadTransport:
    def __init__(self, midi_in, midi_out, message_factory):
        self.mi, self.mo, self.message_factory = midi_in, midi_out, message_factory

    def _send(self, frame):
        for _ in self.mi.iter_pending():
            pass
        self.mo.send(self.message_factory('sysex', data=frame[1:-1]))

    def read_slot(self, slot, timeout=3.0):
        if slot not in (SOURCE, TARGET):
            raise ValueError('Este teste le somente as posicoes 142 e 137.')
        field = (slot - 1) * mk300.SIZE
        self._send(p.read(field, mk300.SIZE, p.SPACE_BANK))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for msg in self.mi.iter_pending():
                if msg.type != 'sysex':
                    continue
                try:
                    f = p.parse(bytes(msg.bytes()))
                except (ValueError, IndexError):
                    continue
                if (f.cls, f.field, f.length, f.space) == (p.CLS_READ, field, mk300.SIZE, p.SPACE_BANK) \
                        and len(f.payload) == mk300.SIZE:
                    return f.payload
            time.sleep(0.01)
        raise TimeoutError(f'Sem resposta ao ler a posicao {slot}.')

    def write_target(self, image, timeout=5.0):
        if len(image) != mk300.SIZE:
            raise ValueError('Imagem de preset invalida.')
        self._write(p.write_preset_image(TARGET - 1, image), timeout)

    def commit(self, timeout=5.0):
        self._write(p.COMMIT, timeout)

    def _write(self, frame, timeout):
        # Only this preset image or the bank commit can be sent.
        f = p.parse(frame)
        is_target = (f.cls == p.CLS_WRITE and f.space == p.SPACE_BANK
                     and f.field == (TARGET - 1) * mk300.SIZE
                     and f.length == mk300.SIZE and len(f.payload) == mk300.SIZE
                     and f.cmd == p.CMD_READ | ((mk300.SIZE // 16) << 7))
        if not is_target and frame != p.COMMIT:
            raise ValueError('Comando de escrita fora deste teste.')
        self._send(frame)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for msg in self.mi.iter_pending():
                if msg.type == 'sysex' and p.is_ack(bytes(msg.bytes())):
                    return
            time.sleep(0.01)
        raise TimeoutError('Sem ACK de escrita. Estado pode ser parcial; nao repita a gravacao '
                           'antes de conferir a posicao 137 e o relatorio.')


def validate(raw):
    ps = mk300.Preset(raw)
    if sorted(ps.chain) != list(range(11)) or not 0 <= ps.volume <= 100:
        raise ValueError('Layout do preset inesperado. Teste interrompido.')
    return ps


def prepare_image(source, target):
    src, dst = validate(source), validate(target)
    if src.name != 'Belief':
        raise ValueError(f'Posicao 142 chama-se {src.name!r}, nao Belief. Nada sera gravado.')
    if not re.fullmatch(r'USER PRESET(?:\s*\d{1,3})?', dst.name.strip(), flags=re.IGNORECASE):
        raise ValueError(f'Posicao 137 chama-se {dst.name!r}. Nada sera sobrescrito.')
    image = bytearray(source)
    image[:20] = NAME.encode('ascii').ljust(20, b'\0')
    return bytes(image)


def copy_test(transport, report, persist, apply=False, verify_timeout=15.0):
    source = transport.read_slot(SOURCE)
    target = transport.read_slot(TARGET)
    report.update(source_raw_hex=source.hex(), target_before_raw_hex=target.hex(),
                  source_name=mk300.Preset(source).name, target_before_name=mk300.Preset(target).name)
    # Save the two original images locally even if a precondition fails.
    persist(report)
    image = prepare_image(source, target)
    report.update(planned_image_hex=image.hex(), status='preview_ready')
    persist(report)
    if not apply:
        return
    # Persist before starting the mutation; no automatic retry of a write.
    report.update(status='write_started', read_only=False)
    persist(report)
    transport.write_target(image)
    transport.commit()
    deadline = time.monotonic() + verify_timeout
    while time.monotonic() < deadline:
        try:
            back = transport.read_slot(TARGET)
        except TimeoutError:
            time.sleep(0.25)
            continue
        if back == image:
            report.update(status='copy_verified', target_after_raw_hex=back.hex())
            persist(report)
            return
        report['target_last_read_hex'] = back.hex()
        time.sleep(0.25)
    raise TimeoutError('A posicao 137 nao confirmou a copia byte a byte. Nao reexecute a '
                       'gravacao; envie o relatorio para investigarmos.')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Belief [142] -> TESTE USB [137]')
    ap.add_argument('--input', default='USB-Midi 0')
    ap.add_argument('--output', default='USB-Midi 1')
    ap.add_argument('--apply', action='store_true', help='Salvar a copia em 137; sem isso, somente previa')
    a = ap.parse_args(argv)
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'source_slot': SOURCE,
              'target_slot': TARGET, 'target_name': NAME, 'firmware_user_reported': 'V75',
              'read_only': True, 'status': 'starting'}
    folder = Path(__file__).parent / 'diagnosticos'
    folder.mkdir(parents=True, exist_ok=True)
    target_file = folder / ('copia_142_137_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')

    def persist(r):
        temp = target_file.with_suffix('.tmp')
        temp.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(target_file)

    result = 1
    try:
        import mido
        mido.set_backend('mido.backends.rtmidi')
        if a.input not in mido.get_input_names() or a.output not in mido.get_output_names():
            raise ValueError('Portas nao encontradas. Confira com testar.cmd --list-only.')
        print('Origem: Belief salvo em 142. Destino: USER PRESET 137 -> TESTE USB.')
        print('Modo:', 'SALVAR COPIA' if a.apply else 'PREVIA SEM ESCRITA')
        with mido.open_input(a.input) as mi, mido.open_output(a.output) as mo:
            copy_test(ReadTransport(mi, mo, mido.Message), report, persist, apply=a.apply)
        result = 0
        print('Copia salva e verificada byte a byte.' if a.apply else 'Previa concluida; nada gravado.')
        print('Nenhum preset foi carregado. Selecione 137 na pedaleira para ouvir a copia.')
    except (Exception, KeyboardInterrupt) as e:
        report.update(status='error', error=f'{type(e).__name__}: {e}')
        print(report['error'], file=sys.stderr)
    finally:
        persist(report)
        print('Backup de dados e relatorio:', target_file.resolve())
    return result


if __name__ == '__main__':
    raise SystemExit(main())
