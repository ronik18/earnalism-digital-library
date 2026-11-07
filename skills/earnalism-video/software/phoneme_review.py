"""Local phonetic evidence only; never substitutes for owner listening approval."""
import json,pathlib,subprocess,sys,hashlib
import numpy as np,torch
from transformers import AutoFeatureExtractor,Wav2Vec2ForCTC
from huggingface_hub import hf_hub_download
MODEL='facebook/wav2vec2-lv-60-espeak-cv-ft';REV='ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4'
root=pathlib.Path(__file__).resolve().parent;cache=pathlib.Path.home()/'.cache/earnalism-video-review/models'
feature=AutoFeatureExtractor.from_pretrained(MODEL,revision=REV,cache_dir=cache)
model=Wav2Vec2ForCTC.from_pretrained(MODEL,revision=REV,cache_dir=cache).eval()
vocab=json.loads(pathlib.Path(hf_hub_download(MODEL,'vocab.json',revision=REV,cache_dir=cache)).read_text());inverse={v:k for k,v in vocab.items()}
records=[]
for spec in sys.argv[1:]:
 filename,start,end=spec.rsplit(':',2);wav=pathlib.Path(filename)
 audio=subprocess.check_output(['ffmpeg','-v','error','-ss',start,'-to',end,'-i',str(wav),'-ar','16000','-ac','1','-f','f32le','-'])
 x=np.frombuffer(audio,dtype='<f4').copy();inputs=feature(x,sampling_rate=16000,return_tensors='pt')
 with torch.inference_mode():ids=model(**inputs).logits.argmax(-1)[0].tolist()
 decoded=[];last=None
 for token in ids:
  if token!=last and token!=model.config.pad_token_id:decoded.append(inverse.get(token,'?'))
  last=token
 records.append({'audio':str(wav),'audio_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'range':[float(start),float(end)],'phonetic_labels':' '.join(decoded),'model':MODEL,'revision':REV,'limitation':'Machine phonetic evidence; owner listening review still required.'})
print(json.dumps(records,indent=2,ensure_ascii=False))
