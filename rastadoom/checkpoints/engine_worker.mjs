/* Test only: run the unchanged real 0.5.0 ARM engine, with the Atari as its
 * cartridge consumer. Core 1 GPIO is replaced by a documented mailbox model.
 * This is not a simultaneous dual-core timing or electrical test. */
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=process.env.RP2040JS_ROOT;
const {RP2040}=await import(pathToFileURL(path.join(root,'dist/esm/rp2040.js')).href);
const {SimulationClock}=await import(pathToFileURL(path.join(root,'dist/esm/clock/simulation-clock.js')).href);
const {bootromB1}=await import(pathToFileURL(path.join(root,'demo/bootrom.ts')).href);
const elf=process.argv[2],wad=process.argv[3],syms={};
for(const line of execFileSync('arm-none-eabi-nm',['-n',elf],{encoding:'utf8'}).split('\n')){const t=line.match(/^([0-9a-f]+) \w (.+)$/);if(t)syms[t[2]]=parseInt(t[1],16);}
const clock=new SimulationClock(250e6),m=new RP2040(clock),code=fs.readFileSync(elf.replace(/\.elf$/,'.bin'));
m.logger={debug(){},info(){},warn(){},error(c,s){throw Error(c+':'+s)}};
m.loadBootrom(bootromB1);m.flash.set(code,0x80200);m.flash.set(fs.readFileSync(wad),0x800000);
m.core.SP=code.readUInt32LE(256);m.core.PC=code.readUInt32LE(260)&~1;m.core.VTOR=0x10080300;
m.onBreak=code=>{throw Error('ARM breakpoint '+code)};
const mb=syms.rd_mailbox;let produced=0,minSP=0x20042000,totalInsns=0,events=[];
function stringAt(a){let s='';for(let i=0;i<180;i++){let c=m.readUint8(a+i);if(!c)break;s+=String.fromCharCode(c);}return s;}
function snapshot(frame=false){
 const r={ack:m.readUint8(mb+0xf5)===5,initialized:m.readUint8(mb+0xf6)===0xa5,produced,pending:m.readUint32(syms.rd_pending),tic:m.readUint32(syms.gametic),leveltime:m.readUint32(syms.leveltime),state:m.readUint8(syms.gamestate),map:m.readUint8(syms.gamemap),menu:m.readUint8(syms.menuactive),events,minSP,totalInsns,cycles:m.core.cycles,mailbox:Buffer.from(m.sram.subarray(mb-0x20000000,mb-0x20000000+256)).toString('base64')};
 // Field offsets verified against this unchanged ELF's DWARF: player_s
 // mo=0, health=32, ammo=104; mobj_s.xy=12, x/y are signed 16.16 values.
 const player=syms.players,mo=m.readUint32(player);
 r.health=m.readUint32(player+32);r.bullets=m.readUint32(player+104);
 if(mo>=0x20000000&&mo<0x20040000){r.x=(m.readUint32(mo+12)|0)/65536;r.y=(m.readUint32(mo+16)|0)/65536;}
 events=[];
 if(frame){const pos=syms.rd_windows-0x20000000+r.pending*16384;r.frame=Buffer.from(m.sram.subarray(pos,pos+16384)).toString('base64');}
 return r;
}
function run(cmd){
 if(cmd.consume){const pending=m.readUint32(syms.rd_pending);if(pending>1)throw Error('Consume without completed frame');m.writeUint32(syms.rd_display,pending);m.writeUint32(syms.rd_pending,2);m.writeUint8(mb+0xfd,0);m.writeUint8(mb+0xf4,(m.readUint8(mb+0xf4)+1)&255);}
 if(cmd.input)for(const i of [0,1,3,4])m.writeUint8(mb+i,cmd.input[i]);
 if(cmd.release)m.writeUint8(mb+0xf8,0xa5);
 for(let i=0;i<120000000;i++){
  const pc=m.core.PC;
  if(pc===syms.multicore_launch_core1){m.core.PC=m.core.LR&~1;continue;}
  if(pc===syms.I_Error||pc===syms.panic||pc===syms.rd_fault)throw Error('DOOM ERROR: '+stringAt(m.core.registers[0]));
  if(pc===syms.D_PostEvent){const p=m.core.registers[0];events.push({type:m.readUint8(p),key:m.readUint32(p+4),tic:m.readUint32(syms.gametic)});}
  if(m.readUint8(mb+0xf5)===5&&!cmd.release)return snapshot();
  if(m.readUint8(mb+0xfd)===1){produced++;return snapshot(true);}
  if(m.core.SP>=0x20040000 && m.core.SP<minSP)minSP=m.core.SP;
  if(minSP<syms.__StackBottom)throw Error('ARM stack overflow');
  clock.tick(m.core.executeInstruction()*4);totalInsns++;
 }
 throw Error('ARM instruction limit at '+m.core.PC.toString(16));
}
for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})){
 try{const cmd=JSON.parse(line);if(cmd.quit)process.exit(0);process.stdout.write(JSON.stringify(run(cmd))+'\n');}
 catch(e){process.stdout.write(JSON.stringify({error:String(e),stack:e.stack})+'\n');break;}
}
