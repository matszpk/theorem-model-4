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
            'PHP','CLC','PLP','SEC','PHA','CLI','PLA','SEI', # 16-23
            'DEY','TYA','TAY','CLV','INY','CLD','INX','SED', # 24-31
            'TXA','TXS','TAX','TSX','DEX','JM1','NOP','JM2', # 32-39
            #----
            'BPL','BMI','BVC','BVS','BCC','BCS','BNE','BEQ', # 40-47
            'STY','LDY','CPY','CPX','JSR','BIT','JMP','JMPind', # 48-55
            'BRK','RTI','RTS','UND'
        ])

op_adc, op_and, op_asl, op_bcc, op_bcs = -10000, -10000, -10000, -100000, -100000
op_und = -10000

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
decode, decode_end = -10000, -10000
decode_ch1, decode_ch2, decode_ch3 = -10000, -10000, -10000
decode_table = -10000
call_op = -10000

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
    # load argument low
    call_proc_8b(load_inc_pc)
    
    # load argument high
    call_proc_8b(load_inc_pc)
    
    ##############################
    # decode it
    global call_op
    global decode, decode_end, decode_table
    global decode_ch1, decode_ch2, decode_ch3
    global op_und
    decode = ml.pc
    #-------------------------------
    ml.sta(nopcode)
    # skip opcodes that satisfies opcode&0x03 == 3. there are undefined
    ml.ana_imm(0x03)
    ml.xor_imm(0x03)
    ml.bne(op_und)
    # skip opcode&0x03 == 3 in table.
    ml.lda(nopcode)
    ml.clc()
    ml.ror()
    ml.clc()
    ml.ror()
    ml.sta(temp1)
    ml.sec()
    ml.lda(nopcode)
    ml.sbc(temp1)
    # A > M - carry on
    # setup address to load decode_table
    ml.sta(decode_ch1+1)
    ml.clc()
    ml.ror()
    ml.clc()
    ml.adc_imm(0xa0)
    ml.sta(decode_ch2+1)
    # carry off - A-X-1
    ml.sbc_imm(0xa0-1)
    #ml.clc()
    ml.ror()    # enables 0x80 - but doesn't matter
    ml.ora_imm(0xc0)
    ml.sta(decode_ch3+1)
    
    decode_ch1 = ml.pc
    ml.lda((decode_table & 0xf00), [False, True])
    ml.sta(call_op+1)
    
    ml.lda(decode_ch1+1)
    ml.ror()
    decode_ch2 = ml.pc
    ml.lda(((decode_table - 0x60) & 0xf00), [False, True])
    ml.bcc(ml.pc+6)    # if not higher nibble
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(0xf)
    ml.sta(addr_mode)   # addr mode
    
    ml.lda(decode_ch1+1)
    ml.xor_imm(1)   # negate first bit
    ml.ror()
    decode_ch3 = ml.pc
    ml.lda(((decode_table + 0xc0) & 0xf00), [False, True])
    ml.bcc(ml.pc+6)    # if higher nibble (no rol)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.rol()
    ml.sta(temp1)
    ml.lda(decode_ch2+1)
    ml.ror()
    ml.lda(temp1)
    ml.bcc(ml.pc+4)
    ml.ror()
    ml.ror()
    #----------
    ml.ana_imm(0x30)
    ml.ora_imm(instr_bcc)
    ml.sta(call_op)   # 12-13 bits - 2 extra address's bits
    
    decode_end = ml.pc
    # end of decode it
    ##############################
    ml.clc()
    
    call_op = ml.pc
    ml.bcc(0, [True, True])
    
    ml.bcc(main_loop)
    
    op_und = ml.pc
    
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
    # before main table - 0xa0 - page offset - 96 entries - 192 nibble entries
    # these values are mapped into 8-11 bit of final value - it is addr mode
    # after main table (192 entries), we have 2-bit entries - 12-13 bits of final values.
    # it is extra bits of call address
    ml.set_pc((ml.pc + 0xff) & 0xf00)
    decode_table = ml.pc
    
    return start

ml.assemble(gencode)

#print("decode len:", decode_end-decode)
stdout.buffer.write(ml.dump())
