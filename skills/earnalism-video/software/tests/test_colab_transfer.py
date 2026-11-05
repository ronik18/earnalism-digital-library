import unittest,tempfile,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from colab_transfer import export,assemble
class ColabTransferTests(unittest.TestCase):
 def test_actual_bytes_round_trip_and_corrupt_chunk_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);data=bytes(range(256))*50;(p/'source.zip').write_bytes(data)
   export(p/'source.zip',p/'parts',1024);assemble(p/'parts',p/'result.zip');self.assertEqual((p/'result.zip').read_bytes(),data)
   with self.assertRaises(FileExistsError):assemble(p/'parts',p/'result.zip')
   (p/'parts/part-000.txt').write_text('AAAA')
   with self.assertRaises(ValueError):assemble(p/'parts',p/'corrupt.zip')
