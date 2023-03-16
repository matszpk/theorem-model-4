from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

start = 0x00
call_handler = -1000
ret_handler = -1000
stack_ptr = -1000
stack = -1000
temp1 = -1000
call_table = -1000
ch_ch0 = -1000
ch_ch1 = -1000
ch_ch2 = -1000
ch_ch3 = -1000
ret_ch0 = -1000
ret_ch1 = -1000
ret_ch2 = -1000
ret_ch3 = -1000
def gencode():
    global call_handler, ret_handler, temp1, stack, stack_ptr
    global call_table
    ml.set_pc(start)
    ml.lda_imm(0x01)
    ml.bne(call_handler)
    ret_0x01 = ml.pc
    
    ml.lda_imm(0x02)
    ml.bne(call_handler)
    ret_0x02 = ml.pc
    ml.spc_imm(1)
    
    subroutine1 = ml.pc
    ml.lda_imm(0x20)
    ml.sta(0xff0)
    ml.clc()
    ml.bcc(ret_handler)
    
    subroutine2 = ml.pc
    ml.lda_imm(0x30)
    ml.sta(0xff1)
    ml.clc()
    ml.bcc(ret_handler)
    
    call_handler = ml.pc
    # push to stack
    global ch_ch0
    ml.sta(temp1)
    ml.lda(stack_ptr)
    ml.sta(ch_ch0+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(stack_ptr)
    ml.lda(temp1)
    ch_ch0 = ml.pc
    ml.sta(stack,[False,True])
    # make jump
    global ch_ch1, ch_ch2, ch_ch3
    # shift address by 2 bits
    for i in range(0,2):
        ml.clc()
        ml.rol()
    # store this address of call_table to address loaders
    ml.sta(ch_ch2+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(ch_ch3+1)
    # load address (really instruction)
    ch_ch2 = ml.pc
    ml.lda(call_table, [False, True])
    ml.sta(ch_ch1)
    ch_ch3 = ml.pc
    ml.lda(call_table, [False, True])
    ml.sta(ch_ch1+1)
    # call this instruction
    ml.clc()
    ch_ch1 = ml.pc
    ml.bcc(0, [True, True])
    
    # return
    ret_handler = ml.pc
    global ret_ch0, ret_ch1, ret_ch2, ret_ch3
    # pop from stack
    ml.lda(stack_ptr)
    ml.clc()
    ml.sbc_imm(0)
    ml.sta(stack_ptr)
    ml.sta(ret_ch0+1)
    ret_ch0 = ml.pc
    ml.lda(stack,[False,True])
    # shift address by 2 bits
    for i in range(0,2):
        ml.clc()
        ml.rol()
    ml.adc_imm(2)
    ml.sta(ret_ch1+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(ret_ch2+1)
    #loader of return address
    ret_ch1 = ml.pc
    ml.lda(call_table, [False, True])
    ml.sta(ret_ch3)
    ret_ch2 = ml.pc
    ml.lda(call_table, [False, True])
    ml.sta(ret_ch3+1)
    ml.clc()
    ret_ch3 = ml.pc
    ml.bcc(0, [True, True])
    
    # call_table
    ml.pc = ((ml.pc + 255) & 0xf00)
    call_table = ml.pc
    ml.word16(0)
    ml.word16(0)
    ml.word16(instr_addr(subroutine1) | instr_bcc)
    ml.word16(instr_addr(ret_0x01) | instr_bcc)
    ml.word16(instr_addr(subroutine2) | instr_bcc)
    ml.word16(instr_addr(ret_0x02) | instr_bcc)
    
    ml.pc = ((ml.pc + 255) & 0xf00) - 2
    # stack
    temp1 = ml.pc
    ml.byte(0,True)
    stack_ptr = ml.pc
    ml.byte(0,True)
    stack = ml.pc
    for i in range(0,16):
        ml.byte(0,True)
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
