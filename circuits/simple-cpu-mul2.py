from simple_cpu_asm import *
from sys import stdout

ml = Memory()

mul_a = 0xf8
mul_b = 0xfa
mul_c = 0xfc
mul_t1 = 0xf0
mul_t2 = 0xf4

skip_add = 0
for i in range(0,2):
    ml.set_pc(0x10)
    start = ml.pc
    # copy mul_a to mul_t1
    ml.lda(start)    # zero
    for i in range(0,2):
        ml.lda(mul_a+i)
        ml.sta(mul_t1+i)
    # copy mul_b to mul_t2
    ml.lda(mul_b)
    ml.sta(mul_t2)
    ml.lda(mul_b+1)
    ml.sta(mul_t2+1)
    
    # main loop
    loop = ml.pc
    # mul_t2>>1, c
    ml.clc()
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
    for i in range(0,4):
        ml.lda(mul_t1+i)
        ml.adc(mul_c+i)
        ml.sta(mul_c+i)
    skip_add = ml.pc
    # shift mul_t1
    ml.clc()
    for i in range(0,4):
        ml.lda(mul_t1+i)
        ml.rol()
        ml.sta(mul_t1+i)
    # check t2
    ml.lda(mul_t2)
    ml.ior(mul_t2+1)
    ml.bne(loop)
    ml.pul()

ml.set_pc(mul_a)
ml.byte(75)
ml.byte(99)

stdout.buffer.write(ml.dump())
