/* Record exact published windows from the unmodified 0.5.0 RP2040 binary.
 * rp2040js substitutes the cartridge consumer for core 1. No host renderer.
 * This is instruction emulation, not a real-time hardware benchmark. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=process.env.RP2040JS_ROOT;
const {RP2040}=await import(pathToFileURL(path.join(root,'dist/esm/rp2040.js')).href);
const {SimulationClock}=await import(pathToFileURL(path.join(root,'dist/esm/clock/simulation-clock.js')).href);
const {bootromB1}=await import(pathToFileURL(path.join(root,'demo/bootrom.ts')).href);
const elf=process.argv[2],whx=process.argv[3],out=process.argv[4];
fs.mkdirSync(out,{recursive:true});
const symbols={};
for(const line of execFileSync('arm-none-eabi-nm',['-n',elf],{encoding:'utf8'}).split('\n')){
 const x=line.match(/^([0-9a-f]+) \w (.+)$/);if(x)symbols[x[2]]=parseInt(x[1],16);
}
const clock=new SimulationClock(250e6),m=new RP2040(clock),program=fs.readFileSync(elf.replace(/\.elf$/,'.bin'));
m.logger={debug(){},info(){},warn(){},error(c,s){throw Error(c+':'+s)}};
m.loadBootrom(bootromB1);m.flash.set(program,0x80200);m.flash.set(fs.readFileSync(whx),0x800000);
m.core.SP=program.readUInt32LE(256);m.core.PC=program.readUInt32LE(260)&~1;m.core.VTOR=0x10080300;
m.onBreak=code=>{throw Error(`ARM breakpoint ${code} at ${m.core.PC.toString(16)}`)};
const mb=symbols.rd_mailbox,frames=[],target=Number(process.env.RD_MOVIE_FRAMES||40);
let minSP=0x20042000,released=false,instructions=0;
function textAt(a){let s='';for(let i=0;i<180;i++){let c=m.readUint8(a+i);if(!c)break;s+=String.fromCharCode(c);}return s;}
while(frames.length<target && instructions<4000000000){
 for(let i=0;i<500000;i++){
  const pc=m.core.PC;
  if(pc===symbols.multicore_launch_core1){m.core.PC=m.core.LR&~1;continue;}
  if(pc===symbols.I_Error||pc===symbols.panic||pc===symbols.rd_fault)throw Error('ENGINE ERROR: '+textAt(m.core.registers[0]));
  if(!released&&m.readUint8(mb+0xf5)===5){
   m.writeUint8(mb+3,15);m.writeUint8(mb+4,255);m.writeUint8(mb+0xf8,0xa5);released=true;
  }
  if(m.readUint8(mb+0xfd)===1){
   const pending=m.readUint32(symbols.rd_pending);if(pending>1)throw Error('Bad pending window');
   const start=symbols.rd_windows+pending*16384,window=Buffer.from(m.sram.subarray(start-0x20000000,start-0x20000000+16384));
   if(window.subarray(0x3fe0,0x3fe4).toString()!=='RD5F')throw Error('Missing frame signature');
   const n=frames.length+1,name=`frame-${String(n).padStart(3,'0')}.bin`;
   fs.writeFileSync(path.join(out,name),window);
   const record={frame:n,file:name,tic:m.readUint32(symbols.gametic),leveltime:m.readUint32(symbols.leveltime),state:m.readUint8(symbols.gamestate),map:m.readUint8(symbols.gamemap),menu:m.readUint8(symbols.menuactive),cycles:m.core.cycles,sha256:crypto.createHash('sha256').update(window).digest('hex')};
   frames.push(record);console.log('FRAME',JSON.stringify(record));
   m.writeUint32(symbols.rd_display,pending);m.writeUint32(symbols.rd_pending,2);m.writeUint8(mb+0xfd,0);
   m.writeUint8(mb+0xf4,(m.readUint8(mb+0xf4)+1)&255);
   // Actual input mailbox: ESC, ENTER x3, then walk, turn and fire.
   m.writeUint8(mb+1,[3,5,7,9].includes(n)?(n===3?1:2):0);
   m.writeUint8(mb,n>=12?(1 | (n>=18?8:0) | (n>=24?16:0)):0);
   // Drain audio in lieu of the Atari DAC; the movie is deliberately silent.
   m.writeUint32(symbols.rd_pcm_read,m.readUint32(symbols.rd_pcm_write));
   if(minSP<symbols.__StackBottom)throw Error('Engine stack overflow');
   if(frames.length>=target)break;
  }
  if(m.core.SP>=0x20040000 && m.core.SP<minSP)minSP=m.core.SP;
  clock.tick(m.core.executeInstruction()*4);instructions++;
 }
 if(instructions%10000000<500000)console.log('PROGRESS',instructions,'PC',m.core.PC.toString(16));
}
if(frames.length!==target)throw Error('Instruction limit');
fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify({engine_binary_sha256:crypto.createHash('sha256').update(program).digest('hex'),source:'Unmodified 0.5.0 ARM firmware executed in rp2040js',hardware_timing_validated:false,ntsc:true,minSP,instructions,frames},null,2)+'\n');
console.log('CAPTURE_OK',frames.length);
