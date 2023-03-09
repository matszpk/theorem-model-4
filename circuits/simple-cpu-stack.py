from simple_cpu_asm import *
from sys import stdout

ml = Memory()

start = 0x10
ml.set_pc(start)
ml.lda(0xf0)
loop = ml.pc
ml.psh()
ml.adc(0xf0)
ml.bne(loop)
loop2 = ml.pc
ml.pul()
x = ml.pc
ml.sta(0xe0)
ml.lda(x+1)
ml.clc()
ml.adc(0xf0)
ml.sta(x+1)
ml.jmp(loop2)

ml.set_pc(0xf0)
ml.nibble(1)

stdout.buffer.write(ml.dump())
