"""Portable execution of the supplied scripts, preserving every original source byte.
Run: python3 reproduce.py [--no-plots]. Requires matplotlib for the PDF/PNG step.
The pinned snapshot ships locally as data.json.gz; no download is required.
"""
import argparse
import ast
import contextlib
import hashlib
import gzip
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
ROOT = Path(__file__).resolve().parent

def input_snapshot():
    manifest = json.loads((ROOT / 'INPUT_MANIFEST.json').read_text())
    target = ROOT / 'data.json'
    compressed = ROOT / 'data.json.gz'
    if target.is_symlink() or compressed.is_symlink():
        raise RuntimeError('Refuse symlink snapshot inputs')
    if target.exists():
        raw = target.read_bytes()
    else:
        wire = compressed.read_bytes()
        if len(wire) != manifest['wire_bytes'] or hashlib.sha256(wire).hexdigest() != manifest['wire_sha256']:
            raise RuntimeError('Compressed snapshot byte count or SHA256 mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(wire)) as stream:
            raw = stream.read(manifest['bytes'] + 1)
    if len(raw) != manifest['bytes'] or hashlib.sha256(raw).hexdigest() != manifest['sha256']:
        raise RuntimeError('Snapshot byte count or SHA256 mismatch')
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    manifest = input_snapshot()
    (ROOT / 'out').mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'compute_table2.py'), 'extra'], cwd=ROOT, check=True)
    strict = json.loads((ROOT / 'out/table2_srk.json').read_text())
    frozen = json.loads((ROOT / 'frozen-data.json').read_text())
    if strict['rows'] != frozen['strict_reference']['rows']:
        raise RuntimeError('Strict table no longer matches its frozen reference')
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        namespace = runpy.run_path(str(ROOT / 'compute_table2_v12best.py'))
    (ROOT / 'out/table2_v12best.txt').write_text(captured.getvalue())
    full = [[row[0]] + [cell.split(' (')[0] for cell in row[1:-1]] + [row[-1]] for row in namespace['rows']]
    if full != frozen['full_rows']:
        raise RuntimeError('Relaxed best-horizon full table differs from frozen values')
    main_rows = []
    for method in ['π0.5', 'Mem-0', 'MemoryVLA', 'TTS-Memory']:
        row = [method]
        rates = []
        for task in [3, 7, 10]:
            choices = namespace['C'].get((method, task))
            if not choices:
                row.append('—')
                continue
            horizon, (success, trials, flag) = max(choices.items(), key=lambda kv: kv[1][0] / kv[1][1])
            rate = 100 * success / trials
            rates.append(rate)
            row.append(f'{rate:.1f}{flag}')
        row.append(f'{sum(rates)/3:.1f}' if len(rates) == 3 else '—')
        main_rows.append(row)
    if main_rows != frozen['rows']:
        raise RuntimeError('Three-setting main table differs from frozen values')
    (ROOT / 'out/table2_main_verified.json').write_text(json.dumps(main_rows, ensure_ascii=False, indent=2) + '\n')
    length_source = ast.parse((ROOT / 'plot_len.py').read_text())
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in length_source.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('X', 'V')}
    if constants['X'] != [3, 7, 10]:
        raise RuntimeError('Supplied length plot uses unexpected task lengths')
    for series in frozen['episode_curves']:
        if constants['V'][series['method']] != series['success_rate']:
            raise RuntimeError('Length plot source differs from Table 2')
    if not args.no_plots:
        subprocess.run([sys.executable, str(ROOT / 'plot_srk.py')], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / 'portable_plot_two.py')], cwd=ROOT, check=True)
    print('Verified snapshot SHA256:', manifest['sha256'])
    print('Verified main three-setting Avg and full four-setting Avg; supplied scripts unchanged.')
if __name__ == '__main__':
    main()
