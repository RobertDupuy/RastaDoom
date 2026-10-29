#!/usr/bin/env python3
"""Package the supplied original firmware, CAR launch hook, and actual DOOM."""
from pathlib import Path
import sys,struct,hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'tools'))
from package_factory import Volume,unpack_uf2
base=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(base).hexdigest()=='3364a0ba142b59790bc6f16f0ceacd2a63616e6e4869fa44a1e4ec18f17e9789'
flash=unpack_uf2(base);original=flash[:]
assert flash[0x13428:0x13430]==bytes.fromhex('d0238022f0b5ce46')
# Redirect only entry to the standard-16K handler. Original bytes are saved
# verbatim in launch.c's original_loop[] and executed from spare SRAM.
flash[0x13428:0x13430]=bytes.fromhex('00480047')+struct.pack('<I',0x10040001)
hook=(ROOT/'build-steps/launch.bin').read_bytes()
flash[0x40000:0x40000+len(hook)]=hook
engine=(ROOT/'build-steps/engine/rastadoom.bin').read_bytes()
assert len(engine)<0x7fe00
assert struct.unpack_from('<I',engine,256)[0]==0x20042000
flash[0x80200:0x80200+len(engine)]=engine
out=ROOT/'dist/steps-0.5.0';out.mkdir(parents=True,exist_ok=True)
car=(out/'DOOMSTEP.CAR').read_bytes()
wad=(HERE.parent/'assets/doom1.whx').read_bytes()
assert wad[:4]==b'IWHX'

# Same filesystem geometry as Robin's firmware, containing the CAR and
# hidden, allocated resource/save files. Physical resource placement is fixed.
logical=bytearray(30716*512)
logical[446:462]=struct.pack('<B3sB3sII',0,b'\x01\x01\x00',1,b'\xfe\xff\xff',63,30653)
logical[510:512]=b'\x55\xaa'
b=bytearray(512);b[:3]=b'\xeb\x3c\x90';b[3:11]=b'MSDOS5.0'
struct.pack_into('<HBHBHHBHHHII',b,11,512,8,8,2,512,30653,0xf8,12,63,255,63,0)
b[36]=0x80;b[38]=0x29;struct.pack_into('<I',b,39,0x52443035)
b[43:54]=b'A8-PICOCART';b[54:62]=b'FAT12   ';b[510:512]=b'\x55\xaa'
logical[63*512:64*512]=b
fat=(63+8)*512
for i in range(2):logical[fat+i*12*512:fat+i*12*512+3]=b'\xf8\xff\xff'
flash[0x100000:0x110000]=bytes(0x10000);flash[0x100000:0x100008]=b'RHE!FS30'
for i in range(127):
    physical=128+i
    struct.pack_into('<H',flash,0x100008+i*2,physical)
    flash[0x100000+physical*512:0x100000+(physical+1)*512]=logical[i*512:(i+1)*512]
v=Volume(flash)
v.add(b'DOOMSTEPCAR',car,0x200000,0x20)
v.add(b'DOOMDATASYS',wad,0x800000,0x07)
v.add(b'RDSAVES SYS',b'\xff'*0x40000,0xfc0000,0x07)
v.flush()
assert Volume(flash).rootfile(b'DOOMSTEPCAR')==car
assert flash[0x800000:0x800000+len(wad)]==wad
changed=[i for i in range(0x18100) if flash[i]!=original[i]]
assert set(changed)<=set(range(0x13428,0x13430))
regions=[(0,0x18100),(0x40000,len(hook)),(0x80200,len(engine)),(0x100000,0x10000)]
regions += [(0x100000+p*512,512) for p in v.mapping if p]
sectors=set()
for addr,n in regions:sectors.update(range(addr//4096,(addr+n+4095)//4096))
blocks=[addr for s in sorted(sectors) for addr in range(s*4096,(s+1)*4096,256)]
uf2=bytearray()
for i,addr in enumerate(blocks):
    uf2+=struct.pack('<8I',0x0a324655,0x9e5d5157,0x2000,0x10000000+addr,256,i,len(blocks),0xe48bff56)
    uf2+=flash[addr:addr+256]+bytes(220)+struct.pack('<I',0x0ab16f30)
name='A8PicoCart-DOOM-Steps-0.5.0.uf2'
(out/name).write_bytes(uf2)
(ROOT/'build-steps/flash.bin').write_bytes(flash)
report={'base_sha256':hashlib.sha256(base).hexdigest(),'original_changed_offsets':[hex(x) for x in changed],
 'original_handler_sram':'0x200001d0','relocated_original_handler_sram':'0x20038000',
 'original_bss_end':'0x20036528','engine_bytes':len(engine),'hook_bytes':len(hook),
 'uf2_bytes':len(uf2),'highest_programmed_address':hex(0x10000000+blocks[-1]+255),
 'uf2_sha256':hashlib.sha256(uf2).hexdigest(),'car_sha256':hashlib.sha256(car).hexdigest(),
 'physical_tested':False,'altirra_tested':False}
(out/'firmware-build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
