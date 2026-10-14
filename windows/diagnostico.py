"""Read-only Windows MIDI probe. No preset loading, global writes or flash writes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mvave import protocol as p
from mvave.devices import mk300


def choose_port(names, requested=None):
    if requested is not None:
        if requested not in names:
            raise ValueError(f"Porta nao encontrada: {requested!r}")
        return requested
    matches = [n for n in names if any(t in n.lower().replace('-', '').replace(' ', '')
               for t in ('mk300', 'mvave', 'cuvave', 'usbcompositedevice'))]
    if len(matches) != 1:
        raise ValueError("Nao foi possivel selecionar uma unica porta da MK-300. "
                         "Use --input e --output com os nomes completos listados.")
    return matches[0]


def read_only_query(midi_in, midi_out, message_factory, field, length, space, timeout=3.0):
    # Deliberately restricted to these two read requests.
    if (field, length, space) not in ((0, 86, p.SPACE_STATUS), (0, 448, p.SPACE_PRESET)):
        raise ValueError("Consulta fora do diagnostico de leitura.")
    for _ in midi_in.iter_pending():
        pass
    frame = p.read(field, length, space)
    midi_out.send(message_factory('sysex', data=frame[1:-1]))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for msg in midi_in.iter_pending():
            if msg.type != 'sysex':
                continue
            try:
                reply = p.parse(bytes(msg.bytes()))
            except (ValueError, IndexError):
                continue
            if (reply.cls, reply.field, reply.space, reply.length) == (p.CLS_READ, field, space, length) \
                    and len(reply.payload) == length:
                return reply.payload
        time.sleep(0.01)
    raise TimeoutError("A MK-300 nao respondeu a consulta. Feche o M-EFCS, confira o cabo "
                       "USB de dados e execute novamente. Compatibilidade V75 ainda nao confirmada.")


def describe_preset(raw):
    ps = mk300.Preset(raw)
    if sorted(ps.chain) != list(range(len(mk300.BLOCKS))):
        raise ValueError("Ordem de blocos inesperada: interrompido, sem interpretar como V73.")
    if not 0 <= ps.volume <= 100 or not 1 <= ps.bpm <= 1000:
        raise ValueError("Volume/BPM inesperados: layout V75 precisa ser investigado.")
    return {'name': ps.name, 'volume': ps.volume, 'bpm': ps.bpm, 'pan': ps.pan,
            'chain': [mk300.BLOCKS[i] for i in ps.chain],
            'blocks': {name: {'enabled': ps.enabled(i), 'model_index': ps.model(i),
                             'raw_knobs': ps.knobs(i)}
                       for i, name in enumerate(mk300.BLOCKS)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description='MK-300: diagnostico somente leitura')
    ap.add_argument('--input', help='Nome completo da porta MIDI de entrada')
    ap.add_argument('--output', help='Nome completo da porta MIDI de saida')
    ap.add_argument('--list-only', action='store_true', help='Listar portas sem enviar mensagens')
    ap.add_argument('--firmware', default='V75', help='Versao informada pelo usuario; nao detectada')
    ap.add_argument('--report-dir', type=Path, default=Path(__file__).parent / 'diagnosticos')
    a = ap.parse_args(argv)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'firmware_user_reported': a.firmware, 'firmware_detected': None,
              'protocol_reference': 'MK-300 V73; V75 requires physical validation',
              'read_only': True, 'status': 'not_tested'}
    result = 1
    try:
        import mido
        mido.set_backend('mido.backends.rtmidi')
        ins, outs = mido.get_input_names(), mido.get_output_names()
        report.update(midi_inputs=ins, midi_outputs=outs)
        print('Entradas MIDI:', json.dumps(ins, ensure_ascii=False))
        print('Saidas MIDI:', json.dumps(outs, ensure_ascii=False))
        if a.list_only:
            report['status'] = 'ports_listed'
            result = 0
        else:
            ip, op = choose_port(ins, a.input), choose_port(outs, a.output)
            report.update(selected_input=ip, selected_output=op)
            with mido.open_input(ip) as mi, mido.open_output(op) as mo:
                status = read_only_query(mi, mo, mido.Message, 0, 86, p.SPACE_STATUS)
                raw = read_only_query(mi, mo, mido.Message, 0, 448, p.SPACE_PRESET)
            report.update(status_raw_hex=status.hex(), edit_buffer_raw_hex=raw.hex())
            report['edit_buffer'] = describe_preset(raw)
            if status[0] >= 160:
                raise ValueError('Indice de preset inesperado no bloco global.')
            report['preset_index_1based'] = status[0] + 1
            report['status'] = 'read_success'
            result = 0
            print('Leitura concluida. Preset atual:', report['edit_buffer']['name'])
            print('Isso confirma somente estas leituras; nao valida gravacao ou NAM na V75.')
    except (Exception, KeyboardInterrupt) as e:
        report.update(status='error', error=f'{type(e).__name__}: {e}')
        print(report['error'], file=sys.stderr)
    finally:
        a.report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        target = a.report_dir / f'mk300_{stamp}.json'
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Relatorio:', target.resolve())
    return result


if __name__ == '__main__':
    raise SystemExit(main())
