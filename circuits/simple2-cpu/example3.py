from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

ml.set_pc(0x00)
ml.byte(0xfe)
ml.byte(0xd)
ml.byte(0x12,True)
ml.byte(0x5,False)

def gencode():
    ml.set_pc(0x10)
    ml.lda(0)
    loop = ml.pc
    ml.sec()
    ml.sbc(1)
    ml.bcc(ml.pc+5)
    ml.clc()
    ml.bcc(loop)
    ml.sta(0x100)

    loop = ml.pc
    ml.lda(0x200)
    ml.sec()
    ml.adc(0xf)
    ml.sta(0x200)
    ml.lda(2)
    ml.clc()
    ml.adc(3)
    ml.sta(2)
    ml.bcc(loop)

    ml.spc(0x80)
    return 0x10

ml.assemble(gencode)

ml.set_pc(0x80)
ml.byte(1)

stdout.buffer.write(ml.dump())
