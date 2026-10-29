/* RP2040 instruction/protocol checks only. NOT an Atari/Altirra display test,
 * NOT a measurement of electrical timing or dual-core contention. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=process.env.RP2040JS_ROOT;
const {RP2040}=await import(pathToFileURL(path.join(root,'dist/esm/rp2040.js')).href);
const {SimulationClock}=await import(pathToFileURL(path.join(root,'dist/esm/clock/simulation-clock.js')).href);
const {bootromB1}=await import(pathToFileURL(path.join(root,'demo/bootrom.ts')).href);
const elf='build-steps/engine/rastadoom.elf';
const symbols={};
for(const line of execFileSync('arm-none-eabi-nm',['-n',elf],{encoding:'utf8'}).split('\n')){
 const x=line.match(/^([0-9a-f]+) \w (.+)$/);if(x)symbols[x[2]]=parseInt(x[1],16);
}
const clock=new SimulationClock(250e6),m=new RP2040(clock);
m.logger={debug(){},info(){},warn(){},error(c,s){throw Error(c+':'+s)}};
m.loadBootrom(bootromB1);m.flash.set(fs.readFileSync('build-steps/flash.bin'));
m.core.SP=0x20042000;m.core.PC=0x100001f6;m.core.VTOR=0x10000100;
let stopped=false;
m.onBreak=(code)=>{throw Error(`ARM breakpoint ${code} at ${m.core.PC.toString(16)}`)};
function step(){clock.tick(m.core.executeInstruction()*4);}
function stepTo(pc,max=10000000){for(let i=0;i<max;i++){if(m.core.PC===pc)return;step();}throw Error('Timeout '+m.core.PC.toString(16));}
stepTo(m.readUint32(0x1000027c)&~1);
// Run the original firmware's actual directory enumeration on the new FAT.
m.writeUint8(0x20040000,0);m.core.registers[0]=0x20040000;
m.core.LR=0x100001c1;m.core.PC=0x100006a4;stepTo(0x100001c0);
if(m.core.registers[0]!==1)throw Error('Original read_directory failed');
const n=m.readUint32(0x200355e4);let found=false;
for(let j=0;j<n;j++){
 let s='';for(let k=1;k<14;k++){const c=m.readUint8(0x20005cc0+j*256+k);if(!c)break;s+=String.fromCharCode(c);}
 console.log('MENU_ENTRY',s);if(s==='DOOMSTEP.CAR')found=true;
}
if(!found)throw Error('CAR missing from original menu');
console.log('ORIGINAL_DIRECTORY_ENUMERATION_OK');
// Run Robin's actual load_file(): parse the CAR header and read its complete
// payload through the original filesystem routines into cart_ram.
const rom=fs.readFileSync('dist/steps-0.5.0/DOOMSTEP.CAR').subarray(16);
const filename=Buffer.from('DOOMSTEP.CAR\0');
m.sram.set(filename,0x40000);
m.core.registers[0]=0x20040000;m.core.LR=0x100001c1;m.core.PC=0x10000890;
stepTo(0x100001c0);
if(m.core.registers[0]!==2)throw Error('Original load_file did not select standard 16K');
for(let i=0;i<rom.length;i++)if(m.readUint8(0x20005cc0+i)!==rom[i])
 throw Error('Original load_file payload mismatch at '+i);
console.log('ORIGINAL_CAR_LOAD_OK: type 2 and all 16384 ROM bytes');
for(const gpio of m.gpio){gpio.ctrl=5;gpio.padValue=0x40;}
const DATA=0x1fe000,PHI2=0x400000,CCTL=0x200000,RW=0x800000,S4=0x1000000,S5=0x2000000;
function pins(v){for(let p=0;p<26;p++)m.gpio[p].setInputValue(!!(v&(1<<p)));}
function run(cycles){const end=m.core.cycles+cycles;while(m.core.cycles<end)step();}
pins(CCTL|RW|S4|S5);m.core.SP=0x20041f00;m.core.PC=0x200001d0;
run(20000);
if(m.readUint16(0x2003803a)!==0xd061)throw Error('Special cartridge not recognized');
for(const high of [0,PHI2])for(const bank of [0,8192]){
 const select=CCTL|RW|(bank?S4:S5)|high;
 for(let addr=0;addr<8192;addr+=29){
  pins(select|addr);run(100);
  const value=(m.sio.gpioValue>>>13)&255;
  if((m.sio.gpioOutputEnable&DATA)!==DATA||value!==rom[bank+addr])
   throw Error(`Static ROM mismatch bank=${bank} addr=${addr} got=${value}`);
 }
 pins(CCTL|RW|S4|S5);run(100);
 if(m.sio.gpioOutputEnable&DATA)throw Error('Bus not released');
}
console.log('ORIGINAL_ROM_SERVICE_OK: both banks, continuous selects, PHI2 high/low');
// Invalid request must not enter engine.
pins(S4|S5|0xdf|PHI2|(0x55<<13));run(100);
pins(S4|S5|0xdf|(0x55<<13));run(100);
pins(CCTL|RW|S4|S5);run(100);
if(m.core.PC<0x20038000||m.core.PC>=0x20038200)throw Error('Invalid request launched');
// Actual STEP 3 command, captured by the SRAM idle extension.
pins(S4|S5|0xdf|PHI2|(0xd6<<13));run(100);
pins(S4|S5|0xdf|(0xd6<<13));
const reset=m.readUint32(0x10080304)&~1;
stepTo(reset,10000);
console.log('REAL_LAUNCH_STUB_REACHED_ENGINE_CRT');
pins(CCTL|RW|S4|S5);
const mailbox=symbols.rd_mailbox;
let released=false,initSeen=false,minSP=0x20042000,ackWait=0;
function strAt(a){let s='';for(let i=0;i<180;i++){const c=m.readUint8(a+i);if(!c)break;s+=String.fromCharCode(c);}return s;}
for(let chunk=0;chunk<400;chunk++){
 for(let i=0;i<500000;i++){
  const pc=m.core.PC;
  if(pc===symbols.multicore_launch_core1){
   // rp2040js models one core; a separate bus test covers the compiled loop.
   m.core.PC=m.core.LR&~1;continue;
  }
  if(pc===symbols.I_Error||pc===symbols.panic||pc===symbols.rd_fault)
   throw Error('ENGINE ERROR: '+strAt(m.core.registers[0]));
  const ack=m.readUint8(mailbox+0xf0)===82&&m.readUint8(mailbox+0xf1)===68&&m.readUint8(mailbox+0xf5)===5;
  if(ack&&!released&&++ackWait===10000){
   if(m.readUint8(mailbox+0xf6))throw Error('Engine initialized before release');
   m.writeUint8(mailbox+3,15);m.writeUint8(mailbox+4,255);m.writeUint8(mailbox+0xf8,0xa5);
   released=true;console.log('RUNTIME_ACK_AND_EXPLICIT_INIT_RELEASE_OK');
  }
  if(!initSeen&&m.readUint8(mailbox+0xf6)===0xa5){initSeen=true;console.log('ACTUAL_ENGINE_INITIALIZATION_COMPLETED');}
  if(m.readUint8(mailbox+0xfd)===1){
   if(!released||!initSeen)throw Error('Frame published before initialization');
   const pending=m.readUint32(symbols.rd_pending);
   if(pending>1)throw Error('Bad pending window');
   const start=symbols.rd_windows+pending*16384;
   const frame=Buffer.alloc(16384);for(let k=0;k<16384;k++)frame[k]=m.readUint8(start+k);
   if(frame.subarray(0x3fe0,0x3fe4).toString()!=='RD5F')throw Error('Missing frame signature');
   fs.writeFileSync('build-steps/first-frame.bin',frame);
   if(minSP<symbols.__StackBottom)throw Error('Engine stack overflow');
   console.log('FIRST_REAL_FRAME_ENCODED',JSON.stringify({pending,minSP,cycles:m.core.cycles,zoneBytes:0x20040000-symbols.__end__}));
   process.exit(0);
  }
  if(m.core.SP>=0x20040000&&m.core.SP<minSP)minSP=m.core.SP;
  step();
 }
 if(chunk%10===0)console.log('ARM_PROGRESS',chunk*500000,'PC',m.core.PC.toString(16));
}
throw Error('Engine test instruction limit reached');
