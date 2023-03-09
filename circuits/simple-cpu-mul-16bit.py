from simple_cpu_asm import *
from sys import stdout

ml = Memory()

mul_a = 0xf0
mul_b = 0xf4
mul_c = 0xf8
mul_t1 = 0xe4
mul_t2 = 0xec

skip_add = 0
for i in range(0,2):
    ml.set_pc(0x0)
    start = ml.pc
    # copy mul_a to mul_t1
    for i in range(0,4):
        ml.lda(mul_a+i)
        ml.sta(mul_t1+i)
    # copy mul_b to mul_t2
    for i in range(0,4):
        ml.lda(mul_b+i)
        ml.sta(mul_t2+i)
    
    # main loop
    loop = ml.pc
    # mul_t2>>1, c
    #ml.clc()
    ml.lda(mul_t2+3)
    ml.ror()
    ml.sta(mul_t2+3)
    ml.lda(mul_t2+2)
    ml.ror()
    ml.sta(mul_t2+2)
    ml.lda(mul_t2+1)
    ml.ror()
    ml.sta(mul_t2+1)
    ml.lda(mul_t2)
    ml.ror()
    ml.sta(mul_t2)
    # bne to do 
    pc = ml.pc
    ml.bcc(skip_add)
    # add: mul_t1 to result mul_c
    ml.clc()
    for i in range(0,8):
        ml.lda(mul_t1+i)
        ml.adc(mul_c+i)
        ml.sta(mul_c+i)
    skip_add = ml.pc
    # shift mul_t1
    #ml.clc()
    for i in range(0,8):
        ml.lda(mul_t1+i)
        ml.rol()
        ml.sta(mul_t1+i)
    # check t2
    ml.lda(mul_t2)
    ml.ior(mul_t2+1)
    ml.ior(mul_t2+2)
    ml.ior(mul_t2+3)
    ml.bne(loop)
    ml.pul()

ml.set_pc(mul_a)
ml.word16(26821)
ml.word16(48716)

stdout.buffer.write(ml.dump())
