"""Create fair, private, loudness-matched music comparisons with measured evidence."""
import pathlib,subprocess,json,hashlib

def measured(path):
 r=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af','loudnorm=I=-24:TP=-2:LRA=25:print_format=json','-f','null','-'],capture_output=True,text=True,check=True).stderr
 return json.loads(r[r.rfind('{'):r.rfind('}')+1])
def render(before,after,folder):
 folder=pathlib.Path(folder);reports=[]
 for label,source in [('before',pathlib.Path(before)),('after',pathlib.Path(after))]:
  output=folder/f'music-{label}-matched.m4a'
  if output.exists():raise FileExistsError(output)
  m=measured(source);f=f'loudnorm=I=-24:TP=-2:LRA=25:measured_I={m["input_i"]}:measured_LRA={m["input_lra"]}:measured_TP={m["input_tp"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true'
  subprocess.run(['ffmpeg','-v','error','-n','-i',str(source),'-af',f,'-ar','48000','-c:a','aac','-b:a','192k',str(output)],check=True)
  reports.append({'version':label,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'comparison_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'measured_output':measured(output)})
 if abs(float(reports[0]['measured_output']['input_i'])-float(reports[1]['measured_output']['input_i']))>.6:raise ValueError('Comparisons are not sufficiently loudness matched')
 (folder/'music-comparison-measurements.json').write_text(json.dumps(reports,indent=2));return reports
