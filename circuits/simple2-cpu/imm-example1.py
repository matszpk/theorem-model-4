from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode(ml):
    global imms
    ml.set_pc(0x00)
    ml.lda_imm(4)
    ml.sec()
    ml.adc_imm(56)
    ml.adc_imm(15)
    ml.sta(0x100)
    ml.spc_imm(1)
    return 0

ml.assemble(gencode)
#print(ml.mem[0:32])

stdout.buffer.write(ml.dump())
