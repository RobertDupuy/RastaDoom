#!/usr/bin/env python3
"""Native AltirraSDL + unchanged RP2040 firmware functional integration check.
The custom device substitutes only the Pico GPIO/memory protocol. This is
not a simultaneous dual-core timing test or a hardware FPS benchmark.
"""
from pathlib import Path
import argparse,subprocess,time,sys,json,hashlib,zlib,base64,os,shutil
p=argparse.ArgumentParser();p.add_argument('sdk',type=Path);p.add_argument('os',type=Path);p.add_argument('car',type=Path);p.add_argument('engine',type=Path);p.add_argument('wad',type=Path);p.add_argument('out',type=Path);args=p.parse_args()
here=Path(__file__).resolve().parent;sdk=args.sdk.resolve();rom=args.os.resolve();car=args.car.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(sdk/'sdk/python'));from altirra_bridge import AltirraBridge
assert zlib.crc32(rom.read_bytes())==0x29f133f7
(out/'pico-windows.bin').write_bytes(car.read_bytes()[16:]+bytes(16384));shutil.copy(here/'pico-model.atdevice',out/'pico-model.atdevice')
log=open(out/'server-private.log','w');p=subprocess.Popen([str(sdk/'AltirraBridgeServer'),'--bridge=tcp:127.0.0.1:0','--machine=800XL','--memory=64K','--no-basic'],stdout=log,stderr=log)
worker=None;encoder=None;engine_log=open(out/'engine.jsonl','w');model=None
try:
 token=Path(f'/tmp/altirra-bridge-{p.pid}.token')
 for _ in range(100):
  if token.exists() and 'token-file:'in(out/'server-private.log').read_text():break
  if p.poll() is not None:raise RuntimeError('Server exited')
  time.sleep(.05)
 worker=subprocess.Popen(['node',str(here/'engine_worker.mjs'),str(args.engine.resolve()),str(args.wad.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
 def arm(command):
  worker.stdin.write(json.dumps(command)+'\n');worker.stdin.flush();s=worker.stdout.readline()
  if not s:raise RuntimeError('Engine worker exited')
  reply=json.loads(s)
  if 'error'in reply:raise RuntimeError(reply['error'])
  record={k:v for k,v in reply.items() if k not in ('frame','mailbox')};record['command']=command;engine_log.write(json.dumps(record)+'\n');engine_log.flush()
  print('ARM',reply['produced'],'TIC',reply['tic'],'STATE',reply['state'],'MENU',reply['menu'],'INPUT',command.get('input'),flush=True)
  return reply
 with AltirraBridge.from_token_file(str(token))as a:
  a.pause()
  for k,v in [('kernel',str(rom)),('video','ntsc'),('fastboot','off'),('siopatch','off'),('fppatch','off')]:a.config(k,v)
  cfg=a.config();a.device_set('custom',True,path=str(out/'pico-model.atdevice'),allowunsafe=True);a.cold_reset();a.pause()
  steps={};trace=[];events=[];last_consumed=0;live_start=None;last_service=-100;published={};video_frames=0;joy_state=None;console_state=None
  def controls(joy='centre',fire=False,start=False,select=False,option=False):
   global joy_state,console_state
   j=(joy,fire);c=(start,select,option)
   if j!=joy_state:a.joy(0,joy,fire);joy_state=j
   if c!=console_state:a.consol(start=start,select=select,option=option);console_state=c
  def publish(reply):
   mb=base64.b64decode(reply['mailbox'])
   for off,n in [(0xf0,4),(0xf5,2),(0xa0,40)]:a.memload(0x108000+off,mb[off:off+n])
   if 'frame'in reply:
    raw=base64.b64decode(reply['frame']);bank=reply['pending'];assert len(raw)==16384 and raw[0x3fe0:0x3fe4]==b'RD5F'
    a.memload(0x100000+bank*16384,raw);published[bank]=raw
    a.memload(0x1080fc,bytes([bank,1]));trace.append({k:v for k,v in reply.items() if k not in ('frame','mailbox')})
    events.extend(reply['events'])
  for f in range(1,4001):
   k=(model['produced']-live_start)if model and live_start is not None else -1
   if k<2:controls()
   elif k<4:controls(select=True)
   elif k<6:controls()
   elif k<8:controls(start=True)
   elif k<10:controls()
   elif k<12:controls(start=True)
   elif k<14:controls()
   elif k<16:controls(start=True)
   elif k<18:controls()
   elif k<28:controls('up')
   elif k<36:controls('right')
   elif k<50:controls('up',fire=True)
   elif k<56:controls(fire=True)
   else:controls()
   a.frame(1);regs=a.regs();pc=int(regs['PC'][1:],16);cur=a.peek(0x80,1)[0];mb=a.peek(0xd500,256);text=a.peek(0x2900,120)
   step=1 if 0xa000<=pc<0xa100 else cur if 2<=cur<=9 and text.startswith(f'STEP {cur}'.encode()) else None
   if step and step not in steps:steps[step]={'frame':f,'clock':a.clock(),'regs':regs};print('STEP',step,'FRAME',f,flush=True)
   if step and f==steps[step]['frame']+2:(out/f'step-{step}.png').write_bytes(a.screenshot())
   if 1 in steps:
    raw=a.rawscreen()
    if encoder is None:encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgra','-video_size',f'{raw.width}x{raw.height}','-framerate','59.922743','-i','-','-an','-vf','scale=672:448:flags=neighbor','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'DOOM-Steps-0.5.1-Gameplay.mp4')],stdin=subprocess.PIPE)
    encoder.stdin.write(raw.pixels);video_frames+=1
   if b'STOPPED'in text:raise AssertionError(('Unexpected stopped screen',f,text))
   if cur==9 and 9 in steps and f>steps[9]['frame']+182 and live_start is None:
    live_start=model['produced'];print('LIVE_START',f,live_start,flush=True)
   if model is None and mb[0xdf]==0xd6:
    model=arm({'release':False});publish(model)
   elif model and not model['initialized'] and mb[0xf8]==0xa5:
    model=arm({'release':True,'input':list(mb[:5])});publish(model);last_service=f
   elif model and model['initialized'] and mb[0xf4]!=last_consumed and f-last_service>=8:
    # Actual Atari code has selected the published bank. Confirm mapped ROM.
    bank=mb[0xfb];assert a.peek(0x8000,16384)==published[bank]
    if cur==9 and live_start is not None:
     for pm in range(4):assert a.peek(0x3204+pm*128,96)==published[bank][0x3e00+pm*96:0x3e60+pm*96]
    last_consumed=mb[0xf4];model=arm({'release':True,'consume':True,'input':list(mb[:5])});publish(model);last_service=f
   if live_start is not None and model['produced']-live_start>=60:
    a.frame(2);a.regs();(out/'gameplay.png').write_bytes(a.screenshot());break
  else:raise AssertionError('No complete gameplay run')
  assert set(steps)==set(range(1,10)),steps
  for n in range(2,10):assert steps[n]['frame']-steps[n-1]['frame']>=180,(n,steps)
  levels=[t for t in trace if t['state']==0 and t['menu']==0];assert len(levels)>=20,len(levels)
  assert len({(t.get('x'),t.get('y'))for t in levels})>5,'No player movement'
  assert min(t['bullets']for t in levels)<max(t['bullets']for t in levels),'No ammunition spent'
  keys={(e['type'],e['key'])for e in events}
  # DOOM key definitions: escape, enter, up, right, fire.
  for key in [27,13,0xad,0xae,0x9d]:assert (0,key)in keys and (1,key)in keys,(key,keys)
  returns=int.from_bytes(a.peek(0x8a,2),'little');assert returns>=400,returns
  controls();a.key_raw('all',False)
  input_checks=[]
  for direction,bits in [('centre',0),('up',1),('down',2),('left',4),('right',8),('upleft',5),('upright',9),('downleft',6),('downright',10)]:
   controls(direction);a.frame(3);a.regs();actual=a.peek(0xd500,1)[0];assert actual==bits,(direction,actual,bits);input_checks.append({'direction':direction,'mailbox':actual})
  controls(fire=True,option=True);a.frame(3);a.regs();assert a.peek(0xd500,1)==b'\x30'
  controls();a.frame(3);a.regs();assert a.peek(0xd500,2)==b'\0\0'
  for name,code in [('RETURN',12),('ESC',28),('SPACE',33),('W',46)]:
   a.key_raw(name,True);a.frame(4);a.regs();assert a.peek(0xd504,1)[0]==code,(name,a.peek(0xd504,1))
   a.key_raw('all',False);a.frame(4);a.regs();assert a.peek(0xd504,1)==b'\xff',name
  a.key_raw('W',True,shift=True);a.frame(4);a.regs();assert a.peek(0xd500,1)[0]&128
  a.key_raw('all',False);a.frame(4);a.regs();assert a.peek(0xd500,1)[0]==0
  print('CONTROL_PRESS_RELEASE_CHECKS_OK',flush=True)
  # Stop feeding frames: keep rendering and polling, then show a diagnostic.
  a.frame(2100);a.regs();timeout=a.peek(0x2900,120).decode('ascii','replace');assert 'STOPPED - NO COMPLETE FRAME'in timeout,timeout
  (out/'live-timeout.png').write_bytes(a.screenshot())
  result={'release':'0.5.1','emulator':'Native AltirraSDL + RP2040 instruction model through custom cartridge adapter','os_crc32':'29f133f7','car_sha256':hashlib.sha256(car.read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256(args.engine.with_suffix('.bin').read_bytes()).hexdigest(),'config':cfg,'steps':steps,'produced_frames':model['produced'],'live_raster_returns':returns,'gameplay_frames':len(levels),'player_movement_verified':True,'bullets_before':max(t['bullets']for t in levels),'bullets_after':min(t['bullets']for t in levels),'input_checks':input_checks,'key_events':[list(x) for x in sorted(keys)],'press_and_release_verified':True,'live_frame_timeout_verified':True,'video_frames':video_frames,'audio_tested':False,'hardware_tested':False,'physical_or_dual_core_timing_tested':False}
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PLAY_CHECK_OK',json.dumps({k:v for k,v in result.items() if k in ('produced_frames','live_raster_returns','gameplay_frames','press_and_release_verified','live_frame_timeout_verified')}),flush=True);a.quit()
finally:
 if encoder:encoder.stdin.close();encoder.wait(30)
 if worker:
  if worker.poll() is None:worker.stdin.write('{"quit":true}\n');worker.stdin.flush()
  worker.stdin.close()
  try:worker.wait(10)
  except subprocess.TimeoutExpired:
   worker.terminate();worker.wait(5)
 if p.poll() is None:p.terminate()
 p.wait(5);log.close();engine_log.close()
