#include "hardware/flash.h"
#include "hardware/sync.h"
#include "pico.h"
/* Core 1's complete bus service and displayed cartridge bytes live in SRAM. */
void __not_in_flash_func(picoflash_sector_program)(uint32_t offset,const uint8_t *data) {
    uint32_t state=save_and_disable_interrupts();
    flash_range_erase(offset,4096);
    flash_range_program(offset,data,4096);
    restore_interrupts(state);
}
