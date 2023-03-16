from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

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
    # call exec engine
    # load addr from
    ee_pc_instr = ml.pc
    ml.lda(main_prog)
    ml.sta(ee_jump)
    ee_pc_instr_2 = ml.pc
    ml.lda(main_prog+1)
    ml.sta(ee_jump+1)
    ml.clc()
    ee_jump = ml.pc
    ml.bcc(0)
    ee_ret = ml.pc
    ml.lda(ee_pc_instr+1)
    ml.sec()
    ml.adc(one)
    ml.sta(ee_pc_instr+1)
    ml.lda(ee_pc_instr)
    ml.adc(one)
    ml.sta(ee_pc_instr)
    ml.lda(ee_pc_instr_2+1)
    ml.sec()
    ml.adc(one)
    ml.sta(ee_pc_instr_2+1)
    ml.lda(ee_pc_instr_2)
    ml.adc(one)
    ml.sta(ee_pc_instr_2)
    ml.bcc(main_loop)
    
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
