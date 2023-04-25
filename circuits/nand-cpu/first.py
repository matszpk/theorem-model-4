from nand_cpu_asm import *

#addrlen = 17
ml = Memory()

def gencode():
    start = 0
    ml.set_pc(start)
    ml.zero()
    ml.store_mem_rest(0xff0,4)
    ml.stop()
    end = ml.pc
    ml.set_pc(0xff0)
    ml.byte(0x10, True)
    ml.set_pc(end)
    return start

ml.assemble(gencode)

stdout.buffer.write(ml.dump())
