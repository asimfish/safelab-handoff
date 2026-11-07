"""Execute unchanged plot_two.py and plot_len.py with a portable process-local D.
Use frozen final display arrays for the two-method figures. Keep the legacy
out/table2_srk.json untouched for plot_srk.py and its historical reference curves.
"""
import ast
import json
from pathlib import Path
import shutil
import tempfile
ROOT = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='.final-plot-', dir=ROOT) as staging:
    staging = Path(staging)
    (staging / 'out').mkdir()
    frozen = json.loads((ROOT / 'frozen-data.json').read_text())
    (staging / 'out/table2_srk.json').write_text(json.dumps({'curves': frozen['curves']}))
    for name in ['plot_two.py', 'plot_len.py']:
        source = ROOT / name
        tree = ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
        assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'D' for target in node.targets)]
        if len(assignments) != 1:
            raise RuntimeError('Expected exactly one supplied D assignment in ' + name)
        assignments[0].value = ast.Constant(str(staging) + '/')
        ast.fix_missing_locations(tree)
        exec(compile(tree, str(source), 'exec'), {'__name__': '__main__', '__file__': str(source)})
    (ROOT / 'out').mkdir(exist_ok=True)
    for output in (staging / 'out').iterdir():
        if output.suffix in ('.pdf', '.png'):
            shutil.copyfile(output, ROOT / 'out' / output.name)
