import math
from sys import stdout

class Memory:
    def __init__(self,addrlen=15):
        self.instr_len_log = int(math.ceil(math.log2((addrlen + 1 + 7)//8)))
        self.mmod = [True]*(1 << (addrlen - 3))
        self.mem = [0]*(1 << (addrlen - 3))
        self.pc = 0
        self.pc_mask = (1 << (addrlen - 3)) - 1
        self.zero_addr = (self.pc_mask - 4,0)
        self.one_addr = (self.pc_mask - 4,7)
        self.prim_rest_addr = -((1 << (addrlen - 3)) - 1)*100
        self.prim_rest = []
        self.mem[self.one_addr[0]] = 0x80
        self.mmod[self.one_addr[0]] = True
    
    def set_pc(self, pc):
        self.pc = pc & self.pc_mask
    
    def byte(self, a, mod=False):
        self.mem[self.pc] = a & 0xff
        self.mmod[self.pc] = mod
        self.pc = (self.pc + 1) & self.pc_mask
    
    def word16(self, a, mod=[False,False]):
        self.byte(a&0xff, mod[0])
        self.byte((a>>8)&0xff, mod[1])
    
    def word32(self, a, mod=[False, False, False, False]):
        self.word16(a&0xffff, mod[0:2])
        self.word16((a>>16)&0xffff, mod[2:4])
    
    def nand(self, addr, bit, mod=[False, False, False, False]):
        if not self.mmod[addr]:
            raise(RuntimeError("Illegal write to memory"))
        if self.instr_len_log == 1:
            if isinstance(addr,int) and addr>=0:
                self.word16(((addr & self.pc_mask) << 4) | ((bit&7) << 1), mod)
            else:
                self.word16(((bit&7) << 1), [True, True, True, True])
        elif self.instr_len_log == 2:
            if isinstance(addr,int) and addr>=0:
                self.word32(((addr & self.pc_mask) << 4) | ((bit&7) << 1), mod)
            else:
                self.word32(((bit&7) << 1), [True, True, True, True])
        else:
            raise(RuntimeError("Unsupported instruction length"))
    
    def bne(self, addr, mod=[False, False, False, False]):
        if self.instr_len_log == 1:
            if isinstance(addr,int) and addr>=0:
                self.word16(((addr & (self.pc_mask - 1)) << 4) | 1, mod)
            else:
                self.word16(1, [True, True, True, True])
        elif self.instr_len_log == 2:
            if isinstance(addr,int) and addr>=0:
                self.word32(((addr & (self.pc_mask - 3)) << 4) | 1, mod)
            else:
                self.word32(1, [True, True, True, True])
        else:
            raise(RuntimeError("Unsupported instruction length"))
    
    def stop(self, mod=[False, False, False, False]):
        if self.instr_len_log == 1:
            self.word16(3, mod)
        elif self.instr_len_log == 2:
            self.word32(3, mod)
        else:
            raise(RuntimeError("Unsupported instruction length"))
    
    def create(self, mod=[False, False, False, False]):
        if self.instr_len_log == 1:
            self.word16(5, mod)
        elif self.instr_len_log == 2:
            self.word32(5, mod)
        else:
            raise(RuntimeError("Unsupported instruction length"))
    
    def zero(self):
        self.nand(*self.zero_addr)
        self.nand(*self.zero_addr)
    
    def one(self):
        self.zero()
        self.nand(*self.one_addr)
    
    def neg_mem(self, addr, bit, mod=[False, False, False, False]):
        self.bne(self.pc + (1<<self.instr_len_log)*2)
        self.nand(*self.one_addr)
        self.nand(addr, bit, mod)
    
    def load_mem(self, addr, bit, mod=[False]*8):
        self.neg_mem(addr, bit, mod[0:4])
        self.nand(addr, bit, mod[4:])
    
    def store_one(self, addr, bit, mod=[False, False, False, False]):
        self.zero()
        self.nand(addr, bit, mod)
    
    def store_zero(self, addr, bit, mod=[False]*8):
        self.store_one(addr, bit, mod[0:4])
        self.nand(addr, bit, mod[4:])
    
    def store_mem(self, addr, bit, mod=[False]*12):
        routine_start = self.pc
        self.bne(self.prim_rest_addr + len(self.prim_rest))
        self.nand(addr, bit, mod[0:4])
        self.nand(addr, bit, mod[4:8])
        routine_end = self.pc
        self.store_one(addr, bit, mod[8:])
        self.bne(routine_end)
        self.prim_rest += self.mem[routine_end:self.pc]
        self.set_pc(routine_end)
    
    def store_neg_mem(self, addr, bit, mod=[False]*12):
        self.bne(self.pc + (1<<self.instr_len_log)*3)
        self.nand(addr, bit, mod[0:4])
        self.bne(self.pc + (1<<self.instr_len_log)*5)
        self.store_zero(addr, bit, mod[4:])
        
    def dump(self):
        out = b''
        for i in self.mem:
            out += bytes([i])
        return out

    def assemble(self, codegen, stages=3):
        for i in range(0,stages):
            self.prim_rest = []
            start=codegen()
            self.mem[self.pc:self.pc+len(self.prim_rest)] = self.prim_rest
            self.prim_rest_addr = self.pc
    
