/* GPL-2.0-or-later. Bounded native ANTIC E / GTIA player raster encoder.
 * Each output includes 2bpp playfield, PMG masks and executable palette code.
 * The four wide players sit behind PF0..PF2; bitmap value zero reveals them.
 * PMG masks have two-line resolution. Their colours still change every line.
 */
#include "raster.h"
#include "rd.h"
#include "client_rom.h"
#include "atari_palette.h"
#include <limits.h>
#include <string.h>
#include <assert.h>
static uint8_t nearest[256],last_rgb[768];
static int last_pal=-1;
unsigned rd_bitmap_offset(unsigned y) { return y*40+(y>=102?16:0); }
static void map_palette(const uint8_t *rgb,int pal) {
    if(pal==last_pal && !memcmp(rgb,last_rgb,768))return;
    last_pal=pal;memcpy(last_rgb,rgb,768);
    for(unsigned i=0;i<256;i++) {
        unsigned best=UINT_MAX;
        for(unsigned c=0;c<128;c++) {
            int dr=rgb[i*3]-rd_atari_rgb[pal][c][0];
            int dg=rgb[i*3+1]-rd_atari_rgb[pal][c][1];
            int db=rgb[i*3+2]-rd_atari_rgb[pal][c][2];
            unsigned e=2*dr*dr+3*dg*dg+db*db;
            if(e<best) {best=e;nearest[i]=c;}
        }
    }
}
typedef struct {
    uint8_t pixels[160],pf[3],pm[4],pf_index[128];
    uint16_t pf_error[128];
} row_t;
static void select_row(row_t *r,const uint8_t *source,const uint16_t dist[128][128]) {
    uint8_t hist[128]={0}, unique[128];
    int used=0;
    uint16_t error[128];
    for(int x=0;x<160;x++) {r->pixels[x]=nearest[source[x*2]];hist[r->pixels[x]]++;}
    for(int c=0;c<128;c++) if(hist[c]) {unique[used++]=c;error[c]=dist[c][0];}
    for(int k=0;k<3;k++) {
        // Evaluate the eight most valuable remaining colour candidates.
        uint8_t candidates[8];unsigned scores[8]={0};
        for(int n=0;n<used;n++) {
            int c=unique[n];
            unsigned score=hist[c]*error[c];
            for(int j=0;j<8;j++) if(score>scores[j]) {
                for(int t=7;t>j;t--) {scores[t]=scores[t-1];candidates[t]=candidates[t-1];}
                scores[j]=score;candidates[j]=c;break;
            }
        }
        unsigned bestgain=0;int best=0;
        for(int j=0;j<8 && scores[j];j++) {
            int candidate=candidates[j];unsigned gain=0;
            for(int n=0;n<used;n++) {int c=unique[n];
                if(dist[c][candidate]<error[c])gain+=hist[c]*(error[c]-dist[c][candidate]);}
            if(gain>bestgain) {bestgain=gain;best=candidate;}
        }
        r->pf[k]=best;
        for(int n=0;n<used;n++) {int c=unique[n];if(dist[c][best]<error[c])error[c]=dist[c][best];}
    }
    for(int n=0;n<used;n++) {
        int c=unique[n];unsigned e=UINT_MAX;
        for(int k=0;k<3;k++) if(dist[c][r->pf[k]]<e) {e=dist[c][r->pf[k]];r->pf_index[c]=k+1;}
        r->pf_error[c]=e;
    }
    for(int p=0;p<4;p++) {
        unsigned bestgain=0;int best=0;
        // Histogram weights preserve the exact strip error while avoiding
        // duplicate colour candidates and repeated pixel-distance lookups.
        memset(hist,0,sizeof hist);used=0;
        for(int x=24+p*32;x<56+p*32;x++) {
            int c=r->pixels[x];if(!hist[c]++)unique[used++]=c;
        }
        for(int i=0;i<used;i++) {
            int candidate=unique[i];unsigned gain=0;
            for(int j=0;j<used;j++) {
                int c=unique[j];unsigned before=error[c],after=dist[c][candidate];
                if(after<before)gain+=hist[c]*(before-after);
            }
            if(gain>bestgain) {bestgain=gain;best=candidate;}
        }
        r->pm[p]=best;
    }
}
static uint8_t *emit_register(uint8_t *d,uint8_t colour,uint8_t reg) {
    *d++=0xa9;*d++=colour*2;*d++=0x8d;*d++=reg;*d++=0xd0;return d;
}
void rd_encode(uint8_t *window,const uint8_t *doom,const uint8_t *rgb,int pal) {
    pal=!!pal;map_palette(rgb,pal);
    const uint16_t (*dist)[128]=rd_distance[pal];
    uint8_t *code=window+RD_KERNEL;
    *code++=0x8d;*code++=0x0a;*code++=0xd4; // First row starts at the same WSYNC phase as all others.
    row_t rows[2];
    memset(window+RD_PMG,0,RD_PMG_BYTES);
    for(int y=0;y<RD_HEIGHT;y+=2) {
        if(!(y&7))rd_audio_poll();
        for(int i=0;i<2;i++) select_row(&rows[i],doom+((y+i)*200/192)*320,dist);
        uint8_t mask[4]={0};
        for(int p=0;p<4;p++) for(int bit=0;bit<8;bit++) {
            unsigned on=0,off=0;
            for(int i=0;i<2;i++)for(int x=24+p*32+bit*4;x<28+p*32+bit*4;x++) {
                int c=rows[i].pixels[x];unsigned pf=rows[i].pf_error[c];
                unsigned pm=dist[c][rows[i].pm[p]],bg=dist[c][0];
                on+=pf<pm?pf:pm;off+=pf<bg?pf:bg;
            }
            if(on<off)mask[p]|=0x80>>bit;
        }
        for(int p=0;p<4;p++) window[RD_PMG+p*96+y/2]=mask[p];
        for(int i=0;i<2;i++) {
            row_t *r=rows+i;
            uint8_t *bitmap=window+rd_bitmap_offset(y+i);memset(bitmap,0,40);
            for(int x=0;x<160;x++) {
                int c=r->pixels[x],under=0;
                if(x>=24 && x<152) {int p=(x-24)/32,bit=((x-24)%32)/4;
                    if(mask[p]&(0x80>>bit))under=r->pm[p];}
                int v=dist[c][under]<=r->pf_error[c]?0:r->pf_index[c];
                bitmap[x/4]|=v<<(6-(x&3)*2);
            }
            for(int k=0;k<3;k++)code=emit_register(code,r->pf[k],0x16+k);
            for(int p=0;p<4;p++)code=emit_register(code,r->pm[p],0x12+p);
            if(((y+i)&1)==1) { *code++=0xad;*code++=0x80;*code++=0xd5;
                *code++=0x8d;*code++=0x07;*code++=0xd2; }
            *code++=0x8d;*code++=0x0a;*code++=0xd4;
        }
    }
    *code++=0x4c;*code++=RD_CLIENT_FRAME_END&255;*code++=RD_CLIENT_FRAME_END>>8;
    assert(code<window+RD_PMG);
#if RD_CHECKPOINT_CART
    memcpy(window+0x3fe0,"RD5F",4);
#endif
    // Keep the cartridge signature and RESET entry valid after every flip.
    // The initial ROM installs the client in RAM; warm RESET re-enters it.
    window[0x3fc0]=0x78;window[0x3fc1]=0x4c;window[0x3fc2]=0;window[0x3fc3]=0x20;
    window[0x3ff0]=0x60;
    static const uint8_t vectors[6]={0xc0,0xbf,0,4,0xf0,0xbf};
    memcpy(window+0x3ffa,vectors,sizeof vectors);
}
