from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode():
    ml.set_pc(0x00)
    ml.lda(0x40)
    ml.sec()
    ml.rol()
    ml.sta(0x41)
    ml.lda(0)
    ml.rol()
    ml.sta(0x48)
    ml.lda(0x42)
    ml.sec()
    ml.ror()
    ml.sta(0x43)
    ml.spc(0x80)
    return 0

ml.assemble(gencode)

ml.set_pc(0x40)
ml.byte(0xa1)
ml.set_pc(0x42)
ml.byte(0xb2)
ml.set_pc(0x80)
ml.byte(1)

stdout.buffer.write(ml.dump())
