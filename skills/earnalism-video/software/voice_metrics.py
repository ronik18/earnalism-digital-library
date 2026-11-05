"""Coarse local acoustic comparison. Never infers a speaker's age or human naturalness."""
import subprocess,json,sys
import numpy as np

def measure(path):
 rate=24000
 values=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar',str(rate),'-ac','1','-f','f32le','-']),dtype='<f4').astype(np.float64)
 frames=np.lib.stride_tricks.sliding_window_view(values,960)[::480] if len(values)>=960 else np.empty((0,960))
 pitches=[];centroids=[]
 for frame in frames:
  rms=float(np.sqrt(np.mean(frame*frame)))
  if rms<.01:continue
  spectrum=np.fft.rfft((frame-frame.mean())*np.hanning(960),2048);power=np.abs(spectrum)**2
  corr=np.fft.irfft(power,2048)[:960]
  if corr[0]<=0:continue
  lo,hi=80,343;lag=int(np.argmax(corr[lo:hi])+lo);confidence=float(corr[lag]/corr[0])
  if confidence>.50:pitches.append(rate/lag)
  magnitude=np.abs(spectrum);freq=np.fft.rfftfreq(2048,1/rate);mask=(freq>=65)&(freq<=6000)
  centroids.append(float(np.sum(freq[mask]*magnitude[mask])/max(1e-12,np.sum(magnitude[mask]))))
 return {'seconds':len(values)/rate,'approx_voiced_pitch_hz':{'median':float(np.median(pitches)) if pitches else None,'p10':float(np.percentile(pitches,10)) if pitches else None,'p90':float(np.percentile(pitches,90)) if pitches else None,'frames':len(pitches)},'median_spectral_centroid_hz':float(np.median(centroids)) if centroids else None,'limitations':'Approximate autocorrelation can make octave errors; measures relative consistency only. Cannot establish age, speaker identity, naturalness or perceived vocal weight.'}
if __name__=='__main__':print(json.dumps(measure(sys.argv[1]),indent=2))
