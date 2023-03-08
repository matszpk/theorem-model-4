from simple_cpu_asm import *
from sys import stdout

ml = Memory()

ml.set_pc(0x20)
ml.clc()
for i in range(0,4):
    ml.lda(0xf0+i)
    ml.adc(0xf4+i)
    ml.sta(0xf8+i)
ml.pul()
ml.set_pc(0xf0)
ml.word16(0x7773)
ml.word16(0x43a1)

stdout.buffer.write(ml.dump())
