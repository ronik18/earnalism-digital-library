import unittest,tempfile
from pathlib import Path
from asr_cuda_env import cuda_asr_environment
class CudaAsrEnvironmentTests(unittest.TestCase):
 def test_missing_existing_cublas_stops_without_installation(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'cuBLAS not found'):cuda_asr_environment(d,{})
 def test_child_only_path_keeps_existing_environment_and_deduplicates(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'lib/python3.12/site-packages/nvidia/cublas/lib';p.mkdir(parents=True);(p/'libcublas.so.12').touch()
   original={'LD_LIBRARY_PATH':str(p)+':/existing','UNCHANGED':'yes'}
   result=cuda_asr_environment(d,original)
   self.assertEqual(original,{'LD_LIBRARY_PATH':str(p)+':/existing','UNCHANGED':'yes'})
   self.assertEqual(result['LD_LIBRARY_PATH'],str(p.resolve())+':/existing');self.assertEqual(result['UNCHANGED'],'yes')
