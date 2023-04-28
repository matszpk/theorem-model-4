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

ml.set_pc(0xfc0)
npc = ml.pc # 0xfc0: program counter
ml.word16(args.pc, [True,True])
nix = ml.pc # 0xfc2: IX register
ml.word16(0, [True,True])
nixl = nix+1
nixh = nix
niy = ml.pc # 0xfc4: IY register
ml.word16(0, [True,True])
niyl = niy+1
niyh = niy
nsp = ml.pc # 0xfc6: SP register
ml.word16(0, [True,True])
nspl = niy+1
nsph = niy

nbr = ml.pc # 0xfc8: B
ml.byte(0, True)
ncr = ml.pc # 0xfc9: C
ml.byte(0, True)
ndr = ml.pc # 0xfca: D
ml.byte(0, True)
ner = ml.pc # 0xfcb: E
ml.byte(0, True)
nhr = ml.pc # 0xfcc: H
ml.byte(0, True)
nlr = ml.pc # 0xfcd: L
ml.byte(0, True)
nfr = ml.pc # 0xfce: F
ml.byte(0, True)
nar = ml.pc # 0xfcf: A
ml.byte(0, True)
nbra = ml.pc # 0xfd0: B'
ml.byte(0, True)
ncra = ml.pc # 0xfd1: C'
ml.byte(0, True)
ndra = ml.pc # 0xfd2: D'
ml.byte(0, True)
nera = ml.pc # 0xfd3: E'
ml.byte(0, True)
nhra = ml.pc # 0xfd4: H'
ml.byte(0, True)
nlra = ml.pc # 0xfd5: L'
ml.byte(0, True)
nfra = ml.pc # 0xfd6: F'
ml.byte(0, True)
nara = ml.pc # 0xfd7: A'
ml.byte(0, True)

nint = ml.pc # 0xfd8: Int reg
ml.byte(0, True)
nrfm = ml.pc # 0xfd9: Int refresh reg
ml.byte(0, True)

nopfx = ml.pc # 0xfda: opcode prefix
ml.byte(0, True)
nopcode = ml.pc # 0xfdb:
ml.byte(0, True)
narg1 = ml.pc # 0xfdc:
ml.byte(0, True)
narg2 = ml.pc # 0xfdd:
# nargs: register argument:
# 0x80 - no register argument (value)
# 0x0-0x5,0x7 - register
# 0x6 - (hl)
ml.byte(0, True)
nargr1 = ml.pc # 0xfde
ml.byte(0, True)
nargr2 = ml.pc # 0xfdf
ml.byte(0, True)

mem_val_lo = ml.pc   # 0xfe0
reg2_val_lo = mem_val_lo
ml.byte(0, True)
mem_val_hi = ml.pc   # 0xfe1
reg2_val_hi = mem_val_hi
ml.byte(0, True)

reg1_val_lo = ml.pc   # 0xfe2
ml.byte(0, True)
reg1_val_hi = ml.pc   # 0xfe3
ml.byte(0, True)

addrmode = ml.pc     # 0xfe4  addr mode
ml.byte(0, True)
mem_val_loaded = ml.pc  # 0xfe5
ml.byte(0, True)
op_16bit = ml.pc
ml.byte(0, True)

mm_mem_val = ml.pc # 0xfe6
ml.byte(0x00, True)
mm_mem_addr = ml.pc # 0xfe7
ml.word16(0, [True, True])
mm_mem_temp = ml.pc # 0xfe9
ml.byte(0x00, True)
# cycles - really number T states
instr_cycles = ml.pc # 0xfea
ml.byte(0, True)
old_instr_cycles = ml.pc  # 0xfeb
ml.byte(0, True)
instr_index = ml.pc   # 0xfec
ml.byte(0, True)

temp1 = ml.pc       # 0xfed
ml.byte(0, True)
temp2 = ml.pc       # 0xfee
ml.byte(0, True)
temp3 = ml.pc       # 0xfee
ml.byte(0, True)
temp4 = ml.pc       # 0xfee
ml.byte(0, True)
xx_dont_keep_carry = ml.pc
ml.byte(0, True)

SRFlags = IntFlag('Flags', [ 'C', 'N', 'P', '_', 'H', '_2', 'Z', 'S' ]);

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
    
    ml.lda_imm(0x80)    # no register argument
    ml.sta(nargr1)
    ml.sta(nargr2)
    ml.sta(xx_dont_keep_carry)  # default nonzero
    
    # load instruction
    # load opcode
    ml.cond_auto_call('load_inc_pc')
    ##############################
    # decode it
    ml.sta(nopcode)
    ml.xor_imm(0xcb)
    ml.bne('decode_x1')
    ml.bpl('bit_opcodes')
    
    ml.def_label('decode_x1')
    ml.xor_imm(0xcb^0xdd)
    ml.bne('decode_x2')
    ml.bpl('ix_opcodes')
    
    ml.def_label('decode_x2')
    ml.xor_imm(0xdd^0xed)
    ml.bne('decode_x3')
    ml.bpl('misc_opcodes')
    
    ml.def_label('decode_x3')
    ml.xor_imm(0xed^0xfd)
    ml.bne('main_opcodes')
    ml.bpl('iy_opcodes')
    
    # main opcodes
    ml.def_segment('main_opcodes')
    
    ml.cond_jmpc('decode_end')
    
    # end of main opcodes
    
    # bit opcodes
    ml.def_segment('bit_opcodes')
    ml.cond_auto_call('load_inc_pc')
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
    
    # IX opcodes
    ml.def_segment('ix_opcodes')
    
    # end of IX opcodes
    
    # IY opcodes
    ml.def_segment('iy_opcodes')
    
    # end of IY opcodes
    
    # misc opcodes
    ml.def_segment('misc_opcodes')
    
    ################
    # end of decode
    ml.def_label('decode_end')
    
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
    
    ml.def_segment('am_ix_idx')
    ml.lda(nix)
    ml.cond_clc()
    ml.adc(narg1)
    ml.sta(child_mem_addr)
    ml.lda(nix+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_segment('am_iy_idx')
    ml.lda(niy)
    ml.cond_clc()
    ml.adc(narg1)
    ml.sta(child_mem_addr)
    ml.lda(niy+1)
    ml.adc_imm(0)
    ml.sta(child_mem_addr+1)
    ml.cond_jmpc('am_code_end')
    
    ml.def_segment('am_hl')
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
    
    ml.def_segment('op_push')
    ml.lda(nspl)
    ml.cond_clc()
    ml.sbc_imm(1)
    ml.sta(nspl)
    ml.sta(child_mem_addr)
    ml.lda(nsph)
    ml.sbc_imm(0)
    ml.sta(nsph)
    ml.sta(child_mem_addr+1)
    
    ml.def_label('op_end_with_store')
    ml.def_label('op_ld16_to_mem')
    ml.def_label('op_ld_to_mem')
    ml.cond_auto_call('store_mem_arg')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_pop')
    ml.lda(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.lda(mem_val_hi)
    ml.sta(reg1_val_hi)
    ml.lda(nspl)
    ml.cond_sec()
    ml.adc_imm(1)
    ml.sta(nspl)
    ml.lda(nsph)
    ml.adc_imm(0)
    ml.lda(nsph)
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
    
    # incdec HL and BC
    ml.lda(nopcode)
    ml.ana_imm(8)
    ml.bne('op_ld_str_dec')
    
    ml.lda(ner)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(ner)
    ml.lda(ndr)
    ml.adc_imm(0)
    ml.sta(ndr)
    ml.lda(nlr)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(nlr)
    ml.lda(nhr)
    ml.adc_imm(0)
    ml.sta(nhr)
    ml.cond_jmpc('op_ld_str_incdec_end')
    
    ml.def_segment('op_ld_str_dec')
    
    ml.lda(ner)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(ner)
    ml.lda(ndr)
    ml.sbc_imm(0)
    ml.sta(ndr)
    ml.lda(nlr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(nlr)
    ml.lda(nhr)
    ml.sbc_imm(0)
    ml.sta(nhr)
    
    ml.def_label('op_ld_str_incdec_end')
    
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
    
    ml.def_routine('set_zsvb','set_zs')
    ml.rol()
    ml.xor_imm(1)
    ml.cond_jmpc('set_zsvc_cont')
    
    ml.def_routine('set_zsvc','set_zs')
    ml.rol()
    ml.def_label('set_zsvc_cont')
    ml.ana_imm(1)
    ml.ora(nfr)
    ml.bvc('set_zsvc_no_overflow')
    ml.ora_imm(SRFlags.P)
    ml.cond_jmpc('set_zsvc_no_overflow_end')
    ml.def_segment('set_zsvc_no_overflow')
    ml.ana_imm(0xff^SRFlags.P)
    ml.def_label('set_zsvc_no_overflow_end')
    ml.sta(nfr)
    
    # set half carry
    ml.lda(temp1)   # temp result
    ml.xor(temp2)   # second argument
    ml.xor(temp3)   # first argument
    ml.ana_imm(0x10)
    ml.sta(temp2)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H)
    ml.ora(temp2|SRFlags.N)
    ml.sta(nfr)
    
    ml.cond_auto_call('set_zs')
    
    # temp1 - temporary result
    ml.def_routine('set_zsp','set_zs')
    ml.lda(temp1)
    ml.sta(temp3)   # rolled value of temp1
    ml.sta(temp4)   # value of count of one bits in 7 bit
    ml.lda_imm(7)
    ml.sta(temp2)
    ml.def_label('set_zsp_ploop')
    ml.lda(temp3)
    ml.rol()
    ml.sta(temp3)
    ml.xor(temp4)
    ml.sta(temp4)
    ml.lda(temp2)
    ml.clc()
    ml.sbc_imm(0)
    ml.sta(temp2)
    ml.bne('set_zsp_ploop')
    ml.lda(temp4)
    ml.bpl('set_zsp_pset')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.P)
    ml.cond_jmpc('set_zsp_p_end')
    ml.def_segment('set_zsp_pset')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.P)
    ml.def_label('set_zsp_p_end')
    ml.sta(nfr)
    ml.cond_lastcall('set_zs')
    
    ml.def_routine('set_zs')
    ml.lda(temp1)
    ml.bne('set_zs_nozero')
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.Z)
    ml.sta(nfr)
    ml.cond_jmpc('set_zs_nozero_end')
    ml.def_segment('set_zs_nozero')
    ml.bpl('set_zs_positive')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.Z|SRFlags.S)
    ml.sta(nfr)
    ml.cond_jmpc('set_zs_nozero_end')
    ml.def_segment('set_zs_positive')
    ml.lda(nfr)
    ml.ora_imm(SRFlags.Z)
    ml.ana_imm(0xff^SRFlags.S)
    ml.sta(nfr)
    ml.def_label('set_zs_nozero_end')
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
    ml.sbc(temp2)
    ml.sta(temp1)
    ml.cond_auto_call('set_zs')
    
    # halfcarry
    ml.lda(temp1)
    ml.xor(temp2)
    ml.xor(nar)
    ml.ana_imm(0x10)
    ml.sta(temp2)
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.H)
    ml.ora(temp2|SRFlags.N)
    ml.sta(nfr)
    
    # incdec HL and BC
    ml.lda(nopcode)
    ml.ana_imm(8)
    ml.bne('op_cp_str_dec')
    
    ml.lda(nlr)
    ml.cond_sec()
    ml.adc_imm(0)
    ml.sta(nlr)
    ml.lda(nhr)
    ml.adc_imm(0)
    ml.sta(nhr)
    ml.cond_jmpc('op_cp_str_incdec_end')
    
    ml.def_segment('op_cp_str_dec')
    
    ml.lda(nlr)
    ml.cond_clc()
    ml.sbc_imm(0)
    ml.sta(nlr)
    ml.lda(nhr)
    ml.sbc_imm(0)
    ml.sta(nhr)
    
    ml.def_label('op_cp_str_incdec_end')
    
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
    ml.cond_jmpc('ops_code_end')
    
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
    
    ml.lda(xx_dont_keep_carry)
    ml.bne('op_add_dont_keep_carry')
    ml.lda(nfr)
    ml.ror()    # old carry (keep carry)
    ml.def_label('op_add_dont_keep_carry')
    
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.N)
    ml.sta(nfr)
    ml.cond_auto_call('set_zsvc')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_adc')
    ml.lda(nfr) # get carry
    ml.ror()
    ml.cond_jmpc('op_add_cont')
    
    ml.def_segment('op_sub')
    ml.cond_sec()
    ml.def_label('op_sub_cont')
    ml.lda(mem_val_lo)
    ml.sta(temp3)
    ml.lda(reg1_val_lo)
    ml.sta(temp2)
    ml.sbc(mem_val_lo)
    ml.sta(reg1_val_lo)
    ml.sta(temp1)
    
    ml.lda(xx_dont_keep_carry)
    ml.bne('op_sub_dont_keep_carry')
    ml.lda(nfr)
    ml.ror()    # old carry (keep carry)
    ml.def_label('op_sub_dont_keep_carry')
    
    ml.lda(nfr)
    ml.ora_imm(SRFlags.N)
    ml.sta(nfr)
    ml.cond_auto_call('set_zsvb')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_sbc')
    ml.lda(nfr) # get carry
    ml.xor_imm(1)   # xor carry -> borrw
    ml.ror()
    ml.cond_jmpc('op_sub_cont')
    
    ml.def_segment('op_and')
    ml.lda_imm((instr_and|instr_addr(mem_val_lo))&0xff)
    ml.sta(ml.l('op_and_ch'))
    ml.def_label('op_and_cont')
    ml.lda(reg1_val_lo)
    ml.def_label('op_and_ch')
    ml.ana(mem_val_lo, [True, False])
    ml.sta(reg1_val_lo)
    
    ml.lda(nfr)
    ml.ana_imm(0xff^SRFlags.N)
    ml.sta(nfr)
    ml.cond_auto_call('set_zsp')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_or')
    ml.lda_imm((instr_ora|instr_addr(mem_val_lo))&0xff)
    ml.sta(ml.l('op_and_ch'))
    ml.cond_jmpc('op_and_cont')
    
    ml.def_segment('op_xor')
    ml.lda_imm((instr_xor|instr_addr(mem_val_lo))&0xff)
    ml.sta(ml.l('op_and_ch'))
    ml.cond_jmpc('op_and_cont')
    
    ml.def_segment('op_cp')
    ml.cond_sec()
    ml.lda(mem_val_lo)
    ml.sta(temp3)
    ml.lda(reg1_val_lo)
    ml.sta(temp2)
    ml.sbc(mem_val_lo)
    ml.sta(temp1)
    
    ml.lda(nfr)
    ml.ora_imm(SRFlags.N)
    ml.sta(nfr)
    ml.cond_auto_call('set_zsvb')
    ml.cond_jmpc('ops_code_end')
    
    ml.def_segment('op_inc')
    ml.lda_imm(0)
    ml.sta(xx_dont_keep_carry)
    ml.lda_imm(1)
    ml.sta(mem_val_lo)
    ml.cond_jmpc('op_add')
    
    ml.def_segment('op_dec')
    ml.lda_imm(0)
    ml.sta(xx_dont_keep_carry)
    ml.lda_imm(1)
    ml.sta(mem_val_lo)
    ml.cond_jmpc('op_sub')
    
    ml.def_label('ops_code_end')
    #######################################
    
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
    
    # native machine config
    ml.def_label('native_machine')
    ml.byte(0)      # set true for native machine
    return start

ml.assemble(gencode)

if args.info:
    print("mpc:", ml.pc)
    print("procs_calls:", ml.procs_calls)
else:
    stdout.buffer.write(ml.dump())
