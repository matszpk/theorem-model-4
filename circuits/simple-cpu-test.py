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

"""
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
# gen_testsuite("ite_4bit_2", "ite_4bit", 9, 4, range(0, 1<<3), ite_4bit, \
#        lambda x: (x&1)|((((x>>1)&1)*0xf)<<1)|(((x>>2)*0xf)<<5))
"""

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

cpu_phase012_input_str = (('state',3),('instr',4),('pc',8),('tempreg',4),('mem_value',4))
cpu_phase012_output_str = (('state',3),('instr',4),('pc',8), ('tempreg',4),('mem_rw',1),
    ('mem_address',8))

def cpu_phase012(data):
    v = bin_decomp(cpu_phase012_input_str, data)
    state, instr, pc = v['state'], v['instr'], v['pc']
    tempreg, mem_value = v['tempreg'], v['mem_value']
    next_pc = (pc + 1) & 0xff
    outv = dict()
    if state==0:
        outv = {'state':1,'instr':instr,'pc':next_pc,'tempreg':tempreg,'mem_rw':0,
                 'mem_address':pc}
    elif state==1:
        new_instr = mem_value
        if_clc_rol_psh_pul = new_instr==instr_clc or new_instr==instr_rol or \
                new_instr==instr_ror or new_instr==instr_psh or new_instr==instr_pul
        outv = {
            'state': 3 if if_clc_rol_psh_pul else 2,
            'instr': new_instr,
            'pc': pc if if_clc_rol_psh_pul else next_pc,
            'tempreg': tempreg,
            'mem_rw': 0,
            'mem_address': pc }
    elif state==2:
        new_tempreg = mem_value
        outv = { 'state': 3,'instr':instr,'pc':next_pc,'tempreg':new_tempreg,'mem_rw':0,
                'mem_address':pc }
    else:
        raise "Error!"
    return bin_comp(cpu_phase012_output_str, outv)

cpu_phase3_input_str = (('state',3),('instr',4),('pc',8),('acc',4),('flags',3),
                ('sp',4),('tempreg',4),('mem_value',4))
cpu_phase3_output_str = (('state',3),('pc',8),('sp',4),('mem_rw',1),('mem_value',4),
                ('mem_address',8),('stop',1))

def cpu_phase3(data):
    v = bin_decomp(cpu_phase3_input_str, data)
    state, instr, pc = v['state'], v['instr'], v['pc']
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
    
    return bin_comp(cpu_phase3_output_str,
        { 'state': 4, 'pc': next_pc, 'sp': next_sp, 'mem_rw': new_mem_rw,
            'mem_value': new_mem_value, 'mem_address': new_mem_address, 'stop': stop, })

# print(
#     bin_decomp(cpu_phase012_output_str,
#     cpu_phase012(
#         bin_comp(cpu_phase012_input_str,
#                 {'state':2,'instr':instr_or,'pc':41,'tempreg':7,'mem_value':11})
#         )))

def cpu_phase012_1_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':0,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&3,'mem_value':(case>>14)&3})

def cpu_phase012_1_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':0,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':((case>>12)&3)<<2,'mem_value':((case>>14)&3)<<2})

def cpu_phase012_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':1,'instr':case&0x3,'pc':(case>>2)&0xff,
                 'tempreg':(case>>10)&3,'mem_value':(case>>12)&0xf})

def cpu_phase012_2_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':1,'instr':(case&0x3)<<2,'pc':(case>>2)&0xff,
                 'tempreg':((case>>10)&3)<<2,'mem_value':(case>>12)&0xf})

def cpu_phase012_2_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':1,'instr':9,'pc':case&0xff,
                 'tempreg':(case>>8)&0xf,'mem_value':(case>>12)&0xf})

def cpu_phase012_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&3,'mem_value':(case>>14)&3})

def cpu_phase012_3_2_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':((case>>12)&3)<<2,'mem_value':((case>>14)&3)<<2})

def cpu_phase012_3_3_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':11,'mem_value':(case>>12)&0xf})

def cpu_phase012_3_4_input_test_func(case):
    return bin_comp(cpu_phase012_input_str,
        {'state':2,'instr':case&0xf,'pc':(case>>4)&0xff,
                 'tempreg':(case>>12)&0xf,'mem_value':5})

"""
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
"""

# print(
#     bin_decomp(cpu_phase3_output_str,
#     cpu_phase3(
#         bin_comp(cpu_phase3_input_str,
#                 {'state':3,'instr':instr_lda,'pc':41,'acc':7,'flags':0b011,'sp':4,
#                  'tempreg':7,'mem_value':11})
#         )))
