#!/usr/bin/env python3
"""Make an emulation-only flash fixture; never produces a firmware update."""
from pathlib import Path
import sys,struct,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from package_factory import Volume,unpack_uf2
base=Path(sys.argv[1]).read_bytes();car=Path(sys.argv[2]).read_bytes()
assert hashlib.sha256(base).hexdigest()=='3364a0ba142b59790bc6f16f0ceacd2a63616e6e4869fa44a1e4ec18f17e9789'
flash=unpack_uf2(base);original=flash[:0x100000]
logical=bytearray(30716*512)
logical[446:462]=struct.pack('<B3sB3sII',0,b'\x01\x01\x00',1,b'\xfe\xff\xff',63,30653)
logical[510:512]=b'\x55\xaa';b=bytearray(512);b[:3]=b'\xeb\x3c\x90';b[3:11]=b'MSDOS5.0'
struct.pack_into('<HBHBHHBHHHII',b,11,512,8,8,2,512,30653,0xf8,12,63,255,63,0)
b[36]=0x80;b[38]=0x29;struct.pack_into('<I',b,39,0x52444d31)
b[43:54]=b'A8-PICOCART';b[54:62]=b'FAT12   ';b[510:512]=b'\x55\xaa';logical[63*512:64*512]=b
fat=(63+8)*512
for i in range(2):logical[fat+i*12*512:fat+i*12*512+3]=b'\xf8\xff\xff'
flash[0x100000:0x110000]=bytes(0x10000);flash[0x100000:0x100008]=b'RHE!FS30'
for i in range(127):
 physical=128+i;struct.pack_into('<H',flash,0x100008+i*2,physical)
 flash[0x100000+physical*512:0x100000+(physical+1)*512]=logical[i*512:(i+1)*512]
v=Volume(flash);v.add(b'DOOMMOV CAR',car,0x200000);v.flush()
assert Volume(flash).rootfile(b'DOOMMOV CAR')==car and flash[:0x100000]==original
Path(sys.argv[3]).write_bytes(flash)
