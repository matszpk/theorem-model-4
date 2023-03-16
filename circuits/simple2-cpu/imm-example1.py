from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

jump0 = None
def gencode():
    global jump0
    ml.set_pc(0x00)
    ml.lda_imm(4)
    ml.sec()
    ml.bcc(jump0)
    ml.adc_imm(56)
    ml.adc_imm(15)
    ml.sta(0x100)
    jump0 = ml.pc
    ml.spc_imm(1)
    return 0

ml.assemble(gencode)
#print(ml.mem[0:32])

stdout.buffer.write(ml.dump())
