"""Reduce only MW-FACE Fuzz/Level in LITTLE WING [137]; preserve everything else."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

from copiar_teste import ReadTransport, validate, mk300


def soften(raw):
    ps = validate(raw)
    if ps.name != 'LITTLE WING' or ps.model(3) != 47:
        raise ValueError('Esperado LITTLE WING com MW-FACE na 137. Nada sera alterado.')
    image = bytearray(raw)
    for knob, value in [(0, 25), (1, 35)]:
        off = mk300.knob_offset(3, knob)
        image[off:off + 2] = value.to_bytes(2, 'little')
    return bytes(image)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Little Wing: Fuzz 25, Level 35, somente 137')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--input', default='USB-Midi 0')
    ap.add_argument('--output', default='USB-Midi 1')
    a = ap.parse_args(argv)
    folder = Path(__file__).parent / 'diagnosticos'
    folder.mkdir(exist_ok=True)
    target = folder / ('fuzz_137_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    report = {'target_slot': 137, 'status': 'starting', 'read_only': True}

    def persist():
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(report, indent=2), encoding='utf-8')
        tmp.replace(target)

    result = 1
    try:
        import mido
        mido.set_backend('mido.backends.rtmidi')
        with mido.open_input(a.input) as mi, mido.open_output(a.output) as mo:
            d = ReadTransport(mi, mo, mido.Message)
            before = d.read_slot(137)
            report.update(before_raw_hex=before.hex(), status='backed_up')
            persist()
            image = soften(before)
            report.update(planned_image_hex=image.hex(), status='preview_ready')
            persist()
            print('Somente DS/MW-FACE: Fuzz 25, Level 35. Base, UniVibe e controles preservados.')
            if a.apply and image != before:
                report.update(status='write_started', read_only=False)
                persist()
                d.write_target(image)
                d.commit()
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        back = d.read_slot(137)
                    except TimeoutError:
                        time.sleep(0.25)
                        continue
                    if back == image:
                        report.update(status='fuzz_verified', after_raw_hex=back.hex())
                        break
                    time.sleep(0.25)
                else:
                    raise TimeoutError('Nao confirmou a gravacao. Nao repita; envie o relatorio.')
                print('Fuzz corrigido e verificado byte a byte.')
            elif a.apply:
                report['status'] = 'already_adjusted'
                print('Fuzz ja esta em 25 e Level em 35; nada foi gravado.')
            else:
                print('Somente previa; nada foi gravado.')
        print('Selecione outro preset e volte a 137 para carregar o ajuste.')
        result = 0
    except (Exception, KeyboardInterrupt) as e:
        report.update(status='error', error=f'{type(e).__name__}: {e}')
        print(report['error'], file=sys.stderr)
    finally:
        persist()
        print('Backup e relatorio:', target.resolve())
    return result


if __name__ == '__main__':
    raise SystemExit(main())
