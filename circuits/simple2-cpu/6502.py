from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

ml.set_pc(0xff0)
npc = ml.pc # 0xff0: program counter
ml.word16(0x0000, [True,True])
nsr = ml.pc # 0xff2: processor status
ml.byte(0x00, True)
nsp = ml.pc # 0xff3: stack pointer
ml.byte(0xff, True)
nacc = ml.pc # 0xff4:
ml.byte(0x00, True)
nxind = ml.pc # 0xff5:
ml.byte(0x00, True)
nyind = ml.pc # 0xff6:
ml.byte(0x00, True)
nopcode = ml.pc # 0xff7:
ml.byte(0x00, True)
narglo = ml.pc # 0xff8:
ml.byte(0x00, True)
narghi = ml.pc # 0xff9:
ml.byte(0x00, True)
temp1 = ml.pc # 0xffa:
ml.byte(0x00, True)
temp2 = ml.pc # 0xffb:
ml.byte(0x00, True)

load_inc_pc, load_inc_pc_ch = -10000, -10000

ret_pages = dict()
def call_proc_8b(proc):
    if proc < 0:
        ml.lda_imm(1) # ret address
        ml.bne(proc)
        return
    page = 0
    # get page for this routine and check return page with it.
    if proc in ret_pages:
        page = ret_pages[proc]
        if page != ((ml.pc+4) & 0xf00):
            raise(RuntimeError("Wrong page!"))
    else:
        page = (ml.pc+4) & 0xf00
        ret_pages[proc] = page
    addr = ml.pc+4
    # check address range and generate code
    if addr > 0+page and addr < 0x100+page:
        ml.lda_imm(ml.pc+4) # ret address
        ml.bne(proc)
        return addr
    else:
        raise(RuntimeError("Address above range!"))

def gencode():
    global load_inc_pc, load_inc_pc_ch
    
    start = 0
    ml.set_pc(start)
    # create 6502 machine - memory: 16-bit address, 8-bit cell
    ml.lda_imm(0x10)
    ml.sta(0xffd)
    ml.lda_imm(0x30)
    ml.sta(0xffe)
    ml.lda_imm(0)
    ml.sta(0xfff)
    ml.spc(0) # call it

    main_loop = ml.pc
    # load opcode
    call_proc_8b(load_inc_pc)
    # decode it
    
    # load argument low
    call_proc_8b(load_inc_pc)
    
    # load argument high
    call_proc_8b(load_inc_pc)
    
    ml.clc()
    ml.bcc(main_loop)
    
    # main_prog subprogs
    
    # load byte from pc and increment pc
    load_inc_pc = ml.pc
    ml.sta(load_inc_pc_ch+1)
    ml.lda(npc)
    ml.sta(0xffe)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(npc)
    ml.lda(npc+1)
    ml.sta(0xfff)
    ml.adc_imm(0)
    ml.sta(npc+1)
    ml.lda(0xffd)
    ml.clc()
    load_inc_pc_ch = ml.pc
    ml.bcc(0, [False, True])
    
    # tables:
    # addressing modes:
    # 
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
