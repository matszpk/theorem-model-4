from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

ml.set_pc(0x00)
ml.byte(0x0)
ml.byte(0x10)
ml.byte(0x40)
ml.byte(0x0)
ml.byte(0xff)

def gencode():
    start = 0x10
    ml.set_pc(start)

    for i in range(0,3):
        ml.lda(0x1+i)
        ml.sta(0xffd+i)
    ml.spc(0)

    ml.lda(0)
    ml.sta(0xffe)
    ml.sta(0xfff)

    # fill loop
    loop = ml.pc
    ml.lda(0xffe)
    ml.sec()
    ml.adc(0)
    ml.sta(0xffe)
    ml.xor(4)
    ml.sta(0xffc)
    ml.lda(0xfff)
    ml.adc(0)
    ml.sta(0xfff)
    ml.xor(4)
    ml.sta(0xffd)
    ml.bcc(loop)

    ml.spc(0xff8)
    return 0x10

ml.assemble(gencode)

ml.set_pc(0xff8)
ml.byte(1)

stdout.buffer.write(ml.dump())
