#pragma once
#include <stdint.h>
enum { RD_WIDTH=160, RD_HEIGHT=192, RD_WINDOW=16384, RD_BITMAP_BYTES=7696,
    RD_KERNEL=RD_BITMAP_BYTES, RD_PMG=0x3e00, RD_PMG_BYTES=384 };
void rd_encode(uint8_t *window,const uint8_t *doom,const uint8_t *rgb,int pal);
unsigned rd_bitmap_offset(unsigned y);
extern uint8_t rd_windows[2][RD_WINDOW];
extern volatile unsigned rd_display,rd_pending;
void rd_cart_write(unsigned address,uint8_t value);
uint8_t rd_cart_read(unsigned address);
int rd_cart_flip(void);
