from simple2_cpu_asm import *
from sys import stdout

ml = Memory()

def gencode():
    ml.set_pc(0x00)
    ml.lda_imm(0xff)
    #ml.clc()
    #ml.set_flag(flag_N,flag_set)
    #ml.set_flag(flag_Z,flag_undef)
    ml.sbc_imm(0x01)
    ml.spc(0x80)
    return 0

def gencode2():
    ml.set_pc(0x00)
    ml.def_label('main')
    ml.lda_imm(0xff)
    ml.bne('end')
    ml.lda_imm(0xfe)
    ml.bne('end', extra_jumps=['endlast'])
    ml.spc(0x1)
    
    ml.def_segment('endx')
    ml.cond_clc()
    ml.sbc_imm(0x01)
    
    ml.def_segment('end')
    ml.sbc_imm(0x01)
    ml.clc()
    ml.bcc('endx')
    ml.spc(0x1)
    
    ml.def_segment('endlast')
    ml.adc_imm(0x01)
    return 0

def gencode3():
    ml.set_pc(0x00)
    ml.def_label('main')
    ml.lda_imm(0x2)
    ml.sta(0xff0)
    ml.cond_short_call('rout1')
    ml.spc_imm(1)
    
    ml.def_routine('rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x7c)
    ml.ana_imm(0x3f)
    ml.sta(0xff1)
    ml.cond_ret('rout2')
    
    ml.def_routine('rout1')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x9a)
    ml.ana_imm(0x3f)
    ml.sta(0xff0)
    ml.cond_short_call('rout2')
    ml.cond_ret('rout1')
    
    return 0

def gencode4():
    ml.set_pc(0x00)
    ml.def_label('main')
    ml.lda_imm(0x2)
    ml.sta(0xff0)
    ml.cond_short_call('rout1')
    ml.spc_imm(1)
    
    ml.def_routine('rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x7c)
    ml.ana_imm(0x3f)
    ml.sta(0xff1)
    ml.cond_ret('rout2')
    
    ml.def_routine('rout1', 'rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x9a)
    ml.ana_imm(0x3f)
    ml.sta(0xff0)
    ml.cond_lastcall('rout2')
    
    return 0

def gencode5():
    ml.set_pc(0x00)
    ml.def_label('main')
    ml.lda_imm(0x2)
    ml.sta(0xff0)
    ml.cond_auto_call('rout1')
    ml.lda_imm(0x1)
    ml.sta(0xfe0)
    ml.lda_imm(0x5)
    ml.sta(0xfe1)
    ml.cond_auto_call('rout3')
    ml.clc()
    ml.bcc("x100")
    
    ml.def_routine('rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x7c)
    ml.ana_imm(0x3f)
    ml.sta(0xff1)
    ml.cond_ret()
    
    ml.def_routine('rout1', 'rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x9a)
    ml.ana_imm(0x3f)
    ml.sta(0xff0)
    ml.cond_lastcall('rout2')
    
    ml.def_routine('rout3')
    ml.lda(0xfe0)
    ml.xor(0xfe1)
    ml.sta(0xfe0)
    ml.cond_ret()
    
    ml.align_pc(0x100)
    ml.def_segment("x100")
    ml.lda_imm(0x11)
    ml.sta(0xfe1)
    ml.cond_auto_call('rout3')
    ml.spc_imm(1)
    
    return 0

def gencode6():
    ml.set_pc(0x00)
    ml.def_label('main')
    ml.lda_imm(0x2)
    ml.sta(0xff0)
    ml.cond_auto_call('rout1')
    ml.lda_imm(0x1)
    ml.sta(0xfe0)
    ml.lda_imm(0x5)
    ml.sta(0xfe1)
    ml.long_call('rout3')
    ml.clc()
    ml.bcc("x100")
    
    ml.def_routine('rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x7c)
    ml.ana_imm(0x3f)
    ml.sta(0xff1)
    ml.cond_ret()
    
    ml.def_routine('rout1', 'rout2')
    ml.lda(0xff0)
    ml.cond_clc()
    ml.adc_imm(0x9a)
    ml.ana_imm(0x3f)
    ml.sta(0xff0)
    ml.cond_lastcall('rout2')
    
    ml.def_routine('rout3')
    ml.lda(0xfe0)
    ml.xor(0xfe1)
    ml.sta(0xfe0)
    ml.cond_ret()
    
    ml.align_pc(0x100)
    ml.def_segment("x100")
    ml.lda_imm(0x11)
    ml.sta(0xfe1)
    ml.long_call('rout3')
    ml.spc_imm(1)
    
    return 0

ml.assemble(gencode5)

# print("flags:", ml.flags, ml.acc)
# print("labels:", ml.labels)
# print("long_procs:", ml.long_procs)
# print("proc_calls:", ml.procs_calls);

stdout.buffer.write(ml.dump())
