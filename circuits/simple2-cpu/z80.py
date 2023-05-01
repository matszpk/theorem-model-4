from simple2_cpu_asm import *
from sys import stdout
from enum import *
import argparse

ap = argparse.ArgumentParser(prog = 'z80 simple2-cpu codegen')
ap.add_argument('-p', '--pc', type=lambda x: int(x,0), default=0)
ap.add_argument('-I', '--info', action='store_true')

args = ap.parse_args()

args = ap.parse_args()

ml = Memory()
# Order of these register is important - used while trasnferring to nargX
ml.set_pc(0xfb0)
nbr = ml.pc # 0xfb0: B
ml.byte(0, True)
ncr = ml.pc # 0xfb1: C
ml.byte(0, True)
ndr = ml.pc # 0xfb2: D
ml.byte(0, True)
ner = ml.pc # 0xfb3: E
ml.byte(0, True)
nhr = ml.pc # 0xfb4: H
ml.byte(0, True)
nlr = ml.pc # 0xfb5: L
ml.byte(0, True)
nfr = ml.pc # 0xfb6: F
ml.byte(0, True)
nar = ml.pc # 0xfb7: A
ml.byte(0, True)
nix = ml.pc # 0xfb8: IX register
ml.word16(0, [True,True])
nixl = nix+1
nixh = nix
niy = ml.pc # 0xfba: IY register
ml.word16(0, [True,True])
niyl = niy+1
niyh = niy
npc = ml.pc # 0xfbc: program counter
ml.word16(args.pc, [True,True])
nsp = ml.pc # 0xfbe: SP register
ml.word16(0, [True,True])
nspl = niy+1
nsph = niy
nbra = ml.pc # 0xfc0: B'
ml.byte(0, True)
ncra = ml.pc # 0xfc1: C'
ml.byte(0, True)
ndra = ml.pc # 0xfc2: D'
ml.byte(0, True)
nera = ml.pc # 0xfc3: E'
ml.byte(0, True)
nhra = ml.pc # 0xfc4: H'
ml.byte(0, True)
nlra = ml.pc # 0xfc5: L'
ml.byte(0, True)
nfra = ml.pc # 0xfc6: F'
ml.byte(0, True)
nara = ml.pc # 0xfc7: A'
ml.byte(0, True)

nint = ml.pc # 0xfc8: Int reg
ml.byte(0, True)
nrfm = ml.pc # 0xfc9: Int refresh reg
ml.byte(0, True)

nopfx = ml.pc # 0xfca: opcode prefix
ml.byte(0, True)
nopcode = ml.pc # 0xfcb:
ml.byte(0, True)
narg1 = ml.pc # 0xfcc:
ml.byte(0, True)
narg2 = ml.pc # 0xfcd:
ml.byte(0, True)
# displacement for indexed addressing
nidx_d = ml.pc # 0xfce:
ml.byte(0, True)
# nargs: register argument:
# for 8-bit operations:
# 0x80 - no register argument (value)
# 0x0-0x5,0x7 - register
# 0x6 - (hl) or (ix+d) or (iy+d)
# for 16-bit operations:
# 0x80 - no register argument (value)
# 0x0 - BC, 0x1 - DE, 0x2 - HL, 0x3 - AF
# 0x4 - IX, 0x5 - IY, 0x7 - SP
nargr1 = ml.pc # 0xfcf
nargr_dest = ml.pc
ml.byte(0, True)
nargr2 = ml.pc # 0xfd0
ml.byte(0, True)
bit_imm = ml.pc # 0xfd1
jcc_imm = ml.pc
rst_imm = ml.pc
ml.byte(0, True)

mem_val_lo = ml.pc   # 0xfd2
reg2_val_lo = mem_val_lo
ml.byte(0, True)
mem_val_hi = ml.pc   # 0xfd3
reg2_val_hi = mem_val_hi
ml.byte(0, True)

reg1_val_lo = ml.pc   # 0xfd4
ml.byte(0, True)
reg1_val_hi = ml.pc   # 0xfd5
ml.byte(0, True)

# addrmode:
#############
addrmode = ml.pc     # 0xfd6  addr mode
ml.byte(0, True)
addrmode2 = ml.pc
ml.byte(0, True)
mem_val_loaded = ml.pc  # 0xfd7
ml.byte(0, True)
op_16bit = ml.pc    # 0xfd8
ml.byte(0, True)

mm_mem_val = ml.pc # 0xfd9
ml.byte(0x00, True)
mm_mem_addr = ml.pc # 0xfda
ml.word16(0, [True, True])
mm_mem_temp = ml.pc # 0xfdc
ml.byte(0x00, True)
# cycles - really number T states
instr_cycles = ml.pc # 0xfdd
ml.byte(0, True)
old_instr_cycles = ml.pc  # 0xfde
ml.byte(0, True)
instr_index = ml.pc   # 0xfdf
ml.byte(0, True)

temp1 = ml.pc       # 0xfe0
ml.byte(0, True)
temp2 = ml.pc       # 0xfe1
ml.byte(0, True)
temp3 = ml.pc       # 0xfe2
ml.byte(0, True)
temp4 = ml.pc       # 0xfe3
ml.byte(0, True)
xx_keep_carry = ml.pc # 0xfe4
ml.byte(0, True)
iff1 = ml.pc         # 0xfe5
ml.byte(0, True)
iff2 = ml.pc         # 0xfe6
ml.byte(0, True)
intmode = ml.pc         # 0xfe7
ml.byte(0, True)
set_sr_flag = ml.pc     # 0xfe8
ml.byte(0, True)
io_port_lo = ml.pc     # 0xfe9
ml.byte(0, True)
io_port_hi = ml.pc     # 0xfea
ml.byte(0, True)
io_port_out = ml.pc     # 0xfeb
ml.byte(0, True)
io_port_in = ml.pc     # 0xfec
ml.byte(0, True)
idx_prefix = ml.pc      # 0xfed
ml.byte(0, True)

SRFlags = IntFlag('Flags', [ 'C', 'N', 'P', 'X', 'H', 'Y', 'Z', 'S' ]);

# should be negated in set_sr_flag
SetSRFlags = IntFlag('SetFlags', ['nsub', 'N', 'V', 'ZS', 'XY', 'H', 'C', 'P'])
SetSRFlags_all_zero_n = 0xff^SetSRFlags.nsub

class AddrMode(IntEnum):
    AMImm = 0
    AMExt = 1
    AMImmExt = 2
    AMRel = 3
    AMHL = 4
    AMDE = 5
    AMBC = 6
    AMSP = 7
    RegLow = 8      # reg1 in 0..2
    RegHigh = 16    # reg2 in 3..5
    Reg16AndSP = 32    # 16bit reg1 4..5 (BC,DE,HL,SP)
    Reg16AndAF = 64    # 16bit reg1 4..5 (BC,DE,HL,AF)
    RegSwap = 128      # swap registers (reg1<->reg2)

class AddrMode2(IntEnum):
    Imm3Bit = 1  # in opcode
    MemWrite = 2
    RegToMem = 4
    Implied = 8

child_mem_val = 0xffc
child_mem_addr = 0xffd

def gencode():
    start = 0
    ml.set_pc(start)
    # create z80 machine - memory: 16-bit address, 8-bit cell
    # use 17-bit address for additional memory mapping
    ml.lda_imm(0x11)
    ml.sta(0xffd)
    ml.lda_imm(0x30)
    ml.sta(0xffe)
    ml.lda_imm(0)
    ml.sta(0xfff)
    ml.create() # call it
    
    ml.def_label('main_loop')
    ml.lda(instr_cycles)
    ml.sta(old_instr_cycles)
    ml.lda_imm(0)
    ml.sta(instr_cycles)
    ml.sta(mem_val_loaded)
    ml.sta(op_16bit)
    ml.sta(xx_keep_carry)  # default nonzero
    ml.sta(idx_prefix)
    
    ml.lda_imm(0x80)    # no register argument
    ml.sta(nargr1)
    ml.sta(nargr2)
    
    #################################
    # code change reset
    ###################################
    ml.lda(ml.mem[ml.l('op_sub_ch') + 1 if ml.l('op_sub_ch')>=0 else 0])
    ml.sta(ml.l('op_sub_ch')+1)
    ml.lda_imm(ml.mem[ml.l('op_and_ch') if ml.l('op_and_ch')>=0 else 0])
    ml.sta(ml.l('op_and_ch'))
    
    ml.lda_imm(instr_clc)
    ml.sta('put_reg1')
    ml.sta('put_reg2')
    
    # load instruction
    # load opcode
    ml.def_label('start_decode')
    ml.cond_auto_call('load_inc_pc_opcode')
    ##############################
    # decode it
    ml.sta(nopcode)
    ml.xor_imm(0xcb)
    ml.bne('decode_x1')
    ml.bpl('bit_opcodes')
    
    ml.def_label('decode_x1')
    ml.xor_imm(0xcb^0xdd)
    ml.bne('decode_x2')
    
    ml.lda(idx_prefix)
    ml.bne('decode_unsat')
    ml.lda_imm(1)
    ml.sta(idx_prefix)
    ml.cond_jmpc('start_decode')
    
    ml.def_label('decode_x2')
    ml.xor_imm(0xdd^0xed)
    ml.bne('decode_x3')
    ml.bpl('misc_opcodes')
    
    ml.def_label('decode_x3')
    ml.xor_imm(0xed^0xfd)
    ml.bne('main_opcodes')
    
    ml.lda(idx_prefix)
    ml.bne('decode_unsat')
    ml.lda_imm(2)
    ml.sta(idx_prefix)
    ml.cond_jmpc('start_decode')
    
    # HINT: treat DD (IX) FD (IY) as replaced of HL for main opcodes.
    
    # main opcodes
    ml.def_segment('main_opcodes')
    
    ml.cond_jmpc('decode_end')
    
    # end of main opcodes
    
    # bit opcodes
    ml.def_segment('bit_opcodes')
    ml.cond_auto_call('load_inc_pc_opcode')
    ml.sta(nopcode)
    ml.ana_imm(7)
    ml.sta(nargr1)
    
    ml.lda(nopcode)
    ml.ana_imm(0xc0)
    ml.bne('no_shift_opcodes')
    # shift opcodes
    
    # bit ops opcodes
    ml.def_label('no_shift_opcodes')
    ml.sta(instr_index)
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(7)
    ml.sta(narg2)
    # end of bit opcodes
    
    # misc opcodes
    ml.def_segment('misc_opcodes')
    
    #################################
    # decode addressing mode
    ml.lda(addrmode)
    ml.xor_imm(0xff)
    ml.sta(temp4)
    ml.ana_imm(AddrMode.RegLow)
    ml.bne('amdec_no_reglow')
    ml.lda(nopcode)
    ml.ana_imm(7)
    ml.sta(nargr1)
    ml.def_label('amdec_no_reglow')
    
    ml.lda(temp4)
    ml.ana_imm(AddrMode.RegHigh)
    ml.bne('amdec_no_reghigh')
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(7)
    ml.sta(nargr2)
    ml.def_label('amdec_no_reghigh')
    
    # swap regs
    ml.lda(temp4)
    ml.ana_imm(AddrMode.RegSwap)
    ml.bne('amdec_no_regswap')
    ml.lda(nargr1)
    ml.sta(temp1)
    ml.lda(nargr2)
    ml.sta(nargr1)
    ml.lda(temp1)
    ml.sta(nargr2)
    ml.def_label('amdec_no_regswap')
    
    ml.lda(temp4)
    ml.ana_imm(AddrMode.Reg16AndAF|AddrMode.Reg16AndSP)
    ml.bne('amdec_no_reg16_and_af')
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(3)
    ml.sta(nargr1)
    ml.xor_imm(3)
    ml.bne('amdec_no_reg16_and_af') # if not AF
    ml.lda(temp4)
    ml.ana_imm(AddrMode.Reg16AndSP)
    ml.bne('amdec_no_reg16_and_sp')
    ml.lda(nargr1)  # fix for SP
    ml.ora_imm(4)
    ml.sta(nargr1)
    ml.def_label('amdec_no_reg16_and_sp')
    ml.def_label('amdec_no_reg16_and_af')
    
    ml.lda(addrmode2)
    ml.xor_imm(0xff)
    ml.sta(temp4)
    ml.ana_imm(AddrMode2.Imm3Bit)
    ml.bne('am2dec_no_imm3bit')
    ml.lda(nopcode)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(7)
    ml.sta(bit_imm)
    ml.def_label('am2dec_no_imm3bit')
    
    #################################
    # fix for indexes
    # fix and check operation
    ml.lda(idx_prefix)
    ml.bne('do_idx_fix')
    ml.bpl('no_idx_fix')
    ml.def_label('do_idx_fix')
    
    ml.lda(nopcode)
    ml.xor_imm(0xeb)
    ml.bne('do_idx_fix2')
    ml.bpl('decode_unsat')
    
    ml.def_label('do_idx_fix2')
    ml.lda(op_16bit)
    ml.bne('idx_fix_16_bit_reg')
    ml.lda(nargr1)
    ml.def_label('idx_check_reg')
    ml.xor_imm(0x6)         # (HL)
    ml.bne('no_idx_fix_8bit_narg1')
    ml.bpl('no_idx_fix')    # good. no fix needed
    ml.def_label('no_idx_fix_8bit_narg1')
    ml.lda(nargr2)
    ml.xor_imm(0x6)         # (HL)
    ml.bne('decode_unsat')  # undefined instruction
    ml.bpl('no_idx_fix')    # good. no fix needed
    
    ml.def_segment('idx_fix_16_bit_reg')
    ml.lda(nargr1)
    ml.xor_imm(0x2)
    ml.bne('no_idx_fix_16bit_narg1')
    # fix reg arg1
    ml.lda_imm(3)
    ml.cond_clc()
    ml.adc(idx_prefix)  # to 4 or 5 (IX or IY)
    ml.sta(nargr1)
    ml.cond_jmpc('idx_fix_16_bit_reg_end')
    
    ml.def_segment('no_idx_fix_16bit_narg1')
    ml.lda(nargr2)
    ml.xor_imm(0x2)
    ml.bne('decode_unsat')
    # fix reg arg2
    ml.lda_imm(3)
    ml.cond_clc()
    ml.adc(idx_prefix)  # to 4 or 5 (IX or IY)
    ml.sta(nargr2)
    
    ml.def_label('idx_fix_16_bit_reg_end')
    ml.def_label('no_idx_fix')
    
    ##################################
    # end of decode
    ml.def_label('decode_end')
    
    ####################################
    # put registers
    ml.clc()
    ml.lda(op_16bit)
    ml.bne('put_reg_16')
    ml.lda_imm(instr_ror)
    ml.sta('put_reg1')
    ml.sta('put_reg2')
    ml.def_label('put_reg_16')
    
    ml.lda(nargr1)
    ml.bpl('put_reg1')
    ml.bcc('no_put_reg1')
    ml.def_segment('put_reg1')
    ml.clc(True)
    ml.ora_imm(nbr&0xff)
    ml.sta(ml.l('put_reg1_ch')+1)
    ml.adc(1)
    ml.sta(ml.l('put_reg1_ch2')+1)
    ml.def_label('put_reg1_ch')
    ml.lda(nbr, [False,True])
    ml.sta(reg1_val_lo)
    ml.def_label('put_reg1_ch2')
    ml.lda(nbr, [False,True])
    ml.sta(reg1_val_hi)
    
    ml.def_label('no_put_reg1')
    ml.lda(nargr2)
    ml.bpl('put_reg2')
    ml.bcc('no_put_reg2')
    ml.def_segment('put_reg2')
    ml.clc(True)
    ml.ora_imm(nbr&0xff)
    ml.sta(ml.l('put_reg2_ch')+1)
    ml.adc(1)
    ml.sta(ml.l('put_reg2_ch2')+1)
    ml.def_label('put_reg2_ch')
    ml.lda(nbr, [False,True])
    ml.sta(reg2_val_lo)
    ml.def_label('put_reg2_ch2')
    ml.lda(nbr, [False,True])
    ml.sta(reg2_val_hi)
    
    ml.def_label('no_put_reg2')
    
    ##################################
    # addressing modes
    ##################################
    ml.def_segment('am_code_start')
    
    ml.def_segment('am_ext_imm')
    ml.lda(narg2)
    ml.sta(mem_val_hi)
    
    ml.def_label('am_imm')
    ml.lda(narg1)
    ml.sta(mem_val_lo)
    ml.lda_imm(1)
    ml.sta(mem_val_loaded)
    ml.cond_jmpc('am_code_end')
    
    ml.def_segment('am_rel')
    ml.lda(narg1)
    ml.cond_clc()
    ml.rol()
    ml.lda_imm(0)
    ml.bcc('am_rel_no_sign_ext')
    ml.lda_imm(0xff)    # finaly is sign extension
    ml.def_label('am_rel_no_sign_ext')
    ml.sta(temp1)
    ml.lda(npc)
    ml.clc()
    ml.adc(narg1)
    ml.sta(child_mem_addr)
    ml.lda(npc+1)
    ml.adc(temp1)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_segment('am_ext')
    ml.lda(narg1)
    ml.sta(child_mem_addr)
    ml.lda(narg2)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_segment('am_hl')
    ml.lda(idx_prefix)
    ml.xor_imm(1)
    ml.bne('am_hl_no_ix')
    # IX index addressing
    ml.lda(nix)
    ml.cond_clc()
    ml.adc(nidx_d)
    ml.sta(child_mem_addr)
    ml.lda(nix+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_label('am_hl_no_ix')
    ml.xor_imm(1^2)
    ml.bne('am_hl_no_iy')
    # IY index addressing
    ml.lda(niy)
    ml.cond_clc()
    ml.adc(nidx_d)
    ml.sta(child_mem_addr)
    ml.lda(niy+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_label('am_hl_no_iy')
    ml.lda(nlr)
    ml.cond_jmpc('am_indreg_prep')
    
    ml.def_segment('am_bc')
    ml.lda(ncr)
    ml.cond_jmpc('am_indreg_prep')
    
    ml.def_segment('am_de')
    ml.lda(ner)
    ml.cond_jmpc('am_indreg_prep')
    
    ml.def_segment('am_sp')
    ml.lda(nspl)
    ml.def_label('am_indreg_prep')
    ml.sta(ml.l('am_indreg')+1)
    
    ml.def_label('am_indreg')
    ml.lda(nsp,[False,True])
    ml.sta(child_mem_addr)
    ml.lda(ml.l('am_indreg')+1)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(ml.l('am_indreg_ch')+1)
    ml.def_label('am_indreg_ch')
    ml.lda(nsp+1,[False, True])
    ml.sta(child_mem_addr+1)
    
    ml.def_label('am_code_end')
    ####################################
    
    ml.def_routine('push_arg','store_mem_arg')
    ml.lda(op_16bit)
    ml.xor_imm(1)
    ml.ror()        # to carry, XORed
    ml.lda(nspl)
    ml.sbc_imm(1)
    ml.sta(nspl)
    ml.sta(child_mem_addr)
    ml.lda(nsph)
    ml.sbc_imm(0)
    ml.sta(nsph)
    ml.sta(child_mem_addr+1)
    ml.cond_lastcall('store_mem_arg')
    
    ml.def_routine('pop_arg')
    ml.lda(nspl)
    ml.sta(child_mem_addr)
    ml.lda(nsph)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_reg_arg')
    ml.lda(op_16bit)
    ml.ror()        # to carry
    ml.lda(nspl)
    ml.adc_imm(1)
    ml.sta(nspl)
    ml.lda(nsph)
    ml.adc_imm(0)
    ml.sta(nsph)
    ml.cond_ret()
    
    ml.def_routine('store_mem_arg')
    ml.lda(mem_val_lo)
    ml.sta(mm_mem_val)
    ml.cond_auto_call('store_mem_val')
    ml.lda(op_16bit)
    ml.bpl('store_mem_arg_end')
    ml.lda(child_mem_addr)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(child_mem_addr)
    ml.lda(child_mem_addr+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.lda(mem_val_hi)
    ml.sta(mm_mem_val)
    ml.cond_auto_call('store_mem_val')
    ml.def_label('store_mem_arg_end')
    ml.cond_ret()
    
    ml.def_routine('load_reg_arg')
    ml.cond_auto_call('load_mem_val')
    ml.sta(reg1_val_lo)
    ml.lda(op_16bit)
    ml.bpl('load_reg_arg_end')
    ml.lda(child_mem_addr)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(child_mem_addr)
    ml.lda(child_mem_addr+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_mem_val')
    ml.sta(reg1_val_hi)
    ml.def_label('load_reg_arg_end')
    ml.cond_ret()
    
    #############################################
    # set flags
    ml.def_segment('set_flags')
    
    ml.sta(set_sr_flag)
    ml.ana_imm(SetSRFlags.XY)
    ml.bne('set_flags_skip_xy')
    ml.lda(temp1)
    ml.ana_imm(0xff^SRFlags.X^SRFlags.Y)
    ml.sta(temp2)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.X^SRFlags.Y)
    ml.ora(temp2)
    ml.sta(nfr)
    ml.def_label('set_flags_skip_xy')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.C)
    ml.bne('set_flags_skip_C')
    ml.rol()
    ml.xor_imm(set_sr_flag)     # SetSRFlags.SUB = 1, xor carry
    ml.ror()
    ml.lda(nfr)
    ml.ana_imm(0xfe)
    ml.adc_imm(0)   # set carry
    ml.sta(nfr)
    ml.def_label('set_flags_skip_C')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.C)
    ml.bne('set_flags_skip_V')
    ml.lda(nfr)
    ml.bvc('set_flags_no_overflow')
    ml.ora_imm(SRFlags.P)
    ml.cond_jmpc('set_flags_no_overflow_end')
    ml.def_segment('set_flags_no_overflow')
    ml.ana_imm(0xff^SRFlags.P)
    ml.def_label('set_flags_no_overflow_end')
    ml.sta(nfr)
    ml.def_label('set_flags_skip_V')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.H)
    ml.bne('set_flags_skip_H')
    # set half carry
    ml.lda(temp1)   # temp result
    ml.xor(temp2)   # second argument
    ml.xor(temp3)   # first argument
    ml.ana_imm(0x10)
    ml.sta(temp2)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H)
    ml.ora(temp2)
    ml.sta(nfr)
    ml.def_label('set_flags_skip_H')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.P)
    ml.bne('set_flags_skip_P')
    ml.lda(temp1)
    ml.sta(temp3)   # rolled value of temp1
    ml.sta(temp4)   # value of count of one bits in 7 bit
    ml.lda_imm(7)
    ml.sta(temp2)
    ml.def_label('set_flags_ploop')
    ml.lda(temp3)
    ml.rol()
    ml.sta(temp3)
    ml.xor(temp4)
    ml.sta(temp4)
    ml.lda(temp2)
    ml.clc()
    ml.sbc_imm(0)
    ml.sta(temp2)
    ml.bne('set_flags_ploop')
    ml.lda(temp4)
    ml.bpl('set_flags_pset')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.P)
    ml.cond_jmpc('set_flags_p_end')
    ml.def_segment('set_flags_pset')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.P)
    ml.def_label('set_flags_p_end')
    ml.sta(nfr)
    ml.def_label('set_flags_skip_P')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.ZS)
    ml.bne('set_flags_skip_ZS')
    
    ml.lda(temp1)
    ml.bne('set_flags_zs_nozero')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.Z)
    ml.sta(nfr)
    ml.cond_jmpc('set_flags_zs_nozero_end')
    ml.def_segment('set_flags_zs_nozero')
    ml.bpl('set_flags_zs_positive')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.Z|SRFlags.S)
    ml.sta(nfr)
    ml.cond_jmpc('set_flags_zs_nozero_end')
    ml.def_segment('set_flags_zs_positive')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.Z)
    ml.ana_imm(0xff^SRFlags.S)
    ml.sta(nfr)
    ml.def_label('set_flags_zs_nozero_end')
    ml.def_label('set_flags_skip_ZS')
    
    ml.lda(set_sr_flag)
    ml.ana_imm(SetSRFlags.ZS)
    ml.bne('set_flags_skip_N')
    ml.lda(set_sr_flag)
    ml.rol()    # to N
    ml.ana_imm(0xff^SRFlags.N)
    ml.sta(temp4)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.N)
    ml.ora(temp4)
    ml.sta(nfr)
    ml.def_label('set_flags_skip_N')
    
    ml.cond_jmpc('ops_code_end')
    # end set flags
    #############################################
    
    #######################################
    # ops_code - operations code
    ml.def_segment('ops_code_start')
    
    ml.def_segment('op_ex_sp_xx')
    ml.lda(reg1_val_lo)
    ml.sta(mm_mem_val)
    ml.cond_auto_call('store_mem_val')
    ml.lda(child_mem_addr)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.lda(child_mem_addr)
    ml.lda(child_mem_addr+1)
    ml.adc_imm(0)
    ml.lda(child_mem_addr+1)
    ml.lda(reg1_val_hi)
    ml.sta(mm_mem_val)
    ml.cond_auto_call('store_mem_val')
    
    ml.def_label('op_ld16_from_mem')
    ml.lda(mem_val_hi)
    ml.sta(reg1_val_hi)
    
    ml.def_label('op_ld_from_mem')
    ml.lda(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_label('op_end_with_store')
    ml.def_label('op_ld16_to_mem')
    ml.def_label('op_ld_to_mem')
    ml.cond_auto_call('store_mem_arg')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_ld_a_i')
    ml.def_segment('op_ld_a_r')
    ml.lda(nopcode)
    ml.ana_imm(0x08) # one if LD A,R
    ml.bne('op_if_ld_a_r')
    ml.lda(nint)
    ml.cond_jmpc('op_if_ld_a_r_end')
    ml.def_segment('op_if_ld_a_r')
    ml.lda(nrfm)
    ml.def_label('op_if_ld_a_r_end')
    ml.sta(nar)
    
    ml.lda(iff2)
    ml.ana_imm(SRFlags.H^SRFlags.P)   # must be 0xff in iff2
    ml.ora(nfr)
    ml.sta(nfr)
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.XY^SetSRFlags.ZS^SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_ld_r_a')
    ml.lda(nar)
    ml.sta(nrfm)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_ld_i_a')
    ml.lda(nar)
    ml.sta(nint)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_push')
    ml.lda(reg1_val_lo)
    ml.sta(mem_val_lo)
    ml.lda(reg1_val_hi)
    ml.sta(mem_val_hi)
    ml.cond_auto_call('push_arg')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_pop')
    ml.cond_auto_call('pop_arg')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_ex_af_aafa')
    ml.lda(nfr)
    ml.sta(temp1)
    ml.lda(nfra)
    ml.sta(nfr)
    ml.lda(temp1)
    ml.sta(nfra)
    
    ml.lda(nar)
    ml.sta(temp1)
    ml.lda(nara)
    ml.sta(nar)
    ml.lda(temp1)
    ml.sta(nara)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_ex_de_hl')
    ml.lda(ner)
    ml.sta(temp1)
    ml.lda(nlr)
    ml.sta(ner)
    ml.lda(temp1)
    ml.sta(nlr)
    
    ml.lda(ndr)
    ml.sta(temp1)
    ml.lda(nhr)
    ml.sta(ndr)
    ml.lda(temp1)
    ml.sta(nhr)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_exx')
    ml.lda_imm(nbr)
    ml.sta(ml.l('exx_loop')+1)
    ml.sta(ml.l('exx_loop3')+1)
    ml.lda_imm(nbra)
    ml.sta(ml.l('exx_loop2')+1)
    ml.sta(ml.l('exx_loop4')+1)
    
    ml.def_label('exx_loop')
    ml.lda(nbr,[False,True])
    ml.sta(temp1)
    ml.def_label('exx_loop_2')
    ml.lda(nbra,[False,True])
    ml.def_label('exx_loop_3')
    ml.sta(nbr,[False,True])
    ml.lda(temp1)
    ml.def_label('exx_loop_4')
    ml.sta(nbra,[False,True])
    
    ml.lda(ml.l('exx_loop')+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(ml.l('exx_loop')+1)
    ml.sta(ml.l('exx_loop3')+1)
    ml.lda(ml.l('exx_loop2')+1)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(ml.l('exx_loop2')+1)
    ml.sta(ml.l('exx_loop4')+1)
    ml.xor_imm(nfra)
    ml.bne('exx_loop')
    
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_lddr')
    ml.def_segment('op_ldd')
    ml.def_segment('op_ldir')
    ml.def_segment('op_ldi')
    ml.lda(nlr)
    ml.sta(child_mem_addr)
    ml.lda(nhr)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_mem_val')
    ml.sta(mm_mem_val)
    ml.lda(ner)
    ml.sta(child_mem_addr)
    ml.lda(ndr)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('store_mem_val')
    
    ml.cond_auto_call('op_str_ch_hl')
    
    # incdec HL and BC
    ml.lda(nopcode)
    ml.ana_imm(8)
    ml.cond_clc()
    ml.ror()
    ml.ror()
    ml.ora_imm(ml.l('op_str_data'))
    ml.sta(ml.l('op_ldi_str_ch1')+1)
    ml.ora_imm(ml.l('op_str_data'))
    ml.sta(ml.l('op_ldi_str_ch1')+1)
    
    ml.lda(ner)
    #ml.cond_clc()
    ml.def_label('op_ldi_str_ch1')
    ml.adc(ml.l('op_str_data'),[False,True])
    ml.sta(ner)
    ml.lda(ndr)
    ml.def_label('op_ldi_str_ch2')
    ml.adc(ml.l('op_str_data'),[False,True])
    ml.sta(ndr)
    
    ml.lda(ncr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(ncr)
    ml.lda(nbr)
    ml.sbc_imm(0)
    ml.sta(nbr)
    
    ml.ora(ncr)
    ml.bne('op_ldi_no_end')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H^SRFlags.N)
    ml.ora_imm(int(SRFlags.P))
    ml.sta(nfr)
    ml.cond_jmpc('op_ldi_end')
    ml.def_segment('op_ldi_no_end')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H^SRFlags.N^SRFlags.P)
    ml.sta(nfr)
    ml.def_label('op_ldi_flag_end')
    
    ml.lda(nopcode)
    ml.xor_imm(0x10)
    ml.ana_imm(0x10)    # 'XXXR' code
    ml.bne('op_ldi_end')
    
    # move back PC
    ml.lda(npc)
    ml.cond_clc()
    ml.sbc_imm(1)
    ml.sta(npc)
    ml.lda(npc+1)
    ml.sbc_imm(0)
    ml.sta(npc+1)
    
    ml.def_label('op_ldi_end')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_routine('op_str_ch_hl')
    # incdec HL and BC
    ml.lda(nopcode)
    ml.ana_imm(8)
    ml.cond_clc()
    ml.ror()
    ml.ror()
    ml.ora_imm(ml.l('op_str_data'))
    ml.sta(ml.l('op_str_ch1')+1)
    ml.ora_imm(ml.l('op_str_data'))
    ml.sta(ml.l('op_str_ch1')+1)
    
    ml.lda(nlr)
    #ml.cond_clc()
    ml.def_label('op_str_ch1')
    ml.adc(ml.l('op_str_data'),[False,True])
    ml.sta(nlr)
    ml.lda(nhr)
    ml.def_label('op_str_ch2')
    ml.adc(ml.l('op_str_data'),[False,True])
    ml.sta(nhr)
    ml.cond_ret()
    
    ml.def_segment('op_cpdr')
    ml.def_segment('op_cpd')
    ml.def_segment('op_cpir')
    ml.def_segment('op_cpi')
    ml.lda(nlr)
    ml.sta(child_mem_addr)
    ml.lda(nhr)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_mem_val')
    ml.sta(temp2)
    ml.lda(nar)
    ml.cond_sec()
    ml.sbc(temp2) # for H flag
    ml.sta(temp1)
    ml.lda(nar)
    ml.sta(temp3) # for H flag
    
    ml.cond_auto_call('op_str_ch_hl')
    
    ml.lda(ncr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(ncr)
    ml.lda(nbr)
    ml.sbc_imm(0)
    ml.sta(nbr)
    
    ml.ora(ncr)
    ml.bne('op_cpi_no_end')
    ml.lda(nfr)
    ml.ora_imm(int(SRFlags.P))
    ml.sta(nfr)
    ml.cond_jmpc('op_cpi_end')
    ml.def_segment('op_cpi_no_end')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.P)
    ml.sta(nfr)
    ml.def_label('op_cpi_flag_end')
    
    ml.lda(nopcode)
    ml.xor_imm(0x10)
    ml.ana_imm(0x10)    # 'XXXR' code
    ml.bne('op_cpi_end')
    ml.lda(nfr)
    ml.ana_imm(SRFlags.Z)
    ml.bne('op_cpi_end')
    
    # move back PC
    ml.lda(npc)
    ml.cond_clc()
    ml.sbc_imm(1)
    ml.sta(npc)
    ml.lda(npc+1)
    ml.sbc_imm(0)
    ml.sta(npc+1)
    
    ml.def_label('op_cpi_end')
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.H^SetSRFlags.N^
               SetSRFlags.nsub)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_add')
    ml.cond_clc()
    ml.def_label('op_add_cont')
    ml.lda(mem_val_lo)
    ml.sta(temp3)
    ml.lda(reg1_val_lo)
    ml.sta(temp2)
    ml.adc(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.sta(temp1)
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.V^SetSRFlags.C^
               SetSRFlags.N^SetSRFlags.H^SetSRFlags.XY)
    ml.xor_imm(xx_keep_carry)  # xor SetSRFlags.C
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_adc')
    ml.lda(nfr) # get carry
    ml.ror()
    ml.cond_jmpc('op_add_cont')
    
    ml.def_segment('op_cp')
    # change address of store to temp4 - do not update register
    ml.lda(temp4&0xff)
    ml.sta(ml.l('op_sub_ch')+1)
    
    ml.def_segment('op_sub')
    ml.cond_sec()
    ml.def_label('op_sub_cont')
    ml.lda(mem_val_lo)
    ml.sta(temp3)
    ml.lda(reg1_val_lo)
    ml.sta(temp2)
    ml.sbc(mem_val_lo)
    # for change code point - for op_cp - changed then we have CP
    ml.def_label('op_sub_ch')
    ml.sta(reg1_val_lo, [False, True])
    ml.sta(temp1)
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.V^SetSRFlags.C^
                SetSRFlags.nsub^SetSRFlags.N^SetSRFlags.H^SetSRFlags.XY)
    ml.xor_imm(xx_keep_carry)  # xor SetSRFlags.C
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_sbc')
    ml.lda(nfr) # get carry
    ml.xor_imm(1)   # xor carry -> borrw
    ml.ror()
    ml.cond_jmpc('op_sub_cont')
    
    ml.def_segment('op_or')
    ml.lda_imm((instr_ora|instr_addr(mem_val_lo))&0xff)
    ml.sta(ml.l('op_and_ch'))
    
    ml.def_segment('op_and')
    ml.lda(reg1_val_lo)
    ml.def_label('op_and_ch')
    ml.ana(mem_val_lo, [True, False])
    ml.sta(reg1_val_lo)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H^SRFlags.C)
    ml.sta(nfr)
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.XY^SetSRFlags.P^
               SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_xor')
    ml.lda_imm((instr_xor|instr_addr(mem_val_lo))&0xff)
    ml.sta(ml.l('op_and_ch'))
    ml.cond_jmpc('op_and')
    
    ml.def_segment('op_inc')
    ml.lda_imm(SetSRFlags.C)
    ml.sta(xx_keep_carry)
    ml.lda_imm(1)
    ml.sta(mem_val_lo)
    ml.cond_jmpc('op_add')
    
    ml.def_segment('op_dec')
    ml.lda_imm(SetSRFlags.C)
    ml.sta(xx_keep_carry)
    ml.lda_imm(1)
    ml.sta(mem_val_lo)
    ml.cond_jmpc('op_sub')
    
    # DAA
    ml.def_segment('op_daa')
    ml.lda(nar)
    ml.cond_sec()
    ml.sbc_imm(0x9a)
    ml.bcc('op_daa_zero_correct')
    ml.lda(nfr)
    ml.ana_imm(SRFlags.C)   # carry
    ml.bne('op_daa_zero_correct')
    ml.ora_imm(SRFlags.C)
    ml.sta(nfr)
    ml.lda_imm(0x60)
    ml.cond_jmpc('op_daa_correct_end')
    ml.def_segment('op_daa_zero_correct')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.C)
    ml.sta(nfr) # clear carry
    ml.lda_imm(0)
    ml.def_label('op_daa_correct_end')
    ml.sta(temp4)
    
    ml.lda(nar)
    ml.ana_imm(0xf)
    ml.cond_sec()
    ml.sbc_imm(0x0a)
    ml.bcc('op_daa_h_correct_end')
    ml.lda_imm(6)
    ml.cond_clc()
    ml.adc(temp4)
    ml.sta(temp4)
    ml.def_label('op_daa_h_correct_end')
    
    # negate if N
    ml.lda(nfr)
    ml.ana_imm(SRFlags.N)
    ml.bne('op_daa_sub')
    ml.lda(nar)
    ml.cond_clc()
    ml.adc(temp4)
    ml.cond_jmpc('op_daa_sub_end')
    ml.def_segment('op_daa_sub')
    ml.lda(nar)
    ml.cond_sec()
    ml.sbc(temp4)
    ml.def_label('op_daa_sub_end')
    ml.sta(nar)
    ml.sta(temp1)
    
    ml.lda_imm((SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.P^SetSRFlags.H))
    ml.cond_jmp('set_flags')
    
    
    ml.def_segment('op_cpl')
    ml.lda(nar)
    ml.xor_imm(0xff)
    ml.sta(nar)
    ml.sta(temp1)
    ml.lda(nfr)
    ml.ora_imm(SRFlags.H)
    ml.sta(nfr)
    ml.lda_imm((SetSRFlags_all_zero_n^SetSRFlags.XY))
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_neg')
    ml.lda(nar)
    ml.sta(mem_val_lo)
    ml.lda_imm(0)
    ml.sta(reg1_val_lo)
    ml.cond_jmpc('op_sub')
    
    ml.def_segment('op_ccf')
    ml.lda(nfr)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.rol()
    ml.ana_imm(0x10)
    ml.ora(nfr)
    ml.ana_imm(0xff^SRFlags.C)
    ml.sta(nfr)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_scf')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.C)
    ml.ana_imm(0xff^SRFlags.H)
    ml.sta(nfr)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_nop')
    ml.def_segment('op_halt')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_im 0')
    ml.lda_imm(0)
    ml.sta(intmode)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_im 1')
    ml.lda_imm(1)
    ml.sta(intmode)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_im 2')
    ml.lda_imm(2)
    ml.sta(intmode)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_di')
    ml.lda_imm(0)
    ml.sta(iff1)
    ml.sta(iff2)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_ei')
    ml.lda_imm(0xff)
    ml.sta(iff1)
    ml.sta(iff2)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_adc_16')
    ml.lda(nfr)
    ml.ror()
    ml.lda(reg1_val_lo)
    ml.adc(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.lda(mem_val_hi)
    ml.sta(temp3)
    ml.lda(reg1_val_hi)
    ml.sta(temp2)
    ml.adc(mem_val_hi)
    ml.sta(reg1_val_hi)
    ml.sta(temp1)
    
    ml.lda_imm(0)
    ml.def_label('op_adc_16_end')
    ml.sta(temp4)
    
    ml.lda(reg1_val_lo)
    ml.xor_imm(0xff)
    ml.bne('op_adc_16_no_z_fix')
    ml.lda(temp1)
    ml.ora_imm(2)
    ml.sta(temp1)
    ml.def_label('op_adc_16_no_z_fix')
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.XY^SetSRFlags.ZS^SetSRFlags.V^SetSRFlags.C^
                    SetSRFlags.N^SetSRFlags.H)
    ml.xor_imm(temp4)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_sbc_16')
    ml.lda(nfr)
    ml.ror()
    ml.xor_imm(1)
    ml.lda(reg1_val_lo)
    ml.sbc(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.lda(mem_val_hi)
    ml.sta(temp3)
    ml.lda(reg1_val_hi)
    ml.sta(temp2)
    ml.sbc(mem_val_hi)
    ml.sta(reg1_val_hi)
    ml.sta(temp1)
    
    ml.lda_imm(SetSRFlags.nsub)
    ml.cond_jmp('op_adc_16')
    
    ml.def_segment('op_add_16')
    ml.cond_clc()
    ml.lda(reg1_val_lo)
    ml.adc(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.lda(mem_val_hi)
    ml.sta(temp3)
    ml.lda(reg1_val_hi)
    ml.sta(temp2)
    ml.adc(mem_val_hi)
    ml.sta(reg1_val_hi)
    ml.sta(temp1)
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.XY^SetSRFlags.C^SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_inc_16')
    ml.lda(reg1_val_lo)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(reg1_val_lo)
    ml.lda(reg1_val_hi)
    ml.adc_imm(0)
    ml.sta(reg1_val_hi)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_dec_16')
    ml.lda(reg1_val_lo)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(reg1_val_lo)
    ml.lda(reg1_val_hi)
    ml.sbc_imm(0)
    ml.sta(reg1_val_hi)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_rlca')
    ml.lda(nar)
    ml.rol()
    ml.def_label('op_rlca_end2')
    ml.lda(nar)
    ml.rol()
    ml.def_label('op_rlca_end')
    ml.sta(nar)
    ml.lda_imm((SetSRFlags_all_zero_n^SetSRFlags.XY^SetSRFlags.N))
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_rla')
    ml.lda(nfr)
    ml.ror()
    ml.cond_jmp('op_rlca_end2')
    
    ml.def_segment('op_rrca')
    ml.lda(nar)
    ml.ror()
    ml.def_label('op_rrca_end2')
    ml.lda(nar)
    ml.ror()
    ml.cond_jmp('op_rlca_end')
    
    ml.def_segment('op_rra')
    ml.lda(nfr)
    ml.ror()
    ml.cond_jmp('op_rrca_end2')
    
    ml.def_segment('op_rlc')
    ml.lda(reg1_val_lo)
    ml.rol()
    ml.def_label('op_rlc_end2')
    ml.lda(reg1_val_lo)
    ml.rol()
    ml.def_label('op_rlc_end')
    ml.sta(reg1_val_lo)
    ml.sta(temp1)
    ml.ror()
    ml.lda(nfr)
    ml.ana_imm(0xfe^SRFlags.H)
    ml.sta(nfr)
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.P^SetSRFlags.XY^
               SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_rl')
    ml.lda(nfr)
    ml.ror()
    ml.cond_jmp('op_rlc_end2')
    
    ml.def_segment('op_rrc')
    ml.lda(reg1_val_lo)
    ml.ror()
    ml.def_label('op_rrc_end2')
    ml.lda(reg1_val_lo)
    ml.ror()
    ml.cond_jmp('op_rlc_end')
    
    ml.def_segment('op_rr')
    ml.lda(nfr)
    ml.ror()
    ml.cond_jmp('op_rlc_end')
    
    ml.def_segment('op_sla')
    ml.cond_clc()
    ml.lda(reg1_val_lo)
    ml.rol()
    ml.cond_jmp('op_rlc_end')
    
    ml.def_segment('op_sra')
    ml.lda(reg1_val_lo)
    ml.rol()
    ml.cond_jmp('op_rrc_end2')
    
    ml.def_segment('op_srl')
    ml.cond_clc()
    ml.lda(reg1_val_lo)
    ml.ror()
    ml.cond_jmp('op_rlc_end')
    
    ml.def_segment('op_rld')
    ml.lda(nar)
    ml.ana_imm(0xf)
    ml.sta(temp2)
    ml.lda(nar)
    ml.ana_imm(0xf0)
    ml.sta(nar)
    ml.lda(mem_val_lo)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(0xf)
    ml.ora(nar)
    ml.sta(nar)
    ml.sta(temp1)
    ml.lda(mem_val_lo)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.rol()
    ml.ana_imm(0xf0)
    ml.def_label('op_rld_end')
    ml.ora(temp2)
    ml.sta(mem_val_lo)
    
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H)
    ml.sta(nfr)
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.P^SetSRFlags.XY^
               SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_rrd')
    ml.lda(nar)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.rol()
    ml.ana_imm(0xf0)
    ml.sta(temp2)
    ml.lda(nar)
    ml.ana_imm(0xf0)
    ml.sta(nar)
    ml.lda(mem_val_lo)
    ml.ana_imm(0xf)
    ml.ora(nar)
    ml.sta(nar)
    ml.sta(temp1)
    ml.lda(mem_val_lo)
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ror()
    ml.ana_imm(0xf)
    ml.cond_jmp('op_rld_end')
    
    ml.def_segment('op_bit')
    ml.lda(bit_imm)
    ml.ora_imm(ml.l('bit_table')&0xff)
    ml.sta(ml.l('op_bit_ch')+1)
    ml.lda(reg1_val_lo)
    ml.def_label('op_bit_ch')
    ml.ana(ml.l('bit_table'), [False, True])
    ml.sta(temp1)
    ml.bne('op_bit_nozero')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.P)
    ml.cond_jmp('op_bit_zero_end')
    ml.def_label('op_bit_nozero')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.P)
    ml.def_label('op_bit_zero_end')
    ml.ora_imm(SRFlags.H)
    ml.sta(nfr)
    ml.lda(reg1_val_lo)
    ml.ana_imm(0xff^SRFlags.X^SRFlags.Y)
    ml.sta(temp2)
    ml.lda(nfr)
    ml.ana_imm(SRFlags.X^SRFlags.Y)
    ml.ora(temp2)
    ml.sta(nfr)
    
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^ SetSRFlags.N)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_set')
    ml.lda(bit_imm)
    ml.ora_imm(ml.l('bit_table')&0xff)
    ml.sta(ml.l('op_set_ch')+1)
    ml.lda(reg1_val_lo)
    ml.def_label('op_set_ch')
    ml.ora(ml.l('bit_table'), [False, True])
    ml.sta(reg1_val_lo)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_res')
    ml.lda(bit_imm)
    ml.ora_imm(ml.l('bit_table')&0xff)
    ml.sta(ml.l('op_res_ch')+1)
    ml.def_label('op_res_ch')
    ml.lda(ml.l('bit_table'), [False, True])
    ml.xor_imm(0xff)
    ml.ana(reg1_val_lo)
    ml.sta(reg1_val_lo)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_jr_e')
    ml.def_segment('op_jp')
    ml.lda(mem_val_lo)
    ml.sta(npc)
    ml.lda(mem_val_hi)
    ml.sta(npc+1)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_call')
    ml.lda(npc)
    ml.sta(mem_val_lo)
    ml.lda(npc)
    ml.sta(mem_val_hi)
    ml.cond_auto_call('push_arg')
    ml.cond_jmpc('op_jp')
    
    ml.def_segment('op_ret')
    ml.cond_auto_call('pop_arg')
    ml.lda(reg1_val_lo)
    ml.sta(mem_val_lo)
    ml.lda(reg1_val_hi)
    ml.sta(mem_val_hi)
    ml.cond_jmpc('op_jp')
    
    ml.def_routine('cond_get')
    ml.lda(jcc_imm)
    ml.ror()
    ml.ana_imm(3)
    ml.ora_imm(ml.l('jcc_table')&0xff)
    ml.sta(ml.l('cond_get_ch')+1)
    
    ml.lda(nfr)
    ml.bcc('cond_get_skip_neg')
    ml.xor_imm(0xff)
    ml.def_label('cond_get_skip_neg')
    ml.def_label('cond_get_ch')
    ml.ana(ml.l('jcc_table'),[False,True])
    # zero - if satisfied, nonzero if unsatisfied
    ml.cond_ret()
    
    ml.def_segment('op_jp_cc')
    ml.cond_auto_call('cond_get')
    ml.bne('ops_code_end')
    ml.bpl('op_jp')
    
    ml.def_segment('op_call_cc')
    ml.cond_auto_call('cond_get')
    ml.bne('ops_code_end')
    ml.bpl('op_call')
    
    ml.def_segment('op_ret_cc')
    ml.cond_auto_call('cond_get')
    ml.bne('ops_code_end')
    ml.bpl('op_ret')
    
    ml.def_segment('op_jr_e_c')
    ml.lda_imm(3)
    ml.sta(jcc_imm)
    ml.cond_jmpc('op_jp_cc')
    
    ml.def_segment('op_jr_e_nc')
    ml.lda_imm(2)
    ml.sta(jcc_imm)
    ml.cond_jmpc('op_jp_cc')
    
    ml.def_segment('op_jr_e_z')
    ml.lda_imm(1)
    ml.sta(jcc_imm)
    ml.cond_jmpc('op_jp_cc')
    
    ml.def_segment('op_jr_e_nz')
    ml.lda_imm(0)
    ml.sta(jcc_imm)
    ml.cond_jmpc('op_jp_cc')
    
    ml.def_segment('op_djnz')
    ml.lda(nbr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(nbr)
    ml.bne('op_jr_e')
    ml.cond_jmpc('ops_code_end')
    
    # simple operation - doesn't include interrupt handling
    ml.def_segment('op_retn')
    ml.def_segment('op_reti')
    ml.lda(iff2)
    ml.sta(iff1)
    ml.cond_jmpc('op_ret')
    
    ml.def_segment('op_rst')
    ml.lda(npc)
    ml.sta(mem_val_lo)
    ml.lda(npc)
    ml.sta(mem_val_hi)
    ml.cond_auto_call('push_arg')
    ml.lda(rst_imm)
    ml.rol()
    ml.rol()
    ml.rol()
    ml.ana_imm(0x38)
    ml.sta(child_mem_addr)
    ml.lda_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_reg_arg')
    ml.lda(reg1_val_lo)
    ml.sta(npc)
    ml.lda(reg1_val_hi)
    ml.sta(npc)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_in_a_n')
    ml.lda(narg1)
    ml.sta(io_port_lo)
    ml.lda(nar)
    ml.sta(io_port_hi)
    ml.cond_auto_call('read_io_port')
    ml.sta(nar)
    ml.cond_jmpc('ops_code_end')
    
    ml.def_routine('op_in_r_c_start','read_io_port')
    ml.lda(ncr)
    ml.sta(io_port_lo)
    ml.lda(nbr)
    ml.sta(io_port_hi)
    ml.cond_lastcall('read_io_port')
    
    ml.def_segment('op_in_r_c')
    ml.cond_auto_call('op_in_r_c_start')
    ml.sta(reg1_val_lo)
    ml.sta(temp1)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H)
    ml.sta(nfr)
    ml.lda_imm((SetSRFlags_all_zero_n^SetSRFlags.XY^SetSRFlags.P^SetSRFlags.N))
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_ini')
    ml.def_segment('op_ind')
    ml.def_segment('op_inir')
    ml.def_segment('op_indr')
    
    # change N flag
    ml.lda_imm(SetSRFlags.nsub)
    ml.sta(temp4)
    
    ml.cond_auto_call('op_in_r_c_start')
    ml.sta(mem_val_lo)
    
    ml.lda(nlr)
    ml.sta(child_mem_addr)
    ml.lda(nhr)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('store_mem_val')
    
    ml.def_label('op_inid_cont')
    
    ml.lda(nbr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(nbr)
    ml.sta(temp1)
    
    ml.cond_auto_call('op_str_ch_hl')
    
    ml.lda(nopcode)
    ml.ana_imm(0x10)
    ml.bne('op_inid_end')
    ml.lda(nbr)
    ml.xor_imm(0xff)
    ml.bne('op_inid_end')   # if B=0 then end
    
    ml.lda(npc)
    ml.cond_clc()
    ml.sbc_imm(1)
    ml.sta(npc)
    ml.lda(npc+1)
    ml.sbc_imm(0)
    ml.sta(npc+1)
    
    ml.def_label('op_inid_end')
    # TODO: fix flags
    ml.lda_imm(SetSRFlags_all_zero_n^SetSRFlags.ZS^SetSRFlags.XY^SetSRFlags.N)
    ml.xor_imm(temp4)
    ml.cond_jmp('set_flags')
    
    ml.def_segment('op_out_n_a')
    ml.lda(narg1)
    ml.sta(io_port_lo)
    ml.lda(nar)
    ml.sta(io_port_hi)
    ml.def_label('op_out_xx_end')
    ml.sta(io_port_in)
    ml.cond_auto_call('write_io_port')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_out_n_r')
    ml.lda(ncr)
    ml.sta(io_port_lo)
    ml.lda(nbr)
    ml.sta(io_port_hi)
    ml.lda(reg1_val_lo)
    ml.cond_jmpc('op_out_xx_end')
    
    ml.def_segment('op_outi')
    ml.def_segment('op_outd')
    ml.def_segment('op_outir')
    ml.def_segment('op_outdr')
    
    # change N flag
    ml.lda_imm(0)
    ml.sta(temp4)
    
    ml.lda(ncr)
    ml.sta(io_port_lo)
    ml.lda(nbr)
    ml.sta(io_port_hi)
    ml.lda(nlr)
    ml.sta(child_mem_addr)
    ml.lda(nhr)
    ml.sta(child_mem_addr+1)
    ml.cond_auto_call('load_mem_val')
    ml.cond_auto_call('write_io_port')
    ml.cond_jmpc('op_inid_cont')
    
    ml.def_segment('ops_code_end')
    #######################################
    
    ml.def_routine('load_inc_pc_opcode','load_mem_val')
    ml.lda(nrfm)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.ana_imm(0x7f)
    ml.sta(temp4)
    ml.lda(nrfm)
    ml.ana_imm(0x80)
    ml.ora(temp4)
    ml.sta(nrfm)
    ml.cond_lastcall('load_inc_pc')
    
    # load byte from pc and increment pc
    # load_inc_pc - routine - load byte from 6502's PC
    ml.def_routine('load_inc_pc','load_mem_val')
    ml.lda(npc)
    ml.sta(child_mem_addr)
    ml.sec()
    ml.adc_imm(0)
    ml.sta(npc)
    ml.lda(npc+1)
    ml.sta(child_mem_addr+1)
    ml.adc_imm(0)
    ml.sta(npc+1)
    ml.cond_lastcall('load_mem_val')
    
    ######################################
    ## load/store mem val
    ######################################
    # store_mem_val
    ml.def_routine('store_mem_val')
    ml.lda(ml.l('native_machine'))
    ml.bne('store_mem_val_native')
    
    ml.lda(mm_mem_val)
    ml.sta(child_mem_val)
    ml.cond_jmpc('store_mem_val_end')
    
    ml.def_segment('store_mem_val_native')
    ml.lda(mm_mem_val)
    ml.sta(child_mem_val)
    ml.def_segment('store_mem_val_end')
    ml.cond_ret()
    
    #################
    # load mem val
    ml.def_routine('load_mem_val')
    ml.lda(ml.l('native_machine'))
    ml.bne('load_mem_val_native')
    
    ml.lda(child_mem_val)
    ml.cond_jmpc('load_mem_val_end')
    
    ml.def_segment('load_mem_val_native')
    ml.lda(child_mem_val)
    
    ml.def_segment('load_mem_val_end')
    ml.cond_ret()
    
    #####################################
    # read_input
    ml.def_routine('read_io_port')
    # example code
    ml.lda(io_port_out)
    ml.xor(io_port_lo)
    ml.xor(io_port_hi)
    ml.cond_ret()
    
    #####################################
    # read_input
    ml.def_routine('write_io_port')
    # example code
    ml.lda(io_port_in)
    ml.xor(io_port_lo)
    ml.xor(io_port_hi)
    ml.sta(io_port_out)
    ml.cond_ret()
    
    ml.def_label('decode_unsat')
    ml.unsat()
    
    # native machine config
    ml.def_label('native_machine')
    ml.byte(0)      # set true for native machine

    ml.align_pc(8)
    ml.def_label('bit_table')
    ml.bytes([1,2,4,8,16,32,64,128])
    ml.align_pc(4)
    ml.def_label('jcc_table')
    ml.bytes([SRFlags.Z,SRFlags.C,SRFlags.P,SRFlags.S])
    ml.align_pc(4)
    ml.def_label('op_str_data')
    ml.byte(0x1)
    ml.byte(0x0)
    ml.byte(0xfe)
    ml.byte(0xff)
    
    return start

ml.assemble(gencode)

if args.info:
    print("mpc:", ml.pc)
    print("procs_calls:", ml.procs_calls)
else:
    stdout.buffer.write(ml.dump())
