from simple2_cpu_asm import *
from sys import stdout
from enum import *

ml = Memory()

ml.set_pc(0xfe0)
npc = ml.pc # 0xfe0: program counter
ml.word16(0x0000, [True,True])
nsr = ml.pc # 0xfe2: processor status
ml.byte(0x00, True)
nsp = ml.pc # 0xfe3: stack pointer
ml.byte(0xff, True)
nacc = ml.pc # 0xfe4:
ml.byte(0x00, True)
nxind = ml.pc # 0xfe5:
ml.byte(0x00, True)
nyind = ml.pc # 0xfe6:
ml.byte(0x00, True)
instr_cycles = ml.pc # 0xfe7:
ml.byte(0x00, True)
nopcode = ml.pc # 0xfe8:
ml.byte(0x00, True)
narglo = ml.pc # 0xfe9:
ml.byte(0x00, True)
narghi = ml.pc # 0xfea:
ml.byte(0x00, True)
mem_val = ml.pc # 0xfeb
ml.byte(0x00, True)
mem_addr = ml.pc # 0xfec
ml.word16(0x0000, [True,True])
addr_mode = ml.pc # 0xfee
ml.byte(0x00, True)
op_index = ml.pc # 0xfef
ml.byte(0x00, True)
temp1 = ml.pc # 0xff0:
ml.byte(0x00, True)
temp2 = ml.pc # 0xff1:
ml.byte(0x00, True)

# addressing modes
AddrMode = IntEnum('AddrMode',
        [
            # for ALU encoding (mask=0x1c)
            'pindx','zpg','imm','abs','pindy','zpgx','absy','absx',
            # other addressing modes
            'rel','zpgy','imp'
        ])

# operations
Ops = IntEnum('Ops',
        [
            'ORA','AND','EOR','ADC','STA','LDA','CMP','SBC', # 0-7
            'ASL','ROL','LSR','ROR','STX','LDX','DEC','INC', # 8-15
            'BPL','BMI','BVC','BVS','BCC','BCS','BNE','BEQ', # 16-23
            'TXA','TXS','TAX','TSX','DEX','BRK','NOP','RTI', # 24-31
            'PHP','CLC','PLP','SEC','PHA','CLI','PLA','SEI', # 32-39
            'DEY','TYA','TAY','CLV','INY','CLD','INX','SED', # 40-47
            'STY','LDY','CPY','CPX','JSR','BIT','JMP','JMPind', # 48-55
            'RTS','UND'
        ])

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

def get_ret_page(proc):
    if proc in ret_pages:
        return ret_pages[proc]
    else:
        return -10000

load_inc_pc, load_inc_pc_ch = -10000, -10000
decode_notALU, decode_end, decode_noSTAimm = -10000, -10000, -10000
decode_noALU2IMPA, decode_noAddrMode04 = -10000, -10000
decode_noTXA_other, decode_noIMP, decode_noBRANCH = -10000, -10000, -10000

def gencode():
    global ret_pages
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
    ml.lda_imm(0)
    ml.sta(instr_cycles)
    
    # load opcode
    call_proc_8b(load_inc_pc)
    ##############################
    # decode it
    global decode_notALU, decode_end, decode_noSTAimm, decode_noAddrMode04
    global decode_noTXA_other, decode_noIMP, decode_noBRANCH
    global decode_noALU2IMPA
    #-------------------------------
    ml.sta(nopcode)
    ml.ana_imm(0x1f)
    ml.xor_imm(0x10)
    ml.bne(decode_noBRANCH)
    ml.lda(nopcode)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.rol()
    ml.ana_imm(7)
    ml.adc_imm(Ops.BPL)
    ml.sta(op_index)
    ml.bne(decode_end)
    #------------------------
    decode_noBRANCH = ml.pc
    ml.lda(nopcode)
    ml.ana_imm(0x0f)
    ml.xor_imm(8)
    ml.bne(decode_noIMP)
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(0xf)
    ml.adc_imm(Ops.PHP-1)
    ml.sta(op_index)
    ml.bne(decode_end)
    #--------------------------
    # TXA,TXS impls
    decode_noIMP = ml.pc
    ml.lda(nopcode)
    ml.ana_imm(0x8f)
    ml.xor_imm(0x8a)
    ml.bne(decode_noTXA_other)
    ml.lda_imm(AddrMode.imp)
    ml.sta(addr_mode)
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(0x7)
    ml.adc_imm(Ops.TXA-1)
    ml.sta(op_index)
    ml.ana_imm(5)
    ml.xor_imm(5)
    ml.bne(ml.pc+6)
    decode_UND = ml.pc
    ml.lda_imm(Ops.UND)
    ml.sta(op_index)
    ml.bne(decode_end)
    #------------
    decode_noTXA_other = ml.pc
    ml.lda(nopcode)
    ml.ana_imm(3)
    ml.xor_imm(1)
    ml.bne(decode_notALU)
    #----------------
    # 0x03&opcode = 1 -> ALU
    ml.lda(nopcode)
    ml.clc()            # shift >> 2
    ml.ror()
    ml.clc()
    ml.ror()
    ml.sta(temp1)
    ml.ana_imm(7)       # addr mode
    ml.sta(addr_mode)
    ml.lda(temp1)
    ml.ror()            # shift >> 3
    ml.ror()
    ml.ror()
    ml.ana_imm(7)
    ml.sta(op_index)    # op index
    ml.lda(nopcode)
    ml.xor_imm(0x89) # if STA_imm
    ml.bne(decode_noSTAimm)
    ml.bpl(decode_UND)
    decode_noSTAimm = ml.pc
    ml.bne(decode_end)
    #----------------
    decode_notALU = ml.pc
    #----------------
    # 0x03&opcode = 2 -> shift,inc,dec,stx,ldx
    ml.clc()            # shift >> 2
    ml.ror()
    ml.clc()
    ml.ror()
    ml.sta(temp1)
    ml.ana_imm(7)       # addr mode
    ml.sta(addr_mode)
    ml.lda(temp1)
    ml.ror()            # shift >> 3
    ml.ror()
    ml.ror()
    ml.ana_imm(7)
    ml.ora_imm(Ops.ASL)
    ml.sta(op_index)    # op index
    ml.lda(addr_mode)
    ml.ana_imm(3)       # addr_mode=0 or 4
    ml.bne(decode_noAddrMode04)
    ml.lda(nopcode)
    ml.xor_imm(0xa0)
    ml.bne(decode_UND)
    # if LDX #imm
    ml.lda(AddrMode.imm)
    ml.sta(addr_mode)
    ml.lda(Ops.LDX)
    ml.sta(op_index)
    ml.bne(decode_end)
    decode_noAddrMode04 = ml.pc
    ml.lda(addr_mode)
    ml.xor(AddrMode.absy)
    ml.bne(ml.pc+4) # skip next instr
    ml.bpl(decode_UND)  # undefined
    ml.lda(addr_mode)
    ml.xor_imm(AddrMode.imm)       # if imm -> imp acc
    ml.bne(decode_noALU2IMPA)
    ml.lda(AddrMode.imp)
    ml.sta(addr_mode)
    decode_noALU2IMPA = ml.pc
    # change addr mode for STX and LDX, handle STX, LDX
    
    decode_end = ml.pc
    # end of decode it
    ##############################
    
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
    ml.bcc(get_ret_page(load_inc_pc), [False, True])
    
    # tables:
    # addressing modes:
    # 
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
