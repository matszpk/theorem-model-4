from simple_cpu_asm import *
from sys import stdout

ml = Memory()

mul_a = 0xf8
mul_b = 0xfa
mul_c = 0xfc
mul_t1 = 0xf0
mul_t2 = 0xf4
mul_t3 = 0xf6

skip_add = 0
for i in range(0,2):
    ml.set_pc(0x10)
    start = ml.pc
    # copy mul_a to mul_t1
    ml.lda(start)    # zero
    for i in range(0,2):
        ml.lda(mul_a+i)
        ml.sta(mul_t1+i)
    # copy mul_t2 to 1
    ml.lda(start)    # zero
    ml.sta(mul_t2+1)
    ml.lda(start+2)  # 1
    ml.sta(mul_t2)
    
    # main loop
    loop = ml.pc
    # mul_t2&mul_b
    ml.lda(mul_t2)
    ml.iand(mul_b)
    ml.sta(mul_t3)
    ml.lda(mul_t2+1)
    ml.iand(mul_b+1)
    ml.ior(mul_t3)
    # bne to do 
    pc = ml.pc
    ml.bne(pc+6)
    ml.jmp(skip_add)
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
    # shift mul_t2
    ml.clc()
    for i in range(0,2):
        ml.lda(mul_t2+i)
        ml.rol()
        ml.sta(mul_t2+i)
    # check if t2 is zero (check if carry in last)
    ml.bcc(loop)
    ml.pul()

ml.set_pc(mul_a)
ml.byte(75)
ml.byte(99)

stdout.buffer.write(ml.dump())
