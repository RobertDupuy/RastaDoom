; Count complete video frames with interrupts disabled. 181/151 frames make
; the visible pause at least three seconds on standard NTSC/PAL machines.
pause_three:
    ldx #181
    lda $d014
    and #$0f
    cmp #1
    bne pause_loop
    ldx #151
pause_loop:
    jsr wait_frame
    dex
    bne pause_loop
    rts
wait_frame:
    lda $d40b
    beq wait_frame
wait_zero:
    lda $d40b
    bne wait_zero
    rts
