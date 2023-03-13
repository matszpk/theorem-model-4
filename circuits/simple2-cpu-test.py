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
gen_testsuite("inc_12bit", "inc_12bit", 12, 12, range(0, 1<<12), lambda x: (x+1)&0xfff)

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
instr_bvc=12
instr_bpl=13
instr_spc=14
instr_sec=15

def flag_c(flags):
    return flags&1 != 0
def flag_z(flags):
    return flags&2 != 0
def flag_v(flags):
    return flags&4 != 0
def flag_n(flags):
    return flags&8 != 0
def set_flag_c(flags,c):
    return (flags&~1)|(1 if c else 0)
def set_flag_z(flags,z):
    return (flags&~2)|(2 if z else 0)
def set_flag_v(flags,n):
    return (flags&~4)|(4 if n else 0)
def set_flag_n(flags,n):
    return (flags&~8)|(8 if n else 0)

cpu_phase01_input_str = (('phase0',1),('pc',12),('mem_value',8))
cpu_phase01_output_str = (('phase',2),('instr',4),('pc',12),('tmp',4),('mem_address',12))

def cpu_phase01(data):
    v = bin_decomp(cpu_phase01_input_str, data)
    phase0, pc, mem_value = v['phase0'], v['pc'], v['mem_value']
    next_pc = (pc+1) & 0xfff
    outv=dict()
    if phase0==0:
        outv = {'phase':1, 'instr':mem_value&0xf, 'pc':next_pc, 'tmp':(mem_value>>4)&0xf,
                'mem_address':pc}
    else:
        instr = mem_value&0xf
        single_byte = instr==instr_clc or instr==instr_sec or \
                instr==instr_rol or instr==instr_ror
        outv = {'phase':2, 'instr':mem_value&0xf,
                'pc':pc if single_byte else next_pc, 'tmp':(mem_value>>4)&0xf,
                'mem_address':pc}
    return bin_comp(cpu_phase01_output_str, outv)

def cpu_phase01_1_input_test_func(case):
    return bin_comp(cpu_phase01_input_str,
        {'phase0':case&1,'pc':((case>>1)&0xff)*5,'mem_value':(case>>9)&0x7f})

gen_testsuite("cpu_phase01_1", "cpu_phase01", 21, 34, range(0, 1<<16), cpu_phase01,
                cpu_phase01_1_input_test_func)
