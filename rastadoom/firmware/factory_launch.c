/* GPL-2.0-or-later. A8R package preflight; no initialized C runtime is used.
 * The factory calls this on core 1, with core 0 still serving its RAM loader.
 * A watchdog SRAM boot resets both cores, then installs our own program.
 * Nothing in the factory's executable instruction stream is patched. */
#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(a))
extern const uint32_t rd_reboot_start[], rd_reboot_end[];

int rd_factory_launch(const uint32_t *api) {
    if (!api || api[0]!=1 || api[1]<0xa0) return 0;
    /* The bundle builder reserves these physical flash sectors in the FAT
     * volume. Reject a mismatched image before rebooting. */
    const volatile uint32_t *wad=(const volatile uint32_t *)TINY_WAD_ADDR;
    if (wad[0]!=0x58485749 || wad[3]!=1800344) return 0;
    volatile uint32_t *boot=(volatile uint32_t *)0x20040000;
    const uint32_t *source=(const uint32_t *)0x10080200;
    for (unsigned i=0;i<64;i++) boot[i]=source[i];
    volatile uint32_t *dest=(volatile uint32_t *)0x20040100;
    for (const uint32_t *p=rd_reboot_start;p<rd_reboot_end;p++) *dest++=*p;
    __asm volatile("dmb" ::: "memory");
    REG(0x40058000)=0;                 /* watchdog CTRL */
    REG(0x4005801c)=0xb007c0d3;        /* scratch 4: ROM boot-to-SRAM */
    REG(0x40058020)=0x20040101u ^ (0u-0xb007c0d3u);
    REG(0x40058024)=0x20042000;        /* scratch 6: stack */
    REG(0x40058028)=0x20040101;        /* scratch 7: trampoline */
    REG(0x40010008)=0x1fffc;           /* reset domains except oscillators */
    REG(0x40058000)=0x80000000;        /* immediate watchdog trigger */
    for (;;) __asm volatile("nop");
}
