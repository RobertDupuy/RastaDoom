A8PicoCart DOOM 0.6.0
Regular A8PicoCart: one RP2040 with 16 MB flash; Atari 800XL, 64 KB.

INSTALL

Back up any files and saves you want to keep on the cartridge before flashing.
This UF2 includes a replacement cartridge filesystem.

1. With the cartridge disconnected from the Atari, enter the RP2040's BOOTSEL
   USB mode. Copy A8PicoCart-DOOM-0.6.0.uf2 onto the RPI-RP2 drive.
2. When flashing finishes, disconnect USB. Insert the cartridge with the
   Atari powered off, then power on.
3. Select DOOM.CAR from the usual A8PicoCart menu.

The UF2 already contains DOOM.CAR, the DOOM engine and shareware Episode 1
game data. There is no separate CAR or data-copy step after flashing.

START AND PLAY

Press and release joystick fire to open the menu. Press and release it again
to choose New Game, then the episode, then the difficulty. Joystick up/down
chooses menu items. Each fire press makes one selection; holding it does not
skip through the menus.

During play, fire shoots. Joystick up/down walks forward/backward, and
left/right turns. OPTION or Space opens doors/uses switches. SELECT or Escape
opens/closes the menu; START or Return still confirms choices. Hold Shift to
run. WASD also moves/turns; Q/E strafes; number keys select available weapons.

CHANGES FROM 0.5.1

- Joystick fire confirms menu selections, including the New Game sequence.
- STEP 1-9 screens and their three-second pauses are removed.
- The same startup acknowledgements and complete-frame checks remain internal.
- A failure-only message can still appear if the engine stops or times out.
- The normal cartridge launcher, Pico handoff, raster renderer and controls
  retain the working architecture. This is not a Duo build.

VERIFICATION AND LIMITS

Native Linux AltirraSDL with XL OS 1.3 (BB000001 revision 3, CRC32 29f133f7),
800XL/64 KB, BASIC off and OS acceleration patches off. The delivered CAR
runs unchanged while an RP2040 instruction model executes the delivered
engine. Completed native frame windows are fed through a cartridge protocol
adapter to the Atari's ANTIC/GTIA and CPU.

The checks in checks/release cover fire-only game start, held-fire menu
behaviour, gameplay movement and firing, input release, matching frame/PMG
data and failure-only timeout reporting. NTSC and PAL results are separate.
The original firmware's actual directory, CAR loading and launch routines
also run against the packaged flash image, and the compiled cartridge bus
loop is checked separately.

This is functional emulation, not a physical cartridge test, simultaneous
dual-core timing test or hardware FPS benchmark. Audio was not exercised by
the adapter; the existing audio implementation is unchanged. This 0.6.0 UF2
still needs a physical Atari test.

SOURCE AND REBUILD

The source package includes the UF2, DOOM.CAR, source and licenses, original
firmware input, game-data provenance, build metadata and test evidence.

Prerequisites: Python 3, ca65/ld65, CMake, Ninja, arm-none-eabi GCC/binutils,
and Pico SDK at commit bddd20f928ce76142793bef434d4f75f4af6e433 with submodules.

From the extracted source-package root:

  PICO_SDK_PATH=/path/to/pico-sdk bash rastadoom/release/build.sh

Outputs: dist/0.6.0/A8PicoCart-DOOM-0.6.0.uf2 and dist/0.6.0/DOOM.CAR.
The firmware builder uses inputs/Robin-original.uf2 and verifies its hash.

Functional test prerequisites: native AltirraSDL bridge, the XL OS 1.3 ROM,
a built rp2040js checkout and Node supporting native TypeScript imports.

  RP2040JS_ROOT=/path/to/rp2040js node rastadoom/release/test_firmware.mjs
  RP2040JS_ROOT=/path/to/rp2040js node rastadoom/tests/cart_bus.mts \
    build-release/engine/rastadoom.elf
  RP2040JS_ROOT=/path/to/rp2040js python3 rastadoom/release/check_release.py \
    /path/to/AltirraBridge /path/to/XL-OS-1.3.rom dist/0.6.0/DOOM.CAR \
    build-release/engine/rastadoom.elf rastadoom/assets/doom1.whx test-ntsc

Use a separate output directory and add --tv pal for the PAL check. The OS
ROM, SDK and emulator installations are external dependencies, not bundled.

CREDITS

DOOM: id Software. RP2040 engine: the upstream rp2040-doom contributors.
A8PicoCart firmware and hardware: Robin Edwards. Atari adaptation, generated
raster renderer and this release's integration: OpenAI Codex. All upstream
notices, licenses and game-data provenance are retained in the source package.
