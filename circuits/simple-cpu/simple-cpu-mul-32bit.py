from simple_cpu_asm import *
from sys import stdout

ml = Memory()

mul_a = 0xe0
mul_b = 0xd8
mul_c = 0xf0
mul_temp = 0xd7

skip_add = 0
one = 0
zero = 0
for i in range(0,2):
    ml.set_pc(0x0)
    start = ml.pc
    # main loop
    loop = ml.pc
    # mul_b>>1, c
    ml.clc()
    for i in range(7,-1,-1):
        zero = ml.pc
        ml.lda(mul_b+i)
        ml.ror()
        one = ml.pc
        ml.sta(mul_b+i)
    # bne to do 
    pc = ml.pc
    ml.bcc(skip_add)
    # add: mul_t1 to result mul_c
    ml.lda(zero)
    ml.sta(mul_temp)
    #add_loop
    add_loop = ml.pc
    ml.lda(mul_temp)
    ml.ror()
    
    add_x0 = ml.pc
    ml.lda(mul_a)
    add_x1 = ml.pc
    ml.adc(mul_c)
    add_x2 = ml.pc
    ml.sta(mul_c)
    
    ml.rol()
    ml.sta(mul_temp)
    
    ml.lda(add_x0+1)
    ml.clc()
    ml.adc(one)
    ml.sta(add_x0+1)
    ml.sta(add_x1+1)
    ml.sta(add_x2+1)
    ml.bne(add_loop)
    
    skip_add = ml.pc
    # shift mul_a
    ml.lda(zero)
    ml.sta(mul_temp)
    #rol_loop
    rol_loop = ml.pc
    ml.lda(mul_temp)
    ml.ror()
    
    rol_x0 = ml.pc
    ml.lda(mul_a)
    ml.rol()
    rol_x1 = ml.pc
    ml.sta(mul_a)
    
    ml.rol()
    ml.sta(mul_temp)
    
    ml.lda(rol_x0+1)
    ml.clc()
    ml.adc(one)
    ml.sta(rol_x0+1)
    ml.sta(rol_x1+1)
    ml.bne(rol_loop)
    
    # check b
    ml.lda(mul_b)
    for i in range(1,8):
        ml.ior(mul_b+i)
    ml.bne(loop)
    ml.pul()

ml.set_pc(mul_a)
ml.word32(875911234)
ml.set_pc(mul_b)
ml.word32(789114541)

stdout.buffer.write(ml.dump())
