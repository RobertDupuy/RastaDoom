; GPL-2.0-or-later. Ordinary 128K MegaCart playback of recorded engine windows.
; ANTIC bitmap reads and raster instructions execute directly from cartridge.
.setcpu "6502"
STEP = $80
BANK = $81
HOLD = $82
LOOPS = $83
RENDERS = $84
PTR = $86
.segment "START"
.export client_start, frame_end, sync_raster, stop
client_start:
    lda #0
    sta LOOPS
    sta RENDERS
    sta RENDERS+1
    lda #2
    jsr checkpoint
    lda #3
    jsr checkpoint
    lda #1
    sta BANK
    jsr select_bank
    lda #4
    jsr checkpoint
    lda #0
    ldx #0
clear_pmg:
    sta $3000,x
    sta $3100,x
    sta $3200,x
    sta $3300,x
    inx
    bne clear_pmg
    jsr copy_pmg
    lda #3
    sta $d008
    sta $d009
    sta $d00a
    sta $d00b
    lda #$30
    sta $d407
    lda #$48
    sta $d000
    lda #$68
    sta $d001
    lda #$88
    sta $d002
    lda #$a8
    sta $d003
    lda #5
    jsr checkpoint
    ldx #39
copy_wait_footer:
    lda wait_footer,x
    sta $2900,x
    dex
    bpl copy_wait_footer
    lda #24
    sta HOLD
sync_raster:
    lda $d40b
    cmp #2
    bne sync_raster
    lda #$14
    sta $d01b
    lda #$2e
    sta $d400
    lda #<game_list
    sta $d402
    lda #>game_list
    sta $d403
    lda #2
    sta $d01d
    sta $d40a
    sta $d40a
    sta $d40a
    jmp $9e10
.segment "FRAME_END"
; This is the exact return address emitted by the live engine's raster.c.
frame_end:
    jmp after_frame
.segment "CODE"
after_frame:
    ; STEP 6 is written only after the actual cartridge kernel returns.
    lda STEP
    cmp #6
    beq already_returned
    lda #6
    sta STEP
    ldx #39
copy_return_footer:
    lda footer,x
    sta $2900,x
    dex
    bpl copy_return_footer
already_returned:
    inc RENDERS
    bne count_done
    inc RENDERS+1
count_done:
    lda #0
    sta $d01d
    sta $d01b
    sta $d018
    lda #$0e
    sta $d017
    lda BANK
    clc
    adc #'0'
    sta $290f
    lda LOOPS
    lsr
    lsr
    lsr
    lsr
    tax
    lda hex,x
    sta $2918
    lda LOOPS
    and #15
    tax
    lda hex,x
    sta $2919
    dec HOLD
    bne next_video_frame
    lda #24
    sta HOLD
    inc BANK
    lda BANK
    cmp #8
    bne next_bank
    lda #1
    sta BANK
    inc LOOPS
next_bank:
    jsr select_bank
    jsr copy_pmg
next_video_frame:
    jmp sync_raster
select_bank:
    lda BANK
    sta $d500
    cmp $bfe4
    bne bank_error
    lda $bfe0
    cmp #'M'
    bne bank_error
    rts
bank_error:
    lda #0
    sta $d400
    sta $d01d
    ldx #39
copy_error:
    lda error_text,x
    sta $2928,x
    dex
    bpl copy_error
    jsr text_mode
stop:
    jmp stop
copy_pmg:
    ldx #95
pmg_loop:
    lda $be00,x
    sta $3204,x
    lda $be60,x
    sta $3284,x
    lda $bec0,x
    sta $3304,x
    lda $bf20,x
    sta $3384,x
    dex
    bpl pmg_loop
    rts
checkpoint:
    sta STEP
    sec
    sbc #2
    tax
    lda message_lo,x
    sta PTR
    lda message_hi,x
    sta PTR+1
    ldy #39
copy_message:
    lda (PTR),y
    sta $2900,y
    dey
    bpl copy_message
    lda #' '
    ldx #119
clear_status:
    sta $2928,x
    dex
    bpl clear_status
    jsr text_mode
    jmp pause_three
text_mode:
    lda #0
    sta $d01b
    sta $d01d
    sta $d01a
    sta $d018
    lda #$0e
    sta $d017
    lda #$2c
    sta $d409
    lda #<text_list
    sta $d402
    lda #>text_list
    sta $d403
    lda #$22
    sta $d400
    rts
.include "wait.inc"
.segment "TEXT_LIST"
text_list:
    .byte $70,$70,$70,$42
    .word $2900
    .byte $02,$02,$02,$41
    .word text_list
.segment "GAME_LIST"
game_list:
    .include "game_list.inc"
    .byte $70,$42
    .word $2900
    .byte $41
    .word game_list
.segment "SILENCE"
    .byte $18
.segment "SCREEN"
    .res 160,$20
.segment "MESSAGES"
    .include "movie_messages.inc"
hex: .byte "0123456789ABCDEF"
.segment "FONT"
    .incbin "font.bin"
