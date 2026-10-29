#include "pico/audio_i2s.h"
#include "pico/time.h"
#include "rd.h"
#include <stdio.h>
#include <string.h>
static int16_t mix[256*2];
static mem_buffer_t memory={(uint8_t *)mix,sizeof mix};
static audio_buffer_t buffer;
static audio_buffer_pool_t pool;
static uint64_t due;
static bool enabled;
uint8_t rd_pcm[2048];
volatile unsigned rd_pcm_read,rd_pcm_write;
audio_buffer_pool_t *audio_new_producer_pool(audio_buffer_format_t *f,int n,int count) {
    pool.format=f->format; buffer.buffer=&memory;buffer.format=f;buffer.max_sample_count=256;
    due=time_us_64();return &pool;
}
audio_buffer_t *take_audio_buffer(audio_buffer_pool_t *p,bool block) {
    if(!enabled || time_us_64()<due) return NULL;
    memset(mix,0,sizeof mix);return &buffer;
}
void give_audio_buffer(audio_buffer_pool_t *p,audio_buffer_t *b) {
    rd_audio_samples((int16_t *)b->buffer->bytes,b->sample_count);
    due+=b->sample_count*1000000ull/p->format->sample_freq;
    if(due+100000<time_us_64()) due=time_us_64();
}
const audio_format_t *audio_i2s_setup(const audio_format_t *f,const struct audio_i2s_config *c) { return f; }
bool audio_i2s_connect_extra(audio_buffer_pool_t *p,bool a,int b,int c,void *d) { return true; }
void audio_i2s_set_enabled(bool e) { enabled=e; }
void rd_audio_samples(const int16_t *stereo,unsigned count) {
    static unsigned phase;
    static int sum,n;
    for(unsigned i=0;i<count;i++) {
        sum+=(stereo[i*2]+stereo[i*2+1])/2;n++;phase+=(rd_mailbox[3]==1?7778:7850);
        if(phase>=49716) {
            phase-=49716;
            int sample=8+sum/n/2048; if(sample<0)sample=0;if(sample>15)sample=15;
            unsigned w=rd_pcm_write;
            if(w-rd_pcm_read<sizeof rd_pcm) {rd_pcm[w&(sizeof rd_pcm-1)]=0x10|sample;rd_pcm_write=w+1;}
            sum=n=0;
        }
    }
}
void rd_audio_poll(void) { extern void I_UpdateSound(void);I_UpdateSound(); }
