
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
instr_bvc=12
instr_bpl=13
instr_spc=14
instr_sec=15

def instr_addr(addr):
    return (((addr>>8)&0xf)<<4) | ((addr&0xff)<<8)

class Memory:
    def __init__(self):
        self.mem = [0]*(1<<12)
        self.pc = 0
    
    def set_pc(self, pc):
        self.pc = pc&0xfff
    
    def byte(self, a):
        self.mem[self.pc] = a & 0xff
        self.pc = (self.pc + 1) & 0xfff
    
    def word16(self, a):
        self.byte(a&0xff)
        self.byte((a>>8)&0xff)
    
    def word32(self, a):
        self.word16(a&0xffff)
        self.word16((a>>16)&0xffff)

    def lda(self, addr):
        self.word16(instr_lda | instr_addr(addr))
    def sta(self, addr):
        self.word16(instr_sta | instr_addr(addr))
    def adc(self, addr):
        self.word16(instr_adc | instr_addr(addr))
    def sbc(self, addr):
        self.word16(instr_sbc | instr_addr(addr))
    def ana(self, addr):
        self.word16(instr_and | instr_addr(addr))
    def ora(self, addr):
        self.word16(instr_or | instr_addr(addr))
    def xor(self, addr):
        self.word16(instr_xor | instr_addr(addr))
    def clc(self):
        self.byte(instr_clc)
    def bcc(self, addr):
        self.word16(instr_bcc | instr_addr(addr))
    def bne(self, addr):
        self.word16(instr_bne | instr_addr(addr))
    def bvc(self, addr):
        self.word16(instr_bvc | instr_addr(addr))
    def bpl(self, addr):
        self.word16(instr_bpl | instr_addr(addr))
    def spc(self, addr):
        self.word16(instr_spc | instr_addr(addr))
    def sec(self, addr):
        self.byte(instr_sec)

    def dump(self):
        out = b''
        for i in range(0,1<<12):
            out += bytes(self.mem)
        return out
