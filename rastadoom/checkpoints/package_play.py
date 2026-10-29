#!/usr/bin/env python3
"""Package the tested CAR-only update, preserving the known 0.5.0 source."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,subprocess,tempfile
root=Path(__file__).resolve().parents[3];work=root/'work';out=root/'deliverables';checks=root/'evidence/play/integration'
car=(out/'DOOMSTEP.CAR').read_bytes();carhash=hashlib.sha256(car).hexdigest()
assert json.loads((checks/'result.json').read_text())['car_sha256']==carhash
archive=out/'A8PicoCart-DOOM-Steps-0.5.1.zip';hashes={}
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9)as z:
 def put(name,data):
  assert name not in hashes,name
  hashes[name]=hashlib.sha256(data).hexdigest();z.writestr(name,data)
 def add(path,name):put(name,path.read_bytes())
 with ZipFile(root/'recovered/A8PicoCart-DOOM-Steps-0.5.0.zip')as old:
  for name in old.namelist():
   if name.startswith(('rastadoom/','third_party/','source/'))or name=='COPYING.md':put(name,old.read(name))
 for name in ['play_client.s','play_client.cfg','build_play.py','check_play.py','engine_worker.mjs','pico-model.atdevice','package_play.py']:add(work/'rastadoom/checkpoints'/name,'rastadoom/checkpoints/'+name)
 for name in ['DOOMSTEP.CAR','READ-ME.txt','DOOM-Steps-0.5.1-Gameplay.mp4']:add(out/name,name)
 add(work/'DOOMSTEP.CAR','baseline/DOOMSTEP-0.5.0.CAR')
 for name in ['rastadoom.elf','rastadoom.bin']:add(work/'capture-engine'/name,'reference-engine/'+name)
 for name in ['build.json','client.lbl','client.map','boot.lbl','boot.map']:add(work/'dist/steps-0.5.1'/name,'checks/'+name)
 for path in sorted(checks.iterdir()):
  if path.suffix=='.png' or path.name in ('result.json','engine.jsonl'):add(path,'checks/integration/'+path.name)
 add(root/'evidence/play/integration.log','checks/integration.log')
 add(work/'checks/altirrasdl/os-rom-provenance.json','checks/os-rom-provenance.json')
 deps={'altirrasdl_commit':'288e2b03edf29d97d2c53b7b3e77335862e2e645','altirrasdl_package_sha256':'758455be94716797c41d79ba04a6284fa81fcece3aaf09123de524686c95da18','rp2040js_commit':'5fbd20508a58b9859758c5cd70b207ba1e0b0150','node':subprocess.check_output(['node','--version'],text=True).strip(),'pico_engine_changed':False,'new_uf2_required':False}
 put('checks/dependencies.json',(json.dumps(deps,indent=2)+'\n').encode())
 z.writestr('SHA256SUMS.txt',''.join(h+'  '+n+'\n'for n,h in sorted(hashes.items())))
with tempfile.TemporaryDirectory(prefix='rebuild-',dir=work/'build-play')as tmp:
 temp=Path(tmp)
 with ZipFile(archive)as z:
  assert z.testzip() is None
  for name in z.namelist():
   if name.startswith(('rastadoom/checkpoints/','baseline/')):z.extract(name,temp)
 subprocess.run(['python3',str(temp/'rastadoom/checkpoints/build_play.py'),str(temp/'baseline/DOOMSTEP-0.5.0.CAR'),str(temp/'rebuilt')],check=True,stdout=subprocess.DEVNULL)
 assert(temp/'rebuilt/DOOMSTEP.CAR').read_bytes()==car
print(json.dumps({'archive':str(archive),'size':archive.stat().st_size,'files':len(hashes)+1,'car_sha256':carhash,'rebuilt_identically':True},indent=2))
