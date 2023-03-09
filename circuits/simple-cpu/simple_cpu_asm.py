
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

class Memory:
    def __init__(self):
        self.mem = [0]*256
        self.pc = 0
    
    def set_pc(self, pc):
        self.pc = pc&0xff
    
    def nibble(self, a):
        self.mem[self.pc] = a & 0xf
        self.pc = (self.pc + 1) & 0xff
    
    def word16(self, a):
        self.byte(a&0xff)
        self.byte((a>>8)&0xff)
    
    def word32(self, a):
        self.word16(a&0xffff)
        self.word16((a>>16)&0xffff)
    
    def byte(self, a):
        self.nibble(a&0xf)
        self.nibble((a>>4)&0xf)

    def nibbles3(self, a, b, c):
        self.nibble(a)
        self.nibble(b)
        self.nibble(c)

    def lda(self, addr):
        self.nibbles3(instr_lda, addr&0xf, addr>>4)
    def sta(self, addr):
        self.nibbles3(instr_sta, addr&0xf, addr>>4)
    def adc(self, addr):
        self.nibbles3(instr_adc, addr&0xf, addr>>4)
    def sbc(self, addr):
        self.nibbles3(instr_sbc, addr&0xf, addr>>4)
    def iand(self, addr):
        self.nibbles3(instr_and, addr&0xf, addr>>4)
    def ior(self, addr):
        self.nibbles3(instr_or, addr&0xf, addr>>4)
    def xor(self, addr):
        self.nibbles3(instr_xor, addr&0xf, addr>>4)
    def clc(self):
        self.nibble(instr_clc)
    def rol(self):
        self.nibble(instr_rol)
    def ror(self):
        self.nibble(instr_ror)
    def bcc(self, addr):
        self.nibbles3(instr_bcc, addr&0xf, addr>>4)
    def bne(self, addr):
        self.nibbles3(instr_bne, addr&0xf, addr>>4)
    def bpl(self, addr):
        self.nibbles3(instr_bpl, addr&0xf, addr>>4)
    def jmp(self, addr):
        self.nibbles3(instr_jmp, addr&0xf, addr>>4)
    def psh(self):
        self.nibble(instr_psh)
    def pul(self):
        self.nibble(instr_pul)

    def dump(self):
        out = b''
        for i in range(0,128):
            out += bytes([self.mem[i*2] + (self.mem[i*2+1]<<4)])
        return out
