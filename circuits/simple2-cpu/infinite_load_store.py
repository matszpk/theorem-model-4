from simple2_cpu_asm import *
from sys import stdout
import argparse

ap = argparse.ArgumentParser(prog = '6502 simple2-cpu codegen')
ap.add_argument('-I', '--info', action='store_true')

args = ap.parse_args()

ml = Memory()

ret_pages = dict()
# handle call procedure (by storing 8-bit return address)
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

def get_ret_page(proc):
    if proc in ret_pages:
        return ret_pages[proc]
    else:
        return -10000

inf_load, inf_store, inf_ldst_down = -10000, -10000, -10000
pc, acc, flagc = -10000, -10000, -10000
instr, instr_addr_hi, instr_hi_opcode = -10000, -10000, -10000
normal_load, normal_store, normal_ldst_down = -10000, -10000, -10000
loading_instr, storing_instr = -10000, -10000
child_created, child_ops = -10000, -10000
val_0xff_imm, zero_imm, one_imm = -10000, -10000, -10000
inf_load_lo_imm, inf_load_hi_imm = -10000, -10000
inf_store_lo_imm, inf_store_hi_imm = -10000, -10000
inf_ldst_down_lo_imm, inf_ldst_down_hi_imm = -10000, -10000
value_lo_imm, value_hi_imm = -10000, -10000
addr_lo_imm, addr_hi_imm, addr_lop1_imm = -10000, -10000, -10000
neg_routine_end_lo_imm, neg_routine_end_hi_imm = -10000, -10000
val_0x40_imm, val_0x80_imm, val_0x10_imm, val_0x20_imm = -10000, -10000, -10000, -10000
addr, value = -10000, -10000
temp1 = -10000

prepare_addr = -10000
to_simulator = -10000
to_sim_cont = -10000
fetch_instr_high_byte = -10000
fetch_instr_0_7 = -10000
skip_instr_high_byte = -10000
decode_instr_0_7 = -10000
decode_instr_0_3 = -10000
decode_lda_sta = -10000
execute_lda, execute_bcc = -10000, -10000
do_bcc_jump = -10000

skip_creation = -10000

child_mem_addr = 0xffe
child_mem_val = 0xffd

# sim_code_end
routine_end, sim_end = -10000, -10000

inf_load_store = 0xffff # virtual
inf_load_store_ch = -10000

caddr_instr_lo, caddr_instr_hi = -10000, -10000
copy_instr, copy_op, copy_end = -10000, -10000, -10000
instr_inc_finished = -10000

native_load, native_store = -10000, -10000
native_int_load, native_int_store = -10000, -10000

native_ldst_up, native_ldst_up_ch = -10000, -10000
native_ldst_down, native_ldst_down_ch = -10000, -10000

caddr_addr = -10000

example_start = -10000

def gencode():
    global inf_load, inf_store, inf_ldst_down
    global normal_load, normal_store, normal_ldst_down
    global loading_instr, storing_instr
    global routine_end, sim_end
    global instr, instr_addr_hi, instr_hi_opcode
    global child_created, child_ops
    global prepare_addr
    global val_0xff_imm, zero_imm, one_imm
    global inf_load_lo_imm, inf_load_hi_imm
    global inf_store_lo_imm, inf_store_hi_imm
    global inf_ldst_down_lo_imm, inf_ldst_down_hi_imm
    global value_lo_imm, value_hi_imm
    global addr_lo_imm, addr_hi_imm, addr_lop1_imm
    global neg_routine_end_lo_imm, neg_routine_end_hi_imm
    global addr, value
    global pc, acc, flagc
    global temp1
    global val_0x40_imm, val_0x80_imm, val_0x20_imm, val_0x10_imm
    
    global to_simulator
    global to_sim_cont
    global fetch_instr_high_byte
    global fetch_instr_0_7
    global skip_instr_high_byte
    global decode_instr_0_7
    global decode_instr_0_3
    global decode_lda_sta
    global execute_lda, execute_bcc
    global do_bcc_jump
    
    global inf_load_store_ch
    
    start = 0
    ml.set_pc(0)
    
    #########################################################
    # code for simulated CPU that have limited
    # features of Simple2-CPU:
    # 0 - LDA (no NZ flags)
    # 1 - STA
    # 2 - ADC (addition, set only C flag)
    # 7 - CLC
    # A - BCC
    #########################################################
    
    #####################################
    # infinite load routine
    inf_load = ml.pc
    ml.clc()
    ml.lda(child_ops)
    ml.adc(val_0xff_imm)
    ml.bcc(normal_load)
    # simulated load
    
    ml.lda(inf_load_lo_imm)
    ml.sta(pc)
    ml.lda(inf_load_hi_imm)
    ml.sta(pc+1)
    ml.clc()
    ml.bcc(prepare_addr)
    
    normal_load = ml.pc
    ml.lda(addr)
    ml.sta(loading_instr+1) # to instr
    ml.lda(addr+1)
    ml.clc()
    ml.adc(addr+1)  # x2
    ml.sta(loading_instr)
    ml.clc()
    ml.adc(loading_instr)  # x4
    ml.sta(loading_instr)
    ml.clc()
    ml.adc(loading_instr)  # x8
    ml.sta(loading_instr)
    ml.clc()
    ml.adc(loading_instr)  # x16
    ml.sta(loading_instr) # LDA - opcode - 0
    loading_instr = ml.pc
    ml.lda(0, [True, True])
    ml.clc()
    ml.bcc(routine_end)
    
    #####################################
    # infite store routine
    inf_store = ml.pc
    ml.clc()
    ml.lda(child_ops)
    ml.adc(val_0xff_imm)
    ml.bcc(normal_store)
    # simulated store
    
    ml.lda(inf_store_lo_imm)
    ml.sta(pc)
    ml.lda(inf_store_hi_imm)
    ml.sta(pc+1)
    ml.lda(value_lo_imm)    # transfer value to child
    ml.sta(child_mem_addr)
    ml.lda(value_hi_imm)
    ml.sta(child_mem_addr+1)
    ml.lda(value)
    ml.sta(child_mem_val)
    ml.clc()
    ml.bcc(prepare_addr)
    
    normal_store = ml.pc
    ml.lda(addr)
    ml.sta(storing_instr+1) # to instr
    ml.lda(addr+1)
    ml.clc()
    ml.adc(addr+1)  # x2
    ml.sta(storing_instr)
    ml.clc()
    ml.adc(storing_instr)  # x4
    ml.sta(storing_instr)
    ml.clc()
    ml.adc(storing_instr)  # x8
    ml.sta(storing_instr)
    ml.clc()
    ml.adc(storing_instr)  # x16
    ml.clc()
    ml.adc(one_imm) # STA opcode - 1
    ml.sta(storing_instr) # STA - opcode - 1
    ml.lda(value)
    storing_instr = ml.pc
    ml.sta(storing_instr, [True, True])
    ml.clc()
    ml.bcc(routine_end)
    
    ################################
    # inf_ldst_down
    inf_ldst_down = ml.pc
    ml.clc()
    ml.lda(child_ops)
    ml.adc(val_0xff_imm)
    ml.bcc(normal_ldst_down)
    # simulated
    ml.lda(inf_ldst_down_lo_imm)
    ml.sta(pc)
    ml.lda(inf_ldst_down_hi_imm)
    ml.sta(pc+1)
    ml.clc()
    ml.bcc(prepare_addr)
    
    normal_ldst_down = ml.pc
    ml.bpl(ml.pc+2)       # child_ops - set zero, hack
    ml.clc()
    ml.bcc(routine_end)
    
    #################################
    # next part of simulated stuff (simulator)
    prepare_addr = ml.pc
    # transfer addr to child addr
    ml.lda(addr_lo_imm)
    ml.sta(child_mem_addr)
    ml.lda(addr_hi_imm)
    ml.sta(child_mem_addr+1)
    ml.lda(addr)
    ml.sta(child_mem_val)
    
    ml.lda(addr_lop1_imm)
    ml.sta(child_mem_addr)
    ml.lda(addr+1)
    ml.sta(child_mem_val)
    
    #####################################
    # simulator
    to_simulator = ml.pc
    ml.clc()
    ml.lda(pc)
    ml.adc(neg_routine_end_lo_imm)
    ml.lda(pc+1)
    ml.adc(neg_routine_end_hi_imm)
    ml.bcc(to_sim_cont) # if pc < routine_end
    ml.lda(acc)
    ml.clc()
    ml.bcc(routine_end)
    
    to_sim_cont = ml.pc
    # continue simulation
    ml.lda(pc)
    ml.sta(child_mem_addr)
    ml.clc()
    ml.adc(one_imm)
    ml.sta(pc)
    ml.lda(pc+1)
    ml.sta(child_mem_addr+1)
    ml.adc(zero_imm)
    ml.sta(pc+1)
    # load instruction byte
    ml.lda(child_mem_val)
    ml.sta(instr)
    ml.clc()
    ml.adc(instr) # x2
    ml.sta(instr_hi_opcode)
    ml.clc()
    ml.adc(instr_hi_opcode) # x4
    ml.sta(instr_hi_opcode)
    ml.clc()
    ml.adc(instr_hi_opcode) # x8
    ml.sta(instr_hi_opcode)
    ml.clc()
    ml.adc(instr_hi_opcode) # x16
    ml.sta(instr_hi_opcode) # opcode<<4
    
    ml.clc()
    ml.adc(val_0x80_imm)
    ml.bcc(fetch_instr_0_7)
    # decode_instr_8-f (no CLC)
    ml.clc()
    ml.bcc(fetch_instr_high_byte)
    
    fetch_instr_0_7 = ml.pc
    # acc = instr+8
    ml.adc(val_0x40_imm)
    # instr+8+4 if instr>=4 -> carry
    ml.bcc(fetch_instr_high_byte)   # 0x0-0x3 instr opcode
    ml.clc()
    ml.bcc(skip_instr_high_byte)
    
    fetch_instr_high_byte = ml.pc
    # ROR - 
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
    # end ROR
    
    ml.lda(pc)
    ml.sta(child_mem_addr)
    ml.clc()
    ml.adc(one_imm)
    ml.sta(pc)
    ml.lda(pc+1)
    ml.sta(child_mem_addr+1)
    ml.adc(zero_imm)
    ml.sta(pc+1)
    # load instruction byte
    ml.lda(child_mem_val)
    ml.sta(instr+1)
    
    skip_instr_high_byte = ml.pc
    ###################################
    # real decode
    ml.lda(instr_hi_opcode)
    ml.clc()
    ml.adc(val_0x80_imm)
    ml.bcc(decode_instr_0_7)
    # instr 8-f
    # acc=instr+8 - instr 8..15 acc 0..7
    # BCC
    ml.lda(instr_hi_opcode)
    ml.clc()
    ml.adc(val_0x40_imm)
    ml.bcc(execute_bcc)
    # execute spc - just - disable child_ops in this machine and return
    ml.lda(zero_imm)
    ml.sta(child_ops)
    ml.clc()
    ml.bcc(routine_end)
    
    execute_bcc = ml.pc
    ml.lda(flagc)
    ml.clc()
    ml.adc(val_0xff_imm)        # to carry
    ml.bcc(do_bcc_jump)
    ml.clc()
    ml.bcc(to_simulator)    # do nothing
    do_bcc_jump = ml.pc
    ml.lda(instr+1)
    ml.sta(pc)
    ml.lda(instr_addr_hi)
    ml.sta(pc+1)
    ml.clc()
    ml.bcc(to_simulator)
    
    decode_instr_0_7 = ml.pc
    # instr 0-7
    # acc = instr+8
    ml.clc()
    ml.adc(val_0x40_imm)
    # acc = instr+8+4 if instr=4-7 then carry
    ml.bcc(decode_instr_0_3)
    # instr=4-7 - > CLC
    # execute CLC
    ml.lda(zero_imm)
    ml.sta(flagc)
    ml.clc()
    ml.bcc(to_simulator)
    
    decode_instr_0_3 = ml.pc
    # acc = instr+8+4
    # acc+3 
    ml.adc(val_0x20_imm)
    ml.bcc(decode_lda_sta)
    # execute adc
    ml.lda(instr+1)
    ml.sta(child_mem_addr)
    ml.lda(instr_addr_hi)
    ml.sta(child_mem_addr+1)
    ml.lda(flagc)
    ml.clc()
    ml.adc(val_0xff_imm)    # move bit0 to carry
    ml.lda(acc)
    ml.adc(child_mem_val)
    ml.sta(acc)
    ml.lda(zero_imm)    # move back carry to bit0
    ml.adc(zero_imm)
    ml.sta(flagc)
    ml.clc()
    ml.bcc(to_simulator)
    
    decode_lda_sta = ml.pc
    ml.adc(val_0x10_imm)
    ml.bcc(execute_lda)
    # acc = instr+8+4+2
    # execute sta
    ml.lda(instr+1)
    ml.sta(child_mem_addr)
    ml.lda(instr_addr_hi)
    ml.sta(child_mem_addr+1)
    ml.lda(child_mem_val)
    ml.lda(acc)
    ml.sta(child_mem_val)
    ml.clc()
    ml.bcc(to_simulator)
    
    execute_lda = ml.pc
    ml.lda(instr+1)
    ml.sta(child_mem_addr)
    ml.lda(instr_addr_hi)
    ml.sta(child_mem_addr+1)
    ml.lda(child_mem_val)
    ml.sta(acc)
    ml.clc()
    ml.bcc(to_simulator)
    
    routine_end = ml.pc
    ml.clc()
    inf_load_store_ch = ml.pc
    ml.bcc(get_ret_page(inf_load_store), [True, True])

    val_0xff_imm = ml.pc
    ml.byte(0xff)
    val_0x80_imm = ml.pc
    ml.byte(0x80)
    val_0x40_imm = ml.pc
    ml.byte(0x40)
    val_0x20_imm = ml.pc
    ml.byte(0x20)
    val_0x10_imm = ml.pc
    ml.byte(0x10)
    zero_imm = ml.pc
    ml.byte(0x0)
    one_imm = ml.pc
    ml.byte(0x1)
    inf_load_lo_imm = ml.pc
    ml.byte(inf_load&0xff)
    inf_load_hi_imm = ml.pc
    ml.byte((inf_load>>8)&0xf)
    inf_store_lo_imm = ml.pc
    ml.byte(inf_store&0xff)
    inf_store_hi_imm = ml.pc
    ml.byte((inf_store>>8)&0xf)
    inf_ldst_down_lo_imm = ml.pc
    ml.byte(inf_ldst_down&0xff)
    inf_ldst_down_hi_imm = ml.pc
    ml.byte((inf_ldst_down>>8)&0xf)
    value_lo_imm = ml.pc
    ml.byte(value&0xff)
    value_hi_imm = ml.pc
    ml.byte((value>>8)&0xf)
    addr_lo_imm = ml.pc
    ml.byte(addr&0xff)
    addr_lop1_imm = ml.pc
    ml.byte((addr+1)&0xff)
    addr_hi_imm = ml.pc
    ml.byte((addr>>8)&0xf)
    neg_routine_end = ((routine_end-1)^0xffff)
    #neg_routine_end = ((my_end-1)^0xffff)
    neg_routine_end_lo_imm = ml.pc
    ml.byte(neg_routine_end&0xff)
    neg_routine_end_hi_imm = ml.pc
    # must be full 8-bit! because will be used in arithmetic
    ml.byte((neg_routine_end>>8)&0xff)
    
    sim_end = ml.pc
    
    # arguments
    ml.set_pc((ml.pc+1) & 0xffe)
    addr = ml.pc        # in normal form
    ml.word16(0, [True, True])
    value = ml.pc
    ml.byte(0, True)
    
    # for simulation
    pc = ml.pc
    ml.word16(0, [True, True])
    acc = ml.pc
    ml.byte(0, True)
    flagc = ml.pc
    ml.byte(0, True)
    instr = ml.pc
    ml.word16(0, [True, True])
    instr_hi_opcode = ml.pc
    ml.byte(0, True)
    instr_addr_hi = ml.pc
    ml.byte(0, True)
    
    child_created = ml.pc
    ml.byte(0, True)
    child_ops = ml.pc
    ml.byte(0, True)
    temp1 = ml.pc
    ml.byte(0, True)
    
    ###########################
    # native code
    global skip_creation
    global caddr_instr_lo, caddr_instr_hi
    global copy_instr, copy_op, copy_end
    global instr_inc_finished
    
    global native_ldst_up, native_ldst_up_ch
    global native_ldst_down, native_ldst_down_ch
    
    global native_load, native_store
    global native_int_load, native_int_store
    
    global caddr_addr
    
    native_load = ml.pc
    ml.sta(inf_load_store_ch+1)
    ml.lda_imm((get_ret_page(native_load)>>4) | instr_bcc)
    ml.sta(inf_load_store_ch)
    ml.clc()
    ml.bcc(inf_load)
    
    native_store = ml.pc
    ml.sta(inf_load_store_ch+1)
    ml.lda_imm((get_ret_page(native_store)>>4) | instr_bcc)
    ml.sta(inf_load_store_ch)
    ml.clc()
    ml.bcc(inf_store)
    
    native_int_load = ml.pc
    ml.sta(inf_load_store_ch+1)
    ml.lda_imm((get_ret_page(native_int_load)>>4) | instr_bcc)
    ml.sta(inf_load_store_ch)
    ml.clc()
    ml.bcc(inf_load)
    
    native_int_store = ml.pc
    ml.sta(inf_load_store_ch+1)
    ml.lda_imm((get_ret_page(native_int_store)>>4) | instr_bcc)
    ml.sta(inf_load_store_ch)
    ml.clc()
    ml.bcc(inf_store)
    
    ######################################
    # move loadstore to parent machine
    native_ldst_down = ml.pc
    ml.sta(inf_load_store_ch+1)
    ml.lda_imm((get_ret_page(native_ldst_down)>>4) | instr_bcc)
    ml.sta(inf_load_store_ch)
    ml.clc()
    ml.bcc(inf_ldst_down)
    
    
    ml.set_pc((ml.pc+255) & 0xf00)
    ######################################
    # move loadstore to child machine
    native_ldst_up = ml.pc
    ml.sta(native_ldst_up_ch+1)
    ml.lda_imm(child_created&0xff)
    ml.sta(addr)
    ml.lda_imm(child_created>>8)
    ml.sta(addr+1)
    call_proc_8b(native_int_load)
    ml.xor_imm(0)
    ml.bne(skip_creation)
    
    ml.lda_imm(0xfd)
    ml.sta(addr)
    ml.lda_imm(0xf)
    ml.sta(addr+1)
    ml.lda_imm(12)
    ml.sta(value)
    call_proc_8b(native_int_store)
    
    ml.lda_imm(0xfe)
    ml.sta(addr)
    ml.lda_imm(0xf)
    ml.sta(addr+1)
    ml.lda_imm(0x30)
    ml.sta(value)
    call_proc_8b(native_int_store)
    
    ml.lda_imm(0xff)
    ml.sta(addr)
    ml.lda_imm(0xf)
    ml.sta(addr+1)
    ml.lda_imm(0)
    ml.sta(value)
    call_proc_8b(native_int_store)
    ml.spc_imm(0) # call it
    
    #################################
    # copy routine
    
    ml.lda_imm(0)
    ml.sta(caddr_addr)
    ml.sta(caddr_addr+1)
    ml.sta(copy_instr)  # LDA - opcode - 0
    ml.sta(copy_instr+1)
    
    copy_loop = ml.pc
    ml.lda(caddr_addr)
    ml.xor_imm(sim_end&0xff)
    ml.bne(copy_op)
    ml.lda(caddr_addr+1)
    ml.xor_imm((sim_end>>8)&0xff)
    ml.bne(copy_op)
    ml.bpl(copy_end)
    
    copy_op = ml.pc
    # set address of child_mem_addr (0xffe)
    ml.lda_imm(child_mem_addr&0xff)
    ml.sta(addr)
    ml.lda_imm(child_mem_addr>>8)
    ml.sta(addr+1)
    ml.lda(caddr_addr)
    ml.sta(value)
    call_proc_8b(native_int_store)

    ml.lda_imm((child_mem_addr+1)&0xff)
    ml.sta(addr)
    ml.lda_imm((child_mem_addr+1)>>8)
    ml.sta(addr+1)
    caddr_instr_hi = ml.pc
    ml.lda(caddr_addr+1)
    ml.sta(value)
    call_proc_8b(native_int_store)

    # set value to child_val (0xffd)
    ml.lda_imm(child_mem_val&0xff)
    ml.sta(addr)
    ml.lda_imm(child_mem_val>>8)
    ml.sta(addr+1)
    copy_instr = ml.pc
    ml.lda(0, [True,True])
    ml.sta(value)
    call_proc_8b(native_int_store)
    
    #increase copy instr address
    ml.lda(copy_instr+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(copy_instr+1)
    ml.bcc(instr_inc_finished)
    ml.lda(copy_instr)
    ml.adc_imm(0xf)
    ml.sta(copy_instr)
    instr_inc_finished = ml.pc
    # increase addr to addr_lo and addr_hi
    ml.lda(caddr_addr)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(caddr_addr)
    ml.lda(caddr_addr+1)
    ml.adc_imm(0)
    ml.sta(caddr_addr+1)
    ml.clc()
    ml.bcc(copy_loop)
    copy_end = ml.pc
    
    ml.lda_imm(child_created&0xff)
    ml.sta(addr)
    ml.lda_imm(child_created>>8)
    ml.sta(addr+1)
    ml.lda_imm(1)
    ml.sta(value)
    call_proc_8b(native_int_store)
    
    # child_ops and child_created in new machine is zeroed by default
    skip_creation = ml.pc
    
    ml.lda_imm(child_ops&0xff)
    ml.sta(addr)
    ml.lda_imm(child_ops>>8)
    ml.sta(addr+1)
    ml.lda_imm(1)
    ml.sta(value)
    call_proc_8b(native_int_store)
    ml.clc()
    native_ldst_up_ch = ml.pc
    ml.bcc(get_ret_page(native_ldst_up), [False, True])
    
    caddr_addr = ml.pc
    ml.word16(0, [True, True])
    
    #################################################
    # testings!!!
    # just example:
    #################################################
    ml.set_pc((ml.pc+255)&0xf00)
    global example_start
    example_start = ml.pc
    
    ret_pages[inf_load_store] = ml.pc
    
    ta = 0x7b1
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    ml.lda_imm(0x2a)
    ml.sta(value)
    call_proc_8b(native_store)
    
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_load)
    
    ta2 = 0x421
    ml.clc()
    ml.adc_imm(5)
    ml.sta(value)
    ml.lda_imm(ta2&0xff)
    ml.sta(addr)
    ml.lda_imm((ta2>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_store)
    
    ml.lda_imm(ta2&0xff)
    ml.sta(addr)
    ml.lda_imm((ta2>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_load)
    
    call_proc_8b(native_ldst_up)
    
    # after ldst up
    ta = 0x5da
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    ml.lda_imm(0x69)
    ml.sta(value)
    call_proc_8b(native_store)
    
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_load)
    
    ta2 = 0xb37
    ml.clc()
    ml.adc_imm(9)
    ml.sta(value)
    ml.lda_imm(ta2&0xff)
    ml.sta(addr)
    ml.lda_imm((ta2>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_store)
    
    call_proc_8b(native_ldst_up)
    
    # after ldst up
    ta = 0x6be
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    ml.lda_imm(0x3b)
    ml.sta(value)
    call_proc_8b(native_store)
    
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_load)
    
    ta2 = 0xc39
    ml.clc()
    ml.adc_imm(2)
    ml.sta(value)
    ml.lda_imm(ta2&0xff)
    ml.sta(addr)
    ml.lda_imm((ta2>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_store)
     
    call_proc_8b(native_ldst_down)
    
    # after ldst up
    ta = 0x8cd
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    ml.lda_imm(0x18)
    ml.sta(value)
    call_proc_8b(native_store)
    
    ml.lda_imm(ta&0xff)
    ml.sta(addr)
    ml.lda_imm((ta>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_load)
    
    ta2 = 0xdef
    ml.clc()
    ml.adc_imm(7)
    ml.sta(value)
    ml.lda_imm(ta2&0xff)
    ml.sta(addr)
    ml.lda_imm((ta2>>8)&0xff)
    ml.sta(addr+1)
    call_proc_8b(native_store)
    
    ml.spc_imm(1)
    
    return start

ml.assemble(gencode)

if args.info:
    print("mpc:", ml.pc)
    print(globals())
else:
    stdout.buffer.write(ml.dump())
