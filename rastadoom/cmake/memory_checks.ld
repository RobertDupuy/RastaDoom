/* Supplemental assertions; the Pico SDK supplies the normal RP2040 layout. */
ASSERT(__scratch_y_end__ <= __StackBottom, "Core 0 stack overlaps scratch Y data")
ASSERT(__scratch_x_end__ <= __StackOneBottom, "Core 1 stack overlaps scratch X data")
ASSERT(__flash_binary_end <= 0x10400000, "Program overlaps the WHX asset region")
ASSERT(__end__ <= 0x20030000, "Less than 64K remains for DOOM's dynamic zone")
