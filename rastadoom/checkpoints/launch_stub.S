.syntax unified
.cpu cortex-m0plus
.thumb
.section .launch_stub,"ax"
.global launch_stub
.thumb_func
launch_stub:
    /* Entered only when neither S4 nor S5 is selected. r2 is GPIO_IN,
       r3 is SIO_BASE. All normal ROM service instructions are untouched. */
    movs r0,#7
    lsls r0,r0,#21
    ands r0,r2
    movs r7,#1
    lsls r7,r7,#22
    cmp r0,r7
    bne resume
    uxtb r0,r2
    cmp r0,#0xdf
    bne resume
sample_write:
    movs r0,r2
    ldr r2,[r3,#4]
    lsls r7,r2,#9
    bmi sample_write
    lsrs r0,r0,#13
    uxtb r0,r0
    cmp r0,#0xd6
    bne resume
    ldr r0,=enter_engine
    bx r0
resume:
    ldr r0,=0x20038033
    bx r0
    .ltorg
