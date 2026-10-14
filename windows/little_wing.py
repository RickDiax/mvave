"""Apply Little Wing to the authorized slot 137, preserving its captured controls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from copiar_teste import ReadTransport, validate, mk300

FOLDER = Path(__file__).resolve().parent
CONTROL_START = 0x14A
EXPECTED_CONTROLS = bytes.fromhex(
    '090b00000000080a000000000012800000000007080000000a000000000064000b000000000000000b000000000000000b00000000000000040001000000640004000000000064000400030000006400004e47443400000000000000000000000000000000000000000000000000000000000000003e')


def build_image(before, recipe):
    ps = validate(before)
    if ps.name != 'TESTE USB':
        raise ValueError(f'A posicao 137 chama-se {ps.name!r}, nao TESTE USB. Nada sera gravado.')
    if ps.model(3) != 47 or ps.model(7) != 11:
        raise ValueError('DS/MOD diferentes do MW-FACE/Univibe observado. Confira e salve na 137.')
    if before[CONTROL_START:] != EXPECTED_CONTROLS:
        raise ValueError('Controles salvos diferem do ultimo relatorio. Pressione SAVE na 137 e '
                         'envie um diagnostico atualizado; nada sera gravado.')
    if recipe['target_slot'] != 137:
        raise ValueError('Este aplicador grava somente a posicao 137.')
    image = bytearray(before)
    name = recipe['name'].encode('ascii')
    if not 1 <= len(name) <= 20:
        raise ValueError('Nome precisa de 1 a 20 caracteres ASCII.')
    image[:20] = name.ljust(20, b'\0')

    def u16(offset, value, lo, hi):
        if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
            raise ValueError(f'Valor fora da faixa no offset {offset}: {value!r}')
        image[offset:offset + 2] = (value & 0xFFFF).to_bytes(2, 'little')

    u16(mk300.OFF_VOL, recipe['preset_volume'], 0, 100)
    u16(mk300.OFF_BPM, recipe['bpm'], 40, 240)
    u16(mk300.OFF_PAN, recipe['pan'], -100, 100)
    if sorted(recipe['chain']) != sorted(mk300.BLOCKS):
        raise ValueError('A cadeia deve conter cada bloco uma vez.')
    image[mk300.OFF_CHAIN:mk300.OFF_CHAIN + 11] = bytes(mk300.BLOCK_ID[x] for x in recipe['chain'])
    limits = {'DS': [(0, 100)] * 2, 'AMP': [(0, 100)] * 8,
              'CAB': [(0, 100), (20, 300), (50, 180)], 'EQ': [(-12, 12)] * 10,
              'MOD': [(1, 100), (0, 100), (0, 100), (0, 1), (40, 240)],
              'REV': [(0, 100)] * 5, 'VOL': [(0, 100)]}
    expected_models = {'DS': 47, 'AMP': 42, 'CAB': 42, 'EQ': 2, 'MOD': 11, 'REV': 2, 'VOL': 0}
    for block, settings in recipe['blocks'].items():
        b = mk300.BLOCK_ID[block]
        if not isinstance(settings['enabled'], bool):
            raise ValueError('enabled precisa ser booleano.')
        image[mk300.enabled_offset(b)] = int(settings['enabled'])
        if 'model_index' in settings:
            if expected_models.get(block) != settings['model_index']:
                raise ValueError(f'Modelo de {block} fora deste preset validado.')
            image[mk300.model_offset(b)] = settings['model_index']
        if 'knobs' in settings:
            ranges = limits[block]
            if len(settings['knobs']) != len(ranges):
                raise ValueError(f'Quantidade de parametros incorreta: {block}.')
            # Clear unused knob storage when selecting a known model; controls stay untouched.
            off = mk300.knob_offset(b, 0)
            image[off:off + mk300.KNOB_BYTES] = bytes(mk300.KNOB_BYTES)
            for k, (value, (lo, hi)) in enumerate(zip(settings['knobs'], ranges)):
                u16(mk300.knob_offset(b, k), value, lo, hi)
    if image[CONTROL_START:] != before[CONTROL_START:]:
        raise AssertionError('As atribuicoes de controle foram alteradas.')
    return bytes(image)


def apply_recipe(transport, recipe, report, persist, apply=False, verify_timeout=15):
    before = transport.read_slot(137)
    report.update(before_raw_hex=before.hex(), status='backed_up')
    persist(report)
    image = build_image(before, recipe)
    report.update(planned_image_hex=image.hex(), controls_preserved=True, status='preview_ready')
    persist(report)
    if not apply:
        return
    report.update(status='write_started', read_only=False)
    persist(report)
    transport.write_target(image)
    transport.commit()
    deadline = time.monotonic() + verify_timeout
    while time.monotonic() < deadline:
        try:
            after = transport.read_slot(137)
        except TimeoutError:
            time.sleep(0.25)
            continue
        if after == image:
            report.update(status='little_wing_verified', after_raw_hex=after.hex())
            persist(report)
            return
        report['last_read_hex'] = after.hex()
        time.sleep(0.25)
    raise TimeoutError('Gravacao nao confirmada. Nao repita; confira 137 e envie este relatorio.')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Little Wing na posicao 137')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--input', default='USB-Midi 0')
    ap.add_argument('--output', default='USB-Midi 1')
    a = ap.parse_args(argv)
    recipe = json.loads((FOLDER / 'little_wing.json').read_text(encoding='utf-8'))
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'target_slot': 137,
              'firmware_user_reported': 'V75', 'recipe': recipe, 'read_only': True, 'status': 'starting'}
    folder = FOLDER / 'diagnosticos'
    folder.mkdir(exist_ok=True)
    target = folder / ('little_wing_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')

    def persist(r):
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(target)

    result = 1
    try:
        import mido
        mido.set_backend('mido.backends.rtmidi')
        if a.input not in mido.get_input_names() or a.output not in mido.get_output_names():
            raise ValueError('Portas MIDI nao encontradas. Feche M-EFCS e confira o USB.')
        print('TESTE USB -> LITTLE WING, somente posicao 137.')
        print('Modo:', 'APLICAR E SALVAR' if a.apply else 'PREVIA')
        with mido.open_input(a.input) as mi, mido.open_output(a.output) as mo:
            apply_recipe(ReadTransport(mi, mo, mido.Message), recipe, report, persist, apply=a.apply)
        print('Little Wing salvo e verificado byte a byte.' if a.apply else 'Previa concluida; nada gravado.')
        print('Atribuicoes preservadas. Selecione outro preset e volte ao 137 para carregar os ajustes.')
        result = 0
    except (Exception, KeyboardInterrupt) as e:
        report.update(status='error', error=f'{type(e).__name__}: {e}')
        print(report['error'], file=sys.stderr)
    finally:
        persist(report)
        print('Backup e relatorio:', target.resolve())
    return result


if __name__ == '__main__':
    raise SystemExit(main())
