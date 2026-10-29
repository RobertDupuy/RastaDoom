/* Compatible producer API for upstream DOOM. Output is cartridge PCM, no I2S GPIO. */
#pragma once
#include "pico.h"
#ifdef __cplusplus
extern "C" {
#endif
#define AUDIO_BUFFER_FORMAT_PCM_S16 1
typedef struct { uint8_t *bytes; size_t size; } mem_buffer_t;
typedef struct audio_format { uint32_t sample_freq; uint16_t format,channel_count; } audio_format_t;
typedef struct audio_buffer_format { const audio_format_t *format; uint16_t sample_stride; } audio_buffer_format_t;
typedef struct audio_buffer { mem_buffer_t *buffer; const audio_buffer_format_t *format;
    uint32_t sample_count,max_sample_count,user_data; struct audio_buffer *next; } audio_buffer_t;
typedef struct audio_buffer_pool { const audio_format_t *format; } audio_buffer_pool_t;
struct audio_i2s_config { uint8_t data_pin,clock_pin_base,dma_channel,pio_sm; };
audio_buffer_pool_t *audio_new_producer_pool(audio_buffer_format_t *,int,int);
audio_buffer_t *take_audio_buffer(audio_buffer_pool_t *,bool);
void give_audio_buffer(audio_buffer_pool_t *,audio_buffer_t *);
const audio_format_t *audio_i2s_setup(const audio_format_t *,const struct audio_i2s_config *);
bool audio_i2s_connect_extra(audio_buffer_pool_t *,bool,int,int,void *);
void audio_i2s_set_enabled(bool);
#ifdef __cplusplus
}
#endif
