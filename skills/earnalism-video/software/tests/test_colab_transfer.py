import unittest,tempfile,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from colab_transfer import export,assemble,recover_notebook,sha
import json,base64
class ColabTransferTests(unittest.TestCase):
 def test_actual_bytes_round_trip_and_corrupt_chunk_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);data=bytes(range(256))*50;(p/'source.zip').write_bytes(data)
   export(p/'source.zip',p/'parts',1024);assemble(p/'parts',p/'result.zip');self.assertEqual((p/'result.zip').read_bytes(),data)
   with self.assertRaises(FileExistsError):assemble(p/'parts',p/'result.zip')
   (p/'parts/part-000.txt').write_text('AAAA')
   with self.assertRaises(ValueError):assemble(p/'parts',p/'corrupt.zip')
 def recovery_source(self,data):
  return 'EARNALISM_PRIVATE_RECOVERY_SHA256='+repr(sha(data))+'\nEARNALISM_PRIVATE_RECOVERY_BASE64='+repr(base64.b64encode(data).decode())
 def test_saved_notebook_recovery_preserves_bytes_and_existing_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);data=bytes(range(256))*10;source=self.recovery_source(data)
   (p/'n.ipynb').write_text(json.dumps({'cells':[{'source':source.splitlines(keepends=True)}]}))
   receipt=recover_notebook(p/'n.ipynb',p/'result.zip');self.assertEqual((p/'result.zip').read_bytes(),data);self.assertFalse(receipt['source_executed'])
   with self.assertRaises(FileExistsError):recover_notebook(p/'n.ipynb',p/'result.zip')
   self.assertEqual((p/'result.zip').read_bytes(),data)
 def test_executable_tampered_and_ambiguous_cells_leave_no_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);valid=self.recovery_source(b'preserved bytes')
   cases=[[valid+'\nraise RuntimeError("must never execute")'],[valid.replace(sha(b'preserved bytes'),'0'*64)],[valid,valid]]
   for sources in cases:
    (p/'n.ipynb').write_text(json.dumps({'cells':[{'source':s} for s in sources]}))
    with self.assertRaises(ValueError):recover_notebook(p/'n.ipynb',p/'result.zip')
    self.assertFalse((p/'result.zip').exists())
 def test_nonliteral_and_missing_recovery_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for source in ['print("no recovery")','EARNALISM_PRIVATE_RECOVERY_SHA256=str(1)\nEARNALISM_PRIVATE_RECOVERY_BASE64=""']:
    (p/'n.ipynb').write_text(json.dumps({'cells':[{'source':source}]}))
    with self.assertRaises(ValueError):recover_notebook(p/'n.ipynb',p/'result.zip')
    self.assertFalse((p/'result.zip').exists())
