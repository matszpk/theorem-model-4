from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

subroutine1 = -1000
subroutine2 = -1000
subroutine1_ch = -1000
subroutine2_ch = -1000

start = 0x00
def gencode():
    global subroutine1, subroutine2
    global subroutine1_ch, subroutine2_ch
    
    ml.set_pc(start)
    ml.lda_imm(ml.pc+4)
    ml.bne(subroutine1)
    ml.lda_imm(ml.pc+4)
    ml.bne(subroutine1)
    ml.lda_imm(ml.pc+4)
    ml.bne(subroutine2)
    ml.lda_imm(ml.pc+4)
    ml.bne(subroutine2)
    ml.spc_imm(1)
    
    subroutine1 = ml.pc
    ml.sta(subroutine1_ch+1)
    ml.lda(0xff0)
    ml.clc()
    ml.adc_imm(0x20)
    ml.sta(0xff0)
    ml.lda_imm(ml.pc+4)
    ml.bne(subroutine2)
    subroutine1_ch = ml.pc
    ml.bne(0, [False, True])
    
    subroutine2 = ml.pc
    ml.sta(subroutine2_ch+1)
    ml.lda(0xff1)
    ml.clc()
    ml.adc_imm(0x33)
    ml.sta(0xff1)
    subroutine2_ch = ml.pc
    ml.bne(0, [False, True])
    
    # subroutinexxx
    # store address to final return jump
    # store address to selector where list of jumps (if different returns in different pages)
    # or other combination
    
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
