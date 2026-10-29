; Fixed 16K cartridge code. No Pico commands before the RAM client takes over.
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
    sta $d018
    sta $d404
    sta $d405
    lda #2
    sta $d401
    lda #$0e
    sta $d017
    lda #$b8
    sta $d409
    lda #<$b600
    sta $d402
    lda #>$b600
    sta $d403
    lda #$22
    sta $d400
    ; STEP 1 is now driven entirely by fixed ROM: code, list, text, font.
    jsr pause_three
    ; Copy the actual client, its text/list and font. This is not a RAM test.
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
.include "wait.inc"
.segment "FIXED_TEXT"
    .byte "STEP 1 - CARTRIDGE RUNNING              "
    .byte "FIXED CARTRIDGE ROM                     "
    .byte "PAUSE 3 SECONDS                         "
.segment "FIXED_LIST"
    .byte $70,$70,$70,$42
    .word $b000
    .byte $02,$02,$41
    .word $b600
.segment "FONT"
    .incbin "font.bin"
.segment "SIGNATURE"
    .byte "RASTADOOM-STEP9",0,0
.segment "INIT"
    rts
.segment "VECTORS"
    .word start
    .byte 0,4
    .word $bff0
