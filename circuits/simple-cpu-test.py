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
# gen_testsuite("ite_4bit_2", "ite_4bit", 9, 4, range(0, 1<<3), ite_4bit, \
#        lambda x: (x&1)|((((x>>1)&1)*0xf)<<1)|(((x>>2)*0xf)<<5))

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

def cpu_phase_012(data):
    v = bin_decomp((('state',3),('instr',4),('pc',8),('tempreg',4),('mem_value',4)), data)
    state, instr, pc = v['state'], v['instr'], v['pc']
    tempreg, mem_value = v['tempreg'], v['mem_value']
    next_pc = (pc + 1) & 0xff
    outv = dict()
    if state==0:
        outv = {'state':1,'instr':instr,'pc':next_pc,'tempreg':tempreg,'mem_rw':0,
                 'mem_address':pc }
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
    return bin_comp((('state',3),('instr',4),('pc',8),
                     ('tempreg',4),('mem_rw',1),('mem_address',8)), outv)

print(
    bin_decomp((('state',3),('instr',4),('pc',8),
            ('tempreg',4),('mem_rw',1),('mem_address',8)),
    cpu_phase_012(
        bin_comp((('state',3),('instr',4),('pc',8),('tempreg',4),('mem_value',4)),
                {'state':2,'instr':instr_sbc,'pc':41,'tempreg':7,'mem_value':11})
        )))
