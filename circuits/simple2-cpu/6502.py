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
undef_instr = ml.pc # 0xff0
ml.byte(0x00, True)
temp1 = ml.pc # 0xff1:
ml.byte(0x00, True)
temp2 = ml.pc # 0xff2:
ml.byte(0x00, True)

# addressing modes
AddrMode = IntEnum('AddrMode',
        [
            # for ALU encoding (mask=0x1c)
            'pindx','zpg','imm','abs','pindy','zpgx','absy','absx',
            # other addressing modes
            'rel','zpgy','imp'
        ])

op_adc = -10000
op_and = -10000
op_asl = -10000
op_bcc = -10000
op_bcs = -10000
op_beq = -10000
op_bit = -10000
op_bmi = -10000
op_bne = -10000
op_bpl = -10000
op_brk = -10000
op_bvc = -10000
op_bvs = -10000
op_clc = -10000
op_cld = -10000
op_cli = -10000
op_clv = -10000
op_cmp = -10000
op_cpx = -10000
op_cpy = -10000
op_dec = -10000
op_dex = -10000
op_dey = -10000
op_eor = -10000
op_inc = -10000
op_inx = -10000
op_iny = -10000
op_jmp = -10000
op_jmpind = -10000
op_jsr = -10000
op_lda = -10000
op_ldx = -10000
op_ldy = -10000
op_lsr = -10000
op_nop = -10000
op_ora = -10000
op_pha = -10000
op_php = -10000
op_pla = -10000
op_plp = -10000
op_rol = -10000
op_ror = -10000
op_rti = -10000
op_rts = -10000
op_sbc = -10000
op_sec = -10000
op_sed = -10000
op_sei = -10000
op_sta = -10000
op_stx = -10000
op_sty = -10000
op_tax = -10000
op_tay = -10000
op_tsx = -10000
op_txa = -10000
op_txs = -10000
op_tya = -10000
op_und = -10000
op_crt = -10000     # create machine
op_stp = -10000     # stop machine

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
    
    global op_adc
    global op_and
    global op_asl
    global op_bcc
    global op_bcs
    global op_beq
    global op_bit
    global op_bmi
    global op_bne
    global op_bpl
    global op_brk
    global op_bvc
    global op_bvs
    global op_clc
    global op_cld
    global op_cli
    global op_clv
    global op_cmp
    global op_cpx
    global op_cpy
    global op_dec
    global op_dex
    global op_dey
    global op_eor
    global op_inc
    global op_inx
    global op_iny
    global op_jmp
    global op_jmpind
    global op_jsr
    global op_lda
    global op_ldx
    global op_ldy
    global op_lsr
    global op_nop
    global op_ora
    global op_pha
    global op_php
    global op_pla
    global op_plp
    global op_rol
    global op_ror
    global op_rti
    global op_rts
    global op_sbc
    global op_sec
    global op_sed
    global op_sei
    global op_sta
    global op_stx
    global op_sty
    global op_tax
    global op_tay
    global op_tsx
    global op_txa
    global op_txs
    global op_tya
    global op_und
    global op_crt
    global op_stp
    
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
    decode = ml.pc
    #-------------------------------
    ml.sta(nopcode)
    # skip opcodes that satisfies opcode&0x03 == 3. there are undefined
    ml.ana_imm(0x03)
    ml.xor_imm(0x03)
    ml.bne(ml.pc+4)
    ml.bpl(op_und)
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
    ml.lda_imm(1)
    ml.sta(undef_instr)
    ml.spc_imm(1)
    
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
    
    opcode_table = [
        (AddrMode.imp, op_brk), # 0x00
        (AddrMode.pindx, op_ora), # 0x01
        (AddrMode.imp, op_crt), # 0x02
        (AddrMode.imp, op_stp), # 0x04
        (AddrMode.zpg, op_ora), # 0x05
        (AddrMode.zpg, op_asl), # 0x06
        (AddrMode.imp, op_php), # 0x08
        (AddrMode.imm, op_ora), # 0x09
        (AddrMode.imp, op_asl), # 0x0a
        (AddrMode.imp, op_und), # 0x0c
        (AddrMode.abs, op_ora), # 0x0d
        (AddrMode.abs, op_asl), # 0x0e
        (AddrMode.rel, op_bpl), # 0x10
        (AddrMode.pindy, op_ora), # 0x11
        (AddrMode.imp, op_und), # 0x12
        (AddrMode.imp, op_und), # 0x14
        (AddrMode.zpgx, op_ora), # 0x15
        (AddrMode.zpgx, op_asl), # 0x16
        (AddrMode.imp, op_clc), # 0x18
        (AddrMode.absy, op_ora), # 0x19
        (AddrMode.imp, op_und), # 0x1a
        (AddrMode.imp, op_und), # 0x1c
        (AddrMode.absx, op_ora), # 0x1d
        (AddrMode.absx, op_asl), # 0x1e
        
        (AddrMode.abs, op_jsr), # 0x20
        (AddrMode.pindx, op_and), # 0x21
        (AddrMode.imp, op_und), # 0x22
        (AddrMode.zpg, op_bit), # 0x24
        (AddrMode.zpg, op_and), # 0x25
        (AddrMode.zpg, op_rol), # 0x26
        (AddrMode.imp, op_plp), # 0x28
        (AddrMode.imm, op_and), # 0x29
        (AddrMode.imp, op_rol), # 0x2a
        (AddrMode.abs, op_bit), # 0x2c
        (AddrMode.abs, op_and), # 0x2d
        (AddrMode.abs, op_rol), # 0x2e
        (AddrMode.rel, op_bmi), # 0x30
        (AddrMode.pindy, op_and), # 0x31
        (AddrMode.imp, op_und), # 0x32
        (AddrMode.imp, op_und), # 0x34
        (AddrMode.zpgx, op_and), # 0x35
        (AddrMode.zpgx, op_rol), # 0x36
        (AddrMode.imp, op_sec), # 0x38
        (AddrMode.absy, op_and), # 0x39
        (AddrMode.imp, op_und), # 0x3a
        (AddrMode.imp, op_und), # 0x3c
        (AddrMode.absx, op_and), # 0x3d
        (AddrMode.absx, op_rol), # 0x3e
        
        (AddrMode.imp, op_rti), # 0x40
        (AddrMode.pindx, op_eor), # 0x41
        (AddrMode.imp, op_und), # 0x42
        (AddrMode.imp, op_und), # 0x44
        (AddrMode.zpg, op_eor), # 0x45
        (AddrMode.zpg, op_lsr), # 0x46
        (AddrMode.imp, op_pha), # 0x48
        (AddrMode.imm, op_eor), # 0x49
        (AddrMode.imp, op_lsr), # 0x4a
        (AddrMode.abs, op_jmp), # 0x4c
        (AddrMode.abs, op_eor), # 0x4d
        (AddrMode.abs, op_lsr), # 0x4e
        (AddrMode.rel, op_bvc), # 0x50
        (AddrMode.pindy, op_eor), # 0x51
        (AddrMode.imp, op_und), # 0x52
        (AddrMode.imp, op_und), # 0x54
        (AddrMode.zpgx, op_eor), # 0x55
        (AddrMode.zpgx, op_lsr), # 0x56
        (AddrMode.imp, op_cli), # 0x58
        (AddrMode.absy, op_eor), # 0x59
        (AddrMode.imp, op_und), # 0x5a
        (AddrMode.imp, op_und), # 0x5c
        (AddrMode.absx, op_eor), # 0x5d
        (AddrMode.absx, op_lsr), # 0x5e
        
        (AddrMode.imp, op_rts), # 0x60
        (AddrMode.pindx, op_adc), # 0x61
        (AddrMode.imp, op_und), # 0x62
        (AddrMode.imp, op_und), # 0x64
        (AddrMode.zpg, op_adc), # 0x65
        (AddrMode.zpg, op_ror), # 0x66
        (AddrMode.imp, op_pla), # 0x68
        (AddrMode.imm, op_adc), # 0x69
        (AddrMode.imp, op_ror), # 0x6a
        (AddrMode.abs, op_jmpind), # 0x6c
        (AddrMode.abs, op_adc), # 0x6d
        (AddrMode.abs, op_ror), # 0x6e
        (AddrMode.rel, op_bvs), # 0x70
        (AddrMode.pindy, op_adc), # 0x71
        (AddrMode.imp, op_und), # 0x72
        (AddrMode.imp, op_und), # 0x74
        (AddrMode.zpgx, op_adc), # 0x75
        (AddrMode.zpgx, op_ror), # 0x76
        (AddrMode.imp, op_sei), # 0x78
        (AddrMode.absy, op_adc), # 0x79
        (AddrMode.imp, op_und), # 0x7a
        (AddrMode.imp, op_und), # 0x7c
        (AddrMode.absx, op_adc), # 0x7d
        (AddrMode.absx, op_ror), # 0x7e
        
        (AddrMode.imp, op_und), # 0x80
        (AddrMode.pindx, op_sta), # 0x81
        (AddrMode.imp, op_und), # 0x82
        (AddrMode.zpg, op_sty), # 0x84
        (AddrMode.zpg, op_sta), # 0x85
        (AddrMode.zpg, op_stx), # 0x86
        (AddrMode.imp, op_dey), # 0x88
        (AddrMode.imm, op_und), # 0x89
        (AddrMode.imp, op_txa), # 0x8a
        (AddrMode.abs, op_sty), # 0x8c
        (AddrMode.abs, op_sta), # 0x8d
        (AddrMode.abs, op_stx), # 0x8e
        (AddrMode.rel, op_bcc), # 0x90
        (AddrMode.pindy, op_sta), # 0x91
        (AddrMode.imp, op_und), # 0x92
        (AddrMode.zpgx, op_sty), # 0x94
        (AddrMode.zpgx, op_sta), # 0x95
        (AddrMode.zpgy, op_stx), # 0x96
        (AddrMode.imp, op_tya), # 0x98
        (AddrMode.absy, op_sta), # 0x99
        (AddrMode.imp, op_txs), # 0x9a
        (AddrMode.imp, op_und), # 0x9c
        (AddrMode.absx, op_sta), # 0x9d
        (AddrMode.imp, op_und), # 0x9e
        
        (AddrMode.imm, op_ldy), # 0xa0
        (AddrMode.pindx, op_lda), # 0xa1
        (AddrMode.imm, op_ldx), # 0xa2
        (AddrMode.zpg, op_ldy), # 0xa4
        (AddrMode.zpg, op_lda), # 0xa5
        (AddrMode.zpg, op_ldx), # 0xa6
        (AddrMode.imp, op_tay), # 0xa8
        (AddrMode.imm, op_lda), # 0xa9
        (AddrMode.imp, op_tax), # 0xaa
        (AddrMode.abs, op_ldy), # 0xac
        (AddrMode.abs, op_lda), # 0xad
        (AddrMode.abs, op_ldx), # 0xae
        (AddrMode.rel, op_bcs), # 0xb0
        (AddrMode.pindy, op_lda), # 0xb1
        (AddrMode.imp, op_und), # 0xb2
        (AddrMode.zpgx, op_ldy), # 0xb4
        (AddrMode.zpgx, op_lda), # 0xb5
        (AddrMode.zpgy, op_ldx), # 0xb6
        (AddrMode.imp, op_clv), # 0xb8
        (AddrMode.absy, op_lda), # 0xb9
        (AddrMode.imp, op_tsx), # 0xba
        (AddrMode.absx, op_ldy), # 0xbc
        (AddrMode.absx, op_lda), # 0xbd
        (AddrMode.absy, op_ldx), # 0xbe
        
        (AddrMode.imm, op_cpy), # 0xc0
        (AddrMode.pindx, op_cmp), # 0xc1
        (AddrMode.imp, op_und), # 0xc2
        (AddrMode.zpg, op_cpy), # 0xc4
        (AddrMode.zpg, op_cmp), # 0xc5
        (AddrMode.zpg, op_dec), # 0xc6
        (AddrMode.imp, op_iny), # 0xc8
        (AddrMode.imm, op_cmp), # 0xc9
        (AddrMode.imp, op_dex), # 0xca
        (AddrMode.abs, op_cpy), # 0xcc
        (AddrMode.abs, op_cmp), # 0xcd
        (AddrMode.abs, op_dec), # 0xce
        (AddrMode.rel, op_bne), # 0xd0
        (AddrMode.pindy, op_cmp), # 0xd1
        (AddrMode.imp, op_und), # 0xd2
        (AddrMode.imp, op_und), # 0xd4
        (AddrMode.zpgx, op_cmp), # 0xd5
        (AddrMode.zpgx, op_dec), # 0xd6
        (AddrMode.imp, op_cld), # 0xd8
        (AddrMode.absy, op_cmp), # 0xd9
        (AddrMode.imp, op_und), # 0xda
        (AddrMode.imp, op_und), # 0xdc
        (AddrMode.absx, op_cmp), # 0xdd
        (AddrMode.absx, op_dec), # 0xde
        
        (AddrMode.imm, op_cpx), # 0xe0
        (AddrMode.pindx, op_sbc), # 0xe1
        (AddrMode.imp, op_und), # 0xe2
        (AddrMode.zpg, op_cpx), # 0xe4
        (AddrMode.zpg, op_sbc), # 0xe5
        (AddrMode.zpg, op_inc), # 0xe6
        (AddrMode.imp, op_inx), # 0xe8
        (AddrMode.imm, op_sbc), # 0xe9
        (AddrMode.imp, op_nop), # 0xea
        (AddrMode.abs, op_cpx), # 0xec
        (AddrMode.abs, op_sbc), # 0xed
        (AddrMode.abs, op_inc), # 0xee
        (AddrMode.rel, op_beq), # 0xf0
        (AddrMode.pindy, op_sbc), # 0xf1
        (AddrMode.imp, op_und), # 0xf2
        (AddrMode.imp, op_und), # 0xf4
        (AddrMode.zpgx, op_sbc), # 0xf5
        (AddrMode.zpgx, op_inc), # 0xf6
        (AddrMode.imp, op_sed), # 0xf8
        (AddrMode.absy, op_sbc), # 0xf9
        (AddrMode.imp, op_und), # 0xfa
        (AddrMode.imp, op_und), # 0xfc
        (AddrMode.absx, op_sbc), # 0xfd
        (AddrMode.absx, op_inc), # 0xfe
    ]
    
    ml.set_pc((ml.pc & 0xf00) + 0xa0 + ((ml.pc & 0xff) > 0xa0)*0x100)
    decode_8_11_table = ml.pc
    for i in range(0,96):
        ml.byte(opcode_table[i*2][0].value |(opcode_table[i*2+1][0].value<<4))
    decode_table = ml.pc
    for i in range(0,192):
        ml.byte(opcode_table[i][1] & 0xff)
    decode_12_13_table = ml.pc
    for i in range(0,48):
        ml.byte((opcode_table[i*4][1]&3) | ((opcode_table[i*4+1][1]&3)<<2) |
                ((opcode_table[i*4+2][1]&3)<<4) | ((opcode_table[i*4+3][1]&3)<<6))
    
    op_adc = ml.pc
    ml.bne(main_loop)

    op_and = ml.pc
    ml.bne(main_loop)

    op_asl = ml.pc
    ml.bne(main_loop)

    op_bcc = ml.pc
    ml.bne(main_loop)

    op_bcs = ml.pc
    ml.bne(main_loop)

    op_beq = ml.pc
    ml.bne(main_loop)

    op_bit = ml.pc
    ml.bne(main_loop)

    op_bmi = ml.pc
    ml.bne(main_loop)

    op_bne = ml.pc
    ml.bne(main_loop)

    op_bpl = ml.pc
    ml.bne(main_loop)

    op_brk = ml.pc
    ml.bne(main_loop)

    op_bvc = ml.pc
    ml.bne(main_loop)

    op_bvs = ml.pc
    ml.bne(main_loop)

    op_clc = ml.pc
    ml.bne(main_loop)

    op_cld = ml.pc
    ml.bne(main_loop)

    op_cli = ml.pc
    ml.bne(main_loop)

    op_clv = ml.pc
    ml.bne(main_loop)

    op_cmp = ml.pc
    ml.bne(main_loop)

    op_cpx = ml.pc
    ml.bne(main_loop)

    op_cpy = ml.pc
    ml.bne(main_loop)

    op_dec = ml.pc
    ml.bne(main_loop)

    op_dex = ml.pc
    ml.bne(main_loop)

    op_dey = ml.pc
    ml.bne(main_loop)

    op_eor = ml.pc
    ml.bne(main_loop)

    op_inc = ml.pc
    ml.bne(main_loop)

    op_inx = ml.pc
    ml.bne(main_loop)

    op_iny = ml.pc
    ml.bne(main_loop)

    op_jmp = ml.pc
    ml.bne(main_loop)

    op_jmpind = ml.pc
    ml.bne(main_loop)

    op_jsr = ml.pc
    ml.bne(main_loop)

    op_lda = ml.pc
    ml.bne(main_loop)

    op_ldx = ml.pc
    ml.bne(main_loop)

    op_ldy = ml.pc
    ml.bne(main_loop)

    op_lsr = ml.pc
    ml.bne(main_loop)

    op_nop = ml.pc
    ml.bne(main_loop)

    op_ora = ml.pc
    ml.bne(main_loop)

    op_pha = ml.pc
    ml.bne(main_loop)

    op_php = ml.pc
    ml.bne(main_loop)

    op_pla = ml.pc
    ml.bne(main_loop)

    op_plp = ml.pc
    ml.bne(main_loop)

    op_rol = ml.pc
    ml.bne(main_loop)

    op_ror = ml.pc
    ml.bne(main_loop)

    op_rti = ml.pc
    ml.bne(main_loop)

    op_rts = ml.pc
    ml.bne(main_loop)

    op_sbc = ml.pc
    ml.bne(main_loop)

    op_sec = ml.pc
    ml.bne(main_loop)

    op_sed = ml.pc
    ml.bne(main_loop)

    op_sei = ml.pc
    ml.bne(main_loop)

    op_sta = ml.pc
    ml.bne(main_loop)

    op_stx = ml.pc
    ml.bne(main_loop)

    op_sty = ml.pc
    ml.bne(main_loop)

    op_tax = ml.pc
    ml.bne(main_loop)

    op_tay = ml.pc
    ml.bne(main_loop)

    op_tsx = ml.pc
    ml.bne(main_loop)

    op_txa = ml.pc
    ml.bne(main_loop)

    op_txs = ml.pc
    ml.bne(main_loop)

    op_tya = ml.pc
    ml.bne(main_loop)
    
    op_crt = ml.pc
    ml.bne(main_loop)
    
    op_stp = ml.pc
    ml.bne(main_loop)

    return start

ml.assemble(gencode)

#print("decode len:", decode_end-decode)
stdout.buffer.write(ml.dump())
