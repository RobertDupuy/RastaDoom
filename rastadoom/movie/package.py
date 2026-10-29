#!/usr/bin/env python3
"""Package this separate movie with the exact captured engine's source."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,subprocess,shutil,tempfile
root=Path(__file__).resolve().parents[3];dest=root/'deliverables';checks=root/'evidence/movie'
manifest=json.loads((root/'work/build-movie/cart/manifest.json').read_text())
car=(dest/'DOOMMOV.CAR').read_bytes();digest=hashlib.sha256(car).hexdigest()
assert digest==manifest['sha256']
for name in ['loader-result.json','altirra/result.json']:
 assert json.loads((checks/name).read_text())['car_sha256']==digest
archive=dest/'DOOM-Movie-0.1.0.zip';hashes={}
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
 def put(name,data):
  assert name not in hashes,name
  hashes[name]=hashlib.sha256(data).hexdigest();z.writestr(name,data)
 def add(path,name):put(name,path.read_bytes())
 with ZipFile(dest/'A8PicoCart-DOOM-Steps-0.5.0.zip') as prior:
  for name in prior.namelist():
   if name.startswith(('rastadoom/','third_party/','source/')) or name=='COPYING.md':put(name,prior.read(name))
 for path in sorted((root/'work/rastadoom/movie').iterdir()):
  if path.is_file():add(path,'rastadoom/movie/'+path.name)
 for path in sorted((root/'work/build-movie/captured').iterdir()):
  if path.is_file():add(path,'recorded-frames/'+path.name)
 for name in ['DOOMMOV.CAR','DOOM-MOVIE-README.txt','DOOMMOV-AltirraSDL.mp4']:add(dest/name,name)
 for name in ['rastadoom.elf','rastadoom.bin']:add(root/'work/build-steps/engine'/name,'capture-engine/'+name)
 add(root/'work/build-movie/cart/manifest.json','checks/manifest.json')
 for name in ['player.lbl','boot.lbl']:add(root/'work/build-movie/cart'/name,'checks/'+name)
 for name in ['arm-capture.log','loader-check.log','loader-result.json','altirra-check.log']:add(checks/name,'checks/'+name)
 for path in sorted((checks/'altirra').iterdir()):
  if path.suffix=='.png' or path.name=='result.json':add(path,'checks/altirra/'+path.name)
 add(root/'evidence/os-rom-provenance.json','checks/os-rom-provenance.json')
 put('checks/dependencies.json',(json.dumps({'node':'v24.22.1','ca65':'V2.18 - Ubuntu 2.19-1','rp2040js_commit':'5fbd20508a58b9859758c5cd70b207ba1e0b0150','altirrasdl_commit':'288e2b03edf29d97d2c53b7b3e77335862e2e645'},indent=2)+'\n').encode())
 z.writestr('SHA256SUMS.txt',''.join(h+'  '+name+'\n' for name,h in sorted(hashes.items())))
with tempfile.TemporaryDirectory(prefix='movie-rebuild-',dir=root/'work/build-movie') as tmp:
 temp=Path(tmp)
 with ZipFile(archive) as z:
  assert z.testzip() is None
  for name in z.namelist():
   if name.startswith(('rastadoom/movie/','rastadoom/checkpoints/','recorded-frames/')):z.extract(name,temp)
 subprocess.run(['python3',str(temp/'rastadoom/movie/build.py'),str(temp/'recorded-frames'),str(temp/'rebuild')],check=True,stdout=subprocess.DEVNULL)
 assert (temp/'rebuild/DOOMMOV.CAR').read_bytes()==car
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(hashes)+1,'rebuild_identical':True,'car_sha256':digest,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
