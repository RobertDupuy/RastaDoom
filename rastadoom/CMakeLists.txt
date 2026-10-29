cmake_minimum_required(VERSION 3.20)
list(APPEND PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/firmware/boards)
include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)
set(SKIP_PICO_MALLOC 1)
project(RastaDoom VERSION 0.6.0 LANGUAGES C CXX ASM)
option(RD_FACTORY_PACKAGE "Load through the supplied factory's AUTORUN.BAT package" OFF)
option(RD_MENU_ATR "Launch from original menu through DOOM.ATR" OFF)
option(RD_CHECKPOINT_CART "Fixed CAR entry with acknowledged Pico handoff" OFF)
set(RD_WAD_ADDRESS "0x10400000" CACHE STRING "Physical address of the bundled WHX")
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 14)
pico_sdk_init()
set(ENGINE ${CMAKE_CURRENT_LIST_DIR}/../third_party/rp2040-doom)
add_executable(rastadoom firmware/platform.c firmware/video.c firmware/input.c
    firmware/audio_transport.c firmware/cart.c firmware/raster.c)
include(cmake/common_sources.cmake)
include(cmake/game_sources.cmake)
include(cmake/engine_options.cmake)
add_subdirectory(${ENGINE}/src/doom ${CMAKE_CURRENT_BINARY_DIR}/doom)
target_sources(rastadoom PRIVATE ${ENGINE}/src/pd_render.cpp
    ${ENGINE}/src/tiny_huff.c ${ENGINE}/src/image_decoder.c ${ENGINE}/src/musx_decoder.c
    ${ENGINE}/src/pico/i_picosound.c ${ENGINE}/src/pico/stubs.c
    ${ENGINE}/src/i_oplmusic.c ${ENGINE}/opl/opl_api.c ${ENGINE}/opl/emu8950.c
    ${ENGINE}/opl/slot_render.cpp ${ENGINE}/opl/opl_pico.c)
target_link_libraries(rastadoom PRIVATE doom small_doom_common pico_stdlib pico_multicore pico_util)
target_include_directories(rastadoom PRIVATE firmware ${ENGINE}/src
    ${ENGINE}/src/pico ${ENGINE}/opl ${ENGINE}/textscreen ${CMAKE_CURRENT_BINARY_DIR})
target_compile_options(rastadoom PRIVATE -fms-extensions -Wno-unused-function
    -Wno-unused-variable -Wno-unused-but-set-variable -Wno-format-truncation)
target_compile_definitions(rastadoom PRIVATE
    RASTADOOM=1 PICO_BUILD=1 DOOM_TINY=1 PICODOOM_RENDER_NEWHOPE=1 NO_RDRAW=1
    WHD_SUPER_TINY=1 DEMO1_ONLY=1 NO_USE_FINALE_CAST=1 NO_USE_FINALE_BUNNY=1
    MERGE_DISTSCALE0_INTO_VIEWCOSSINANGLE=1
    USE_MEMORY_WAD=1 USE_WHD=1 USE_MUSX=1 MUSX_COMPRESSED=1
    USE_DIRECT_MIDI_LUMP=1 USE_EMU8950_OPL=1 EMU8950_SLOT_RENDER=1 EMU8950_NO_RATECONV=1
    SAVE_COMPRESSED=1 LOAD_COMPRESSED=1
    NO_USE_NET=1 NO_USE_MOUSE=1 NO_USE_ARGS=1 NO_USE_SAVE_CONFIG=1
    NO_USE_FLOAT=1 NO_USE_BOUND_CONFIG=1 NO_USE_LOADING_DISK=1 NO_SCREENSHOT=1
    NO_USE_ENDOOM=1 NO_Z_MALLOC_USER_PTR=1 FIXED_SCREENWIDTH=1
    FLOOR_CEILING_CLIP_8BIT=1 USE_VANILLA_KEYBOARD_MAPPING_ONLY=1
    PICO_TIME_DEFAULT_ALARM_POOL_DISABLED=1 PICO_DISABLE_SHARED_IRQ_HANDLERS=1
    PICO_SCANVIDEO_SCANLINE_BUFFER_COUNT=1 PICO_AUDIO_I2S_DATA_PIN=0 PICO_AUDIO_I2S_CLOCK_PIN_BASE=0
    TINY_WAD_ADDR=${RD_WAD_ADDRESS} PICO_FLASH_SIZE_BYTES=16777216)
if(PICO_ON_DEVICE)
    if(NOT PICO_RP2040)
        message(FATAL_ERROR "RastaDoom targets the single RP2040 standard A8PicoCart")
    endif()
    target_compile_options(rastadoom PRIVATE -fstack-usage)
    target_sources(rastadoom PRIVATE ${ENGINE}/opl/slot_render_pico.S firmware/save_flash.c)
    if(RD_CHECKPOINT_CART)
        target_compile_definitions(rastadoom PRIVATE RD_CHECKPOINT_CART=1)
    endif()
    if(RD_FACTORY_PACKAGE OR RD_MENU_ATR OR RD_CHECKPOINT_CART)
        if(RD_FACTORY_PACKAGE)
        target_sources(rastadoom PRIVATE firmware/factory_launch.c firmware/factory_reboot.S)
        target_compile_definitions(rastadoom PRIVATE RD_FACTORY_PACKAGE=1)
        target_link_options(rastadoom PRIVATE -Wl,--undefined=rd_factory_launch)
        endif()
        file(READ ${PICO_SDK_PATH}/src/rp2_common/pico_crt0/rp2040/memmap_default.ld RD_LINKER)
        string(REPLACE "INCLUDE \"pico_flash_region.ld\""
            "FLASH(rx) : ORIGIN = 0x10080200, LENGTH = 0x7fc00" RD_LINKER "${RD_LINKER}")
        file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/factory_memmap.ld "${RD_LINKER}")
        pico_set_linker_script(rastadoom ${CMAKE_CURRENT_BINARY_DIR}/factory_memmap.ld)
    endif()
    target_link_libraries(rastadoom PRIVATE hardware_interp hardware_flash hardware_watchdog hardware_clocks)
    target_compile_definitions(rastadoom PRIVATE NO_FILE_ACCESS=1 USE_ZONE_FOR_MALLOC=1
        PICO_HEAP_SIZE=0 PICO_STACK_SIZE=0x1000 PICO_CORE1_STACK_SIZE=0x400)
    # SDK pico_wrap_function attaches INTERFACE options; this is the executable.
    target_link_options(rastadoom PRIVATE -Wl,--wrap=malloc,--wrap=calloc,--wrap=free)
    target_link_options(rastadoom PRIVATE "LINKER:-T,${CMAKE_CURRENT_LIST_DIR}/cmake/memory_checks.ld")
    set_property(TARGET rastadoom APPEND PROPERTY LINK_DEPENDS ${CMAKE_CURRENT_LIST_DIR}/cmake/memory_checks.ld)
    pico_enable_stdio_uart(rastadoom 0)
    pico_enable_stdio_usb(rastadoom 0)
    pico_set_float_implementation(rastadoom none)
    pico_set_double_implementation(rastadoom none)
    pico_add_extra_outputs(rastadoom)
else()
    find_package(SDL2 REQUIRED)
    target_link_libraries(rastadoom PRIVATE SDL2::SDL2)
    target_sources(rastadoom PRIVATE host/capture.c)
    if(ATARI800_PATH)
        target_sources(rastadoom PRIVATE host/ui.c)
        target_include_directories(rastadoom PRIVATE ${ATARI800_PATH}/src ${ATARI800_PATH}/src/libatari800)
        target_link_libraries(rastadoom PRIVATE ${ATARI800_PATH}/src/libatari800.a m pthread)
        target_compile_definitions(rastadoom PRIVATE RD_ATARI_EMULATOR=1 RD_BOOT_CART="${CMAKE_CURRENT_LIST_DIR}/atari/boot.car")
    endif()
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_LIST_DIR}/tools/embed_whx.py
        ${CMAKE_CURRENT_LIST_DIR}/assets/doom1.whx ${CMAKE_CURRENT_BINARY_DIR}/tiny.whd.h
        COMMAND_ERROR_IS_FATAL ANY)
endif()
