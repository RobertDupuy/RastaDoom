#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$project_root"
base_uf2="${1:-inputs/Robin-original.uf2}"
: "${PICO_SDK_PATH:?Set PICO_SDK_PATH to Pico SDK bddd20f928ce76142793bef434d4f75f4af6e433}"
python3 rastadoom/release/build_client.py
arm-none-eabi-gcc -mcpu=cortex-m0plus -mthumb -Os -ffreestanding -fno-builtin -nostdlib \
 -Wl,-T,rastadoom/checkpoints/launch.ld rastadoom/checkpoints/launch.c rastadoom/checkpoints/launch_stub.S \
 -o build-release/launch.elf
arm-none-eabi-objcopy -O binary build-release/launch.elf build-release/launch.bin
cmake -S rastadoom -B build-release/engine -G Ninja \
 -DPICO_SDK_PATH="$PICO_SDK_PATH" -DPICO_BOARD=a8picocart \
 -DRD_CHECKPOINT_CART=ON -DRD_FACTORY_PACKAGE=OFF -DRD_MENU_ATR=OFF \
 -DRD_WAD_ADDRESS=0x10800000 -DPICO_NO_PICOTOOL=1 -DCMAKE_BUILD_TYPE=Release \
 -DCMAKE_C_COMPILER="$(command -v arm-none-eabi-gcc)" -DCMAKE_CXX_COMPILER="$(command -v arm-none-eabi-g++)"
cmake --build build-release/engine -j4
arm-none-eabi-objcopy -O binary build-release/engine/rastadoom.elf build-release/engine/rastadoom.bin
python3 rastadoom/release/package_firmware.py "$base_uf2"
