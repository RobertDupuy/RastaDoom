#!/usr/bin/env python3
"""CAR-only 0.5.1 update. Reuses the installed 0.5.0 engine and its ABI."""
from pathlib import Path
import argparse,subprocess,hashlib,struct,json
h=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
for name in ('client','boot'):
 source='play_client' if name=='client' else name
 subprocess.run(['ca65',str(h/(source+'.s')),'-I',str(h),'-o',str(out/(name+'.o'))],cwd=h,check=True)
 subprocess.run(['ld65','-C',str(h/(source+'.cfg')),str(out/(name+'.o')),'-o',str(out/(name+'.bin')),'-Ln',str(out/(name+'.lbl')),'-m',str(out/(name+'.map'))],check=True)
client=(out/'client.bin').read_bytes();rom=bytearray((out/'boot.bin').read_bytes());old=a.baseline.read_bytes()[16:]
assert len(client)==4096 and len(rom)==len(old)==16384
rom[:4096]=client
labels={line.split()[2][1:]:int(line.split()[1],16) for line in (out/'client.lbl').read_text().splitlines()}
assert labels['frame_end']==0x2144 and labels['hold']==0x215a
changes=[i for i,(x,y) in enumerate(zip(old,rom)) if x!=y]
assert all(0x144<=i<0x15a or 0x400<=i<0x700 for i in changes),changes
assert rom[0x1000:]==old[0x1000:]
car=b'CART'+struct.pack('>III',2,sum(rom)&0xffffffff,0)+rom
(out/'DOOMSTEP.CAR').write_bytes(car)
meta={'release':'0.5.1','required_firmware':'Existing 0.5.0 UF2, unchanged','car_sha256':hashlib.sha256(car).hexdigest(),'baseline_car_sha256':hashlib.sha256(a.baseline.read_bytes()).hexdigest(),'changed_rom_offsets':changes,'startup_before_first_return_byte_identical':True,'fixed_ROM_upper_12K_byte_identical':True,'labels':labels}
(out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:v for k,v in meta.items() if k!='changed_rom_offsets'},indent=2))
