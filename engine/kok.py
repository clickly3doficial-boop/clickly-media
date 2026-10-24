import numpy as np, onnxruntime as ort, subprocess, re, wave, sys
import os
D=os.environ.get('KOKORO_DIR','/opt/kokoro-multi-lang-v1_0')+'/'
sess=ort.InferenceSession(D+'model.onnx')
VO=np.fromfile(D+'voices.bin',dtype=np.float32).reshape(54,510,256)
NAMES=sess.get_modelmeta().custom_metadata_map['speaker_names'].split(',')
VOC={}
for l in open(D+'tokens.txt',encoding='utf-8'):
    l=l.rstrip('\n')
    if not l: continue
    k,v=l.rsplit(' ',1) if l.count(' ')>=1 and not l.startswith('  ') else (' ',l.strip())
    VOC[k if k!='' else ' ']=int(v)
def esp(t):
    o=subprocess.run(['/opt/espeak/bin/espeak-ng','-q','--ipa','-v','es-419','--path=/opt/espeak/share',t],capture_output=True,text=True).stdout
    return ' '.join(o.split())
def phon(text):
    parts=re.split(r'([,.!?¿¡:;…]+)',text); out=''
    for p in parts:
        if not p.strip(): continue
        if re.fullmatch(r'[,.!?¿¡:;…]+',p):
            q=p.replace('¿','').replace('¡','').replace('…','...')
            out=out.rstrip()+q[:1]+' '
        else: out+=esp(p)+' '
    return out.strip()
def synth(text,out,voice='em_alex',speed=1.0,blend=None):
    ph=phon(text); ids=[VOC[c] for c in ph if c in VOC][:508]
    sid=NAMES.index(voice); st=VO[sid,len(ids)]
    if blend: st=st*(1-blend[1])+VO[NAMES.index(blend[0]),len(ids)]*blend[1]
    a=sess.run(None,{'tokens':np.array([[0]+ids+[0]],dtype=np.int64),'style':st[None].astype(np.float32),'speed':np.array([speed],dtype=np.float32)})[0].squeeze()
    a=a/max(1e-6,np.abs(a).max())*0.9
    w=wave.open(out,'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes((a*32767).astype(np.int16).tobytes());w.close()
    return len(a)/24000, ph
if __name__=='__main__':
    print(synth(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else 'em_alex',float(sys.argv[4]) if len(sys.argv)>4 else 1.0))
