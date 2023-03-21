#######
# 6502 testsuite
#######

import os
import shutil
import subprocess

THEOREM_MODEL = './target/release/theorem-model-4'
CIRCUIT = 'circuits/simple2-cpu/simple2-cpu.circuit'
CG6502 = 'circuits/simple2-cpu/6502.py'
PYTHON = '/usr/bin/python'

pc_offset = 0xfe0
sr_offset = 0xfe2
sp_offset = 0xfe3
acc_offset = 0xfe4
xind_offset = 0xfe5
yind_offset = 0xfe6
instr_cycles_offset = 0xfe7

def cleanup():
    for r in ['6502mem.raw', '6502membase.raw', '6502progbase.raw',
                '6502prog.raw', '6502memdump.raw', '6502progdump.raw']:
        try:
            os.remove(r)
        except:
            pass
        finally:
            pass

cleanup()

def run_testcase(name, exp_list, mem_list, pc=0, acc=0, xind=0, yind=0, sp=0xff, sr=0):
    # prepare test
    shutil.copyfile('6502progbase.raw', '6502prog.raw')
    with open('6502prog.raw','rb+') as f:
        f.seek(pc_offset, 0)
        f.write(bytes([pc&0xff, (pc>>8)&0xff, sr&0xff, sp&0xff, acc&0xff, xind&0xff, yind&0xff]))
    shutil.copyfile('6502membase.raw', '6502mem.raw')
    with open('6502mem.raw','rb+') as f:
        for (offset, bts) in mem_list:
            f.seek(offset, 0)
            f.write(bytes([x&0xff for  x in bts]))
    # run command
    cp = subprocess.run([THEOREM_MODEL, 'run-machine', CIRCUIT, '3', '0', '6502mem.raw',
                '6502prog.raw', '-f', '6502memdump.raw,6502progdump.raw'], capture_output=True)
    if cp.returncode != 0:
        print("State:", cp)
        raise(RuntimeError('{}: Error while running testcase'.format(name)))
    # get outputs
    memdump=b''
    progdump=b''
    with open('6502memdump.raw','rb') as f:
        memdump = f.read()
    with open('6502progdump.raw','rb') as f:
        progdump = f.read()
    mems = [memdump,progdump]
    passed = True
    for (m,pos,exp) in exp_list:
        if mems[m][pos] != exp:
            posname = '{} {}'.format(m, pos)
            if m == 1:
                if pos==pc_offset:
                    posname = 'pclo'
                elif pos==pc_offset+1:
                    posname = 'pchi'
                elif pos==sr_offset:
                    posname='sr'
                elif pos==sp_offset:
                    posname='sp'
                elif pos==acc_offset:
                    posname='acc'
                elif pos==xind_offset:
                    posname='xind'
                elif pos==yind_offset:
                    posname='yind'
            print('TEST {}: FAILURE: {}: {}!={}'.format(name, posname, exp, mems[m][pos]))
            passed = False
    if passed:
        print("TEST", name, "PASSED")

try:
    ###################
    cp = subprocess.run([PYTHON, CG6502], capture_output=True)
    if cp.returncode != 0:
        raise(RuntimeError('Error while running code generation of 6502'))
    with open('6502progbase.raw','wb') as f:
        f.write(cp.stdout)

    with open('6502membase.raw','wb') as f:
        f.write(b'\x00'*(1<<16))
    
    ####################
    # main tests
    
    def test_chsr(name, opcode, bit, clr, sr):
        run_testcase('{} sr={}'.format(name, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, sr & (0xff ^ (1<<bit)) if clr else (sr | (1<<bit))),
                (1, acc_offset, 0),
                (1, xind_offset, 0),
                (1, yind_offset, 0),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [opcode&0xff, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr)
    
    def test_clc(sr): test_chsr('clc', 0x18, 0, True, sr)
    def test_cld(sr): test_chsr('cld', 0xd8, 3, True, sr)
    def test_cli(sr): test_chsr('cli', 0x58, 2, True, sr)
    def test_clv(sr): test_chsr('clv', 0xb8, 6, True, sr)
    def test_sec(sr): test_chsr('sec', 0x38, 0, False, sr)
    def test_sed(sr): test_chsr('sed', 0xf8, 3, False, sr)
    def test_sei(sr): test_chsr('sei', 0x78, 2, False, sr)
    
    for i in range(0,256):
        test_clc(i)
        test_cld(i)
        test_cli(i)
        test_clv(i)
        test_sec(i)
        test_sed(i)
        test_sei(i)
    
finally:
    cleanup()
