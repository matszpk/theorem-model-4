from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

zero_imm = -10000
one_imm = -10000
instr_addr_hi = -10000
instr = -10000
temp1 = -10000

def gencode():
    global zero_imm
    global one_imm
    global instr_addr_hi
    global instr
    global temp1
    
    start = 0
    ml.set_pc(start)
    ml.lda(zero_imm)
    ml.sta(instr_addr_hi)
    ml.lda(instr)
    ml.clc()
    ml.adc(instr)
    ml.sta(temp1)
    ml.lda(instr_addr_hi)
    ml.adc(instr_addr_hi)
    ml.sta(instr_addr_hi)       # [0...b7]
    
    ml.lda(temp1)
    ml.clc()
    ml.adc(temp1)
    ml.sta(temp1)
    ml.lda(instr_addr_hi)
    ml.adc(instr_addr_hi)
    ml.sta(instr_addr_hi)       # [0...b7,b6]
    
    ml.lda(temp1)
    ml.clc()
    ml.adc(temp1)
    ml.sta(temp1)
    ml.lda(instr_addr_hi)
    ml.adc(instr_addr_hi)
    ml.sta(instr_addr_hi)       # [0...b7,b6,b5]
    
    ml.lda(temp1)
    ml.clc()
    ml.adc(temp1)
    ml.sta(temp1)
    ml.lda(instr_addr_hi)
    ml.adc(instr_addr_hi)
    ml.sta(instr_addr_hi)       # [0...b7,b6,b5,b4]
    ml.spc(one_imm)
    
    zero_imm = ml.pc
    ml.byte(0)
    one_imm = ml.pc
    ml.byte(1)
    instr_addr_hi = ml.pc
    ml.byte(0, True)
    instr = ml.pc
    ml.byte(0x60, True)
    temp1 = ml.pc
    ml.byte(0, True)
    
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
