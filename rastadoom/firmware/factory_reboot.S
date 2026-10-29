/* GPL-2.0-or-later. Copied to SRAM before the watchdog resets both cores. */
.syntax unified
.cpu cortex-m0plus
.thumb
.section .rodata.rd_reboot,"a",%progbits
.balign 4
.global rd_reboot_start, rd_reboot_end
rd_reboot_start:
    cpsid i
    ldr r0, =0x20040001
    blx r0                  /* copied boot2 sets up XIP and returns */
    ldr r0, =0xe000ed08
    ldr r1, =0x10080300     /* staged application's vector table */
    str r1, [r0]
    ldmia r1!, {r0, r2}
    msr msp, r0
    bx r2
    .ltorg
rd_reboot_end:
