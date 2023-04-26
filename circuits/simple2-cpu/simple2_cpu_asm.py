
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

flag_C = 0
flag_Z = 1
flag_V = 2
flag_N = 3

flag_clear = 0
flag_set = 1
flag_undef = 2

acc_undef = -1

def instr_addr(addr):
    return (((addr>>8)&0xf)<<4) | ((addr&0xff)<<8)

def join_flags(flags_a, flags_b, acc_a, acc_b):
    flags_out = [flags_a[0],flags_a[1],flags_a[2],flags_a[3]]
    for i in range(0,4):
        if flags_a[i]==flag_undef or flags_b[i]==flag_undef:
            flags_out[i] = flag_undef
        elif flags_a[i] != flags_b[i]:
            flags_out[i] = flag_undef
    acc_out = acc_a
    if acc_a==acc_undef or acc_b==acc_undef:
        acc_out = acc_undef
    elif acc_a != acc_b:
        acc_out = acc_undef
    return flags_out, acc_out

# TODO: write subroutine handling
# TODO: extend flags handling (add label handling)

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
        self.flags = [flag_undef,flag_undef,flag_undef,flag_undef]
        self.acc = acc_undef
        self.labels = dict()
    
    def clearmod(self):
        self.mmod = [True]*(1<<12)
    
    def clearflags(self):
        self.flags = [flag_undef,flag_undef,flag_undef,flag_undef]
    
    def clearacc(self):
        self.acc = acc_undef
    
    def set_flag(self, flag, value):
        self.flags[flag] = value
    
    def flag_is_set(self, flag):
        return self.flags[flag]==flag_set
    
    def flag_is_not_set(self, flag):
        return self.flags[flag]!=flag_set
    
    def flag_is_clear(self, flag):
        return self.flags[flag]==flag_clear
    
    def flag_is_not_clear(self, flag):
        return self.flags[flag]!=flag_clear
    
    def set_flag_NZ(self, value):
        if value==0:
            self.set_flag(flag_Z, flag_set)
            self.set_flag(flag_N, flag_clear)
        elif (value&0x80)!=0:
            self.set_flag(flag_Z, flag_clear)
            self.set_flag(flag_N, flag_set)
        else:
            self.set_flag(flag_Z, flag_clear)
            self.set_flag(flag_N, flag_clear)
    
    def acc_is_undef(self):
        return self.acc < 0
    
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

    def lda(self, addr, mod=[False,False], imm=acc_undef):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_lda | instr_addr(addr), mod)
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            
            if imm!=acc_undef:
                self.set_flag_NZ(imm)
                self.acc = imm
            else:
                self.set_flag(flag_N, flag_undef)
                self.set_flag(flag_Z, flag_undef)
                self.acc = acc_undef
        else:
            self.word16(instr_lda | instr_addr(0), [True, True])
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
            self.acc = acc_undef
    
    def sta(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            if self.mmod[addr]:
                self.word16(instr_sta | instr_addr(addr), mod)
            else:
                raise(RuntimeError("Illegal write to memory %d"%addr))
        else:
            self.word16(instr_sta | instr_addr(0), [True, True])
    
    def adc(self, addr, mod=[False,False], imm=acc_undef):
        new_flag_N = self.flags[flag_N]
        new_flag_Z = self.flags[flag_Z]
        new_acc = self.acc
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_adc | instr_addr(addr), mod)
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            new_flag_C = flag_undef
            determined = False
            determined_all = False
            if self.acc != acc_undef:
                if imm!=acc_undef and self.flags[flag_C]!=flag_undef:
                    acc = self.acc
                    mem_value = imm
                    flagc = int(self.flag_is_set(flag_C))
                    s = (acc + mem_value + flagc) & 0x1ff
                    fc = (s>>8)&1
                    a7,b7,s7 = (acc>>7)&1, (mem_value>>7)&1, (s>>7)&1
                    fv = (a7&b7&(s7^1)) | ((a7^1)&(b7^1)&s7)
                    self.acc = s&0xff
                    self.set_flag(flag_C, fc)
                    self.set_flag(flag_V, fv)
                    self.set_flag_NZ(self.acc)
                    determined = True
                    determined_all = True
                elif self.flag_is_set(flag_C) and self.acc==0xff:
                    new_flag_C = flag_set
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
                elif self.flag_is_set(flag_C) or self.acc!=0x00:
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
                    
            if imm!=acc_undef:
                if self.flag_is_set(flag_C) and imm==0xff:
                    new_flag_C = flag_set
                    if not determined:
                        new_flag_N = flag_undef
                        new_flag_Z = flag_undef
                        new_acc = acc_undef
                elif not determined and (self.flag_is_set(flag_C) or imm!=0x00):
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
            
            if not determined_all:
                self.set_flag(flag_C, new_flag_C)
                self.set_flag(flag_V, flag_undef)
                self.set_flag(flag_N, new_flag_N)
                self.set_flag(flag_Z, new_flag_Z)
                self.acc = new_acc
        else:
            self.word16(instr_adc | instr_addr(0), [True, True])
            self.set_flag(flag_C, flag_undef)
            self.set_flag(flag_V, flag_undef)
            self.set_flag(flag_N, new_flag_N)
            self.set_flag(flag_Z, new_flag_Z)
            self.acc = new_acc
    
    def sbc(self, addr, mod=[False,False], imm=acc_undef):
        new_flag_N = self.flags[flag_N]
        new_flag_Z = self.flags[flag_Z]
        new_acc = self.acc
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_sbc | instr_addr(addr), mod)
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            
            new_flag_C = flag_undef
            determined = False
            determined_all = False
            if self.acc != acc_undef:
                if imm!=acc_undef and self.flags[flag_C]!=flag_undef:
                    acc = self.acc
                    mem_value = imm
                    flagc = int(self.flag_is_set(flag_C))
                    s = (acc + (mem_value^0xff) + flagc) & 0x1ff
                    fc = (s>>8)&1
                    a7,b7,s7 = (acc>>7)&1, (mem_value>>7)&1, (s>>7)&1
                    fv = (a7&(b7^1)&(s7^1)) | ((a7^1)&b7&s7)
                    self.acc = s&0xff
                    self.set_flag(flag_C, fc)
                    self.set_flag(flag_V, fv)
                    self.set_flag_NZ(self.acc)
                    determined = True
                    determined_all = True
                elif self.flag_is_set(flag_C) and self.acc==0xff:
                    new_flag_C = flag_set
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
                elif self.flag_is_set(flag_C) or self.acc!=0x00:
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
                    
            if imm!=acc_undef:
                if self.flag_is_set(flag_C) and imm==0x00:
                    new_flag_C = flag_set
                    if not determined:
                        new_flag_N = flag_undef
                        new_flag_Z = flag_undef
                        new_acc = acc_undef
                elif not determined and (self.flag_is_set(flag_C) or imm!=0xff):
                    new_flag_N = flag_undef
                    new_flag_Z = flag_undef
                    new_acc = acc_undef
            
            if not determined_all:
                self.set_flag(flag_C, new_flag_C)
                self.set_flag(flag_V, flag_undef)
                self.set_flag(flag_N, new_flag_N)
                self.set_flag(flag_Z, new_flag_Z)
                self.acc = new_acc
        else:
            self.word16(instr_sbc | instr_addr(0), [True, True])
            self.set_flag(flag_C, flag_undef)
            self.set_flag(flag_V, flag_undef)
            self.set_flag(flag_N, new_flag_N)
            self.set_flag(flag_Z, new_flag_Z)
            self.acc = new_acc
    
    def ana(self, addr, mod=[False,False], imm=acc_undef):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_and | instr_addr(addr), mod)
            determined_N = False
            determined_Z = False
            determined_acc = False
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            
            if self.acc != acc_undef:
                if imm!=acc_undef:
                    self.acc = self.acc & imm
                    self.set_flag_NZ(self.acc)
                    determined_N = True
                    determined_Z = True
                    determined_acc = True
                elif self.acc == 0:
                    self.set_flag(flag_N, flag_clear)
                    self.set_flag(flag_Z, flag_set)
                    determined_N = True
                    determined_Z = True
                    determined_acc = True
                elif (self.acc&0x80) == 0:
                    self.set_flag(flag_N, flag_clear)
                    determined_N = True
                    self.set_flag(flag_Z, flag_undef)
            
            if imm!=acc_undef and self.acc==acc_undef:
                if (imm&0x80) == 0:
                    self.set_flag(flag_N, flag_clear)
                if self.flag_is_clear(flag_N):
                    if (imm&0x7f) == 0:
                        self.set_flag(flag_Z, flag_set)
                        self.acc = 0
                    else:
                        if not determined_Z:
                            self.set_flag(flag_Z, flag_undef)
                        if not determined_acc:
                            self.acc = acc_undef
                elif self.flag_is_set(flag_N):
                    self.set_flag(flag_Z, flag_clear)
                    if (imm&0x7f) == 0:
                        self.acc = 0x80
                    elif (imm&0x7f) != 0x7f:
                        if not determined_acc:
                            self.acc = acc_undef
                else:
                    if not determined_N:
                        self.set_flag(flag_N, flag_undef)
                    if not determined_Z:
                        self.set_flag(flag_Z, flag_undef)
                    if not determined_acc:
                        self.acc = acc_undef
            else:
                if not determined_N:
                    self.set_flag(flag_N, flag_undef)
                if not determined_Z:
                    self.set_flag(flag_Z, flag_undef)
                if not determined_acc:
                    self.acc = acc_undef
        else:
            self.word16(instr_and | instr_addr(0), [True, True])
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
    
    def ora(self, addr, mod=[False,False], imm=acc_undef):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_ora | instr_addr(addr), mod)
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            
            determined_N = False
            determined_Z = False
            determined_acc = False
            if self.acc != acc_undef:
                if imm!=acc_undef:
                    self.acc = self.acc | imm
                    self.set_flag_NZ(self.acc)
                    determined_N = True
                    determined_Z = True
                    determined_acc = True
                elif self.acc == 0xff:
                    self.set_flag(flag_N, flag_set)
                    self.set_flag(flag_Z, flag_clear)
                    determined_N = True
                    determined_Z = True
                    determined_acc = True
                elif (self.acc&0x80) != 0:
                    self.set_flag(flag_N, flag_set)
                    self.set_flag(flag_Z, flag_clear)
                    determined_N = True
                    determined_Z = True
                elif self.acc != 0:
                    self.set_flag(flag_N, flag_undef)
                    self.set_flag(flag_Z, flag_clear)
                    determined_Z = True
            
            if imm!=acc_undef and self.acc==acc_undef:
                if (imm&0x80) != 0:
                    self.set_flag(flag_N, flag_set)
                if self.flag_is_set(flag_N):
                    self.set_flag(flag_Z, flag_clear)
                    if (imm&0x7f) == 0x7f:
                        self.acc = 0xff
                    else:
                        if not determined_acc:
                            self.acc = acc_undef
                elif self.flag_is_clear(flag_N):
                    if (imm&0x7f) == 0x7f:
                        self.acc = 0x7f
                        self.set_flag(flag_Z, flag_clear)
                    elif (imm&0x7f) != 0:
                        if not determined_acc:
                            self.acc = acc_undef
                        self.set_flag(flag_Z, flag_clear)
                    else:
                        if not determined_Z:
                            self.set_flag(flag_Z, flag_undef)
                else:
                    if not determined_N:
                        self.set_flag(flag_N, flag_undef)
                    if (imm&0x7f) != 0:
                        self.set_flag(flag_Z, flag_clear)
                    elif not determined_Z:
                        self.set_flag(flag_Z, flag_undef)
                    if not determined_acc:
                        self.acc = acc_undef
            else:
                if not determined_N:
                    self.set_flag(flag_N, flag_undef)
                if not determined_Z:
                    self.set_flag(flag_Z, flag_undef)
                if not determined_acc:
                        self.acc = acc_undef
        else:
            self.word16(instr_ora | instr_addr(0), [True, True])
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
    
    def xor(self, addr, mod=[False,False], imm=acc_undef):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_xor | instr_addr(addr), mod)
            
            if imm==acc_undef and not mod[0] and not mod[1] and not self.mmod[addr]:
                imm = self.mem[addr]
            
            determined_N = False
            determined_Z = False
            determined_acc = False
            if self.acc != acc_undef:
                if imm!=acc_undef:
                    self.acc = self.acc ^ imm
                    self.set_flag_NZ(self.acc)
                    determined_N = True
                    determined_Z = True
                    determined_acc = True
            
            if imm!=acc_undef and self.acc==acc_undef:
                if (imm&0x80) != 0:
                    if self.flag_is_clear(flag_N):
                        self.set_flag(flag_N, flag_set)
                    elif self.flag_is_set(flag_N):
                        self.set_flag(flag_N, flag_clear)
                if (imm&0x7f) != 0:
                    if not determined_acc:
                        self.acc = acc_undef
                    if self.flag_is_not_set(flag_N):
                        if not determined_Z:
                            self.set_flag(flag_Z, flag_undef)
                    else:
                        self.set_flag(flag_Z, flag_clear)
                else:
                    if self.flag_is_set(flag_N):
                        self.set_flag(flag_Z, flag_clear)
                        if not determined_acc:
                            self.acc = acc_undef
            else:
                if not determined_N:
                    self.set_flag(flag_N, flag_undef)
                if not determined_Z:
                    self.set_flag(flag_Z, flag_undef)
                if not determined_acc:
                    self.acc = acc_undef
        else:
            self.word16(instr_xor | instr_addr(0), [True, True])
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
    
    def clc(self, mod=False):
        self.byte(instr_clc, mod)
        if not mod:
            self.set_flag(flag_C, flag_clear)
        else:
            self.set_flag(flag_C, flag_undef)
    
    def cond_clc(self, mod=False):
        if mod or self.flag_is_not_clear(flag_C):
            self.clc(mod)
    
    def rol(self, mod=False):
        self.byte(instr_rol, mod)
        if not mod:
            if self.acc!=acc_undef:
                new_flag_C = flag_set if (self.acc&0x80)!=0 else flag_clear
                if self.flag_is_set(flag_C):
                    self.acc = (self.acc << 1) + 1
                    self.set_flag_NZ(self.acc)
                if self.flag_is_clear(flag_C):
                    self.acc = (self.acc << 1)
                    self.set_flag_NZ(self.acc)
                else:
                    self.acc = acc_undef
                self.set_flag(flag_C, new_flag_C)
            else:
                if self.flag_is_set(flag_C):
                    self.set_flag(flag_Z, flag_clear)
                else:
                    self.set_flag(flag_Z, flag_undef)
                
                if self.flag_is_set(flag_N):
                    self.set_flag(flag_C, flag_set)
                elif self.flag_is_clear(flag_N):
                    self.set_flag(flag_C, flag_clear)
                else:
                    self.set_flag(flag_C, flag_undef)
                self.set_flag(flag_N, flag_undef)
        else:
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
            self.set_flag(flag_C, flag_undef)
    
    def ror(self, mod=False):
        self.byte(instr_ror, mod)
        
        if not mod:
            if self.acc!=acc_undef:
                new_flag_C = flag_set if (self.acc&0x1)!=0 else flag_clear
                if self.flag_is_set(flag_C):
                    self.acc = (self.acc >> 1) + 0x80
                    self.set_flag_NZ(self.acc)
                if self.flag_is_clear(flag_C):
                    self.acc = (self.acc >> 1)
                    self.set_flag_NZ(self.acc)
                else:
                    self.acc = acc_undef
                self.set_flag(flag_C, new_flag_C)
            else:
                new_flag_C = flag_undef
                if self.flag_is_set(flag_Z):
                    new_flag_C = flag_clear
                if self.flag_is_set(flag_C):
                    self.set_flag(flag_N, flag_set)
                    self.set_flag(flag_Z, flag_clear)
                elif self.flag_is_clear(flag_C):
                    self.set_flag(flag_N, flag_clear)
                    self.set_flag(flag_Z, flag_undef)
                else:
                    self.set_flag(flag_N, flag_undef)
                    self.set_flag(flag_Z, flag_undef)
                self.set_flag(flag_C, new_flag_C)
        else:
            self.set_flag(flag_N, flag_undef)
            self.set_flag(flag_Z, flag_undef)
            self.set_flag(flag_C, flag_undef)
    
    def bcc(self, addr, mod=[False,False]):
        if isinstance(addr,str):
            bflags = self.flags[:]
            bflags[flag_C] = flag_clear
            if addr in self.labels:
                self.labels[addr][1:2] = join_flags(self.labels[addr][1], bflags, \
                                    self.labels[addr][2], self.acc)
                self.bcc(self.labels[addr][0], mod)
            else:
                self.bcc(-100000, mod)
                self.labels[addr] = (-1000000, bflags, self.acc)
        elif isinstance(addr,int) and addr>=0:
            self.word16(instr_bcc | instr_addr(addr), mod)
        else:
            self.word16(instr_bcc | instr_addr(0), [True,True])
        # for next instruction
        self.set_flag(flag_C, flag_set)
    
    def cond_bcc(self, addr, mod=[False,False]):
        if mod[0] or mod[1] or self.flag_is_not_set(flag_C):
            self.bcc(addr, mod)
    
    def bne(self, addr, mod=[False,False]):
        if isinstance(addr,str):
            bflags = self.flags[:]
            bflags[flag_Z] = flag_clear
            if addr in self.labels:
                self.labels[addr][1:2] = join_flags(self.labels[addr][1], bflags, \
                                    self.labels[addr][2], self.acc)
                self.bne(self.labels[addr][0], mod)
            else:
                self.bne(-100000, mod)
                self.labels[addr] = (-1000000, bflags, self.acc)
        elif isinstance(addr,int) and addr>=0:
            self.word16(instr_bne | instr_addr(addr), mod)
        else:
            self.word16(instr_bne | instr_addr(0), [True,True])
        # for next instruction
        self.set_flag(flag_Z, flag_set)
    
    def cond_bne(self, addr, mod=[False,False]):
        if mod[0] or mod[1] or self.flag_is_not_set(flag_Z):
            self.bne(addr, mod)
    
    def bvc(self, addr, mod=[False,False]):
        if isinstance(addr,str):
            bflags = self.flags[:]
            bflags[flag_V] = flag_clear
            if addr in self.labels:
                self.labels[addr][1:2] = join_flags(self.labels[addr][1], bflags, \
                                    self.labels[addr][2], self.acc)
                self.bvc(self.labels[addr][0], mod)
            else:
                self.bvc(-100000, mod)
                self.labels[addr] = (-1000000, bflags, self.acc)
        elif isinstance(addr,int) and addr>=0:
            self.word16(instr_bvc | instr_addr(addr), mod)
        else:
            self.word16(instr_bvc | instr_addr(0), [True,True])
        # for next instruction
        self.set_flag(flag_V, flag_set)
    
    def cond_bvc(self, addr, mod=[False,False]):
        if mod[0] or mod[1] or self.flag_is_not_set(flag_V):
            self.bvc(addr, mod)
    
    def bpl(self, addr, mod=[False,False]):
        if isinstance(addr,str):
            bflags = self.flags[:]
            bflags[flag_N] = flag_clear
            if addr in self.labels:
                self.labels[addr][1:2] = join_flags(self.labels[addr][1], bflags, \
                                    self.labels[addr][2], self.acc)
                self.bpl(self.labels[addr][0], mod)
            else:
                self.bpl(-100000, mod)
                self.labels[addr] = (-1000000, bflags, self.acc)
        elif isinstance(addr,int) and addr>=0:
            self.word16(instr_bpl | instr_addr(addr), mod)
        else:
            self.word16(instr_bpl | instr_addr(0), [True,True])
        # for next instruction
        self.set_flag(flag_N, flag_set)
    
    def cond_bpl(self, addr, mod=[False,False]):
        if mod[0] or mod[1] or self.flag_is_not_set(flag_N):
            self.bpl(addr, mod)
    
    def spc(self, addr, mod=[False,False]):
        if isinstance(addr,int) and addr>=0:
            self.word16(instr_spc | instr_addr(addr), mod)
        else:
            self.word16(instr_spc | instr_addr(0), [True, True])
    
    def sec(self, mod=False):
        self.byte(instr_sec, mod)
        if not mod:
            self.set_flag(flag_C, flag_set)
        else:
            self.set_flag(flag_C, flag_undef)
    
    def cond_sec(self, mod=False):
        if mod or self.flag_is_not_set(flag_C):
            self.sec(mod)
    
    def lda_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.lda(imms[im], mod, im)
        else:
            self.lda(0, [True,True], im)
            imms[im] = -1
    
    def adc_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms:
            self.adc(imms[im], mod, im)
        else:
            self.adc(0, [True,True], im)
            imms[im] = -1
    
    def sbc_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.sbc(imms[im], mod, im)
        else:
            self.sbc(0, [True,True], im)
            imms[im] = -1
    
    def ana_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.ana(imms[im], mod, im)
        else:
            self.ana(0, [True,True], im)
            imms[im] = -1
    
    def ora_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.ora(imms[im], mod, im)
        else:
            self.ora(0, [True,True], im)
            imms[im] = -1
    
    def xor_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.xor(imms[im], mod, im)
        else:
            self.xor(0, [True,True], im)
            imms[im] = -1
    
    def spc_imm(self, im, mod=[False,False]):
        im=im&0xff
        global imms
        if im in imms and imms[im]>=0:
            self.spc(imms[im], mod)
        else:
            self.spc(0, [True,True])
            imms[im] = -1
    
    def jmp(self, addr, mod=[True,True,True,True]):
        if self.flag_is_clear(flagC):
            self.bcc(addr, mod[2:4])
        elif self.flag_is_clear(flagZ):
            self.bne(addr, mod[2:4])
        elif self.flag_is_clear(flagV):
            self.bvc(addr, mod[2:4])
        elif self.flag_is_clear(flagN):
            self.bpl(addr, mod[2:4])
        else:
            self.bne(addr, mod[0:2])
            self.bpl(addr, mod[2:4])
    
    def jmpc(self, addr, mod=[True,True,True]):
        if self.flag_is_clear(flagC):
            self.bcc(addr, mod[1:])
        elif self.flag_is_clear(flagZ):
            self.bne(addr, mod[1:])
        elif self.flag_is_clear(flagV):
            self.bvc(addr, mod[1:])
        elif self.flag_is_clear(flagN):
            self.bpl(addr, mod[1:])
        else:
            self.clc(mod[0])
            self.bcc(addr, mod[1:])

    def label(self, name):
        if name in self.labels:
            return self.labels[name][0]
        else:
            return -10000000000
    
    def def_label(self, name):
        if name in self.labels:
            old_flags = self.labels[name][1]
            old_acc =self.labels[name][2]
            new_flags = join_flags(old_flags, self.flags, old_acc, self.acc)
            self.labels[name] = (self.pc, *new_flags)
        else:
            self.labels[name] = (self.pc, self.flags, self.acc)

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
            self.clearflags()
            self.clearacc()
            start=codegen()
        imm_pc = self.pc
        start=codegen()
        join_imms(imms, self.imms(range(start,self.pc)))
        while self.rest_imms(imms):
            self.clearflags()
            self.clearacc()
            imm_pc = self.pc
            start=codegen()
            join_imms(imms, self.imms(range(start,self.pc)))
            self.pc = imm_pc
        self.clearflags()
        self.clearacc()
        imm_pc = self.pc
        codegen()
        
def join_imms(imms1, imms2):
    for (k,v) in imms2.items():
        if v>=0 and (k not in imms1 or imms1[k]<0):
            imms1[k] = v
