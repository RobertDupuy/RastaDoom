#!/usr/bin/env python3
"""Boot the actual CAR in native AltirraSDL, record its real GTIA output."""
from pathlib import Path
import argparse,subprocess,time,sys,json,hashlib,zlib
p=argparse.ArgumentParser();p.add_argument('sdk',type=Path);p.add_argument('os',type=Path);p.add_argument('car',type=Path);p.add_argument('out',type=Path)
a0=p.parse_args();sdk=a0.sdk.resolve();rom=a0.os.resolve();car=a0.car.resolve();out=a0.out.resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(sdk/'sdk/python'))
from altirra_bridge import AltirraBridge
assert zlib.crc32(rom.read_bytes())==0x29f133f7
payload=car.read_bytes()[16:];log=open(out/'server-private.log','w')
p=subprocess.Popen([str(sdk/'AltirraBridgeServer'),'--bridge=tcp:127.0.0.1:0','--machine=800XL','--memory=64K','--no-basic'],stdout=log,stderr=log)
encoder=None
try:
 token=Path(f'/tmp/altirra-bridge-{p.pid}.token')
 for _ in range(100):
  if token.exists() and 'token-file:' in (out/'server-private.log').read_text():break
  if p.poll() is not None:raise RuntimeError('Server exited '+str(p.returncode))
  time.sleep(.05)
 with AltirraBridge.from_token_file(str(token)) as a:
  a.pause()
  for k,v in [('video','ntsc'),('fastboot','off'),('siopatch','off'),('fppatch','off'),('kernel',str(rom))]:a.config(k,v)
  cfg=a.config();print('CONFIG',json.dumps(cfg),flush=True)
  a.boot(str(car));a.pause();print('CART',a.cart_info(),flush=True)
  steps={};banks={};transitions=[];last_bank=None;video_frames=0;last_render=0
  for frame in range(1,2401):
   a.frame(1);regs=a.regs();pc=int(regs['PC'][1:],16);state=a.peek(0x80,8);step,bank,hold,loops=state[:4];renders=int.from_bytes(state[4:6],'little')
   screen=a.peek(0x2900,80)
   valid_step=step if (step==1 and 0xa000<=pc<0xa100) or (step in (2,3,4,5) and screen.startswith(f'STEP {step}'.encode())) else None
   if valid_step and valid_step not in steps:
    steps[valid_step]={'emulator_frame':frame,'clock':a.clock(),'regs':regs}
    # This frame began before the CPU changed the display. Save the next one.
    print('STEP',valid_step,'FRAME',frame,flush=True)
   if valid_step and frame==steps[valid_step]['emulator_frame']+2:
    (out/f'step-{step}.png').write_bytes(a.screenshot())
   if 1 in steps:
    raw=a.rawscreen()
    if encoder is None:
     assert raw.stride==raw.width*4
     encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgra','-video_size',f'{raw.width}x{raw.height}','-framerate','59.922743','-i','-','-an','-vf','scale=672:448:flags=neighbor','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'DOOMMOV-AltirraSDL.mp4')],stdin=subprocess.PIPE)
    encoder.stdin.write(raw.pixels);video_frames+=1
   if step==6 and 1<=bank<=7 and renders:
    if bank!=last_bank:
     transitions.append({'bank':bank,'emulator_frame':frame,'renders':renders,'loops':loops});last_bank=bank
    if bank not in banks and 10<=hold<=20:
     actual=a.peek(0x8000,16384);expected=payload[bank*16384:(bank+1)*16384]
     assert actual==expected,('ROM mismatch',bank)
     for pm in range(4):assert a.peek(0x3204+pm*128,96)==expected[0x3e00+pm*96:0x3e60+pm*96],('PMG mismatch',bank,pm)
     assert screen[15:18]==f'{bank}/7'.encode(),('Footer mismatch',screen)
     png=a.screenshot();(out/f'frame-{bank}.png').write_bytes(png)
     banks[bank]={'emulator_frame':frame,'renders':renders,'hold':hold,'screenshot_sha256':hashlib.sha256(png).hexdigest(),'rom_sha256':hashlib.sha256(actual).hexdigest(),'clock':a.clock(),'regs':regs}
     print('BANK_RENDERED',bank,'RENDERS',renders,flush=True)
    if loops>=3 and bank==1 and hold<=20:break
   if frame%240==0:print('PROGRESS',frame,'PC',hex(pc),'STATE',list(state[:6]),flush=True)
  assert set(steps)=={1,2,3,4,5},steps
  assert set(banks)==set(range(1,8)),banks
  assert loops>=3 and renders>=504,(loops,renders)
  assert len(set(b['screenshot_sha256'] for b in banks.values()))==7
  for left,right in zip(transitions,transitions[1:]):
   assert right['bank']==left['bank']%7+1,(left,right)
  observed_loop=transitions[14]['emulator_frame']-transitions[7]['emulator_frame'];assert observed_loop==168,observed_loop
  for left,right in zip(transitions[1:],transitions[2:]):
   assert right['renders']-left['renders']==24,(left,right)
  # Verify warm RESET returns to fixed-ROM STEP 1 from a frame bank.
  a.warm_reset();a.pause();reset_ok=False
  for n in range(1,401):
   a.frame(1);regs=a.regs();pc=int(regs['PC'][1:],16)
   if 0xa000<=pc<0xa100 and a.peek(0x80,1)==b'\x01':reset_ok=True;break
  assert reset_ok,'Warm reset did not return to ROM STEP 1'
  a.frame(2);a.regs();(out/'reset-step-1.png').write_bytes(a.screenshot())
  result={'emulator':'AltirraSDL native AltirraBridgeServer','emulator_commit':'288e2b03edf29d97d2c53b7b3e77335862e2e645','wine_used':False,'os_crc32':'29f133f7','car_sha256':hashlib.sha256(car.read_bytes()).hexdigest(),'config':cfg,'steps':steps,'banks':banks,'transitions':transitions,'complete_loops':loops,'raster_returns':renders,'video_frames':video_frames,'loop_video_frames':observed_loop,'warm_reset_step1':reset_ok,'hardware_tested':False}
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');a.quit()
  print('MOVIE_NATIVE_ALTIRRA_OK',json.dumps({'steps':list(steps),'banks':list(banks),'loops':loops,'raster_returns':renders,'warm_reset':reset_ok}),flush=True)
finally:
 if encoder:
  encoder.stdin.close();assert encoder.wait(timeout=30)==0
 if p.poll() is None:p.terminate()
 p.wait(timeout=5);log.close()
