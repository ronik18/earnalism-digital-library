import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from colab_runner import execute
class BudgetTests(unittest.TestCase):
 def test_paid_runtime_requires_explicit_allowance(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused')
 def test_above_five_units_rejected(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',approved_compute_units=6,observed_units_per_hour=1.07)
 def test_unknown_rate_rejected(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',approved_compute_units=5)
 def test_estimated_usage_must_fit_margin(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',approved_compute_units=5,observed_units_per_hour=6)
 def test_unbounded_generation_rejected(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',budget_seconds=3600,approved_compute_units=5,observed_units_per_hour=1.07)

 def test_declared_shorter_runtime_keeps_twofold_unit_margin(self):
  from unittest.mock import patch
  # Stop before setup: passing validation must reach the GPU probe, never a model/API.
  with patch('colab_runner.subprocess.run') as run:
   run.return_value.returncode=1
   with self.assertRaisesRegex(RuntimeError,'CUDA'):execute('unused',budget_seconds=1000,approved_compute_units=1,observed_units_per_hour=1.07,runtime_limit_seconds=1100)
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',budget_seconds=1000,approved_compute_units=.5,observed_units_per_hour=1.07,runtime_limit_seconds=1100)
 def test_execution_cannot_exceed_declared_runtime(self):
  with self.assertRaisesRegex(RuntimeError,'allowance'):execute('unused',budget_seconds=1200,approved_compute_units=1,observed_units_per_hour=1.07,runtime_limit_seconds=1100)
