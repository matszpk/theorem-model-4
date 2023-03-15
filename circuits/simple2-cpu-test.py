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
#gen_testsuite("and_4", "and_4", 4, 1, range(0, 1<<4), lambda x: (x&1)&((x>>1)&1)&((x>>2)&1)&(x>>3))
gen_testsuite("or_4", "or_4", 4, 1, range(0, 1<<4), lambda x: (x&1)|((x>>1)&1)|((x>>2)&1)|(x>>3))
gen_testsuite("ite", "ite", 3, 1, range(0, 1<<3), ite)
gen_testsuite("ite_4bit", "ite_4bit", 9, 4, range(0, 1<<9), ite_4bit)
gen_testsuite("full_adder", "full_adder", 3, 2, range(0, 1<<3), full_adder)
#gen_testsuite("half_adder", "half_adder", 2, 2, range(0, 1<<2), full_adder)
#gen_testsuite("half_suber", "half_suber", 2, 2, range(0, 1<<2), lambda x: full_adder(x+4))
gen_testsuite("carry_adder_4bit", "carry_adder_4bit", 9, 5, range(0, 1<<9), carry_adder_4bit)
gen_testsuite("carry_suber_4bit", "carry_suber_4bit", 9, 5, range(0, 1<<9), carry_suber_4bit)
#gen_testsuite("dec_4bit", "dec_4bit", 4, 4, range(0, 1<<4), lambda x: (16+x-1)&0xf)
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
def set_flag_v(flags,v):
    return (flags&~4)|(4 if v else 0)
def set_flag_n(flags,n):
    return (flags&~8)|(8 if n else 0)

cpu_phase01_input_str = (('phase0',1),('pc',12),('mem_value',8))
cpu_phase01_output_str = (('phase',2),('instr',4),('tmp',4),('pc',12),('mem_address',12))

def cpu_phase01(data):
    v = bin_decomp(cpu_phase01_input_str, data)
    phase0, pc, mem_value = v['phase0'], v['pc'], v['mem_value']
    next_pc = (pc+1) & 0xfff
    outv = dict()
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

cpu_exec_0_input_str = (('instr',4),('acc',8),('flags',4),('mem_value',8))
cpu_exec_0_output_str = (('acc',8),('flag_c',1),('flag_v',1))

def cpu_exec_0(data):
    v = bin_decomp(cpu_exec_0_input_str, data)
    instr, acc, flags, mem_value = v['instr'], v['acc'], v['flags'], v['mem_value']
    outv = dict()
    if instr==instr_lda or instr==instr_sta:
        outv = { 'acc':mem_value&0xff,
                 'flag_c':int(flag_c(flags)), 'flag_v':int(flag_v(flags)) }
    elif instr==instr_adc:
        s = (acc + mem_value + (flags&1)) & 0x1ff
        fc = (s>>8)&1
        a7,b7,s7 = (acc>>7)&1, (mem_value>>7)&1, (s>>7)&1
        fv = (a7&b7&(s7^1)) | ((a7^1)&(b7^1)&s7)
        outv = { 'acc': s & 0xff, 'flag_c':fc, 'flag_v':fv }
    elif instr==instr_sbc:
        s = (acc + (mem_value^0xff) + (flags&1)) & 0x1ff
        fc = (s>>8)&1
        a7,b7,s7 = (acc>>7)&1, (mem_value>>7)&1, (s>>7)&1
        fv = (a7&(b7^1)&(s7^1)) | ((a7^1)&b7&s7)
        outv = { 'acc': s & 0xff, 'flag_c':fc, 'flag_v':fv }
    elif instr==instr_and:
        outv = { 'acc': (acc & mem_value) & 0xff, 
                'flag_c':int(flag_c(flags)), 'flag_v':int(flag_v(flags)) }
    elif instr==instr_or:
        outv = { 'acc': (acc | mem_value) & 0xff, 
                'flag_c':int(flag_c(flags)), 'flag_v':int(flag_v(flags)) }
    elif instr==instr_xor:
        outv = { 'acc': (acc ^ mem_value) & 0xff, 
                'flag_c':int(flag_c(flags)), 'flag_v':int(flag_v(flags)) }
    elif instr==instr_clc:
        outv = { 'acc': acc, 'flag_c':0, 'flag_v':int(flag_v(flags)) }
    else:
        raise("Error panic")

    return bin_comp(cpu_exec_0_output_str, outv)

def cpu_exec_0_1_input_test_func(case):
    return bin_comp(cpu_exec_0_input_str,
        {'instr':case&0x7, 'acc':(case>>3)&0xff, 'flags':((case>>11)&0x1)|6,
            'mem_value':(case>>12)&0xff})

gen_testsuite("cpu_exec_0_1", "cpu_exec_0", 24, 10, range(0, 1<<20), cpu_exec_0,
                cpu_exec_0_1_input_test_func)

cpu_exec_input_str = (('instr',4),('acc',8),('flags',4),('mem_value',8))
cpu_exec_output_str = (('acc',8),('flags',4),('create',1),('stop',1))

def cpu_exec(data):
    v = bin_decomp(cpu_exec_input_str, data)
    instr, acc, flags, mem_value = v['instr'], v['acc'], v['flags'], v['mem_value']
    outv = dict()
    
    if instr<8:
        outv = bin_decomp(cpu_exec_0_output_str, cpu_exec_0(data))
        out_acc, fc, fv = outv['acc'], outv['flag_c'], outv['flag_v']
        flags = set_flag_c(flags, fc!=0)
        flags = set_flag_v(flags, fv!=0)
        flags = set_flag_z(flags, out_acc==0)
        flags = set_flag_n(flags, (out_acc&0x80)!=0)
        outv = {'acc':out_acc, 'flags':flags, 'create':0,'stop':0}
    elif instr==instr_rol:
        out_acc = ((acc<<1) + (flags&1)) & 0xff
        flags = set_flag_c(flags, (acc>>7)&1)
        flags = set_flag_z(flags, out_acc==0)
        flags = set_flag_n(flags, (out_acc&0x80)!=0)
        outv = {'acc':out_acc, 'flags':flags, 'create':0,'stop':0}
    elif instr==instr_ror:
        out_acc = ((acc>>1) + ((flags&1)<<7)) & 0xff
        flags = set_flag_c(flags, acc&1)
        flags = set_flag_z(flags, out_acc==0)
        flags = set_flag_n(flags, (out_acc&0x80)!=0)
        outv = {'acc':out_acc, 'flags':flags, 'create':0,'stop':0}
    elif instr==instr_sec:
        outv = {'acc':acc, 'flags':set_flag_c(flags,True), 'create':0,'stop':0}
    elif instr==instr_spc:
        outv = {'acc':acc, 'flags':flags, 'create':(mem_value&1)^1,'stop':mem_value&1}
    else:
        raise("Error panic")
    return bin_comp(cpu_exec_output_str, outv)

def cpu_exec_t1_input_test_func(case):
    return bin_comp(cpu_exec_input_str,
        {'instr':case&0x7, 'acc':(case>>3)&0xff, 'flags':((case>>11)&0x1)|6,
            'mem_value':(case>>12)&0xff})
def cpu_exec_t2_input_test_func(case):
    return bin_comp(cpu_exec_input_str,
        {'instr':8+(case&1), 'acc':(case>>1)&0xff, 'flags':((case>>9)&0x1)|6,
            'mem_value':(case>>10)&0xff})
def cpu_exec_t3_input_test_func(case):
    return bin_comp(cpu_exec_input_str,
        {'instr':14+(case&1), 'acc':(case>>1)&0xff, 'flags':((case>>9)&0x1)|6,
            'mem_value':(case>>10)&0xff})

gen_testsuite("cpu_exec_t1", "cpu_exec", 24, 14, range(0, 1<<20), cpu_exec,
                cpu_exec_t1_input_test_func)
gen_testsuite("cpu_exec_t2", "cpu_exec", 24, 14, range(0, 1<<18), cpu_exec,
                cpu_exec_t2_input_test_func)
gen_testsuite("cpu_exec_t3", "cpu_exec", 24, 14, range(0, 1<<18), cpu_exec,
                cpu_exec_t3_input_test_func)

cpu_phase23_input_str = (('phase0',1),('ign',1),('instr',4),('tmp',4),('acc',8),('flags',4),
                         ('pc',12),('mem_value',8))
cpu_phase23_output_str = (('phase',2),('acc',8),('flags',4),('pc',12),('mem_rw',1),
                          ('mem_value',8),('mem_address',12),('create',1),('stop',1))

def cpu_phase23(data):
    v = bin_decomp(cpu_phase23_input_str, data)
    phase0, instr, tmp, acc = v['phase0'], v['instr'], v['tmp'], v['acc']
    flags, pc, mem_value = v['flags'], v['pc'], v['mem_value']
    outv = dict()
    
    if phase0==0:
        next_pc = pc
        maddr = (mem_value+(tmp<<8))&0xfff
        if_sta = instr==instr_sta
        if_branch = instr==instr_bcc or instr==instr_bne or instr==instr_bvc or instr==instr_bpl
        if (instr==instr_bcc and not flag_c(flags)) or \
            (instr==instr_bne and not flag_z(flags)) or \
            (instr==instr_bvc and not flag_v(flags)) or \
            (instr==instr_bpl and not flag_n(flags)):
            next_pc = maddr
        outv = {'phase':0 if if_sta or if_branch else 3,
                'acc':acc, 'flags':flags, 'pc':next_pc, 'mem_rw':int(if_sta),
                'mem_value':acc, 'mem_address':maddr, 'create':0, 'stop':0}
    else:
        maddr = (mem_value+(tmp<<8))&0xfff
        outv = bin_decomp(cpu_exec_output_str, cpu_exec(bin_comp(cpu_exec_input_str,
                {'instr':instr, 'acc':acc, 'flags':flags, 'mem_value':mem_value})))
        outv |= {'phase':0, 'pc':pc, 'mem_rw':0, 'mem_value':acc, 'mem_address':maddr}
    
    return bin_comp(cpu_phase23_output_str, outv)

def cpu_phase23_sta_input_test_func(case):
    return bin_comp(cpu_phase23_input_str,
        {'phase0':0, 'ign':0, 'instr':instr_sta, 'tmp':(case)&0xf, 'acc':(case>>4)&0xff,
         'flags':(case>>12)&0x1,'pc':0x452+((case>>13)&0xf), 'mem_value':0x1c+((case>>17)&1)})
def cpu_phase23_branch_input_test_func(case):
    return bin_comp(cpu_phase23_input_str,
        {'phase0':0, 'ign':0, 'instr':10+(case&3), 'tmp':(case>>2)&0xf, 'acc':(case>>6)&0xff,
         'flags':(case>>14)&0xf,'pc':0x452+((case>>8)&0x1), 'mem_value':0x1c+((case>>19)&1)})
def cpu_phase23_other_input_test_func(case):
    return bin_comp(cpu_phase23_input_str,
        {'phase0':0, 'ign':0, 'instr':case&0xf, 'tmp':(case>>4)&0xf, 'acc':((case>>8)&0xf)<<2,
         'flags':(case>>12)&0x1,'pc':0x452+((case>>13)&0xf), 'mem_value':0x1c+((case>>17)&1)})

gen_testsuite("cpu_phase23_sta", "cpu_phase23", 42, 49, range(0, 1<<18), cpu_phase23,
                cpu_phase23_sta_input_test_func)
gen_testsuite("cpu_phase23_branch", "cpu_phase23", 42, 49, range(0, 1<<20), cpu_phase23,
                cpu_phase23_branch_input_test_func)
gen_testsuite("cpu_phase23_other", "cpu_phase23", 42, 49, range(0, 1<<18), cpu_phase23,
                cpu_phase23_other_input_test_func)

def cpu_phase23_3_t1_input_test_func(case):
    return bin_comp(cpu_phase23_input_str,
        {'phase0':1,'ign':0,'instr':case&0x7,'tmp':11, 'acc':(case>>3)&0xff,
            'flags':((case>>11)&0x1)|6, 'pc':0xb1a,'mem_value':(case>>12)&0xff})
def cpu_phase23_3_t3_input_test_func(case):
    return bin_comp(cpu_phase23_input_str,
        {'phase0':1,'ign':0,'instr':14+(case&1),'tmp':11,'acc':(case>>1)&0xff,
            'flags':((case>>9)&0x1)|6,'pc':0xd7b,'mem_value':(case>>10)&0xff})

gen_testsuite("cpu_phase23_3_t1", "cpu_phase23", 42, 49, range(0, 1<<20), cpu_phase23,
                cpu_phase23_3_t1_input_test_func)
gen_testsuite("cpu_phase23_3_t3", "cpu_phase23", 42, 49, range(0, 1<<18), cpu_phase23,
                cpu_phase23_3_t3_input_test_func)

cpu_main_input_str = (('phase',2),('instr',4),('tmp',4),('acc',8),('flags',4),('pc',12),
                    ('mem_value',8))
cpu_main_output_str = (('phase',2),('instr',4),('tmp',4),('acc',8),('flags',4),('pc',12),
                    ('mem_value',8),('mem_rw',1),('mem_address',12),('create',1),('stop',1))

def cpu_main(data):
    v = bin_decomp(cpu_main_input_str, data)
    phase, instr, tmp, acc = v['phase'], v['instr'], v['tmp'], v['acc']
    flags, pc, mem_value = v['flags'], v['pc'], v['mem_value']
    outv = dict()

    if phase<2:
        outvtmp = bin_decomp(cpu_phase23_output_str, cpu_phase23(bin_comp(cpu_phase23_input_str,
                {'phase0':phase&1, 'ign':0, 'instr':instr, 'tmp':tmp, 'acc':acc, 'flags':flags,
                 'pc':pc, 'mem_value':mem_value})))
        outv = bin_decomp(cpu_phase01_output_str, cpu_phase01(bin_comp(cpu_phase01_input_str,
                {'phase0':phase&1, 'pc':pc, 'mem_value': mem_value})))
        outv |= {'acc':acc, 'flags':flags, 'mem_value':outvtmp['mem_value'],
                 'mem_rw':0, 'create':0, 'stop':0}
    else:
        outv = bin_decomp(cpu_phase23_output_str, cpu_phase23(bin_comp(cpu_phase23_input_str,
                {'phase0':phase&1, 'ign':0, 'instr':instr, 'tmp':tmp, 'acc':acc, 'flags':flags,
                 'pc':pc, 'mem_value':mem_value})))
        outv |= {'instr':instr, 'tmp':tmp}
    
    return bin_comp(cpu_main_output_str, outv)

def cpu_main_phase01_1_input_test_func(case):
    return bin_comp(cpu_main_input_str,
        {'phase':case&1,'instr':5,'tmp':13,'acc':172,'flags':10,
            'pc':((case>>1)&0xff)*5,'mem_value':(case>>9)&0x7f})
def cpu_main_phase23_branch_input_test_func(case):
    return bin_comp(cpu_main_input_str,
        {'phase':2, 'instr':10+(case&3), 'tmp':(case>>2)&0xf, 'acc':(case>>6)&0xff,
         'flags':(case>>14)&0xf,'pc':0x452+((case>>8)&0x1), 'mem_value':0x1c+((case>>19)&1)})
def cpu_main_phase23_3_t1_input_test_func(case):
    return bin_comp(cpu_main_input_str,
        {'phase':3,'instr':case&0x7,'tmp':11, 'acc':(case>>3)&0xff, 'flags':((case>>11)&0x1)|6,
            'pc':0xb1a,'mem_value':(case>>12)&0xff})
def cpu_main_phase23_3_t3_input_test_func(case):
    return bin_comp(cpu_main_input_str,
        {'phase':3,'instr':14+(case&1),'tmp':11,'acc':(case>>1)&0xff,'flags':((case>>9)&0x1)|6,
            'pc':0xd7b,'mem_value':(case>>10)&0xff})

gen_testsuite("cpu_main_phase01_1", "main", 42, 57, range(0, 1<<16), cpu_main,
                cpu_main_phase01_1_input_test_func)
gen_testsuite("cpu_main_phase23_branch", "main", 42, 57, range(0, 1<<20), cpu_main,
                cpu_main_phase23_branch_input_test_func)
gen_testsuite("cpu_main_phase23_3_t3", "main", 42, 57, range(0, 1<<18), cpu_main,
                cpu_main_phase23_3_t3_input_test_func)
