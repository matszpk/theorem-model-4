from testbase import *

def ite(case):
    a,b,c = case&1,(case>>1)&1,case>>2
    return (a&b) | (~a&c)

def ite_4bit(case):
    v = bin_decomp((('a',1),('b',4),('c',4)), case)
    a,b,c = v['a'],v['b'],v['c']
    a *= 0xf
    return (a&b)|((a^0xf)&c)

def full_adder(case):
    a,b,c = case&1,(case>>1)&1,case>>2
    return ((a+b+c) & 1) | ((a+b+c >= 2)<<1)

def carry_adder_4bit(case):
    v = bin_decomp((('c',1),('a',4),('b',4)), case)
    a,b,c = v['a'],v['b'],v['c']
    return (a + b + c) & 0x1f

def carry_suber_4bit(case):
    v = bin_decomp((('c',1),('a',4),('b',4)), case)
    a,b,c = v['a'],v['b'],v['c']
    return (a + (b ^ 0xf) + c) & 0x1f

gen_testsuite("copy", "copy", 1, 1, range(0, 1<<1), lambda x: x)
gen_testsuite("copy_4bit", "copy_4bit", 4, 4, range(0, 1<<4), lambda x: x)
gen_testsuite("not_4bit", "not_4bit", 4, 4, range(0, 1<<4), lambda x: x^0xf)
gen_testsuite("xor", "xor", 2, 1, range(0, 1<<2), lambda x: (x&1)^(x>>1))
gen_testsuite("xor_4bit", "xor_4bit", 8, 4, range(0, 1<<8), lambda x: (x&0xf)^(x>>4))
gen_testsuite("and", "and", 2, 1, range(0, 1<<2), lambda x: (x&1)&(x>>1))
gen_testsuite("and_4bit", "and_4bit", 8, 4, range(0, 1<<8), lambda x: (x&0xf)&(x>>4))
gen_testsuite("or", "or", 2, 1, range(0, 1<<2), lambda x: (x&1)|(x>>1))
gen_testsuite("or_4bit", "or_4bit", 8, 4, range(0, 1<<8), lambda x: (x&0xf)|(x>>4))
gen_testsuite("and_3", "and_3", 3, 1, range(0, 1<<3), lambda x: (x&1)&((x>>1)&1)&(x>>2))
gen_testsuite("and_4", "and_4", 4, 1, range(0, 1<<4), lambda x: (x&1)&((x>>1)&1)&((x>>2)&1)&(x>>3))
gen_testsuite("or_4", "or_4", 4, 1, range(0, 1<<4), lambda x: (x&1)|((x>>1)&1)|((x>>2)&1)|(x>>3))
gen_testsuite("ite", "ite", 3, 1, range(0, 1<<3), ite)
gen_testsuite("ite_4bit", "ite_4bit", 9, 4, range(0, 1<<9), ite_4bit)
gen_testsuite("full_adder", "full_adder", 3, 2, range(0, 1<<3), full_adder)
gen_testsuite("half_adder", "half_adder", 2, 2, range(0, 1<<2), full_adder)
gen_testsuite("half_suber", "half_suber", 2, 2, range(0, 1<<2), lambda x: full_adder(x+4))
gen_testsuite("carry_adder_4bit", "carry_adder_4bit", 9, 5, range(0, 1<<9), carry_adder_4bit)
gen_testsuite("carry_suber_4bit", "carry_suber_4bit", 9, 5, range(0, 1<<9), carry_suber_4bit)
gen_testsuite("dec_4bit", "dec_4bit", 4, 4, range(0, 1<<4), lambda x: (16+x-1)&0xf)
gen_testsuite("inc_8bit", "inc_8bit", 8, 8, range(0, 1<<8), lambda x: (x+1)&0xff)

# cpu phases

instr_lda=0
instr_sta=1
instr_adc=2
instr_sbc=3
instr_and=4
instr_or=5
instr_xor=6
instr_clc=7
instr_rol=8
instr_ror=9
instr_bcc=10
instr_bne=11
instr_bpl=12
instr_jmp=13
instr_psh=14
instr_pul=15

def flag_c(flags):
    return flags&1 != 0
def flag_z(flags):
    return flags&2 != 0
def flag_n(flags):
    return flags&4 != 0
def set_flag_c(flags,c):
    return (flags&~1)|(1 if c else 0)
def set_flag_z(flags,z):
    return (flags&~2)|(2 if z else 0)
def set_flag_n(flags,n):
    return (flags&~4)|(4 if n else 0)

cpu_phase012_input_str = (('phase',3),('instr',4),('pc',8),('tempreg',4),('mem_value',4))
cpu_phase012_output_str = (('phase',3),('instr',4),('pc',8), ('tempreg',4),('mem_rw',1),
    ('mem_address',8))

def cpu_phase012(data):
    v = bin_decomp(cpu_phase012_input_str, data)
    phase, instr, pc = v['phase'], v['instr'], v['pc']
    tempreg, mem_value = v['tempreg'], v['mem_value']
    next_pc = (pc + 1) & 0xff
    outv = dict()
    if phase==0:
        outv = {'phase':1,'instr':instr,'pc':next_pc,'tempreg':tempreg,'mem_rw':0,
                 'mem_address':pc}
    elif phase==1:
        new_instr = mem_value
        if_clc_rol_psh_pul = new_instr==instr_clc or new_instr==instr_rol or \
                new_instr==instr_ror or new_instr==instr_psh or new_instr==instr_pul
        outv = {
            'phase': 3 if if_clc_rol_psh_pul else 2,
            'instr': new_instr,
            'pc': pc if if_clc_rol_psh_pul else next_pc,
            'tempreg': tempreg,
            'mem_rw': 0,
            'mem_address': pc }
    elif phase==2:
        new_tempreg = mem_value
        outv = { 'phase': 3,'instr':instr,'pc':next_pc,'tempreg':new_tempreg,'mem_rw':0,
                'mem_address':pc }
    else:
        raise "Error!"
    return bin_comp(cpu_phase012_output_str, outv)

def cpu_phase012_1_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':0,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&3,'mem_value':(case>>14)&3})

def cpu_phase012_1_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':0,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':((case>>12)&3)<<2,'mem_value':((case>>14)&3)<<2})

def cpu_phase012_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':1,'instr':case&0x3,'pc':(case>>2)&0xff,
                 'tempreg':(case>>10)&3,'mem_value':(case>>12)&0xf})

def cpu_phase012_2_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':1,'instr':(case&0x3)<<2,'pc':(case>>2)&0xff,
                 'tempreg':((case>>10)&3)<<2,'mem_value':(case>>12)&0xf})

def cpu_phase012_2_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':1,'instr':9,'pc':case&0xff,
                 'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})

def cpu_phase012_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&3,'mem_value':(case>>14)&3})

def cpu_phase012_3_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':((case>>12)&3)<<2,'mem_value':((case>>14)&3)<<2})

def cpu_phase012_3_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':11,'mem_value':(case>>12)&0xf})

def cpu_phase012_3_4_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'phase':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&0xf,'mem_value':5})

gen_testsuite("cpu_phase012_1", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_1_input_test_func)
gen_testsuite("cpu_phase012_1_2", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_1_2_input_test_func)
gen_testsuite("cpu_phase012_2", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_2_input_test_func)
gen_testsuite("cpu_phase012_2_2", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_2_2_input_test_func)
gen_testsuite("cpu_phase012_2_3", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_2_3_input_test_func)
gen_testsuite("cpu_phase012_3", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_3_input_test_func)
gen_testsuite("cpu_phase012_3_2", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_3_2_input_test_func)
gen_testsuite("cpu_phase012_3_3", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_3_3_input_test_func)
gen_testsuite("cpu_phase012_3_4", "cpu_phase012", 23, 28, range(0, 1<<16), cpu_phase012,
                cpu_phase012_3_4_input_test_func)

cpu_phase3_input_str = (('phase',3),('instr',4),('pc',8),('acc',4),('flags',3),
                ('sp',4),('tempreg',4),('mem_value',4))
cpu_phase3_output_str = (('phase',3),('pc',8),('sp',4),('mem_rw',1),('mem_value',4),
                ('mem_address',8),('stop',1))

def cpu_phase3(data):
    v = bin_decomp(cpu_phase3_input_str, data)
    phase, instr, pc = v['phase'], v['instr'], v['pc']
    acc, flags, sp = v['acc'], v['flags'], v['sp']
    tempreg, mem_value = v['tempreg'], v['mem_value']
    
    new_address = (mem_value<<4) | tempreg
    next_pc = pc
    # if jmp or conditional jump and condition satisfied
    if instr==instr_jmp or (instr==instr_bcc and not flag_c(flags)) or \
        (instr==instr_bne and not flag_z(flags)) or \
        (instr==instr_bpl and not flag_n(flags)):
        next_pc = new_address
    
    new_mem_rw = 1 if instr==instr_sta or instr==instr_psh else 0
    new_mem_value = acc
    stop = sp==0 and instr==instr_pul
    next_sp = sp
    if instr==instr_psh:
        next_sp = (sp + 1) & 0xf
    elif instr==instr_pul:
        next_sp = (16 + sp - 1) & 0xf
    
    new_mem_address = new_address
    if instr==instr_psh:
        new_mem_address = sp
    elif instr==instr_pul:
        new_mem_address = next_sp
    
    next_phase = 4
    if instr==instr_sta or instr==instr_psh:
        next_phase = 0
    
    return bin_comp(cpu_phase3_output_str,
        { 'phase': next_phase, 'pc': next_pc, 'sp': next_sp, 'mem_rw': new_mem_rw,
            'mem_value': new_mem_value, 'mem_address': new_mem_address, 'stop': stop })

def cpu_phase3_lda_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_lda,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_lda_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_lda,'pc':32+(case&0xf),'acc':(case>>4)&0xf,
            'flags':0b110,'sp':13,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_sta_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_sta,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_sta_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_sta,'pc':32+(case&0xf),'acc':(case>>4)&0xf,
            'flags':0b110,'sp':13,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_adc_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_adc,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_adc_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_adc,'pc':32+(case&0xf),'acc':(case>>4)&0xf,
            'flags':0b110,'sp':13,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_sbc_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_sbc,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_and_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_and,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_or_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_or,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_xor_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_xor,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_clc_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_clc,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_clc_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_clc,'pc':32+(case&0xf),'acc':(case>>4)&0xf,
            'flags':0b110,'sp':11,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_rol_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_rol,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_ror_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_ror,'pc':(case&0xf)<<2,'acc':(case>>4)&0xf,
            'flags':0b011,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_bcc_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_bcc,'pc':(case&0x1f)<<2,'acc':11,
            'flags':(case>>5)&0x7,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_bcc_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_bcc,'pc':64+(case&0x1f),'acc':11,
            'flags':(case>>5)&0x7,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_bne_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_bne,'pc':(case&0x1f)<<2,'acc':11,
            'flags':(case>>5)&0x7,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_bpl_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_bpl,'pc':(case&0x1f)<<2,'acc':11,
            'flags':(case>>5)&0x7,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_jmp_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_jmp,'pc':(case&0x1f)<<2,'acc':11,
            'flags':(case>>5)&0x7,'sp':6,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_psh_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_psh,'pc':(case&0xf)<<2,'acc':12,'flags':0b011,
            'sp':(case>>4)&0xf,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_psh_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_psh,'pc':32+(case&0xf),'acc':12,'flags':0b110,
            'sp':(case>>4)&0xf,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_pul_1_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_pul,'pc':(case&0xf)<<2,'acc':12,'flags':0b011,
            'sp':(case>>4)&0xf,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})
def cpu_phase3_pul_1_2_input_test_func(case):
    return bin_comp(cpu_phase3_input_str,
        {'phase':3,'instr':instr_pul,'pc':32+(case&0xf),'acc':12,'flags':0b110,
            'sp':(case>>4)&0xf,'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})

gen_testsuite("cpu_phase3_lda_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_lda_1_input_test_func)
gen_testsuite("cpu_phase3_lda_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_lda_1_2_input_test_func)
gen_testsuite("cpu_phase3_sta_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_sta_1_input_test_func)
gen_testsuite("cpu_phase3_sta_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_sta_1_2_input_test_func)
gen_testsuite("cpu_phase3_adc_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_adc_1_input_test_func)
gen_testsuite("cpu_phase3_adc_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_adc_1_2_input_test_func)
gen_testsuite("cpu_phase3_sbc_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_sbc_1_input_test_func)
gen_testsuite("cpu_phase3_and_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_and_1_input_test_func)
gen_testsuite("cpu_phase3_or_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_or_1_input_test_func)
gen_testsuite("cpu_phase3_xor_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_xor_1_input_test_func)
gen_testsuite("cpu_phase3_clc_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_clc_1_input_test_func)
gen_testsuite("cpu_phase3_clc_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_clc_1_2_input_test_func)
gen_testsuite("cpu_phase3_rol_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_rol_1_input_test_func)
gen_testsuite("cpu_phase3_ror_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_ror_1_input_test_func)
gen_testsuite("cpu_phase3_bcc_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_bcc_1_input_test_func)
gen_testsuite("cpu_phase3_bcc_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_bcc_1_2_input_test_func)
gen_testsuite("cpu_phase3_bne_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_bne_1_input_test_func)
gen_testsuite("cpu_phase3_bpl_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_bpl_1_input_test_func)
gen_testsuite("cpu_phase3_jmp_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_jmp_1_input_test_func)
gen_testsuite("cpu_phase3_psh_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_psh_1_input_test_func)
gen_testsuite("cpu_phase3_psh_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_psh_1_2_input_test_func)
gen_testsuite("cpu_phase3_pul_1", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_pul_1_input_test_func)
gen_testsuite("cpu_phase3_pul_1_2", "cpu_phase3", 34, 29, range(0, 1<<16), cpu_phase3,
                cpu_phase3_pul_1_2_input_test_func)

cpu_merge_phase012_3_input_str = (('phase',3),('instr',4),('tempreg',4),('phase_012',3),
                ('instr_012',4),('pc_012',8),('sp_012',4),('tempreg_012',4),('phase_3',3),
                ('pc_3',8),('sp_3',4),('mem_rw_012',1),('mem_value_012',4),
                ('mem_address_012',8),('mem_rw_3',1),('mem_value_3',4),('mem_address_3',8),
                ('stop_3',1))
cpu_merge_phase012_3_output_str = (('phase',3),('instr',4),('pc',8),('sp',4),('tempreg',4),
                ('mem_rw',1),('mem_value',4),('mem_address',8),('stop',1))

def cpu_merge_phase012_3(data):
    v = bin_decomp(cpu_merge_phase012_3_input_str, data)
    if_phase3 = v['phase']==3
    return bin_comp(cpu_merge_phase012_3_output_str, {
            'phase': v['phase_3'] if if_phase3 else v['phase_012'],
            'instr': v['instr'] if if_phase3 else v['instr_012'],
            'pc': v['pc_3'] if if_phase3 else v['pc_012'],
            'sp': v['sp_3'] if if_phase3 else v['sp_012'],
            'tempreg': v['tempreg'] if if_phase3 else v['tempreg_012'],
            'mem_rw': v['mem_rw_3'] if if_phase3 else v['mem_rw_012'],
            'mem_value': v['mem_value_3'] if if_phase3 else v['mem_value_012'],
            'mem_address': v['mem_address_3'] if if_phase3 else v['mem_address_012'],
            'stop': v['stop_3'] if if_phase3 else 0
        })

def cpu_merge_phase012_3_1_input_test_func(case):
    return bin_comp(cpu_merge_phase012_3_input_str,
        {
            'phase':case&3,
            'instr':3,
            'tempreg':14,
            'phase_012':2,
            'instr_012':5,
            'pc_012':131,
            'sp_012':11,
            'tempreg_012':8,
            'phase_3':4,
            'pc_3':74,
            'sp_3':5,
            'mem_rw_012':0,
            'mem_value_012':11,
            'mem_address_012':89,
            'mem_rw_3':1,
            'mem_value_3':3,
            'mem_address_3':118,
            'stop_3':1,
        })

def cpu_merge_phase012_3_2_input_test_func(case):
    return bin_comp(cpu_merge_phase012_3_input_str,
        {
            'phase':case&3,
            'instr':1,
            'tempreg':2,
            'phase_012':3,
            'instr_012':4,
            'pc_012':111,
            'sp_012':5,
            'tempreg_012':6,
            'phase_3':7,
            'pc_3':222,
            'sp_3':8,
            'mem_rw_012':9,
            'mem_value_012':10,
            'mem_address_012':77,
            'mem_rw_3':1,
            'mem_value_3':11,
            'mem_address_3':99,
            'stop_3':1,
        })

gen_testsuite("cpu_merge_phase012_3_1", "cpu_merge_phase012_3", 76, 37, range(0, 1<<2),
                cpu_merge_phase012_3, cpu_merge_phase012_3_1_input_test_func)
gen_testsuite("cpu_merge_phase012_3_2", "cpu_merge_phase012_3", 76, 37, range(0, 1<<2),
                cpu_merge_phase012_3, cpu_merge_phase012_3_2_input_test_func)

cpu_phase4_input_str = (('instr',4),('flags',3),('acc',4),('mem_value',4))
cpu_phase4_output_str = (('acc',4),('flags',3))

def cpu_phase4(data):
    v = bin_decomp(cpu_phase4_input_str, data)
    instr, flags, acc, mem_value = v['instr'], v['flags'], v['acc'], v['mem_value']
    
    new_acc = acc
    new_flags = flags
    if instr==instr_lda:
        new_acc = mem_value
    elif instr==instr_adc:
        res = acc + mem_value + (flags&1)
        new_flags = set_flag_c(new_flags, res>=16)
        new_acc = res & 0xf
    elif instr==instr_sbc:
        res = acc + (mem_value^0xf) + (flags&1)
        new_flags = set_flag_c(new_flags, res>=16)
        new_acc = res & 0xf
    elif instr==instr_and:
        new_acc = (acc & mem_value) & 0xf
    elif instr==instr_or:
        new_acc = (acc | mem_value) & 0xf
    elif instr==instr_xor:
        new_acc = (acc ^ mem_value) & 0xf
    elif instr==instr_clc:
        new_flags = set_flag_c(new_flags, False)
    elif instr==instr_rol:
        res = (acc<<1) + (flags&1)
        new_flags = set_flag_c(new_flags, res>=16)
        new_acc = res & 0xf
    elif instr==instr_ror:
        res = (acc>>1) + ((flags&1)<<3)
        new_flags = set_flag_c(new_flags, acc&1!=0)
        new_acc = res
    elif instr==instr_pul:
        new_acc = mem_value
    
    if instr!=instr_clc:
        new_flags = set_flag_z(new_flags, new_acc==0)
        new_flags = set_flag_n(new_flags, (new_acc&8)!=0)
    
    return bin_comp(cpu_phase4_output_str, { 'acc': new_acc, 'flags': new_flags })

def cpu_phase4_lda_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_lda,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_adc_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_adc,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_sbc_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_sbc,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_and_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_and,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_or_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_or,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_xor_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_xor,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_clc_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_clc,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_rol_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_rol,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_ror_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_ror,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})
def cpu_phase4_pul_1_input_test_func(case):
    return bin_comp(cpu_phase4_input_str,{'instr':instr_pul,'flags':case&7,
            'acc':(case>>3)&0xf,'mem_value':(case>>7)&0xf})

gen_testsuite("cpu_phase4_lda_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_lda_1_input_test_func)
gen_testsuite("cpu_phase4_adc_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_adc_1_input_test_func)
gen_testsuite("cpu_phase4_sbc_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_sbc_1_input_test_func)
gen_testsuite("cpu_phase4_and_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_and_1_input_test_func)
gen_testsuite("cpu_phase4_or_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_or_1_input_test_func)
gen_testsuite("cpu_phase4_xor_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_xor_1_input_test_func)
gen_testsuite("cpu_phase4_clc_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_clc_1_input_test_func)
gen_testsuite("cpu_phase4_rol_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_rol_1_input_test_func)
gen_testsuite("cpu_phase4_ror_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_ror_1_input_test_func)
gen_testsuite("cpu_phase4_pul_1", "cpu_phase4", 15, 7, range(0, 1<<11), cpu_phase4,
                cpu_phase4_pul_1_input_test_func)

cpu_merge_phase0123_4_input_str = (('phase_0123',3),('instr_0123',4),('pc',8),
                ('pc_0123',8),('acc_0123',4),('flags_0123',3),('sp',4),('phase2',1),
                ('instr',4),('acc_t_all',4),('flags_t_all',3),('sp_0123',4),
                ('tempreg',4),('tempreg_0123',4),('mem_value_0123',4),('mem_rw_0123',1),
                ('mem_address_0123',8),('stop_0123',1))
cpu_merge_phase0123_4_output_str = (('phase',3),('instr',4),('pc',8),('acc',4),('flags',3),
                ('sp',4), ('tempreg',4),('mem_value',4),('mem_rw',1),('mem_address',8),
                ('create',1),('stop',1))


def cpu_merge_phase0123_4(data):
    v = bin_decomp(cpu_merge_phase0123_4_input_str, data)
    if_phase4 = v['phase2']==1
    return bin_comp(cpu_merge_phase0123_4_output_str, {
            'phase': 0 if if_phase4 else v['phase_0123'],
            'instr': v['instr'] if if_phase4 else v['instr_0123'],
            'pc': v['pc'] if if_phase4 else v['pc_0123'],
            'acc': v['acc_t_all'] if if_phase4 else v['acc_0123'],
            'flags': v['flags_t_all'] if if_phase4 else v['flags_0123'],
            'sp': v['sp'] if if_phase4 else v['sp_0123'],
            'tempreg': v['tempreg'] if if_phase4 else v['tempreg_0123'],
            'mem_value': 0 if if_phase4 else v['mem_value_0123'],
            'mem_rw': 0 if if_phase4 else v['mem_rw_0123'],
            'mem_address': 0 if if_phase4 else v['mem_address_0123'],
            'create': 0,
            'stop': 0 if if_phase4 else v['stop_0123']
        })

def cpu_merge_phase0123_4_1_input_test_func(case):
    return bin_comp(cpu_merge_phase0123_4_input_str,
        {
            'phase2':case&1,
            'phase_0123':2,
            'instr_0123':7,
            'pc':52,
            'pc_0123':167,
            'acc_0123':8,
            'flags_0123':9,
            'sp':12,
            'instr':2,
            'acc_t_all':10,
            'flags_t_all':5,
            'sp_0123':1,
            'tempreg':6,
            'tempreg_0123':13,
            'mem_value_0123':4,
            'mem_rw_0123':0,
            'mem_address_0123':159,
            'stop_0123':0,
        })

def cpu_merge_phase0123_4_2_input_test_func(case):
    return bin_comp(cpu_merge_phase0123_4_input_str,
        {
            'phase2':case&1,
            'phase_0123':2,
            'instr_0123':1,
            'pc':52,
            'pc_0123':167,
            'acc_0123':2,
            'flags_0123':3,
            'sp':4,
            'instr':5,
            'acc_t_all':6,
            'flags_t_all':7,
            'sp_0123':8,
            'tempreg':9,
            'tempreg_0123':10,
            'mem_value_0123':11,
            'mem_rw_0123':1,
            'mem_address_0123':189,
            'stop_0123':1,
        })

def cpu_merge_phase0123_4_3_input_test_func(case):
    return bin_comp(cpu_merge_phase0123_4_input_str,
        {
            'phase2':case&1,
            'phase_0123':3,
            'instr_0123':15,
            'pc':52,
            'pc_0123':167,
            'acc_0123':2,
            'flags_0123':6,
            'sp':4,
            'instr':5,
            'acc_t_all':6,
            'flags_t_all':2,
            'sp_0123':8,
            'tempreg':9,
            'tempreg_0123':10,
            'mem_value_0123':11,
            'mem_rw_0123':1,
            'mem_address_0123':189,
            'stop_0123':0,
        })

gen_testsuite("cpu_merge_phase0123_4_1", "cpu_merge_phase0123_4", 72, 45, range(0, 2),
                cpu_merge_phase0123_4, cpu_merge_phase0123_4_1_input_test_func)
gen_testsuite("cpu_merge_phase0123_4_2", "cpu_merge_phase0123_4", 72, 45, range(0, 2),
                cpu_merge_phase0123_4, cpu_merge_phase0123_4_2_input_test_func)
gen_testsuite("cpu_merge_phase0123_4_3", "cpu_merge_phase0123_4", 72, 45, range(0, 2),
                cpu_merge_phase0123_4, cpu_merge_phase0123_4_3_input_test_func)
