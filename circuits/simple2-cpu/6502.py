from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

# handling calls:
# lda call_descriptor -> call address, return address, should be nonzero
# bne call_handler
#
# # lda call_descriptor -> call address, return address, should be nonzero
# bne subroutine
#
# subroutine:
# bne call_handler

# 16-element table and LDA, XOR combinations to get 256 values???
# no: use loading from memory. extra 2 bytes added by extra instructions
#
main_prog = 0
ee_jump = 0
for p in range(0,2):
    start = 0
    ml.byte(0x0)
    ml.byte(0x10)
    ml.byte(0x30)
    ml.byte(0x0)
    npc = ml.pc # program counter
    ml.word16(0x0000)
    nsr = ml.pc # processor status
    ml.byte(0x00)
    nsp = ml.pc # stack pointer
    ml.byte(0xff)
    nacc = ml.pc
    ml.byte(0x00)
    nxind = ml.pc
    ml.byte(0x00)
    nyind = ml.pc
    ml.byte(0x00)
    nopcode = ml.pc
    ml.byte(0x00)
    narglo = ml.pc
    ml.byte(0x00)
    narghi = ml.pc
    ml.byte(0x00)
    call_exec_p = ml.pc
    ml.byte(0x00)

    start = (ml.pc + 15) & 16
    ml.set_pc(start)
    one = ml.pc+2
    # create 6502 machine - memory: 16-bit address, 8-bit cell
    for i in range(0,3):
        ml.lda(0x1+i)
        ml.sta(0xffd+i)
    ml.spc(0) # call it

    main_loop = ml.pc
    # load instruction from pc
    ml.lda(npc)
    ml.sta(0xffe)
    ml.sec()
    ml.adc(0x0)
    ml.sta(npc)
    ml.sta(0xffe)
    ml.lda(npc+1)
    ml.adc(0x0)
    ml.sta(npc+1)
    ml.lda(0xffd)
    # opcode
    ml.sta(nopcode)
    # decode instruction
    

    ml.lda(npc)
    ml.sta(0xffe)
    ml.sec()
    ml.adc(0x0)
    ml.sta(npc)
    ml.sta(0xffe)
    ml.lda(npc+1)
    ml.adc(0x0)
    ml.sta(npc+1)
    ml.lda(0xffd)
    ml.sta(narglo)

    ml.lda(npc)
    ml.sta(0xffe)
    ml.sec()
    ml.adc(0x0)
    ml.sta(npc)
    ml.sta(0xffe)
    ml.lda(npc+1)
    ml.adc(0x0)
    ml.sta(npc+1)
    ml.lda(0xffd)
    ml.sta(narghi)

    ml.spc(one)
    
    # main_prog subprogs
    
    # tables:
    # addressing modes:
    # 
    

stdout.buffer.write(ml.dump())
