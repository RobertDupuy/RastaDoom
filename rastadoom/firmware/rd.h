#pragma once
#include <stdint.h>
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
void rd_cart_init(void);
void rd_present(const uint8_t *pixels, const uint8_t *palette);
void rd_input_poll(void);
void rd_audio_samples(const int16_t *stereo, unsigned count);
void rd_audio_poll(void);
void rd_fault(const char *message);
void rd_video_present(void);
extern volatile uint8_t rd_mailbox[256];
#if RD_FACTORY_PACKAGE
extern volatile uint8_t rd_input_valid;
#endif
enum { RD_DIAG_MAGIC=0xf0, RD_DIAG_STAGE=0xf2, RD_DIAG_PRODUCED=0xf3,
       RD_DIAG_CONSUMED=0xf4, RD_DIAG_ERROR=0xa0 };
enum { RD_STAGE_RUNTIME=1, RD_STAGE_GRAPHICS=2, RD_STAGE_ENCODE=3,
       RD_STAGE_READY=4, RD_STAGE_WAIT=5, RD_STAGE_ERROR=0xee };
#if !PICO_ON_DEVICE
void rd_host_init(int argc, char **argv);
void rd_host_frame(const uint8_t *pixels, const uint8_t *palette);
#endif
#ifdef __cplusplus
}
#endif
