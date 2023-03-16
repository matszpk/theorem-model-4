from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

start = 0x00
call_handler = -1000
ret_handler = -1000
stack_ptr = -1000
stack = -1000
temp1 = -1000
call_table = -100000
ch_ch0 = -1000
ch_ch1 = -1000
ch_ch2 = -1000
ch_ch3 = -1000
ret_ch0 = -1000
ch_sh1 = -1000
ch_sh2 = -1000
ch_sh3 = -1000
ch_shend = -1000
def gencode():
    global call_handler, ret_handler, temp1, stack, stack_ptr
    global call_table
    ct_start = (call_table>>2)&0xff
    ml.set_pc(start)
    ml.lda_imm(ct_start)
    ml.bne(call_handler)
    ret_0x01 = ml.pc
    
    ml.lda_imm(ct_start+1)
    ml.bne(call_handler)
    ret_0x02 = ml.pc
    ml.spc_imm(1)
    
    subroutine1 = ml.pc
    ml.lda_imm(0x20)
    ml.sta(0xff0)
    ml.bne(ret_handler)
    
    subroutine2 = ml.pc
    ml.lda_imm(0x30)
    ml.sta(0xff1)
    ml.clc()
    ml.bne(ret_handler)
    
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
    global ch_sh1, ch_sh2, ch_sh3, ch_shend
    # shift address by 2 bits
    ml.clc()
    # if sec then add 2
    ch_finish = ml.pc
    ml.rol()
    ml.bcc(ch_sh1)
    ml.clc()
    ml.rol()
    ml.sta(temp1)
    ml.bcc(ch_sh3)
    # entry&0xc0 = 0xc0
    ml.lda_imm((((call_table>>8) + 3) << 4) + instr_lda)
    ml.bne(ch_shend)
    
    ch_sh3 = ml.pc
    # entry&0xc0 = 0x80
    ml.lda_imm((((call_table>>8) + 2) << 4) + instr_lda)
    ml.bne(ch_shend)
    
    ch_sh1 = ml.pc
    ml.rol()
    ml.sta(temp1)
    ml.bcc(ch_sh2)
    # entry&0xc0 = 0x40
    ml.lda_imm((((call_table>>8) + 1) << 4) + instr_lda)
    ml.bne(ch_shend)
    
    ch_sh2 = ml.pc
    # entry&0xc0 = 0x00
    ml.lda_imm((((call_table>>8) + 0) << 4) + instr_lda)
    
    ch_shend = ml.pc
    ml.sta(ch_ch2)
    ml.sta(ch_ch3)
    # store this address of call_table to address loaders
    ml.lda(temp1)
    ml.sta(ch_ch2+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(ch_ch3+1)
    # load address (really instruction)
    ch_ch2 = ml.pc
    ml.lda(call_table, [True, True])
    ml.sta(ch_ch1)
    ch_ch3 = ml.pc
    ml.lda(call_table, [True, True])
    ml.sta(ch_ch1+1)
    # call this instruction
    ml.clc()
    ch_ch1 = ml.pc
    ml.bcc(0, [True, True])
    
    # return
    ret_handler = ml.pc
    global ret_ch0
    # pop from stack
    ml.lda(stack_ptr)
    ml.clc()
    ml.sbc_imm(0)
    ml.sta(stack_ptr)
    ml.sta(ret_ch0+1)
    ret_ch0 = ml.pc
    ml.lda(stack,[False,True])
    ml.sec()
    ml.adc_imm(0xff)
    # overflow always is zero - becuase no change sign in acc
    ml.bvc(ch_finish)
    
    # call_table
    ml.pc = ((ml.pc + 3) & 0xffc)
    call_table = ml.pc
    ml.word16(instr_addr(subroutine1) | instr_bcc)
    ml.word16(instr_addr(ret_0x01) | instr_bcc)
    ml.word16(instr_addr(subroutine2) | instr_bcc)
    ml.word16(instr_addr(ret_0x02) | instr_bcc)
    
    ml.pc = ((ml.pc + 255) & 0xf00) - 2
    if (ml.pc&0xff)>=255:
        ml.pc = (ml.pc + 0x101) & 0xfff
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
