/* GPL-2.0-or-later. Standard A8PicoCart GPIO bus, one RP2040. */
#include "rd.h"
#include "raster.h"
#include "client_rom.h"
#include "pico/stdlib.h"
#include <stdio.h>
#include <string.h>
#if PICO_ON_DEVICE
#include "pico/multicore.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"
#include "hardware/structs/sio.h"
#endif
uint8_t __aligned(4) rd_windows[2][RD_WINDOW];
volatile unsigned rd_display,rd_pending=2;
volatile uint8_t rd_mailbox[256];
#if RD_FACTORY_PACKAGE
volatile uint8_t rd_input_valid;
#endif
extern uint8_t rd_pcm[2048];
extern volatile unsigned rd_pcm_read,rd_pcm_write;
int __not_in_flash_func(rd_cart_flip)(void) {
    unsigned p=rd_pending;
    if(p<2) {
        __compiler_memory_barrier();rd_display=p;
        __compiler_memory_barrier();rd_pending=2;
        rd_mailbox[0xfd]=0;rd_mailbox[RD_DIAG_CONSUMED]++;return 1;
    }
    return 0;
}
uint8_t __not_in_flash_func(rd_cart_read)(unsigned address) {
    unsigned a=address&255;
    if(a==0xfd)return rd_pending<2;
    if(a==0x80) {
        unsigned r=rd_pcm_read;
        if(r!=rd_pcm_write) {uint8_t v=rd_pcm[r&2047];rd_pcm_read=r+1;return v;}
        return 0x18;
    }
    return rd_mailbox[a];
}
void __not_in_flash_func(rd_cart_write)(unsigned address,uint8_t value) {
    unsigned a=address&255;
    if(a==0xfe && value==0xa5) {rd_cart_flip();return;}
    rd_mailbox[a]=value;
#if RD_FACTORY_PACKAGE
    if(a==0)rd_input_valid=1;
#endif
}
#if PICO_ON_DEVICE
#define DATA 0x001fe000u
#define PHI2 0x00400000u
#define CCTL 0x00200000u
#define RW   0x00800000u
#define S4   0x01000000u
#define S5   0x02000000u
static void __attribute__((optimize("O3"))) __not_in_flash_func(bus_loop)(void) {
    save_and_disable_interrupts();
    for(;;) {
        uint32_t pins;
        pins=sio_hw->gpio_in;
        /* ANTIC can change the address while S4/S5 remains asserted, even
         * with PHI2 low. Follow the original A8PicoCart 16K ROM handler. */
        if((pins&(S4|S5))!=(S4|S5)) {
            const uint8_t *window=rd_windows[rd_display];
            sio_hw->gpio_oe_set=DATA;
            if(!(pins&S4)) {
                do {
                    gpio_put_masked(DATA,(uint32_t)window[pins&8191]<<13);
                    pins=sio_hw->gpio_in;
                } while(!(pins&S4));
            } else {
                do {
                    gpio_put_masked(DATA,(uint32_t)window[8192|(pins&8191)]<<13);
                    pins=sio_hw->gpio_in;
                } while(!(pins&S5));
            }
            sio_hw->gpio_oe_clr=DATA;
        } else if((pins&PHI2) && !(pins&CCTL)) {
            unsigned address=pins&255;
            if(pins&RW) {
                /* Same direct SRAM mailbox read as the working cartridge
                 * command handler. Process FIFO bookkeeping after the bus
                 * cycle instead of spending the response time in a call. */
                uint32_t value=rd_mailbox[address];
                gpio_put_masked(DATA,value<<13);sio_hw->gpio_oe_set=DATA;
                while(sio_hw->gpio_in&PHI2) {}
                sio_hw->gpio_oe_clr=DATA;
                if(address==0x80)rd_mailbox[0x80]=rd_cart_read(0x80);
            } else {
                uint32_t last=pins;
                while((pins=sio_hw->gpio_in)&PHI2)last=pins;
                rd_cart_write(address,(last>>13)&255);
            }
        }
    }
}
#endif
void rd_cart_init(void) {
    memcpy(rd_windows[0],rd_boot_rom,RD_WINDOW);
    rd_mailbox[4]=0xff;
    rd_mailbox[0x80]=0x18;
    rd_mailbox[RD_DIAG_MAGIC]='R';rd_mailbox[RD_DIAG_MAGIC+1]='D';
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_RUNTIME;
#if RD_CHECKPOINT_CART
    rd_mailbox[0xf5]=5;
#endif
#if RD_FACTORY_PACKAGE
    rd_mailbox[0]=0x11; /* original loader's ready byte, until client input */
#endif
#if PICO_ON_DEVICE
    gpio_init_mask(0x0fffffffu);
    gpio_set_dir_in_masked(0x03ffffffu);
    gpio_put_masked(0x0c000000u,0x0c000000u);
    gpio_set_dir_out_masked(0x0c000000u);
    for(unsigned pin=0;pin<26;pin++)gpio_disable_pulls(pin);
    multicore_launch_core1(bus_loop);
#endif
}
void rd_present(const uint8_t *pixels,const uint8_t *palette) {
#if PICO_ON_DEVICE
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_WAIT;
    while(rd_pending<2) {extern void I_UpdateSound(void);I_UpdateSound();}
#elif !RD_ATARI_EMULATOR
    if(rd_pending<2)rd_cart_flip();
#endif
    unsigned back=rd_display^1;
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_ENCODE;
    rd_encode(rd_windows[back],pixels,palette,rd_mailbox[3]==1);
    rd_mailbox[RD_DIAG_PRODUCED]++;
    __compiler_memory_barrier();rd_pending=back;
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_READY;
    __compiler_memory_barrier();rd_mailbox[0xfd]=1;
#if !PICO_ON_DEVICE
    rd_host_frame(pixels,palette);
#endif
}
void rd_fault(const char *message) {
    const char *original=message;
    for(unsigned i=0;i<40;i++) {
        rd_mailbox[RD_DIAG_ERROR+i]=*message?*message++:' ';
    }
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_ERROR;
    rd_mailbox[255]=0xff;puts(original);
}
