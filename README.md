# retron-1
Retron-1 TTL CPU

I decided to build a CPU in TTL logic to learn more about how they work. The Retron-1 is a microcoded 8-bit CPU loosely based on the 6502.

It will address 64kb of memory, has five general-purpose registers, stack support, interrupts, and hardware subroutines. 

The preliminary design of the CPU has been done in Logisim, a java-based logic simulation program. This was ideal for me because it allowed me to model all the MSI chips (like the 74181 ALU, bus drivers, binary counters for the program counter, etc.) as individual gates to promote greater understanding of the whole system at the gate level.

The eventual goal is to have a working hardware version of the CPU, and now that the Logisim version is working, I'm beginning the hardware prototyping stage. 

Microcode is generated by a python script which currently spits out three logisim-formatted ROM files which can be loaded for quick testing.
