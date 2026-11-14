"""Offline visible-link recovery: exact delivery, bounded input, no overwrite."""
import base64
import io
import pathlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from colab_transfer import recover_visible_data_link,sha,VISIBLE_ARCHIVE_MAX_BYTES


class VisibleDataLinkRecoveryTests(unittest.TestCase):
 def setUp(self):
  archive=io.BytesIO()
  with zipfile.ZipFile(archive,'w') as z:z.writestr('private.wav',b'unchanged private waveform fixture')
  self.data=archive.getvalue()
  self.href='data:application/zip;base64,'+base64.b64encode(self.data).decode('ascii')

 def recover(self,href,path,**overrides):
  args={'expected_bytes':len(self.data),'expected_sha256':sha(self.data)}
  args.update(overrides)
  return recover_visible_data_link(href,path,**args)

 def test_exact_archive_and_receipt_without_network_or_execution(self):
  with tempfile.TemporaryDirectory() as folder:
   dest=pathlib.Path(folder)/'private.zip'
   receipt=self.recover(self.href,dest)
   self.assertEqual(dest.read_bytes(),self.data)
   self.assertEqual(receipt['archive_sha256'],sha(self.data))
   self.assertEqual(receipt['archive_bytes'],len(self.data))
   self.assertEqual(receipt['visible_href_sha256'],sha(self.href.encode('ascii')))
   self.assertFalse(receipt['network_accessed'])
   self.assertFalse(receipt['source_executed'])
   self.assertEqual(receipt['media_qualification'],'PENDING_NORMAL_ARCHIVE_IMPORT')
   self.assertEqual(list(pathlib.Path(folder).iterdir()),[dest])

 def test_wrong_source_malformed_length_and_hash_leave_no_output(self):
  with tempfile.TemporaryDirectory() as folder:
   dest=pathlib.Path(folder)/'private.zip'
   wrong_payload=self.href[:-1]+'!'
   cases=[
    ('https://example.invalid/private.zip',{}),
    ('<a href="'+self.href+'">Download</a>',{}),
    ('data:text/plain;base64,'+self.href.split(',',1)[1],{}),
    (self.href+'\n',{}),
    (wrong_payload,{}),
    (self.href,{'expected_bytes':len(self.data)+1}),
    (self.href,{'expected_sha256':'0'*64}),
    (self.href,{'expected_sha256':'not a digest'}),
    (self.href,{'expected_bytes':True}),
    (self.href,{'expected_bytes':0}),
    (self.href,{'expected_bytes':VISIBLE_ARCHIVE_MAX_BYTES+1}),
   ]
   for href,overrides in cases:
    with self.subTest(href=href[:35],overrides=overrides):
     with self.assertRaises(ValueError):self.recover(href,dest,**overrides)
     self.assertFalse(dest.exists())
   # A payload above the limit is rejected before decoding, even if a small
   # independently observed length was supplied.
   large='data:application/zip;base64,'+'A'*(4*((VISIBLE_ARCHIVE_MAX_BYTES+2)//3)+4)
   with self.assertRaises(ValueError):self.recover(large,dest)
   self.assertFalse(dest.exists())

 def test_noncanonical_padding_bits_are_rejected(self):
  # Zh== and Zg== decode to the same byte; accept only the exact encoding.
  with tempfile.TemporaryDirectory() as folder:
   dest=pathlib.Path(folder)/'private.zip'
   with self.assertRaises(ValueError):
    recover_visible_data_link('data:application/zip;base64,Zh==',dest,expected_bytes=1,expected_sha256=sha(b'f'))
   self.assertFalse(dest.exists())

 def test_existing_file_and_live_or_dangling_symlinks_are_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder);target=root/'target.zip';target.write_bytes(b'preserve existing')
   with self.assertRaises(FileExistsError):self.recover(self.href,target)
   for name,link_target in [('live',target),('dangling',root/'absent.zip')]:
    link=root/name;link.symlink_to(link_target)
    with self.assertRaises(FileExistsError):self.recover(self.href,link)
    self.assertTrue(link.is_symlink())
   self.assertEqual(target.read_bytes(),b'preserve existing')
   self.assertFalse((root/'absent.zip').exists())


if __name__=='__main__':unittest.main()
