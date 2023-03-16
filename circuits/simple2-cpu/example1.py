from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode():
    ml.set_pc(0x00)
    ml.clc()
    for i in range(0,4):
        ml.lda(0x210+i)
        ml.adc(0x214+i)
        ml.sta(0x330+i)
    ml.spc(0x80)
    return 0

ml.assemble(gencode)

ml.set_pc(0x80)
ml.byte(1)
ml.set_pc(0x210)
ml.word32(0x7771bb23)
ml.word32(0x436981a1)

stdout.buffer.write(ml.dump())
