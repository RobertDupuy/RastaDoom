/* Execute the user's exact original Robin Edwards firmware loader.
 * Fixture has a populated filesystem; firmware instructions are unchanged. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root=process.env.RP2040JS_ROOT;
const {RP2040}=await import(pathToFileURL(path.join(root,'dist/esm/rp2040.js')).href);
const {SimulationClock}=await import(pathToFileURL(path.join(root,'dist/esm/clock/simulation-clock.js')).href);
const {bootromB1}=await import(pathToFileURL(path.join(root,'demo/bootrom.ts')).href);
const [fixture,original,car,out]=process.argv.slice(2);
const flash=fs.readFileSync(fixture),base=fs.readFileSync(original),payload=fs.readFileSync(car).subarray(16);
if(crypto.createHash('sha256').update(base).digest('hex')!=='3364a0ba142b59790bc6f16f0ceacd2a63616e6e4869fa44a1e4ec18f17e9789')throw Error('Wrong original firmware');
for(let i=0;i<base.length;i+=512){const off=base.readUInt32LE(i+12)-0x10000000,len=base.readUInt32LE(i+16);if(off<0x100000&&!flash.subarray(off,off+len).equals(base.subarray(i+32,i+32+len)))throw Error('Original firmware changed');}
const clock=new SimulationClock(250e6),m=new RP2040(clock);
m.logger={debug(){},info(){},warn(){},error(c,s){throw Error(c+':'+s)}};
m.loadBootrom(bootromB1);m.flash.set(flash);m.core.SP=0x20042000;m.core.PC=0x100001f6;m.core.VTOR=0x10000100;
m.onBreak=code=>{throw Error('Breakpoint '+code)};
function stepTo(pc,max=20000000){for(let i=0;i<max;i++){if(m.core.PC===pc)return;clock.tick(m.core.executeInstruction()*4);}throw Error('Timeout '+m.core.PC.toString(16));}
stepTo(m.readUint32(0x1000027c)&~1);
m.writeUint8(0x20040000,0);m.core.registers[0]=0x20040000;m.core.LR=0x100001c1;m.core.PC=0x100006a4;stepTo(0x100001c0);
if(m.core.registers[0]!==1)throw Error('Original directory read failed');
const n=m.readUint32(0x200355e4);let found=false;
for(let j=0;j<n;j++){let s='';for(let k=1;k<14;k++){const c=m.readUint8(0x20005cc0+j*256+k);if(!c)break;s+=String.fromCharCode(c);}console.log('MENU_ENTRY',s);if(s==='DOOMMOV.CAR')found=true;}
if(!found)throw Error('Movie not present in menu');
m.sram.set(Buffer.from('DOOMMOV.CAR\0'),0x40000);m.core.registers[0]=0x20040000;m.core.LR=0x100001c1;m.core.PC=0x10000890;stepTo(0x100001c0);
if(m.core.registers[0]!==12)throw Error('Original loader did not select MegaCart128K: '+m.core.registers[0]);
if(payload.length!==131072)throw Error('Wrong CAR size');
for(let i=0;i<payload.length;i++)if(m.readUint8(0x20005cc0+i)!==payload[i])throw Error('Loaded byte mismatch at '+i);
const result={original_firmware_sha256:crypto.createHash('sha256').update(base).digest('hex'),firmware_instructions_changed:0,menu_entry:'DOOMMOV.CAR',car_header_type:29,original_internal_type:12,bytes_compared:payload.length,car_sha256:crypto.createHash('sha256').update(fs.readFileSync(car)).digest('hex'),hardware_tested:false};
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log('ORIGINAL_MOVIE_CAR_LOAD_OK',JSON.stringify(result));
