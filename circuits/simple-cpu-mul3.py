from simple_cpu_asm import *
from sys import stdout

ml = Memory()

mul_a = 0xf0
mul_b = 0xec
mul_c = 0xf8

skip_add = 0
for i in range(0,2):
    ml.set_pc(0x0)
    start = ml.pc
    # main loop
    loop = ml.pc
    # mul_b>>1, c
    #ml.clc()
    for i in range(3,-1,-1):
        ml.lda(mul_b+i)
        ml.ror()
        ml.sta(mul_b+i)
    # bne to do 
    pc = ml.pc
    ml.bcc(skip_add)
    # add: mul_t1 to result mul_c
    ml.clc()
    for i in range(0,8):
        ml.lda(mul_a+i)
        ml.adc(mul_c+i)
        ml.sta(mul_c+i)
    skip_add = ml.pc
    # shift mul_a
    #ml.clc()
    for i in range(0,8):
        ml.lda(mul_a+i)
        ml.rol()
        ml.sta(mul_a+i)
    # check b
    ml.lda(mul_b)
    for i in range(1,4):
        ml.ior(mul_b+i)
    ml.bne(loop)
    ml.pul()

ml.set_pc(mul_a)
ml.word16(26821)
ml.set_pc(mul_b)
ml.word16(48719)

stdout.buffer.write(ml.dump())
