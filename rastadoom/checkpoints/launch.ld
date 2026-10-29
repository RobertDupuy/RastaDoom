ENTRY(dispatch)
SECTIONS {
 . = 0x10040000;
 .text : { KEEP(*(.entry)) *(.text*) *(.rodata*) }
 .launch_stub 0x20038100 : AT(0x10041000) { *(.launch_stub) }
 _stub_load = LOADADDR(.launch_stub);
 _stub_size = SIZEOF(.launch_stub);
 ASSERT(SIZEOF(.text) <= 0x1000, "launcher overlaps stub flash")
 ASSERT(SIZEOF(.launch_stub) <= 0x100, "stub exceeds reserved SRAM")
 /DISCARD/ : { *(.comment) *(.ARM.attributes) *(.ARM.exidx*) }
}
