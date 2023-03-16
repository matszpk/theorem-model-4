from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode():
    ml.set_pc(0x00)
    ml.lda(0)   # zero
    loop = ml.pc
    ml.sta(0x200,[False,True])
    ml.sec()
    ml.adc(0)
    ml.sta(loop+1)
    ml.bne(loop)
    ml.spc(0x80)
    return 0

ml.assemble(gencode)

ml.set_pc(0x80)
ml.byte(1)

stdout.buffer.write(ml.dump())
