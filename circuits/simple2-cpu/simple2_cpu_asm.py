
instr_lda=0
instr_sta=1
instr_adc=2
instr_sbc=3
instr_and=4
instr_ora=5
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

def instr_addr(addr):
    return (((addr>>8)&0xf)<<4) | ((addr&0xff)<<8)

"""
Assemblying program should be done by using assemble method which argument is function that
generates code. Function should return start address from assemble method will start
collecting of immediates for *_imm pseudo-instructions.
Methods byte, word16, word32 - put values into memory.
Methods lda, sta, ... generates instructions. 'addr' is address.
Special argument is mod - defines which byte of instruction will be modified while
executing code.
Methods lda_imm, ... generates instructions that operates on specified immediate.
Because processor doesn't have immediate mode for instructions, thus assembler
manages immediates after program code.
"""

class Memory:
    def __init__(self):
        self.mem = [0]*(1<<12)
        self.mmod = [True]*(1<<12)
        self.pc = 0
    
    def clearmod(self):
        self.mmod = [True]*(1<<12)
    
    def set_pc(self, pc):
        self.pc = pc&0xfff
    
    def byte(self, a, mod=False):
        self.mem[self.pc] = a & 0xff
        self.mmod[self.pc] = mod
        self.pc = (self.pc + 1) & 0xfff
    
    def word16(self, a, mod=[False,False]):
        self.byte(a&0xff, mod[0])
        self.byte((a>>8)&0xff, mod[1])
    
    def word32(self, a, mod=[False,False,False,False]):
        self.word16(a&0xffff, mod[0:2])
        self.word16((a>>16)&0xffff, mod[2:4])

    def lda(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_lda | instr_addr(addr), mod)
        else:
            self.word16(instr_lda | instr_addr(0), [True, True])
    
    def sta(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            if self.mmod[addr]:
                self.word16(instr_sta | instr_addr(addr), mod)
            else:
                raise(RuntimeError("Illegal write to memory %d"%addr))
        else:
            self.word16(instr_sta | instr_addr(0), [True, True])
    
    def adc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_adc | instr_addr(addr), mod)
        else:
            self.word16(instr_adc | instr_addr(0), [True, True])
    
    def sbc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_sbc | instr_addr(addr), mod)
        else:
            self.word16(instr_sbc | instr_addr(0), [True, True])
    
    def ana(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_and | instr_addr(addr), mod)
        else:
            self.word16(instr_and | instr_addr(0), [True, True])
    
    def ora(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_ora | instr_addr(addr), mod)
        else:
            self.word16(instr_ora | instr_addr(0), [True, True])
    
    def xor(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_xor | instr_addr(addr), mod)
        else:
            self.word16(instr_xor | instr_addr(0), [True, True])
    
    def clc(self, mod=False):
        self.byte(instr_clc, mod)
    
    def rol(self, mod=False):
        self.byte(instr_rol, mod)
    
    def ror(self, mod=False):
        self.byte(instr_ror, mod)
    
    def bcc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_bcc | instr_addr(addr), mod)
        else:
            self.word16(instr_bcc | instr_addr(0), [True,True])
    
    def bne(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_bne | instr_addr(addr), mod)
        else:
            self.word16(instr_bne | instr_addr(0), [True,True])
    
    def bvc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_bvc | instr_addr(addr), mod)
        else:
            self.word16(instr_bvc | instr_addr(0), [True,True])
    
    def bpl(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_bpl | instr_addr(addr), mod)
        else:
            self.word16(instr_bpl | instr_addr(0), [True,True])
    
    def spc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_spc | instr_addr(addr), mod)
        else:
            self.word16(instr_spc | instr_addr(0), [True, True])
    
    def sec(self, mod=False):
        self.byte(instr_sec, mod)
    
    def lda_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.lda(imms[im], mod)
        else:
            self.lda(0, [True,True])
            imms[im] = -1
    
    def adc_imm(self, im, mod=[False,False]):
        global imms
        if im in imms:
            self.adc(imms[im], mod)
        else:
            self.adc(0, [True,True])
            imms[im] = -1
    
    def sbc_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.sbc(imms[im], mod)
        else:
            self.sbc(0, [True,True])
            imms[im] = -1
    
    def ana_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.ana(imms[im], mod)
        else:
            self.ana(0, [True,True])
            imms[im] = -1
    
    def ora_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.ora(imms[im], mod)
        else:
            self.ora(0, [True,True])
            imms[im] = -1
    
    def xor_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.xor(imms[im], mod)
        else:
            self.xor(0, [True,True])
            imms[im] = -1
    
    def spc_imm(self, im, mod=[False,False]):
        global imms
        if im in imms and imms[im]>=0:
            self.spc(imms[im], mod)
        else:
            self.spc(0, [True,True])
            imms[im] = -1

    def dump(self):
        out = b''
        for i in range(0,1<<12):
            out += bytes([self.mem[i]])
        return out

    def imms(self,r):
        vals=dict()
        for i in r:
            if not self.mmod[i] and self.mem[i] not in vals:
                vals[self.mem[i]] = i
        return vals
    
    def rest_imms(self, imms):
        new_imms = dict()
        for (k,v) in imms.items():
            if v<0:
                new_imms[k] = self.pc
                self.byte(k)
                break
        imms |= new_imms
        return len(new_imms)!=0
    
    def assemble(self, codegen, stages=3):
        global imms
        imms = dict()
        for i in range(0,stages):
            start=codegen()
        imm_pc = self.pc
        start=codegen()
        join_imms(imms, self.imms(range(start,self.pc)))
        while self.rest_imms(imms):
            imm_pc = self.pc
            start=codegen()
            join_imms(imms, self.imms(range(start,self.pc)))
            self.pc = imm_pc

def join_imms(imms1, imms2):
    for (k,v) in imms2.items():
        if v>=0 and (k not in imms1 or imms1[k]<0):
            imms1[k] = v
