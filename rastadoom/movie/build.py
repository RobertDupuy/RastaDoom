#!/usr/bin/env python3
"""Build standalone 128KB type-29 MegaCart from captured firmware windows."""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('out',type=Path)
a=p.parse_args();here=Path(__file__).resolve().parent;check=here.parent/'checkpoints';out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
selected=[12,16,20,24,28,32,36]
capture=json.loads((a.capture/'capture.json').read_text())
def line(s):
 assert len(s)<=40
 return '    .byte '+json.dumps(s.ljust(40))+'\n'
messages=['STEP 2 - MOVIE PLAYER READY','STEP 3 - SELECTING FRAME BANK','STEP 4 - FRAME BANK SELECTED','STEP 5 - STARTING RECORDED DISPLAY']
inc='message_lo: .byte '+','.join('<msg'+str(i) for i in range(4))+'\nmessage_hi: .byte '+','.join('>msg'+str(i) for i in range(4))+'\n'
for i,m in enumerate(messages):inc+=f'msg{i}:\n'+line(m)
inc+='wait_footer:\n'+line('STEP 5 - WAITING FOR RASTER RETURN')+'footer:\n'+line('STEP 6 - FRAME 1/7 LOOP 00')+'error_text:\n'+line('STOPPED - WRONG ROM BANK')
(out/'movie_messages.inc').write_text(inc)
for name in ['wait.inc','game_list.inc','font.bin']:(out/name).write_bytes((check/name).read_bytes())
boot=(check/'boot.s').read_text()
boot=boot.replace('    jsr pause_three','    lda #1\n    sta $80\n    jsr pause_three',1)
boot=boot[:boot.index('.segment "FIXED_TEXT"')]+'.segment "FIXED_TEXT"\n'+line('STEP 1 - CARTRIDGE RUNNING')+line('DOOM MOVIE - FIXED CARTRIDGE ROM')+line('PAUSE 3 SECONDS')+'''\n.segment "FIXED_LIST"
    .byte $70,$70,$70,$42
    .word $b000
    .byte $02,$02,$41
    .word $b600
.segment "FONT"
    .incbin "font.bin"
.segment "RESET"
    sei
    lda #0
    sta $d500
    jmp $a000
.segment "INIT"
    rts
.segment "VECTORS"
    .word start
    .byte 0,4
    .word $bff0
'''
(out/'boot.s').write_text(boot)
cfg=(check/'boot.cfg').read_text().replace(' SIGNATURE: load=ROM, type=ro, start=$bfd0;',' RESET: load=ROM, type=ro, start=$bfc0;')
(out/'boot.cfg').write_text(cfg)
for name,src,cfg in [('player',here/'player.s',here/'player.cfg'),('boot',out/'boot.s',out/'boot.cfg')]:
 subprocess.run(['ca65','--bin-include-dir',str(out),'-I',str(out),'-o',str(out/(name+'.o')),str(src)],check=True)
 subprocess.run(['ld65','-C',str(cfg),'-o',str(out/(name+'.bin')),'-Ln',str(out/(name+'.lbl')),str(out/(name+'.o'))],check=True)
boot=bytearray((out/'boot.bin').read_bytes());player=(out/'player.bin').read_bytes();assert len(boot)==16384 and len(player)==4096
boot[:4096]=player
banks=[bytes(boot)];records=[]
for bank,frame in enumerate(selected,1):
 meta=capture['frames'][frame-1];raw=(a.capture/meta['file']).read_bytes();w=bytearray(raw)
 assert len(w)==16384 and hashlib.sha256(w).hexdigest()==meta['sha256'] and meta['state']==0 and meta['menu']==0
 # Preserve exact playfield, PMG, colour instructions and live return address.
 # Replace each absent Pico audio FIFO read by an equal-cycle RAM silence read.
 pos=0x1e10+3;audio_patches=[]
 for y in range(192):
  pos+=35
  if y&1:
   assert w[pos:pos+6]==bytes.fromhex('ad80d58d07d2')
   w[pos+1:pos+3]=bytes.fromhex('f028');audio_patches.extend([pos+1,pos+2]);pos+=6
  assert w[pos:pos+3]==bytes.fromhex('8d0ad4');pos+=3
 assert w[pos:pos+3]==bytes.fromhex('4c4421')
 w[0x3fc0:0x3fc9]=bytes.fromhex('78a9008d00d54c00a0')
 w[0x3fe0:0x3fe5]=b'MOV1'+bytes([bank])
 # Warm RESET from any selected bank returns through its identical stub.
 w[0x3ffa:0x3ffc]=bytes.fromhex('c0bf')
 allowed=set(audio_patches)|set(range(0x3fc0,0x3fc9))|set(range(0x3fe0,0x3fe5))|{0x3ffa,0x3ffb}
 differences=[i for i,(x,y) in enumerate(zip(raw,w)) if x!=y]
 assert all(i in allowed for i in differences)
 assert raw[:0x1e10]==w[:0x1e10] and raw[0x3e00:0x3f80]==w[0x3e00:0x3f80]
 banks.append(bytes(w));records.append({'bank':bank,'source':meta,'patched_byte_offsets':differences,'bank_sha256':hashlib.sha256(w).hexdigest()})
payload=b''.join(banks);assert len(payload)==131072
car=b'CART'+struct.pack('>III',29,sum(payload)&0xffffffff,0)+payload
(out/'DOOMMOV.CAR').write_bytes(car)
manifest={'cartridge':'DOOMMOV.CAR','type':29,'payload_bytes':len(payload),'sha256':hashlib.sha256(car).hexdigest(),'bank_count':8,'movie_frames':7,'video_frames_per_picture':24,'loop_video_frames':168,'audio':'Silent; FIFO reads redirected to RAM byte $18 without changing instruction timing.','engine_capture':{k:v for k,v in capture.items() if k!='frames'},'records':records}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ('records','engine_capture')},indent=2))
