"""Read-only canonical private qualification; never grants publication authority."""
from pathlib import Path
from .package_preview import validate_inputs
try:
 from ..thermal_touch.assemble import load,require,sha
except ImportError:
 from thermal_touch.assemble import load,require,sha
ORIGINAL_SHA='62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
def check_private(folder,project_root):
 folder=Path(folder).resolve();root=Path(project_root).resolve()
 require(folder.is_relative_to(root),'Candidate outside project')
 require(sha(root/'Earnalism_English_Audiobook_Pipeline_Qwew&Ace.ipynb')==ORIGINAL_SHA,'Original notebook changed')
 manifest=load(folder/'delivery-manifest.json')
 require(manifest.get('schema')=='earnalism.rainbow-private-kit.v1','Wrong private candidate')
 require(manifest.get('publication_approved') is False,'Private check cannot infer or grant release approval')
 for name,digest in manifest['files'].items():
  p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'Unsafe manifest member')
  target=(folder/p).resolve();require(target.is_relative_to(root) and sha(target)==digest,'Changed candidate member')
 validate_inputs(folder)
 return {'state':'PRIVATE_REVIEW_REQUIRES_ACCEPTANCE','delivery_manifest_sha256':sha(folder/'delivery-manifest.json'),
  'publication_approved':False,'uploads':False,'scope':'Source, actual-audio captions, soundtrack identity, mux/decode and package binding verified. Factual/graphical/listening review and final owner decision remain separate evidence; this check authorizes no publication.'}
