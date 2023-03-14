from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

ml.set_pc(0x00)
ml.lda(0)   # zero
loop = ml.pc
ml.sta(0x200)
ml.sec()
ml.adc(0)
ml.sta(loop+1)
ml.bne(loop)
ml.spc(0x80)

ml.set_pc(0x80)
ml.byte(1)

stdout.buffer.write(ml.dump())
