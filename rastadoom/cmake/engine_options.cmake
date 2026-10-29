add_library(small_doom_common INTERFACE)

#target_link_libraries(small_doom_common INTERFACE adpcm-lib) # handy to have about

target_compile_definitions(small_doom_common INTERFACE
        SHRINK_MOBJ=1 # may break saved games

        DOOM_ONLY=1 # don't support hexxen etc.
        DOOM_SMALL=1
        DOOM_CONST=1 # thread const thru lots of places

        SOUND_LOW_PASS=1
        NUM_SOUND_CHANNELS=8 # sounds ok (actually that is how many are used by default)

        # functionality
        NO_USE_CHECKSUM=1
        NO_USE_RELOAD=1
        USE_SINGLE_IWAD=1
        NO_USE_WIPE=1 #memory if nothing else - we can fix this (you can do it)
        NO_USE_JOYSTICK=1
        NO_USE_DEH=1
        NO_USE_MUSIC_PACKS=1

        USE_FLAT_MAX_256=1
        USE_MEMMAP_ONLY=1

        USE_LIGHTMAP_INDEXES=1 # saves about 9K

        #FRACBITS=15 # ha ha doesn't seem to be passed thru everywhere!
        #NO_USE_ENDDOOM=1
        #NO_DRAW_VISPLANES=1

        USE_ERASE_FRAME=1 #
        NO_DRAW_MID=1
        NO_DRAW_TOP=1
        NO_DRAW_BOTTOM=1
        NO_DRAW_MASKED=1
        NO_DRAW_SKY=1
        #NO_DRAW_SPANS=1
        NO_DRAW_SPRITES=1
        NO_DRAW_PSPRITES=1

#        NO_VISPLANES=1
        NO_VISPLANE_GUTS=1
        NO_VISPLANE_CACHES=1 # todo these might be fine as they can be temporary
        NO_DRAWSEGS=1
        NO_VISSPRITES=1


        NO_MASKED_FLOOR_CLIP=1 # not needed with PD_ rendering and with floor clip it we have occasional visual glitches with sprites split across visplanes

        PD_DRAW_COLUMNS=1
        PD_DRAW_MARKERS=1
        PD_DRAW_PLANES=1

        PD_SCALE_SORT=1

        PD_CLIP_WALLS=1
        PD_QUANTIZE=1

        PD_SANITY=1

        #MU_STATS=1
        PD_COLUMNS=1
        PICO_DOOM=1
        NO_USE_DS_COLORMAP=1
        NO_USE_DC_COLORMAP=1

        #PRINT_COLORMAPS=1
        #PRINT_PALETTE=1
        USE_READONLY_MMAP=1

# -----------------------------------------------------------------
# MUSIC RELATED
# -----------------------------------------------------------------
        NO_USE_TIMIDITY=1
        NO_USE_GUS=1
        NO_USE_LIBSAMPLERATE=1

        # slightly slower but only uses 1K of sin tables vs 9K
        EMU8950_NO_WAVE_TABLE_MAP=1

        EMU8950_NO_TLL=1 # don't use lookup table for total level
        EMU8950_NO_FLOAT=1 # double check there is no float
        EMU8950_NO_TIMER=1 # disable timer which isn't used
        EMU8950_NO_TEST_FLAG=1 # disable test flags (which aren't used)
        EMU8950_SIMPLER_NOISE=1 # only generate noise bit when needed
        EMU8950_SHORT_NOISE_UPDATE_CHECK=1 # only update short noise if it is used
        # actually this doesn't make things faster
        #EMU8950_LINEAR_NEG_NOT_NOT=1 # negative values rounded towrds -infinity not 0 without this; does it matter?

        EMU8950_LINEAR_SKIP=1 # skip silent slots
        EMU8950_LINEAR_END_OF_NOTE_OPTIMIZATION # early out envelope when DECAY/SUSTAIN/RELEASE envelope reaches mute
        EMU8950_NO_PERCUSSION_MODE=1 # rhythm only mode (doom doesn't use percussion; whhhaaaah!?)
        EMU8950_LINEAR=1 # reorganize to do linear runs of channels

        # things we really don't care about but need for diff-ing with non linear version
        # BEWARE - need to turn this off for comparison with on device version which doesn't do nitpicks (though could i guess)

        EMU8950_ASM=1
#        EMU8950_NIT_PICKS=1
#        DUMPO=1

# -----------------------------------------------------------------
# FLASH SIZE
# -----------------------------------------------------------------
        NO_USE_STATE_MISC #doesn't appear to be used anyway - perhaps in doom only

# -----------------------------------------------------------------
# RAM SIZE
# -----------------------------------------------------------------
        USE_RAW_MAPNODE=1
        USE_RAW_MAPVERTEX=1
        USE_RAW_MAPSEG=1
        USE_RAW_MAPLINEDEF=1
        # USE_RAW_MAPSUBSECTOR=1 # obsolete... now WHD
        # USE_RAW_MAPSIDEDEF=1 obsolete
        USE_RAW_MAPTHING=1

        USE_INDEX_LINEBUFFER=1
        NO_USE_ZLIGHT=1
        NO_Z_ZONE_ID=1 # seems unused

        Z_MALOOC_EXTRA_DATA=1
        USE_THINKER_POOL=1
        NO_INTERCEPTS_OVERRUN=1
#        INCLUDE_SOUND_C_IN_S_SOUND=1 # avoid issues with non static const array
# -----------------------------------------------------------------
# IMMUTABLE
# -----------------------------------------------------------------

        TEMP_IMMUTABLE_DISABLED=1
        USE_CONST_SFX=1
        USE_CONST_MUSIC=1

        NO_DEMO_RECORDING=1
        PICO_NO_TIMING_DEMO=1
        NO_USE_EXIT=1 # not sure whether we have an exit... if so what does it need to do?

        PICO_DEBUG_PIN_BASE=18
        PICO_DEBUG_PIN_COUNT=2
)

target_compile_options(small_doom_common INTERFACE
        -Wall
        -Wno-unused-function
        -Wno-unused-but-set-variable
        -Wno-unused-variable
        )

