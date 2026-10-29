/* GPL-2.0-or-later. Full DOOM drawing workspace; native Atari output follows. */
#include "pico/sem.h"
#include "doomtype.h"
#include "doom/doomdef.h"
#include "i_video.h"
#include "i_system.h"
#include "w_wad.h"
#include "z_zone.h"
#include "v_video.h"
#include "picodoom.h"
#include "rd.h"
#include "tables.h"
#include <string.h>
static uint8_t __aligned(4) workspace[SCREENWIDTH * SCREENHEIGHT];
uint8_t *frame_buffer[2] = {workspace, workspace};
pixel_t *I_VideoBuffer = workspace;
volatile uint8_t interp_in_use;
semaphore_t render_frame_ready, display_frame_freed;
boolean screenvisible = true, screensaver_mode;
isb_int8_t usegamma=1;
unsigned joywait;
uint8_t next_video_type, next_frame_index, next_overlay_index;
uint8_t *wipe_yoffsets;
volatile uint8_t wipe_min;
int16_t *wipe_yoffsets_raw;
uint32_t *wipe_linelookup;
static uint8_t current_palette[768];
static int palette_num;
void I_InitGraphics(void) {
    rd_mailbox[RD_DIAG_STAGE]=RD_STAGE_GRAPHICS;
    sem_init(&render_frame_ready, 0, 1);
    sem_init(&display_frame_freed, 1, 1);
    pd_init();
}
void I_SetPaletteNum(int n) { palette_num = n; }
void rd_video_present(void) {
    const uint8_t *pal = W_CacheLumpName("PLAYPAL", PU_STATIC);
    int len = W_LumpLength(W_GetNumForName("PLAYPAL"));
    int n = palette_num;
    if (len >= (n+1)*768) memcpy(current_palette, pal + n*768, 768);
    else {
        int mul=0, target[3]={0,0,0};
        if (n>0 && n<9) { mul=n*65536/9; target[0]=255; }
        else if (n<13 && n>=9) { mul=(n-8)*65536/8; target[0]=215;target[1]=186;target[2]=69; }
        else if (n>=13) { mul=65536/8; target[1]=255; }
        for (int i=0;i<768;i++) current_palette[i]=pal[i]+((target[i%3]-pal[i])*mul>>16);
    }
    if (usegamma) for (int i=0;i<768;i++) current_palette[i]=gammatable[usegamma-1][current_palette[i]];
    rd_present(workspace, current_palette);
}
void I_StartFrame(void) {}
void I_StartTic(void) { rd_input_poll(); }
void I_FinishUpdate(void) {}
void I_UpdateNoBlit(void) {}
void I_ShutdownGraphics(void) {}
void I_GraphicsCheckCommandLine(void) {}
void I_SetWindowTitle(const char *s) {}
void I_CheckIsScreensaver(void) {}
void I_SetGrabMouseCallback(grabmouse_callback_t f) {}
void I_DisplayFPSDots(boolean dots) {}
void I_BindVideoVariables(void) {}
void I_InitWindowTitle(void) {}
void I_InitWindowIcon(void) {}
