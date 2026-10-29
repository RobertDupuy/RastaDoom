/* ARM instruction-model check of the real SRAM cartridge bus loop.
 * This tests protocol/tri-state behaviour and reports modeled latency.
 * It is not an electrical timing measurement or a dual-core contention model.
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=process.env.RP2040JS_ROOT!,elf=process.argv[2];
const {RP2040}=await import(pathToFileURL(path.join(root,'dist/esm/rp2040.js')).href);
const symbols:any={};
for(const line of execFileSync('arm-none-eabi-nm',['-n',elf],{encoding:'utf8'}).split('\n')) {
    const m=line.match(/^([0-9a-f]+) \w (.+)$/);if(m)symbols[m[2]]=parseInt(m[1],16);
}
const mcu=new RP2040();
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'rd-bus-'));
// Supply an output file: objcopy otherwise rewrites the input ELF in place,
// which races other read-only tests even when only dumping a section.
execFileSync('arm-none-eabi-objcopy',['--dump-section',`.data=${temp}/data`,elf,`${temp}/copy.elf`]);
mcu.sram.set(fs.readFileSync(temp+'/data'),symbols.__data_start__-0x20000000);
fs.rmSync(temp,{recursive:true});
mcu.writeUint8(symbols.rd_mailbox+0x80,0x18);
mcu.core.PC=symbols.bus_loop;mcu.core.SP=0x20041000;
for(const gpio of mcu.gpio){gpio.ctrl=5;gpio.padValue=0x40;}
function pins(v:number){for(let p=0;p<26;p++)mcu.gpio[p].setInputValue(!!(v&(1<<p)));}
function run(cycles:number){const end=mcu.core.cycles+cycles;while(mcu.core.cycles<end)mcu.core.executeInstruction();}
const DATA=0x1fe000,PHI2=0x400000,CCTL=0x200000,RW=0x800000,S4=0x1000000,S5=0x2000000;
let worst=0;
function read(name:string,select:number,address:number,expected:number){
    pins(select|RW|address);run(70);pins(select|RW|address|PHI2);
    const start=mcu.core.cycles;let driven=-1,value=-1;
    while(mcu.core.cycles-start<70){mcu.core.executeInstruction();
        if((mcu.sio.gpioOutputEnable&DATA)===DATA){value=(mcu.sio.gpioValue>>>13)&255;
            if(driven<0 && value===expected)driven=mcu.core.cycles-start;}}
    pins(CCTL|S4|S5|RW);run(25);
    if(value!==expected || (mcu.sio.gpioOutputEnable&DATA))throw new Error(`${name}: value=${value}, expected=${expected}, latency=${driven}`);
    worst=Math.max(worst,driven);console.log(JSON.stringify({read:name,cycles:driven,value}));
}
function write(address:number,value:number){
    pins(S4|S5|address);run(70);pins(S4|S5|address|PHI2|(value<<13));run(70);
    pins(S4|S5|address|(value<<13));run(70);
    if(mcu.sio.gpioOutputEnable&DATA)throw new Error('Cart drove data during a write');
}
pins(CCTL|S4|S5|RW);run(200); // finish the core-entry prologue before bus traffic
mcu.writeUint8(symbols.rd_windows+0x123,0x5a);
mcu.writeUint8(symbols.rd_windows+0x2345,0xc3);
read('S4',CCTL|S5,0x123,0x5a);
read('S5',CCTL|S4,0x345,0xc3);
// ANTIC DMA: keep the ROM select asserted, hold PHI2 low, change address.
// The previous 0.1.0 loop waited for PHI2 and fails this regression.
for(const phi of [0,PHI2])for(const bank of [0,8192]){
    const select=CCTL|(bank?S4:S5);
    for(let n=0;n<32;n++){
        const addr=(n*137+39)&8191,value=(n*31+bank/8192+3)&255;
        mcu.writeUint8(symbols.rd_windows+bank+addr,value);
        pins(select|RW|addr|phi);run(70);
        if((mcu.sio.gpioOutputEnable&DATA)!==DATA || ((mcu.sio.gpioValue>>>13)&255)!==value)
            throw new Error(`Continuous ROM select failed: PHI2=${!!phi}, bank=${bank}, address=${addr}`);
    }
    pins(CCTL|S4|S5|RW|phi);run(30);
    if(mcu.sio.gpioOutputEnable&DATA)throw new Error('Data stayed driven after ROM deselect');
}
console.log('ANTIC_CONTINUOUS_SELECT_OK: 128 address changes, both banks, PHI2 high and low');
read('pending-empty',S4|S5,0xfd,0);
mcu.writeUint32(symbols.rd_pending,1);mcu.writeUint8(symbols.rd_mailbox+0xfd,1);
read('pending-full',S4|S5,0xfd,1);
read('pcm-empty',S4|S5,0x80,0x18);
mcu.writeUint8(symbols.rd_pcm,0x1c);mcu.writeUint32(symbols.rd_pcm_write,1);
read('pcm-prefetch',S4|S5,0x80,0x18);
read('pcm-sample',S4|S5,0x80,0x1c);
write(0x04,0x87);read('keyboard',S4|S5,0x04,0x87);
if(symbols.rd_input_valid) {
    if(mcu.readUint8(symbols.rd_input_valid))throw new Error('Inputs live before joystick write');
    write(0x00,0x10);
    if(mcu.readUint8(symbols.rd_input_valid)!==1)throw new Error('Joystick write did not release bootstrap input guard');
    read('joystick',S4|S5,0x00,0x10);
}
write(0xfe,0xa5);
if(mcu.readUint32(symbols.rd_display)!==1 || mcu.readUint32(symbols.rd_pending)!==2)throw new Error('Frame acknowledgement failed');
pins(CCTL|S4|S5|RW|PHI2);run(70);
if(mcu.sio.gpioOutputEnable&DATA)throw new Error('Cart drove an unselected bus');
console.log('CART_BUS_OK',JSON.stringify({worst_modeled_cycles:worst,modeled_ns_at_250MHz:worst*4}));
