#######
# 6502 testsuite
#######

import os
import os.path
import shutil
import subprocess

PROJECT_PATH = os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0]

THEOREM_MODEL = os.path.join(PROJECT_PATH, 'target/release/theorem-model-4')
CIRCUIT =  os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/simple2-cpu.circuit')
CG6502 =  os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/6502.py')
PYTHON = '/usr/bin/python'

pc_offset = 0xfe0
sr_offset = 0xfe2
sp_offset = 0xfe3
acc_offset = 0xfe4
xind_offset = 0xfe5
yind_offset = 0xfe6
instr_cycles_offset = 0xff8

tests_passed = 0
tests_failed = 0

def cleanup():
    tests_passed = 0
    tests_failed = 0
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
    global tests_passed, tests_failed
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
            tests_failed += 1
            passed = False
    if passed:
        tests_passed += 1
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
    
    def test_tax(acc, sr):
        run_testcase('tax acc={} sr={}'.format(acc, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, (sr&(0xff^2^128)) | (0 if acc!=0 else 2) | (acc&0x80)),
                (1, acc_offset, acc),
                (1, xind_offset, acc),
                (1, yind_offset, 0),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xaa, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=acc, sr=sr, xind=1 if acc==0 else 0)
    
    def test_txa(xind, sr):
        run_testcase('txa xind={} sr={}'.format(xind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, (sr&(0xff^2^128)) | (0 if xind!=0 else 2) | (xind&0x80)),
                (1, acc_offset, xind),
                (1, xind_offset, xind),
                (1, yind_offset, 0),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0x8a, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=1 if xind==0 else 0, sr=sr, xind=xind)
    
    def test_tay(acc, sr):
        run_testcase('tay acc={} sr={}'.format(acc, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, (sr&(0xff^2^128)) | (0 if acc!=0 else 2) | (acc&0x80)),
                (1, acc_offset, acc),
                (1, xind_offset, 0),
                (1, yind_offset, acc),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xa8, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=acc, sr=sr, yind=1 if acc==0 else 0)
    
    def test_tya(yind, sr):
        run_testcase('tya yind={} sr={}'.format(yind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, (sr&(0xff^2^128)) | (0 if yind!=0 else 2) | (yind&0x80)),
                (1, acc_offset, yind),
                (1, xind_offset, 0),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0x98, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=1 if yind==0 else 0, sr=sr, yind=yind)
    
    def test_tsx(sp, sr):
        run_testcase('tsx sp={} sr={}'.format(sp, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, (sr&(0xff^2^128)) | (0 if sp!=0 else 2) | (sp&0x80)),
                (1, acc_offset, 0),
                (1, xind_offset, sp),
                (1, yind_offset, 0),
                (1, sp_offset, sp),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xba, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, sp=sp, sr=sr, xind=1 if sp==0 else 0)
    
    def test_txs(xind, sr):
        run_testcase('txs xind={} sr={}'.format(xind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 0),
                (1, xind_offset, xind),
                (1, yind_offset, 0),
                (1, sp_offset, xind),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0x9a, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, sp=1 if xind==0 else 0, sr=sr, xind=xind)
    
    # test addressing modes (reads)
    def test_read_op_imm(name, acc_op, opcode, acc, imm, sr):
        new_acc, new_sr = acc_op(acc, imm, sr)
        run_testcase('{} imm acc={} imm={} sr={}'.format(name, acc, imm, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, 0),
                (1, yind_offset, 0),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
                (0, imm&0xff, 0),
            ],
            # instructions. last is undefined (stop)
            [ (0x200, [opcode&0xff, imm&0xff, 0x04]) ],
            pc=0x200, acc=acc, sr=sr)
    
    def test_read_op_xind_imm(name, xind_op, opcode, xind, imm, sr):
        new_xind, new_sr = xind_op(xind, imm, sr)
        run_testcase('{} imm xind={} imm={} sr={}'.format(name, xind, imm, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 0),
                (1, xind_offset, new_xind),
                (1, yind_offset, 0),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
                (0, imm&0xff, 0),
            ],
            # instructions. last is undefined (stop)
            [ (0x200, [opcode&0xff, imm&0xff, 0x04]) ],
            pc=0x200, xind=xind, sr=sr)
    
    def test_read_op_yind_imm(name, yind_op, opcode, yind, imm, sr):
        new_yind, new_sr = yind_op(yind, imm, sr)
        run_testcase('{} imm yind={} imm={} sr={}'.format(name, yind, imm, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 0),
                (1, xind_offset, 0),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
                (0, imm&0xff, 0),
            ],
            # instructions. last is undefined (stop)
            [ (0x200, [opcode&0xff, imm&0xff, 0x04]) ],
            pc=0x200, yind=yind, sr=sr)
    
    def test_read_op_zpg(name, acc_op, opcode, acc, addr, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} zpg acc={} addr={} val={} sr={}'.format(name, acc, addr, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, val),
            ],
            [
                (addr&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=1)
    
    def test_read_op_xind_zpg(name, xind_op, opcode, xind, addr, val, sr):
        new_xind, new_sr = xind_op(xind, val, sr)
        run_testcase('{} zpg xind={} addr={} val={} sr={}'.format(name, xind, addr, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, new_xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, val),
            ],
            [
                (addr&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, acc=2, yind=1)
    
    def test_read_op_yind_zpg(name, yind_op, opcode, yind, addr, val, sr):
        new_yind, new_sr = yind_op(yind, val, sr)
        run_testcase('{} zpg yind={} addr={} val={} sr={}'.format(name, yind, addr, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, val),
            ],
            [
                (addr&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, acc=2, xind=1)
    
    def test_read_op_zpgx(name, acc_op, opcode, acc, addr, xind, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} zpgx acc={} addr={} xind={} val={} sr={}' \
                     .format(name, acc, addr, xind, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+xind)&0xff, val),
            ],
            [
                ((addr+xind)&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_read_op_yind_zpgx(name, yind_op, opcode, yind, addr, xind, val, sr):
        new_yind, new_sr = yind_op(yind, val, sr)
        run_testcase('{} zpgx yind={} addr={} xind={} val={} sr={}' \
                     .format(name, yind, addr, xind, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 1),
                (1, xind_offset, xind),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+xind)&0xff, val),
            ],
            [
                ((addr+xind)&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, xind=xind, acc=1)
    
    def test_read_op_xind_zpgy(name, xind_op, opcode, xind, addr, yind, val, sr):
        new_xind, new_sr = xind_op(xind, val, sr)
        run_testcase('{} zpgy xind={} addr={} yind={} val={} sr={}' \
                     .format(name, xind, addr, yind, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 1),
                (1, xind_offset, new_xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+yind)&0xff, val),
            ],
            [
                ((addr+yind)&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, yind=yind, acc=1)
    
    def test_read_op_abs(name, acc_op, opcode, acc, addr, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} abs acc={} addr={} val={} sr={}'.format(name, acc, addr, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, val),
            ],
            [
                (addr&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=1)
    
    def test_read_op_xind_abs(name, xind_op, opcode, xind, addr, val, sr):
        new_xind, new_sr = xind_op(xind, val, sr)
        run_testcase('{} abs xind={} addr={} val={} sr={}'.format(name, xind, addr, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, new_xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, val),
            ],
            [
                (addr&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, acc=2, yind=1)
    
    def test_read_op_yind_abs(name, yind_op, opcode, yind, addr, val, sr):
        new_yind, new_sr = yind_op(yind, val, sr)
        run_testcase('{} abs yind={} addr={} val={} sr={}'.format(name, yind, addr, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, val),
            ],
            [
                (addr&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, acc=2, xind=1)
    
    def test_read_op_absx(name, acc_op, opcode, acc, addr, xind, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} absx acc={} addr={} xind={} val={} sr={}' \
                     .format(name, acc, addr, xind, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4 + int((addr&0xff)+xind >= 256)),
                (0, (addr+xind)&0xffff, val),
            ],
            [
                ((addr+xind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_read_op_yind_absx(name, yind_op, opcode, yind, addr, xind, val, sr):
        new_yind, new_sr = yind_op(yind, val, sr)
        run_testcase('{} absx yind={} addr={} xind={} val={} sr={}' \
                     .format(name, yind, addr, xind, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 1),
                (1, xind_offset, xind),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4 + int((addr&0xff)+xind >= 256)),
                (0, (addr+xind)&0xffff, val),
            ],
            [
                ((addr+xind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, xind=xind, acc=1)
    
    def test_read_op_absy(name, acc_op, opcode, acc, addr, yind, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} absy acc={} addr={} yind={} val={} sr={}' \
                     .format(name, acc, addr, yind, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, 2),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4 + int((addr&0xff)+yind >= 256)),
                (0, (addr+yind)&0xffff, val),
            ],
            [
                ((addr+yind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=yind)
    
    def test_read_op_xind_absy(name, xind_op, opcode, xind, addr, yind, val, sr):
        new_xind, new_sr = xind_op(xind, val, sr)
        run_testcase('{} absy xind={} addr={} yind={} val={} sr={}' \
                     .format(name, xind, addr, yind, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, new_xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4 + int((addr&0xff)+yind >= 256)),
                (0, (addr+yind)&0xffff, val),
            ],
            [
                ((addr+yind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, acc=2, yind=yind)
    
    def test_read_op_pindx(name, acc_op, opcode, acc, addr, xind, addr2, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} pindx acc={} addr={} xind={} addr2={} val={} sr={}' \
                     .format(name, acc, addr, xind, addr2, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, addr2&0xffff, val),
            ],
            [
                ((addr+xind)&0xff, [addr2&0xff]),
                ((addr+xind+1)&0xff, [(addr2>>8)&0xff]),
                (addr2&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_read_op_pindy(name, acc_op, opcode, acc, addr, addr2, yind, val, sr):
        new_acc, new_sr = acc_op(acc, val, sr)
        run_testcase('{} pindy acc={} addr={} addr2={} yind={} val={} sr={}' \
                     .format(name, acc, addr, addr2, yind, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_acc),
                (1, xind_offset, 2),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 5 + int((addr2&0xff)+yind >= 256)),
                (0, (addr2+yind)&0xffff, val),
            ],
            [
                ((addr)&0xff, [addr2&0xff]),
                ((addr+1)&0xff, [(addr2>>8)&0xff]),
                ((addr2+yind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=yind)
    
    ################
    
    def test_sta_zpg(acc, addr, sr):
        opcode = 0x85
        run_testcase('sta zpg acc={} addr={} sr={}'.format(acc, addr, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, acc),
            ],
            [
                (addr&0xff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=1)
    
    def test_sta_zpgx(acc, addr, xind, sr):
        opcode = 0x95
        run_testcase('sta zpgx acc={} addr={} xind={} sr={}'.format(acc, addr, xind, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+xind)&0xff, acc),
            ],
            [
                ((addr+xind)&0xff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_sta_abs(acc, addr, sr):
        opcode = 0x8d
        run_testcase('sta abs acc={} addr={} sr={}'.format(acc, addr, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, acc),
            ],
            [
                (addr&0xffff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=2, yind=1)
    
    def test_sta_absx(acc, addr, xind, sr):
        opcode = 0x9d
        run_testcase('sta absx acc={} addr={} xind={} sr={}'.format(acc, addr, xind, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 5),
                (0, (addr+xind)&0xffff, acc),
            ],
            [
                ((addr+xind)&0xffff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_sta_absy(acc, addr, yind, sr):
        opcode = 0x99
        run_testcase('sta absy acc={} addr={} yind={} sr={}'.format(acc, addr, yind, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 5),
                (0, (addr+yind)&0xffff, acc),
            ],
            [
                ((addr+yind)&0xffff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, yind=yind, xind=2)
    
    def test_sta_pindx(acc, addr, xind, addr2, sr):
        opcode = 0x81
        run_testcase('sta pindx acc={} addr={} xind={} addr2={} sr={}' \
                .format(acc, addr, xind, addr2, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, addr2&0xffff, acc),
            ],
            [
                ((addr+xind)&0xff, [addr2&0xff]),
                ((addr+xind+1)&0xff, [(addr2>>8)&0xff]),
                (addr2&0xffff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=1)
    
    def test_sta_pindy(acc, addr, addr2, yind, sr):
        opcode = 0x91
        run_testcase('sta pindy acc={} addr={} addr2={} yind={} sr={}' \
                     .format(acc, addr, addr2, yind, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, (addr2+yind)&0xffff, acc),
            ],
            [
                ((addr)&0xff, [addr2&0xff]),
                ((addr+1)&0xff, [(addr2>>8)&0xff]),
                ((addr2+yind)&0xffff, [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, yind=yind, xind=2)
    
    def test_stx_zpg(xind, addr, sr):
        opcode = 0x86
        run_testcase('stx zpg xind={} addr={} sr={}'.format(xind, addr, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, xind),
            ],
            [
                (addr&0xff, [0 if xind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, acc=2, yind=1)
    
    def test_stx_zpgy(xind, addr, yind, sr):
        opcode = 0x96
        run_testcase('stx zpgy xind={} addr={} yind={} sr={}'.format(xind, addr, yind, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+yind)&0xff, xind),
            ],
            [
                ((addr+yind)&0xff, [0 if xind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=2, sr=sr, xind=xind, yind=yind)
    
    def test_stx_abs(xind, addr, sr):
        opcode = 0x8e
        run_testcase('stx abs xind={} addr={} sr={}'.format(xind, addr, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, xind),
            ],
            [
                (addr&0xffff, [0 if xind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, xind=xind, sr=sr, acc=2, yind=1)
    
    def test_sty_zpg(yind, addr, sr):
        opcode = 0x84
        run_testcase('sty zpg yind={} addr={} sr={}'.format(yind, addr, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xff, yind),
            ],
            [
                (addr&0xff, [0 if yind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, acc=2, xind=1)
    
    def test_sty_zpgx(yind, addr, xind, sr):
        opcode = 0x94
        run_testcase('sty zpgx yind={} addr={} xind={} sr={}'.format(yind, addr, xind, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, (addr+xind)&0xff, yind),
            ],
            [
                ((addr+xind)&0xff, [0 if yind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=2, sr=sr, xind=xind, yind=yind)
    
    def test_sty_abs(yind, addr, sr):
        opcode = 0x8c
        run_testcase('sty abs yind={} addr={} sr={}'.format(yind, addr, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, yind),
            ],
            [
                (addr&0xffff, [0 if yind!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, yind=yind, sr=sr, acc=2, xind=1)
    
    ################
    
    def test_clc(sr): test_chsr('clc', 0x18, 0, True, sr)
    def test_cld(sr): test_chsr('cld', 0xd8, 3, True, sr)
    def test_cli(sr): test_chsr('cli', 0x58, 2, True, sr)
    def test_clv(sr): test_chsr('clv', 0xb8, 6, True, sr)
    def test_sec(sr): test_chsr('sec', 0x38, 0, False, sr)
    def test_sed(sr): test_chsr('sed', 0xf8, 3, False, sr)
    def test_sei(sr): test_chsr('sei', 0x78, 2, False, sr)
    
    def lda_op(acc, val, sr):
        return val, (sr&(0xff^2^128)) | (0 if val!=0 else 2) | (val&0x80)
    def and_op(acc, val, sr):
        res = (acc & val) & 0xff
        return res, (sr&(0xff^2^128)) | (0 if res!=0 else 2) | (res&0x80)
    
    def test_lda_imm(acc, imm, sr):
        test_read_op_imm('lda', lda_op, 0xa9, acc, imm, sr)
    def test_lda_zpg(acc, addr, val, sr):
        test_read_op_zpg('lda', lda_op, 0xa5, acc, addr, val, sr)
    def test_lda_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('lda', lda_op, 0xb5, acc, addr, xind, val, sr)
    def test_lda_abs(acc, addr, val, sr):
        test_read_op_abs('lda', lda_op, 0xad, acc, addr, val, sr)
    def test_lda_absx(acc, addr, xind, val, sr):
        test_read_op_absx('lda', lda_op, 0xbd, acc, addr, xind, val, sr)
    def test_lda_absy(acc, addr, xind, val, sr):
        test_read_op_absy('lda', lda_op, 0xb9, acc, addr, yind, val, sr)
    def test_lda_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('lda', lda_op, 0xa1, acc, addr, xind, addr2, val, sr)
    def test_lda_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('lda', lda_op, 0xb1, acc, addr, addr2, yind, val, sr)
    
    def test_ldx_imm(xind, imm, sr):
        test_read_op_xind_imm('ldx', lda_op, 0xa2, xind, imm, sr)
    def test_ldx_zpg(xind, addr, val, sr):
        test_read_op_xind_zpg('ldx', lda_op, 0xa6, xind, addr, val, sr)
    def test_ldx_zpgy(xind, addr, yind, val, sr):
        test_read_op_xind_zpgy('ldx', lda_op, 0xb6, xind, addr, yind, val, sr)
    def test_ldx_abs(xind, addr, val, sr):
        test_read_op_xind_abs('ldx', lda_op, 0xae, xind, addr, val, sr)
    def test_ldx_absy(xind, addr, yind, val, sr):
        test_read_op_xind_absy('ldx', lda_op, 0xbe, xind, addr, yind, val, sr)
    
    def test_ldy_imm(yind, imm, sr):
        test_read_op_yind_imm('ldy', lda_op, 0xa0, yind, imm, sr)
    def test_ldy_zpg(yind, addr, val, sr):
        test_read_op_yind_zpg('ldy', lda_op, 0xa4, yind, addr, val, sr)
    def test_ldy_zpgx(yind, addr, xind, val, sr):
        test_read_op_yind_zpgx('ldy', lda_op, 0xb4, yind, addr, xind, val, sr)
    def test_ldy_abs(yind, addr, val, sr):
        test_read_op_yind_abs('ldy', lda_op, 0xac, yind, addr, val, sr)
    def test_ldy_absx(yind, addr, xind, val, sr):
        test_read_op_yind_absx('ldy', lda_op, 0xbc, yind, addr, xind, val, sr)
    
    def test_and_imm(acc, imm, sr):
        test_read_op_imm('and', and_op, 0x29, acc, imm, sr)
    
    ###############################
    # testsuite
    
    sr_flags_values = [0, 1, 2, 3, 4, 6, 8, 16, 24, 32, 49, 64, 128, 129, 136, 192, 255]
    transfer_values = [0, 3, 5, 35, 128, 44, 196, 255, 251, 136, 138, 139, 160, 161, 162, 163]
    zpg_addr_values = [0, 12, 1, 55, 128, 64, 195, 231, 255]
    zpgx_xind_values = [0, 3, 66, 12, 145, 255, 197, 217, 191]
    abs_addr_values = [0x1316, 0xffff, 0xfe11, 0xffe, 0x0451, 0xb5a1, 0x2988]
    pindx_addr_values = [(0, 42), (54, 76), (187, 68), (200, 55), (178, 121)]
    pindy_addr2_values = [(0x34dd, 11), (0x828b, 141), (0xbd20, 55), (0x6b92, 0x6e)]
    small_nz_values = [0, 31, 128, 55]
    small_sr_nz_values = [ 0x11, 0x13, 0x91, 0x93 ]
    
    """
    for i in sr_flags_values:
        test_clc(i)
        test_cld(i)
        test_cli(i)
        test_clv(i)
        test_sec(i)
        test_sed(i)
        test_sei(i)
    
    for i in transfer_values:
        for sr in small_sr_nz_values:
            test_tax(i, sr)
            test_txa(i, sr)
            test_tay(i, sr)
            test_tya(i, sr)
            test_tsx(i, sr)
            test_txs(i, sr)
    
    for i in transfer_values:
        for v in small_nz_values:
            for sr in small_sr_nz_values:
                test_lda_imm(i, v, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_zpgx(11, addr, xind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_absx(11, addr, xind, v, sr)
    
    for addr in abs_addr_values:
        for yind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_absy(11, addr, yind, v, sr)
    
    for (addr, xind) in pindx_addr_values:
        for addr2 in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_pindx(11, addr, xind, addr2, v, sr)
    
    for addr in zpg_addr_values:
        for (addr2, yind) in pindy_addr2_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_lda_pindy(11, addr, addr2, yind, v, sr)
    
    for i in transfer_values:
        for v in small_nz_values:
            for sr in small_sr_nz_values:
                test_ldx_imm(i, v, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldx_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for yind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldx_zpgy(11, addr, yind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldx_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for yind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldx_absy(11, addr, yind, v, sr)
    
    for i in transfer_values:
        for v in small_nz_values:
            for sr in small_sr_nz_values:
                test_ldy_imm(i, v, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldy_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldy_zpgx(11, addr, xind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldy_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_ldy_absx(11, addr, xind, v, sr)
    
    for acc in transfer_values:
        for addr in zpg_addr_values:
            for sr in small_sr_nz_values:
                test_sta_zpg(acc, addr, sr)
    
    for acc in small_nz_values:
        for addr in zpg_addr_values:
            for xind in zpgx_xind_values:
                for sr in small_sr_nz_values:
                    test_sta_zpgx(acc, addr, xind, sr)
    
    for acc in transfer_values:
        for addr in abs_addr_values:
            for sr in small_sr_nz_values:
                test_sta_abs(acc, addr, sr)
    
    for acc in small_nz_values:
        for addr in abs_addr_values:
            for xind in zpgx_xind_values:
                for sr in small_sr_nz_values:
                    test_sta_absx(acc, addr, xind, sr)
    
    for acc in small_nz_values:
        for addr in abs_addr_values:
            for yind in zpgx_xind_values:
                for sr in small_sr_nz_values:
                    test_sta_absy(acc, addr, yind, sr)
    
    for acc in small_nz_values:
        for (addr, xind) in pindx_addr_values:
            for addr2 in abs_addr_values:
                for sr in small_sr_nz_values:
                    test_sta_pindx(acc, addr, xind, addr2, sr)
    
    for acc in small_nz_values:
        for addr in zpg_addr_values:
            for (addr2, yind) in pindy_addr2_values:
                for sr in small_sr_nz_values:
                    test_sta_pindy(acc, addr, addr2, yind, sr)
    
    for xind in transfer_values:
        for addr in zpg_addr_values:
            for sr in small_sr_nz_values:
                test_stx_zpg(xind, addr, sr)
    
    for xind in small_nz_values:
        for addr in zpg_addr_values:
            for yind in zpgx_xind_values:
                for sr in small_sr_nz_values:
                    test_stx_zpgy(xind, addr, yind, sr)
    
    for xind in transfer_values:
        for addr in abs_addr_values:
            for sr in small_sr_nz_values:
                test_stx_abs(xind, addr, sr)
    """
    
    for yind in transfer_values:
        for addr in zpg_addr_values:
            for sr in small_sr_nz_values:
                test_sty_zpg(yind, addr, sr)
    
    for yind in small_nz_values:
        for addr in zpg_addr_values:
            for xind in zpgx_xind_values:
                for sr in small_sr_nz_values:
                    test_sty_zpgx(yind, addr, xind, sr)
    
    for yind in transfer_values:
        for addr in abs_addr_values:
            for sr in small_sr_nz_values:
                test_sty_abs(yind, addr, sr)
    
    """
    for i in transfer_values:
        for j in transfer_values:
            for sr in small_sr_nz_values:
                test_and_imm(i, j, sr)
    """
    
    #########################
    # Summary
    print("Tests passed: {}, Tests failed: {}, Total: {}" \
            .format(tests_passed, tests_failed, tests_passed+tests_failed))
finally:
    cleanup()
