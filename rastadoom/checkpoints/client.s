.setcpu "6502"
CURRENT = $80
EXPECT = $81
FRAMES = $82
SECONDS = $83
PTR = $84
ERRPTR = $86
.segment "CODE"
.export client_start, frame_end, hold, launch_request, enter_raster
client_start:
    lda #2
    jsr checkpoint
    lda #3
    jsr checkpoint
    lda #<err_link
    ldx #>err_link
    jsr begin_wait
launch_request:
    lda #$d6
    sta $d5df
wait_link:
    lda $d5f0
    cmp #'R'
    bne link_retry
    lda $d5f1
    cmp #'D'
    bne link_retry
    lda $d5f5
    cmp #5
    beq got_link
link_retry:
    jsr poll_tick
    jmp wait_link
got_link:
    lda #4
    jsr checkpoint
    lda $d014
    and #$0f
    sta $d503
    lda #$ff
    sta $d504
    lda #<err_init
    ldx #>err_init
    jsr begin_wait
    lda #$a5
    sta $d5f8
wait_init:
    lda $d5f6
    cmp #$a5
    beq got_init
    jsr engine_tick
    jmp wait_init
got_init:
    lda #5
    jsr checkpoint
    lda #<err_frame
    ldx #>err_frame
    jsr begin_wait
wait_frame_ready:
    lda $d5fd
    cmp #1
    beq got_frame
    jsr engine_tick
    jmp wait_frame_ready
got_frame:
    lda #6
    jsr checkpoint
    lda $d5f4
    clc
    adc #1
    sta EXPECT
    lda #<err_select
    ldx #>err_select
    jsr begin_wait
    lda #$a5
    sta $d5fe
wait_selected:
    lda $d5f4
    cmp EXPECT
    bne select_retry
    lda $bfe0
    cmp #'R'
    bne select_retry
    lda $bfe1
    cmp #'D'
    bne select_retry
    lda $bfe2
    cmp #'5'
    bne select_retry
    lda $bfe3
    cmp #'F'
    beq got_selected
select_retry:
    jsr engine_tick
    jmp wait_selected
got_selected:
    lda #7
    jsr checkpoint
    ; Actual PMG setup and transfer, while the RAM text screen stays visible.
    lda #0
    ldx #0
clear_pmg:
    sta $3000,x
    sta $3100,x
    sta $3200,x
    sta $3300,x
    inx
    bne clear_pmg
    ldx #95
copy_pmg:
    lda $be00,x
    sta $3204,x
    lda $be60,x
    sta $3284,x
    lda $bec0,x
    sta $3304,x
    lda $bf20,x
    sta $3384,x
    dex
    bpl copy_pmg
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
    lda #8
    jsr checkpoint
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
enter_raster:
    jmp $9e10
frame_end:
    ; This address is emitted as the renderer's final JMP.
    lda #0
    sta $d400
    sta $d01d
    sta $d01b
    sta $d207
    jsr wait_frame
    lda #9
    jsr checkpoint
hold:
    jmp hold

checkpoint:
    sta CURRENT
    tax
    dex
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
    jmp pause_three

begin_wait:
    sta ERRPTR
    stx ERRPTR+1
    lda #30
    sta SECONDS
reset_frames:
    lda #60
    ldx $d014
    cpx #1
    bne set_frames
    lda #50
set_frames:
    sta FRAMES
    rts
engine_tick:
    lda $d5f2
    cmp #$ee
    bne poll_tick
    ldx #39
copy_engine_error:
    lda $d5a0,x
    and #$7f
    sta $2950,x
    dex
    bpl copy_engine_error
    jmp show_error
poll_tick:
    jsr wait_frame
    dec FRAMES
    bne tick_done
    dec SECONDS
    beq show_error
    jsr reset_frames
tick_done:
    rts
show_error:
    ldy #39
error_copy:
    lda (ERRPTR),y
    sta $2928,y
    dey
    bpl error_copy
    jmp hold
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
    .byte $41
    .word game_list
.segment "SCREEN"
    .res 160,$20
.segment "MESSAGES"
    .include "messages.inc"
.segment "ERROR_MESSAGES"
    .include "errors.inc"
.segment "FONT"
    .incbin "font.bin"
