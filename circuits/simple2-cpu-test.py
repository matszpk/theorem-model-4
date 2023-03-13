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
