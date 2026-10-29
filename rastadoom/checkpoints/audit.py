#!/usr/bin/env python3
"""Static artifact audit; this does not emulate Atari hardware or Altirra."""
from pathlib import Path
import hashlib, json, struct
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'dist/steps-0.5.0'
car=(out/'DOOMSTEP.CAR').read_bytes(); rom=car[16:]
assert car[:4]==b'CART' and len(rom)==16384
kind,checksum,reserved=struct.unpack('>III',car[4:16])
assert kind==2 and checksum==sum(rom)&0xffffffff and reserved==0
assert rom[0x3ffa:]==bytes.fromhex('00a00004f0bf') and rom[0x3ff0]==0x60
assert rom[0x2000]==0x78 # SEI at fixed cartridge RUN address A000.
assert rom[0x3000:0x3028].decode().rstrip()=='STEP 1 - CARTRIDGE RUNNING'
assert rom[0x3600:0x360b]==bytes.fromhex('7070704200b002024100b6')
assert rom[:4096]==(ROOT/'build-steps/client.bin').read_bytes()
font=(ROOT/'rastadoom/checkpoints/font.bin').read_bytes()
assert rom[0x3800:0x3c00]==font and rom[0xc00:0x1000]==font
assert len(font)==1024 and font[ord(' ')*8:(ord(' ')+1)*8]==bytes(8)
for c in b'STEP 1 - CARTRIDGE RUNNING':
    if c!=32: assert any(font[c*8:c*8+8])
assert rom[0x3fd0:0x3fe0]==b'RASTADOOM-STEP9\0'
report=json.loads((out/'client-build.json').read_text())
for message in report['messages']:assert message.encode() in rom[:4096]
frame=(ROOT/'build-steps/first-frame.bin').read_bytes()
assert len(frame)==16384 and frame[0x3fe0:0x3fe4]==b'RD5F'
i=0x1e10
assert frame[i:i+3]==bytes.fromhex('8d0ad4');i+=3
for y in range(192):
    for reg in [0x16,0x17,0x18,0x12,0x13,0x14,0x15]:
        assert frame[i]==0xa9 and frame[i+2:i+5]==bytes([0x8d,reg,0xd0]);i+=5
    if y&1:assert frame[i:i+6]==bytes.fromhex('ad80d58d07d2');i+=6
    assert frame[i:i+3]==bytes.fromhex('8d0ad4');i+=3
assert frame[i:i+3]==b'\x4c'+struct.pack('<H',report['labels']['frame_end'])
assert i+3<=0x3e00
uf2=(out/'A8PicoCart-DOOM-Steps-0.5.0.uf2').read_bytes()
flash=(ROOT/'build-steps/flash.bin').read_bytes()
count=len(uf2)//512; addresses=[]
for j in range(count):
    block=uf2[j*512:(j+1)*512]
    h=struct.unpack_from('<8I',block)
    assert h[:3]==(0x0a324655,0x9e5d5157,0x2000)
    assert h[4:]==(256,j,count,0xe48bff56)
    addr=h[3]-0x10000000
    assert 0<=addr<=0xffff00 and addr%256==0
    assert block[32:288]==flash[addr:addr+256]
    assert struct.unpack_from('<I',block,508)[0]==0x0ab16f30
    addresses.append(addr)
assert len(set(addresses))==count
assert all(sum(a//4096==sector for a in addresses)==16 for sector in {a//4096 for a in addresses})
result={'car_type':kind,'rom_bytes':len(rom),'fixed_text':'STEP 1 - CARTRIDGE RUNNING',
        'encoded_raster_rows':192,'kernel_return':hex(report['labels']['frame_end']),
        'uf2_blocks':count,'uf2_sha256':hashlib.sha256(uf2).hexdigest(),
        'static_checks_passed':True,'altirra_tested':False,'hardware_tested':False}
(out/'static-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
