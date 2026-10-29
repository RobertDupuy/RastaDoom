#!/usr/bin/env python3
"""Build a factory-derived AUTORUN.BAT image; require the exact supplied base.

Factory changes are the autorun filename, bootstrap caption and two CRC fields.
AUTORUN.BAT is an A8P1 executable package with our native ARM engine and 6502
client, not a batch-language script. Physical WHX/save sectors are reserved in
FAT and the factory sector map; the full UF2 installs that reproducible layout.
"""
import argparse, hashlib, json, struct, subprocess, zlib
from pathlib import Path
BASE_SHA='4c6dc65d12377988a3670f30fe61cd5254c716b91328236b9c3b87196491fa7b'
BASE=0x100000
PACKAGE_PHYSICAL=0x800000
RESOURCE_OFFSET=0x60000
SAVE_PHYSICAL=0xfc0000

def u32(b,p):return struct.unpack_from('<I',b,p)[0]
def put32(b,p,v):struct.pack_into('<I',b,p,v)
def sha(b):return hashlib.sha256(b).hexdigest()
def unpack_uf2(b):
    flash=bytearray(b'\xff'*0x1000000)
    for i in range(0,len(b),512):
        m0,m1,flags,addr,size,num,total,family=struct.unpack_from('<8I',b,i)
        assert (m0,m1,u32(b,i+508),family)==(0x0a324655,0x9e5d5157,0x0ab16f30,0xe48bff56)
        assert size==256 and 0x10000000<=addr<0x11000000
        flash[addr-0x10000000:addr-0x10000000+size]=b[i+32:i+32+size]
    return flash

def pack_uf2(flash):
    out=bytearray();total=(len(flash)+255)//256
    for i in range(total):
        out+=struct.pack('<8I',0x0a324655,0x9e5d5157,0x2000,0x10000000+i*256,256,i,total,0xe48bff56)
        out+=flash[i*256:(i+1)*256].ljust(256,b'\xff')+bytes(220)+struct.pack('<I',0x0ab16f30)
    return out

class Volume:
    def __init__(self,flash):
        self.flash=flash
        assert flash[BASE:BASE+8]==b'RHE!FS30'
        self.mapping=list(struct.unpack_from('<30716H',flash,BASE+8))
        self.data=bytearray(len(self.mapping)*512)
        for i,physical in enumerate(self.mapping):
            if physical:self.data[i*512:(i+1)*512]=flash[BASE+physical*512:BASE+(physical+1)*512]
        self.original=self.data[:]
        self.partition=u32(self.data,454)*512
        bps,spc,res,nf,roots,nsec,media,spf=struct.unpack_from('<HBHBHHBH',self.data,self.partition+11)
        assert (bps,spc,nf)==(512,8,2)
        self.fat=self.partition+res*512;self.spf=spf;self.nf=nf
        self.root=self.fat+nf*spf*512;self.root_size=((roots*32+511)//512)*512
        self.start=self.root+self.root_size;self.cs=spc*512
        self.max_cluster=(self.partition+nsec*512-self.start)//self.cs+2
    def next(self,c):
        n=struct.unpack_from('<H',self.data,self.fat+c*3//2)[0]
        return n>>4 if c&1 else n&4095
    def setnext(self,c,n):
        for f in range(self.nf):
            p=self.fat+f*self.spf*512+c*3//2
            old=struct.unpack_from('<H',self.data,p)[0]
            struct.pack_into('<H',self.data,p,(old&15)|(n<<4) if c&1 else (old&0xf000)|n)
    def chain(self,c):
        seen=set();out=bytearray()
        while 2<=c<0xff8:
            assert c not in seen;seen.add(c)
            p=self.start+(c-2)*self.cs;out+=self.data[p:p+self.cs];c=self.next(c)
        return bytes(out)
    def rootfile(self,name):
        for p in range(self.root,self.root+self.root_size,32):
            if self.data[p:p+11]==name:
                c=struct.unpack_from('<H',self.data,p+26)[0];return self.chain(c)[:u32(self.data,p+28)]
        raise KeyError(name)
    def add(self,name,payload,physical,attr=0x20):
        assert len(name)==11 and physical%self.cs==0
        count=(len(payload)+self.cs-1)//self.cs
        free=[c for c in range(2,self.max_cluster) if self.next(c)==0][:count]
        assert len(free)==count
        occupied=set(self.mapping);physical_sector=(physical-BASE)//512
        assert all(physical_sector+i not in occupied for i in range(count*self.cs//512))
        for i,c in enumerate(free):
            self.setnext(c,free[i+1] if i+1<len(free) else 0xfff)
            pos=self.start+(c-2)*self.cs
            chunk=payload[i*self.cs:(i+1)*self.cs].ljust(self.cs,b'\xff')
            self.data[pos:pos+self.cs]=chunk
            for k in range(self.cs//512):self.mapping[pos//512+k]=physical_sector+i*self.cs//512+k
        for p in range(self.root,self.root+self.root_size,32):
            if self.data[p] in (0,0xe5):break
        else:raise ValueError('Root directory full')
        entry=bytearray(32);entry[:11]=name;entry[11]=attr
        struct.pack_into('<H',entry,26,free[0]);put32(entry,28,len(payload));self.data[p:p+32]=entry
    def flush(self):
        used=set(self.mapping);candidate=0x500000//512-BASE//512
        for i in range(len(self.mapping)):
            chunk=self.data[i*512:(i+1)*512]
            if not self.mapping[i] and chunk!=self.original[i*512:(i+1)*512]:
                while candidate in used:candidate+=1
                self.mapping[i]=candidate;used.add(candidate)
            if self.mapping[i]:
                p=BASE+self.mapping[i]*512;self.flash[p:p+512]=chunk
        struct.pack_into('<30716H',self.flash,BASE+8,*self.mapping)

def make_package(program,client,whx,launch):
    assert len(client)==8192 and len(whx)==1800344 and whx[:4]==b'IWHX'
    code_size=RESOURCE_OFFSET-512-8192-512
    assert len(program)<=code_size
    code=program.ljust(code_size,b'\0')
    h=bytearray(512)
    fields=[0x31523841,1,512+len(code),zlib.crc32(code),512,len(code),launch,0,launch,512+len(code),0,0,1,0,launch,0]
    struct.pack_into('<16I',h,0,*fields);put32(h,52,zlib.crc32(h));engine=bytes(h)+code
    entries=[('client.bin',client),('engine.a8r',engine),('resources.bin',whx)]
    table=bytearray(384);payload=bytearray();offset=512
    for i,(name,data) in enumerate(entries):
        p=i*128;table[p:p+len(name)]=name.encode()
        struct.pack_into('<5I',table,p+64,0,len(data),offset,len(data),zlib.crc32(data))
        payload+=data;offset+=len(data)
    assert u32(table,256+72)==RESOURCE_OFFSET
    header=bytearray(128)
    fields=[0x31503841,1,offset,zlib.crc32(table+payload),128,3,128,1,0,2,1,1,0,0,0,0]
    struct.pack_into('<16I',header,0,*fields)
    header[64:73]=b'RASTADOOM';header[88:110]=b'RastaDoom native Atari'
    # Slice assignment above must not resize the fixed 128-byte header.
    assert len(header)==128
    put32(header,48,zlib.crc32(header))
    return bytes(header+table+payload)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('factory',type=Path);p.add_argument('elf',type=Path);p.add_argument('whx',type=Path);p.add_argument('client',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();raw=a.factory.read_bytes();assert sha(raw)==BASE_SHA,'Wrong factory image; refusing to patch'
    original=unpack_uf2(raw);flash=original[:]
    old=b'/HAMSTEROS.MPE\0';new=b'/AUTORUN.BAT\0'.ljust(len(old),b'\0')
    assert flash[0x30e34:0x30e34+len(old)]==old
    flash[0x30e34:0x30e34+len(old)]=new
    # The existing factory bootstrap draws this literal before package launch.
    # Keep the executable code and the fixed 40-character row length intact.
    banner_offset=0x40b7
    banner_old=b'A8PICO STARTUP'.ljust(40)
    banner_new=b'RASTADOOM 03 - FACTORY LOADER'.ljust(40)
    assert flash[banner_offset:banner_offset+40]==banner_old
    flash[banner_offset:banner_offset+40]=banner_new
    assert u32(flash,0x600c)==0x8000 and u32(flash,0x6010)==0x38700
    put32(flash,0x6014,zlib.crc32(flash[0x8000:0x40700]))
    put32(flash,0x601c,0);put32(flash,0x601c,zlib.crc32(flash[0x6000:0x7000]))
    symbols={}
    for line in subprocess.check_output(['arm-none-eabi-nm','-n',str(a.elf)],text=True).splitlines():
        parts=line.split()
        if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
    assert symbols['__flash_binary_start']==0x10080200
    package=make_package(a.elf.with_suffix('.bin').read_bytes(),a.client.read_bytes()[8192:],a.whx.read_bytes(),(symbols['rd_factory_launch']-0x10080200)|1)
    v=Volume(flash);v.add(b'AUTORUN BAT',package,PACKAGE_PHYSICAL)
    v.add(b'RDSAVES SYS',b'\xff'*0x40000,SAVE_PHYSICAL,0x06);v.flush()
    check=Volume(flash);assert check.rootfile(b'AUTORUN BAT')==package
    assert check.rootfile(b'RDSAVES SYS')==b'\xff'*0x40000
    assert flash[0x860000:0x860000+len(a.whx.read_bytes())]==a.whx.read_bytes()
    allowed=set(range(0x6014,0x6018))|set(range(0x601c,0x6020))|set(range(0x30e34,0x30e34+len(old)))|set(range(banner_offset,banner_offset+40))
    changed=[i for i in range(BASE) if flash[i]!=original[i]]
    assert set(changed)<=allowed
    # Every original logical sector outside FAT/root metadata is unchanged.
    oldv=Volume(original)
    for i in range(len(oldv.mapping)):
        if oldv.mapping[i] and not v.fat<=i*512<v.start:
            assert oldv.data[i*512:(i+1)*512]==check.data[i*512:(i+1)*512]
    a.out.mkdir(parents=True,exist_ok=True)
    uf2=pack_uf2(flash)
    (a.out/'AUTORUN.BAT').write_bytes(package)
    (a.out/'A8PicoCart-RastaDoom-Diagnostics-0.3.0.uf2').write_bytes(uf2)
    (a.out/'factory-rastadoom.bin').write_bytes(flash)
    meta={'base_factory_sha256':BASE_SHA,'uf2_sha256':sha(uf2),'autorun_sha256':sha(package),'firmware_changed_bytes':len(changed),'firmware_changed_offsets':[hex(x) for x in changed],
        'factory_instructions_changed':0,'startup_path':'/AUTORUN.BAT','staged_engine_address':'0x10080200','whx_address':'0x10860000','package_bytes':len(package),'bootstrap_banner':banner_new.decode().rstrip(),'physical_cartridge_tested':False}
    (a.out/'factory-build.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
