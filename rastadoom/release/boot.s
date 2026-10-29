; GPL-2.0-or-later. Fixed ROM entry for the release cartridge.
.setcpu "6502"
.segment "BOOT"
.export start
start:
    sei
    cld
    ldx #$ff
    txs
    lda #0
    sta $d40e
    sta $d20e
    sta $d400
    sta $d01d
    sta $d01b
    sta $d01a
    sta $d404
    sta $d405
    sta $d207
    lda #2
    sta $d401
    ; Copy the working Atari client before requesting the Pico handoff.
    lda #0
    sta $84
    sta $86
    lda #$80
    sta $85
    lda #$20
    sta $87
    ldx #16
    ldy #0
copy_client:
    lda ($84),y
    sta ($86),y
    iny
    bne copy_client
    inc $85
    inc $87
    dex
    bne copy_client
    jmp $2000
.segment "SIGNATURE"
    ; Preserve the installed launch protocol's private recognition bytes.
    .byte "RASTADOOM-STEP9",0,0
.segment "INIT"
    rts
.segment "VECTORS"
    .word start
    .byte 0,4
    .word $bff0
