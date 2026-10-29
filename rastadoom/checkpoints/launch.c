/* Original Robin Edwards binary remains the base. Only the 16K-handler entry
 * is redirected. Its entire original 136-byte loop is copied unchanged; for
 * this signed diagnostic cart only, the idle/no-ROM-selected branch visits
 * launch_stub. The selected-ROM response paths remain original instructions.
 * GPL-2.0-or-later. */
#include <stdint.h>
#include "original_loop.h"
extern const uint8_t _stub_load[], _stub_size[];
#define R32(a) (*(volatile uint32_t *)(a))

__attribute__((section(".entry"),noreturn)) void dispatch(void) {
    volatile uint8_t *loop=(void *)0x20038000;
    volatile uint8_t *stub=(void *)0x20038100;
    const volatile uint8_t *cart=(void *)0x20005cc0;
    static const char signature[16]="RASTADOOM-STEP9";
    unsigned match=1;
    for(unsigned i=0;i<sizeof original_loop;i++)loop[i]=original_loop[i];
    for(unsigned i=0;i<(uintptr_t)_stub_size;i++)stub[i]=_stub_load[i];
    for(unsigned i=0;i<16;i++)if(cart[0x3fd0+i]!=signature[i])match=0;
    if(match) *(volatile uint16_t *)(loop+0x3a)=0xd061;
    __asm volatile("dsb\nisb" ::: "memory");
    ((void (*)(void))0x20038001)();
    __builtin_unreachable();
}

__attribute__((naked,noreturn)) void enter_engine(void) {
    __asm volatile(
      ".syntax unified\ncpsid i\n"
      "ldr r0, =0xe000e180\nmovs r1,#0\nmvns r1,r1\nstr r1,[r0]\n"
      "ldr r0, =0xe000e280\nstr r1,[r0]\n"
      "ldr r0, =0xe000e010\nmovs r1,#0\nstr r1,[r0]\n"
      "ldr r0, =0x40054038\nstr r1,[r0]\n"
      "ldr r0, =0x10080300\nldr r1, =0xe000ed08\nstr r0,[r1]\n"
      "ldr r1,[r0,#4]\nldr r0,[r0]\nmsr msp,r0\n"
      "dsb\nisb\ncpsie i\nbx r1\n");
}
