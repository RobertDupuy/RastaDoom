/* RastaDoom platform, GPL-2.0-or-later. One RP2040, standard A8PicoCart. */
#include "pico/stdlib.h"
#include "pico/sem.h"
#include "rd.h"
#include "doomtype.h"
#include "i_system.h"
#include "i_timer.h"
#include "z_zone.h"
#include "m_argv.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if PICO_ON_DEVICE
#include "hardware/clocks.h"
#include "hardware/vreg.h"
#include "hardware/watchdog.h"
#endif

int8_t at_exit_screen;
uint8_t *exit_screen_kb_buffer_80;
void I_Init(void) {}
void I_AtExit(atexit_func_t f, boolean run_on_error) { (void) f; (void) run_on_error; }
byte *I_ZoneBase(int *size) {
#if PICO_ON_DEVICE
    extern char __end__;
    byte *base = (byte *)(((uintptr_t)&__end__ + 3) & ~3u);
    *size = (byte *)SRAM4_BASE - base;
#else
    *size = 512 * 1024;
    byte *base = malloc(*size);
#endif
    printf("DOOM zone: %d bytes\n", *size);
    return base;
}
void I_Error(const char *format, ...) {
    char message[180];
    va_list args; va_start(args, format);
    vsnprintf(message, sizeof message, format, args); va_end(args);
    rd_fault(message);
#if PICO_ON_DEVICE
    for (;;) tight_loop_contents();
#else
    fprintf(stderr, "DOOM ERROR: %s\n", message);
    exit(2);
#endif
}
void I_Quit(void) {
#if PICO_ON_DEVICE
    watchdog_reboot(0, 0, 10); for (;;) tight_loop_contents();
#else
    exit(0);
#endif
}
void *I_Realloc(void *p, size_t size) {
    void *r = realloc(p, size); if (!r && size) I_Error("realloc failed"); return r;
}
void I_PrintBanner(const char *s) { puts(s); }
void I_PrintDivider(void) { puts("----------------------------------------"); }
void I_PrintStartupBanner(const char *s) { puts(s); }
boolean I_ConsoleStdout(void) { return false; }
void I_Tactile(int on, int off, int total) {}
boolean I_GetMemoryValue(unsigned offset, void *value, int size) {
    static const uint8_t dos71[10] = {0x9e,0x0f,0xc9,0,0x65,4,0x70,0,0x16,0};
    if (offset + size > sizeof dos71) return false;
    memcpy(value, dos71 + offset, size); return true;
}
int I_GetTime(void) { return (uint32_t)(time_us_64() / 1000) * 35 / 1000; }
int I_GetTimeMS(void) { return (uint32_t)(time_us_64() / 1000); }
void I_Sleep(int ms) { if (ms > 0) sleep_ms(ms); }
void I_WaitVBL(int count) { I_Sleep(count * 1000 / 70); }
void I_InitTimer(void) {}
#if PICO_ON_DEVICE
void *__wrap_malloc(size_t n) { return Z_MallocNoUser(n, PU_STATIC); }
void *__wrap_calloc(size_t n, size_t s) { void *p = __wrap_malloc(n*s); memset(p, 0, n*s); return p; }
void __wrap_free(void *p) { if (p) Z_Free(p); }
#endif
extern void D_DoomMain(void);
int main(int argc, char **argv) {
#if PICO_ON_DEVICE
    vreg_set_voltage(VREG_VOLTAGE_1_30); busy_wait_us(1000);
    set_sys_clock_khz(250000, true);
#else
    rd_host_init(argc, argv);
#endif
    rd_cart_init();
#if RD_CHECKPOINT_CART
    /* STEP 4 stays visible before the Atari explicitly releases engine init. */
    while(rd_mailbox[0xf8]!=0xa5) tight_loop_contents();
#endif
    I_Init(); D_DoomMain(); return 0;
}

void rd_engine_initialized(void) { rd_mailbox[0xf6]=0xa5; }

void I_Endoom(byte *data) {}
#if !PICO_ON_DEVICE
void hard_assertion_failure(void) { I_Error("Engine assertion failed"); }
#endif
