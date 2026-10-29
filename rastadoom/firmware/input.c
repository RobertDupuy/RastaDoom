/* GPL-2.0-or-later. All controls originate on the Atari, via the CCTL mailbox. */
#include "doomtype.h"
#include "d_event.h"
#include "doomkeys.h"
#include "doom/m_menu.h"
#include "doom/doomstat.h"
#include "rd.h"
#include "i_input.h"
#include <string.h>
int usemouse,novert;
static bool text_input;
void I_StartTextInput(int a,int b,int c,int d) { text_input=true; }
void I_StopTextInput(void) { text_input=false; }
void I_BindInputVariables(void) {}
void I_ReadMouse(void) {}
void I_GetEvent(void) { rd_input_poll(); }
static int keyboard(unsigned scan) {
    static const uint8_t ascii[64]={
        'l','j',';',0,0,'k','+','*','o',0,'p','u',KEY_ENTER,'i','-','=',
        'v',KEY_F1,'c',0,0,'b','x','z','4',0,'3','6',KEY_ESCAPE,'5','2','1',
        ',', ' ','.','n',0,'m','/',0,'r',0,'e','y',KEY_TAB,'t','w','q',
        '9',0,'0','7',KEY_BACKSPACE,'8','<','>','f','h','d',0,0,'g','s','a'};
    if(scan==255)return 0;
    switch(scan) {
        case 0x86:return KEY_LEFTARROW;case 0x87:return KEY_RIGHTARROW;
        case 0x8e:return KEY_UPARROW;case 0x8f:return KEY_DOWNARROW;
        case 0xbe:return KEY_F2; // Ctrl-S: save menu
        case 0xbd:return KEY_F11; // Ctrl-G: TV brightness
        case 0x80:return KEY_F3; // Ctrl-L: load menu
    }
    int key=ascii[scan&63];
    return key;
}
void rd_input_poll(void) {
    static uint8_t old[256];uint8_t now[256]={0};
    unsigned bits=rd_mailbox[0]|(rd_mailbox[1]<<8);
#if RD_FACTORY_PACKAGE
    /* D500 holds the factory loader's ready byte until the first actual
     * joystick write. That byte must not become UP+FIRE in DOOM. */
    if(!rd_input_valid)bits&=~255u;
#endif
    static const uint8_t keys[12]={KEY_UPARROW,KEY_DOWNARROW,KEY_LEFTARROW,KEY_RIGHTARROW,
        KEY_RCTRL,' ',KEY_RALT,KEY_RSHIFT,KEY_ESCAPE,KEY_ENTER,KEY_TAB,KEY_PAUSE};
    for(int i=0;i<12;i++)if(bits&(1u<<i))now[keys[i]]=1;
    int key=keyboard(rd_mailbox[4]);if(key)now[key]=1;
    // Keep the typed key as well, so Doom's original cheat responder works.
    if(!menuactive && !text_input) {
        switch(key) {
            case 'w':now[KEY_UPARROW]=1;break;case 's':now[KEY_DOWNARROW]=1;break;
            case 'a':now[KEY_LEFTARROW]=1;break;case 'd':now[KEY_RIGHTARROW]=1;break;
            case 'q':now[',']=1;break;case 'e':now['.']=1;break;
            case 'p':now[KEY_PAUSE]=1;break;
        }
    }
    for(int k=1;k<256;k++)if(now[k]!=old[k]) {
        event_t e={0};e.type=now[k]?ev_keydown:ev_keyup;e.data1=k;
        if(k>=32 && k<127) {e.data2=k;e.data3=(rd_mailbox[4]&64) && k>='a' && k<='z'?k-32:k;}
        D_PostEvent(&e);
    }
    memcpy(old,now,sizeof old);
}
