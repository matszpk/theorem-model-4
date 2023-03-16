from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode(ml, imms):
    ml.set_pc(0x00)
    ml.lda_imm(4, imms)
    ml.sec()
    ml.adc_imm(56, imms)
    ml.adc_imm(15, imms)
    ml.sta(0x100)
    ml.spc_imm(1, imms)
    join_imms(imms, ml.imms(range(0,ml.pc)))
    #print("imms", imms)
    #print(ml.mem[0:32])

ml.assemble(gencode)
#print(ml.mem[0:32])

stdout.buffer.write(ml.dump())
