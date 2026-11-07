"""Verify the new notebook is inert until scoped runtime authorization."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import base64
import hashlib
import json
import tempfile
import unittest

from .build_colab import build, PROJECT, RUNTIME_ROOT


class NotebookSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.units = json.loads((PROJECT / 'output/episodes/04-thermal-touch/production-v1/units.json').read_text())
        (self.folder / 'units.json').write_text(json.dumps(self.units))
        with redirect_stdout(StringIO()):
            build(self.folder)

    def test_safe_run_all_needs_no_colab_or_model(self):
        notebook = json.loads((self.folder / 'Earnalism_Everyday_Science_04_Narration.ipynb').read_text())
        launch = ''.join(notebook['cells'][1]['source'])
        namespace = {}
        with redirect_stdout(StringIO()) as result:
            exec(compile(launch, 'private disabled notebook', 'exec'), namespace)
        self.assertIn('THERMAL_TOUCH_DISABLED', result.getvalue())
        self.assertFalse(namespace['RUN_THERMAL_TOUCH'])
        self.assertFalse(namespace['EXISTING_COMPUTE_ALLOWED'])
        self.assertFalse(namespace['FREE_RUNTIME_CONFIRMED'])
        self.assertNotIn('ROOT', namespace)

    def test_enabling_run_without_authority_stops_before_import(self):
        launch = (self.folder / 'colab-launch.py').read_text().replace('RUN_THERMAL_TOUCH = False', 'RUN_THERMAL_TOUCH = True', 1)
        with self.assertRaisesRegex(RuntimeError, 'No compute authorization'):
            exec(compile(launch, 'unauthorized launch', 'exec'), {})

    def test_embedded_recipe_pins_original_worker_and_isolated_paths(self):
        import ast
        launch = (self.folder / 'colab-launch.py').read_text()
        tree = ast.parse(launch)
        encoded = next(n.args[0].value for n in ast.walk(tree)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == 'b64decode')
        raw = base64.b64decode(encoded)
        payload = json.loads(raw)
        receipt = json.loads((self.folder / 'colab-payload.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt['payload_sha256'])
        self.assertEqual(payload['units'], self.units)
        self.assertEqual(payload['baseline'], json.loads((PROJECT / 'output/episodes/03-refraction/production-v1/baseline-job.json').read_text()))
        self.assertEqual(payload['software']['qwen_worker.py'], (PROJECT / 'video_studio/vendor/qwen_worker.py').read_text())
        self.assertIn(RUNTIME_ROOT.split('/')[-1], payload['software']['episode.py'])
        self.assertNotIn('earnalism-refraction-v1', payload['software']['episode.py'])

    def test_changed_prepared_job_is_never_replaced(self):
        launch = self.folder / 'colab-launch.py'
        launch.write_text('preserve prior job')
        with self.assertRaises(FileExistsError):
            build(self.folder)
        self.assertEqual(launch.read_text(), 'preserve prior job')


if __name__ == '__main__':
    unittest.main()
