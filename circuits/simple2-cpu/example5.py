from simple2_cpu_asm import *
from sys import stdout

ml = Memory()
ch0 = -1000
def gencode():
    global ch0
    ml.set_pc(0x00)
    ml.lda_imm(0x22)
    ml.sta(ch0+1)
    ml.lda_imm(0xdd)
    ch0 = ml.pc
    ml.sta(0x100, [False,True])
    ml.spc_imm(1)
    return 0

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
