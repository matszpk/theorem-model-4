#######
# 6502 testsuite
#######

import os
import os.path
import shutil
import subprocess

PROJECT_PATH = os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0]

THEOREM_MODEL = os.path.join(PROJECT_PATH, 'target/release/theorem-model-4')
CIRCUIT = os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/simple2-cpu.circuit')
CG6502 = os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/6502.py')
C64BASIC = os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/basic')
C64KERNAL = os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/kernal')
C64CHARGEN = os.path.join(PROJECT_PATH, 'circuits/simple2-cpu/chargen')
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

def run_testcase(name, exp_list, mem_list, pc=0, acc=0, xind=0, yind=0, sp=0xff, sr=0, \
                 unsat=False):
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
        if b'Unsatisfied execution' in cp.stderr and unsat:
            tests_passed += 1
            print("TEST", name, "PASSED")
            return
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
    def set_sr_nz(val, sr):
        return (sr&(0xff^2^128)) | (0 if val!=0 else 2) | (val&0x80)
    def set_sr_nzc(val, c, sr):
        return (sr&(0xff^2^128^1)) | (0 if val!=0 else 2) | (val&0x80) | int(c)
    def set_sr_v(v, sr):
        return (sr&(0xff^0x40)) | (int(v)<<6)
    
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
                (1, sr_offset, set_sr_nz(acc, sr)),
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
                (1, sr_offset, set_sr_nz(xind, sr)),
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
                (1, sr_offset, set_sr_nz(acc, sr)),
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
                (1, sr_offset, set_sr_nz(yind, sr)),
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
                (1, sr_offset, set_sr_nz(sp, sr)),
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
    
    # increment/decrement
    def test_dex(xind, sr):
        new_xind = (256+xind-1)&0xff
        new_sr = set_sr_nz(new_xind, sr)
        run_testcase('dex xind={} sr={}'.format(xind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, new_xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xca, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=2, sr=sr, xind=xind, yind=1)
    
    def test_dey(yind, sr):
        new_yind = (256+yind-1)&0xff
        new_sr = set_sr_nz(new_yind, sr)
        run_testcase('dey yind={} sr={}'.format(yind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0x88, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=2, sr=sr, xind=1, yind=yind)
    
    def test_inx(xind, sr):
        new_xind = (256+xind+1)&0xff
        new_sr = set_sr_nz(new_xind, sr)
        run_testcase('inx xind={} sr={}'.format(xind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, new_xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xe8, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=2, sr=sr, xind=xind, yind=1)
    
    def test_iny(yind, sr):
        new_yind = (256+yind+1)&0xff
        new_sr = set_sr_nz(new_yind, sr)
        run_testcase('iny yind={} sr={}'.format(yind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 2),
                (1, xind_offset, 1),
                (1, yind_offset, new_yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xc8, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=2, sr=sr, xind=1, yind=yind)
    
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
    
    def test_read_write_op_zpg(name, mem_op, opcode, addr, val, sr):
        new_val, new_sr = mem_op(val, sr)
        run_testcase('{} zpg addr={} val={} sr={}'.format(name, addr, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 3),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 5),
                (0, addr&0xff, new_val),
            ],
            [
                (addr&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=2, yind=1)
    
    def test_read_write_op_zpgx(name, mem_op, opcode, addr, xind, val, sr):
        new_val, new_sr = mem_op(val, sr)
        run_testcase('{} zpgx addr={} xind={} val={} sr={}' \
                    .format(name, addr, xind, val, sr),
            [
                (1, pc_offset, (0x203)&0xff),
                (1, pc_offset+1, ((0x203)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 3),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, (addr+xind)&0xff, new_val),
            ],
            [
                ((addr+xind)&0xff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=xind, yind=1)
    
    def test_read_write_op_abs(name, mem_op, opcode, addr, val, sr):
        new_val, new_sr = mem_op(val, sr)
        run_testcase('{} abs addr={} val={} sr={}'.format(name, addr, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 3),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, addr&0xffff, new_val),
            ],
            [
                (addr&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=2, yind=1)
    
    def test_read_write_op_absx(name, mem_op, opcode, addr, xind, val, sr):
        new_val, new_sr = mem_op(val, sr)
        run_testcase('{} absx addr={} xind={} val={} sr={}' \
                    .format(name, addr, xind, val, sr),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, 3),
                (1, xind_offset, xind),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 7),
                (0, (addr+xind)&0xffff, new_val),
            ],
            [
                ((addr+xind)&0xffff, [val]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=xind, yind=1)
    
    def test_acc_op_imp(name, mem_op, opcode, val, sr):
        new_val, new_sr = mem_op(val, sr)
        run_testcase('{} imp val={} sr={}'.format(name, val, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, new_val),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, 0x04])
            ],
            pc=0x200, acc=val, sr=sr, xind=2, yind=1)
    
    def test_op_branch(name, set_sr, sr_flag, opcode, start, rel, sr):
        do_jump = set_sr if (sr&sr_flag)!=0 else not set_sr
        rel_addr = start+2+(rel&0x7f) if rel<0x80 else start+2+(rel-0x100)
        final_pc = (rel_addr if do_jump else start+2) + 1
        run_testcase('{} rel sr_flag={} start={} rel={} sr={}' \
                .format(name, sr_flag, start, rel, sr),
            [
                (1, pc_offset, (final_pc)&0xff),
                (1, pc_offset+1, ((final_pc)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 3),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2 + int(do_jump) +
                        int(do_jump and ((start+2)&0xff00)!=(rel_addr&0xff00))),
            ],
            [
                # instructions. last is undefined (stop)
                (start, [opcode&0xff, rel&0xff, 0x04]),
                 # if jump done
                (rel_addr, [0x04]),
            ],
            pc=start, acc=3, sr=sr, xind=2, yind=1)
    
    def test_nop(acc, xind, yind, sr):
        run_testcase('nop acc={} xind={} yind={} sr={}'.format(acc, xind, yind, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 2),
            ],
            [ (0x200, [0xea, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=yind)
    
    def test_pha(acc, sp, sr):
        run_testcase('pha acc={} sp={} sr={}'.format(acc, sp, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp-1)&0xff),
                (1, instr_cycles_offset, 3),
                (0, 0x100 + ((0x100+sp-1)&0xff), 0),
                (0, 0x100 + (sp&0xff), acc),
            ],
            [
                # stack
                (0x100 + (sp&0xff), [0 if acc!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [0x48, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=1, yind=2, sp=sp)
    
    def test_pla(val, sp, sr):
        run_testcase('pla val={} sp={} sr={}'.format(val, sp, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, set_sr_nz(val, sr)),
                (1, acc_offset, val),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp+1)&0xff),
                (1, instr_cycles_offset, 4),
                (0, 0x100 + (sp&0xff), 0),
                (0, 0x100 + ((sp+1)&0xff), val),
            ],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [val]),
                # instructions. last is undefined (stop)
                (0x200, [0x68, 0x04])
            ],
            pc=0x200, acc=0 if val!=0 else 1, sr=sr, xind=1, yind=2, sp=sp)
    
    def test_php(sp, sr):
        run_testcase('php sp={} sr={}'.format(sp, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 3),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp-1)&0xff),
                (1, instr_cycles_offset, 3),
                (0, 0x100 + ((0x100+sp-1)&0xff), 0),
                (0, 0x100 + (sp&0xff), sr|0x10),
            ],
            [
                # stack
                (0x100 + (sp&0xff), [0 if sr!=0 else 1]),
                # instructions. last is undefined (stop)
                (0x200, [0x08, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp)
    
    def test_plp(val, sp, sr):
        run_testcase('plp val={} sp={} sr={}'.format(val, sp, sr),
            [
                (1, pc_offset, (0x202)&0xff),
                (1, pc_offset+1, ((0x202)>>8)&0xff),
                (1, sr_offset, val),
                (1, acc_offset, 3),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp+1)&0xff),
                (1, instr_cycles_offset, 4),
                (0, 0x100 + (sp&0xff), 0),
                (0, 0x100 + ((sp+1)&0xff), val),
            ],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [val]),
                # instructions. last is undefined (stop)
                (0x200, [0x28, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp)
    
    def test_jmp(addr, acc, xind, yind, sr):
        run_testcase('jmp abs addr={} acc={} xind={} yind={} sr={}' \
                     .format(addr, acc, xind, yind, sr),
            [
                (1, pc_offset, (addr+1)&0xff),
                (1, pc_offset+1, ((addr+1)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 3),
                (0, addr&0xffff, 0x04),
            ],
            [
                (addr&0xffff, [0x04]),
                # instructions. last is undefined (stop)
                (0x200, [0x4c, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=yind)
    
    def test_jmp_ind(addr, addr2, acc, xind, yind, sr):
        run_testcase('jmp ind addr={} addr2={} acc={} xind={} yind={} sr={}' \
                     .format(addr, addr2, acc, xind, yind, sr),
            [
                (1, pc_offset, (addr2+1)&0xff),
                (1, pc_offset+1, ((addr2+1)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, acc),
                (1, xind_offset, xind),
                (1, yind_offset, yind),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 5),
                (0, addr2&0xffff, 0x04),
            ],
            [
                (addr&0xffff, [addr2&0xff]),
                (((addr)&0xff00)+((addr+1)&0xff), [(addr2>>8)&0xff]),
                (addr2&0xffff, [0x04]),
                # instructions. last is undefined (stop)
                (0x200, [0x6c, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=sr, xind=xind, yind=yind)
    
    def test_jsr(start, addr, sp, sr):
        ret_addr = start+2
        run_testcase('jsr abs start={} addr={} sp={} sr={}'.format(start, addr, sp, sr),
            [
                (1, pc_offset, (addr+1)&0xff),
                (1, pc_offset+1, ((addr+1)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 1),
                (1, xind_offset, 2),
                (1, yind_offset, 3),
                (1, sp_offset, (0x100+sp-2)&0xff),
                (1, instr_cycles_offset, 6),
                (0, addr&0xffff, 0x04),
                (0, 0x100 + ((0x100+sp-2)&0xff), 0),
                (0, 0x100 + ((0x100+sp-1)&0xff), ret_addr&0xff),
                (0, 0x100 + (sp&0xff), (ret_addr>>8)&0xff),
            ],
            [
                (addr&0xffff, [0x04]),
                # instructions. last is undefined (stop)
                (start, [0x20, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=start, acc=1, sr=sr, xind=2, yind=3, sp=sp)
    
    def test_rts(ret, sp, sr):
        run_testcase('rts ret={} sp={} sr={}'.format(ret, sp, sr),
            [
                (1, pc_offset, (ret+2)&0xff),
                (1, pc_offset+1, ((ret+2)>>8)&0xff),
                (1, sr_offset, sr),
                (1, acc_offset, 3),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp+2)&0xff),
                (1, instr_cycles_offset, 6),
                (0, 0x100 + (sp&0xff), 0),
                (0, 0x100 + ((sp+1)&0xff), ret&0xff),
                (0, 0x100 + ((sp+2)&0xff), (ret>>8)&0xff),
            ],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [ret&0xff]),
                (0x100 + ((sp+2)&0xff), [(ret>>8)&0xff]),
                ((ret+1)&0xffff, [0x4]),
                # instructions. last is undefined (stop)
                (0x200, [0x60, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp)
    
    def test_brk(start, vecfffe, sp, sr):
        ret_addr = start+2
        run_testcase('brk start={} fffe={} sp={} sr={}'.format(start, vecfffe, sp, sr),
            [
                (1, pc_offset, (vecfffe+1)&0xff),
                (1, pc_offset+1, ((vecfffe+1)>>8)&0xff),
                (1, sr_offset, sr|0x14),
                (1, acc_offset, 1),
                (1, xind_offset, 2),
                (1, yind_offset, 3),
                (1, sp_offset, (0x100+sp-3)&0xff),
                (1, instr_cycles_offset, 7),
                (0, vecfffe&0xffff, 0x04),
                (0, 0x100 + ((0x100+sp-3)&0xff), 0),
                (0, 0x100 + ((0x100+sp-2)&0xff), sr|0x10),
                (0, 0x100 + ((0x100+sp-1)&0xff), ret_addr&0xff),
                (0, 0x100 + (sp&0xff), (ret_addr>>8)&0xff),
            ],
            [
                (0xfffe, [vecfffe&0xff, (vecfffe>>8)&0xff]),
                (vecfffe&0xffff, [0x04]),
                # instructions. last is undefined (stop)
                (start, [0x00, 0x04])
            ],
            pc=start, acc=1, sr=sr, xind=2, yind=3, sp=sp)
    
    def test_rti(ret, ret_sr, sp, sr):
        run_testcase('rti ret={} ret_sr={} sp={} sr={}'.format(ret, ret_sr, sp, sr),
            [
                (1, pc_offset, (ret+1)&0xff),
                (1, pc_offset+1, ((ret+1)>>8)&0xff),
                (1, sr_offset, ret_sr),
                (1, acc_offset, 3),
                (1, xind_offset, 1),
                (1, yind_offset, 2),
                (1, sp_offset, (0x100+sp+3)&0xff),
                (1, instr_cycles_offset, 6),
                (0, 0x100 + (sp&0xff), 0),
                (0, 0x100 + ((sp+1)&0xff), ret_sr&0xff),
                (0, 0x100 + ((sp+2)&0xff), ret&0xff),
                (0, 0x100 + ((sp+3)&0xff), (ret>>8)&0xff),
            ],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [ret_sr&0xff]),
                (0x100 + ((sp+2)&0xff), [ret&0xff]),
                (0x100 + ((sp+3)&0xff), [(ret>>8)&0xff]),
                (ret&0xffff, [0x4]),
                # instructions. last is undefined (stop)
                (0x200, [0x40, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp)
    
    ################
    
    def test_clc(sr): test_chsr('clc', 0x18, 0, True, sr)
    def test_cld(sr): test_chsr('cld', 0xd8, 3, True, sr)
    def test_cli(sr): test_chsr('cli', 0x58, 2, True, sr)
    def test_clv(sr): test_chsr('clv', 0xb8, 6, True, sr)
    def test_sec(sr): test_chsr('sec', 0x38, 0, False, sr)
    def test_sed(sr): test_chsr('sed', 0xf8, 3, False, sr)
    def test_sei(sr): test_chsr('sei', 0x78, 2, False, sr)
    
    def lda_op(acc, val, sr):
        return val, set_sr_nz(val, sr)
    def and_op(acc, val, sr):
        res = (acc & val) & 0xff
        return res, set_sr_nz(res, sr)
    def ora_op(acc, val, sr):
        res = (acc | val) & 0xff
        return res, set_sr_nz(res, sr)
    def eor_op(acc, val, sr):
        res = (acc ^ val) & 0xff
        return res, set_sr_nz(res, sr)
    def cmp_op(acc, val, sr):
        res = (acc + (val^0xff) + 1) & 0xff
        c = ((acc + (val^0xff) + 1) >> 8) != 0
        return acc, set_sr_nzc(res, c, sr)
    def bit_op(acc, val, sr):
        res = (acc & val) & 0xff
        sr_res = set_sr_nz(res, sr)
        return acc, ((sr_res&(0xff^0xc0)) | (val&0xc0))
    
    def adc_dec_op(acc, val, sr):
        reg_a_read, tmp_value = acc, val
        tmp = (reg_a_read & 0xf) + (tmp_value & 0xf) + (sr & 0x1)
        if (tmp > 0x9):
            tmp += 0x6
        if (tmp <= 0x0f):
            tmp = (tmp & 0xf) + (reg_a_read & 0xf0) + (tmp_value & 0xf0)
        else:
            tmp = (tmp & 0xf) + (reg_a_read & 0xf0) + (tmp_value & 0xf0) + 0x10
        sr = (sr & (0xff ^ 0x2)) | (int(((reg_a_read + tmp_value + (sr & 0x1)) & 0xff) == 0)<<1)
        sr = (sr & (0xff ^ 0x80)) | (tmp & 0x80)
        sr = (sr & (0xff ^ 0x40)) | (int(((reg_a_read ^ tmp) & 0x80)!=0 and \
                            ((reg_a_read ^ tmp_value) & 0x80)==0)<<6)
        if ((tmp & 0x1f0) > 0x90):
            tmp += 0x60
        sr = (sr & (0xff^1)) | int((tmp & 0xff0) > 0xf0)
        return tmp&0xff, sr

    def sbc_dec_op(acc, val, sr):
        reg_a_read, src = acc, val
        tmp = (0x10000 + reg_a_read - src - (0 if (sr & 1)!=0 else 1)) & 0xffff
        tmp_a = (0x10000 + (reg_a_read & 0xf) - (src & 0xf) - (0 if (sr & 1)!=0 else 1)) & 0xffff
        if (tmp_a & 0x10):
            tmp_a = ((tmp_a - 6) & 0xf) | (((reg_a_read & 0xf0) - (src & 0xf0) - 0x10) & 0xffff)
        else:
            tmp_a = (tmp_a & 0xf) | (((reg_a_read & 0xf0) - (src & 0xf0)) & 0xffff)
        if (tmp_a & 0x100):
            tmp_a -= 0x60
        sr = (sr & (0xff^1)) | int(tmp < 0x100)
        sr = (sr & (0xff^2)) | (int((tmp & 0xff) == 0)<<1)
        sr = (sr & (0xff ^ 0x80)) | ((tmp & 0xff) & 0x80)
        sr = (sr & (0xff ^ 0x40)) | (int(((reg_a_read ^ tmp) & 0x80)!=0 and \
                                ((reg_a_read ^ src) & 0x80)!=0)<<6)
        return tmp_a&0xff, sr
    
    def adc_op(acc, val, sr):
        if sr&8 != 0:
            return adc_dec_op(acc, val, sr)
        else:
            res = (acc + val + (sr&1)) & 0xff
            c = ((acc + val + (sr&1)) >> 8) != 0
            v = ((((acc ^ val) & 0x80) ^ 0x80) & ((acc ^ res) & 0x80)) != 0
            sr_res = set_sr_v(v, set_sr_nzc(res, c, sr))
            return res, sr_res
    
    def sbc_op(acc, val, sr):
        if sr&8 != 0:
            return sbc_dec_op(acc, val, sr)
        else:
            res = (acc + (val^0xff) + (sr&1)) & 0xff
            c = ((acc + (val^0xff) + (sr&1)) >> 8) != 0
            v = (((acc ^ res) & 0x80) & ((acc ^ val) & 0x80)) != 0
            sr_res = set_sr_v(v, set_sr_nzc(res, c, sr))
            return res, sr_res
    
    def dec_op(val, sr):
        res = (256 + val - 1) & 0xff
        return res, set_sr_nz(res, sr)
    def inc_op(val, sr):
        res = (val + 1) & 0xff
        return res, set_sr_nz(res, sr)
    
    def asl_op(val, sr):
        res = (val << 1) & 0xff
        c = (val&0x80) != 0
        return res, set_sr_nzc(res, c, sr)
    def lsr_op(val, sr):
        res = (val >> 1) & 0xff
        c = (val&0x1) != 0
        return res, set_sr_nzc(res, c, sr)
    def rol_op(val, sr):
        res = ((val << 1) & 0xff) + (sr&1)
        c = (val&0x80) != 0
        return res, set_sr_nzc(res, c, sr)
    def ror_op(val, sr):
        res = ((val >> 1) & 0xff) + ((sr&1)<<7)
        c = (val&0x1) != 0
        return res, set_sr_nzc(res, c, sr)
    
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
    def test_and_zpg(acc, addr, val, sr):
        test_read_op_zpg('and', and_op, 0x25, acc, addr, val, sr)
    def test_and_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('and', and_op, 0x35, acc, addr, xind, val, sr)
    def test_and_abs(acc, addr, val, sr):
        test_read_op_abs('and', and_op, 0x2d, acc, addr, val, sr)
    def test_and_absx(acc, addr, xind, val, sr):
        test_read_op_absx('and', and_op, 0x3d, acc, addr, xind, val, sr)
    def test_and_absy(acc, addr, xind, val, sr):
        test_read_op_absy('and', and_op, 0x39, acc, addr, yind, val, sr)
    def test_and_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('and', and_op, 0x21, acc, addr, xind, addr2, val, sr)
    def test_and_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('and', and_op, 0x31, acc, addr, addr2, yind, val, sr)
    
    def test_ora_imm(acc, imm, sr):
        test_read_op_imm('ora', ora_op, 0x09, acc, imm, sr)
    def test_ora_zpg(acc, addr, val, sr):
        test_read_op_zpg('ora', ora_op, 0x05, acc, addr, val, sr)
    def test_ora_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('ora', ora_op, 0x15, acc, addr, xind, val, sr)
    def test_ora_abs(acc, addr, val, sr):
        test_read_op_abs('ora', ora_op, 0x0d, acc, addr, val, sr)
    def test_ora_absx(acc, addr, xind, val, sr):
        test_read_op_absx('ora', ora_op, 0x1d, acc, addr, xind, val, sr)
    def test_ora_absy(acc, addr, xind, val, sr):
        test_read_op_absy('ora', ora_op, 0x19, acc, addr, yind, val, sr)
    def test_ora_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('ora', ora_op, 0x01, acc, addr, xind, addr2, val, sr)
    def test_ora_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('ora', ora_op, 0x11, acc, addr, addr2, yind, val, sr)
    
    def test_eor_imm(acc, imm, sr):
        test_read_op_imm('eor', eor_op, 0x49, acc, imm, sr)
    def test_eor_zpg(acc, addr, val, sr):
        test_read_op_zpg('eor', eor_op, 0x45, acc, addr, val, sr)
    def test_eor_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('eor', eor_op, 0x55, acc, addr, xind, val, sr)
    def test_eor_abs(acc, addr, val, sr):
        test_read_op_abs('eor', eor_op, 0x4d, acc, addr, val, sr)
    def test_eor_absx(acc, addr, xind, val, sr):
        test_read_op_absx('eor', eor_op, 0x5d, acc, addr, xind, val, sr)
    def test_eor_absy(acc, addr, xind, val, sr):
        test_read_op_absy('eor', eor_op, 0x59, acc, addr, yind, val, sr)
    def test_eor_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('eor', eor_op, 0x41, acc, addr, xind, addr2, val, sr)
    def test_eor_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('eor', eor_op, 0x51, acc, addr, addr2, yind, val, sr)
    
    def test_cmp_imm(acc, imm, sr):
        test_read_op_imm('cmp', cmp_op, 0xc9, acc, imm, sr)
    def test_cmp_zpg(acc, addr, val, sr):
        test_read_op_zpg('cmp', cmp_op, 0xc5, acc, addr, val, sr)
    def test_cmp_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('cmp', cmp_op, 0xd5, acc, addr, xind, val, sr)
    def test_cmp_abs(acc, addr, val, sr):
        test_read_op_abs('cmp', cmp_op, 0xcd, acc, addr, val, sr)
    def test_cmp_absx(acc, addr, xind, val, sr):
        test_read_op_absx('cmp', cmp_op, 0xdd, acc, addr, xind, val, sr)
    def test_cmp_absy(acc, addr, xind, val, sr):
        test_read_op_absy('cmp', cmp_op, 0xd9, acc, addr, yind, val, sr)
    def test_cmp_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('cmp', cmp_op, 0xc1, acc, addr, xind, addr2, val, sr)
    def test_cmp_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('cmp', cmp_op, 0xd1, acc, addr, addr2, yind, val, sr)
    
    def test_cpx_imm(xind, imm, sr):
        test_read_op_xind_imm('cpx', cmp_op, 0xe0, xind, imm, sr)
    def test_cpx_zpg(xind, addr, val, sr):
        test_read_op_xind_zpg('cpx', cmp_op, 0xe4, xind, addr, val, sr)
    def test_cpx_abs(xind, addr, val, sr):
        test_read_op_xind_abs('cpx', cmp_op, 0xec, xind, addr, val, sr)
    
    def test_cpy_imm(yind, imm, sr):
        test_read_op_yind_imm('cpy', cmp_op, 0xc0, yind, imm, sr)
    def test_cpy_zpg(yind, addr, val, sr):
        test_read_op_yind_zpg('cpy', cmp_op, 0xc4, yind, addr, val, sr)
    def test_cpy_abs(yind, addr, val, sr):
        test_read_op_yind_abs('cpy', cmp_op, 0xcc, yind, addr, val, sr)
    
    def test_adc_imm(acc, imm, sr):
        test_read_op_imm('adc', adc_op, 0x69, acc, imm, sr)
    def test_adc_zpg(acc, addr, val, sr):
        test_read_op_zpg('adc', adc_op, 0x65, acc, addr, val, sr)
    def test_adc_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('adc', adc_op, 0x75, acc, addr, xind, val, sr)
    def test_adc_abs(acc, addr, val, sr):
        test_read_op_abs('adc', adc_op, 0x6d, acc, addr, val, sr)
    def test_adc_absx(acc, addr, xind, val, sr):
        test_read_op_absx('adc', adc_op, 0x7d, acc, addr, xind, val, sr)
    def test_adc_absy(acc, addr, xind, val, sr):
        test_read_op_absy('adc', adc_op, 0x79, acc, addr, yind, val, sr)
    def test_adc_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('adc', adc_op, 0x61, acc, addr, xind, addr2, val, sr)
    def test_adc_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('adc', adc_op, 0x71, acc, addr, addr2, yind, val, sr)
    
    def test_sbc_imm(acc, imm, sr):
        test_read_op_imm('sbc', sbc_op, 0xe9, acc, imm, sr)
    def test_sbc_zpg(acc, addr, val, sr):
        test_read_op_zpg('sbc', sbc_op, 0xe5, acc, addr, val, sr)
    def test_sbc_zpgx(acc, addr, xind, val, sr):
        test_read_op_zpgx('sbc', sbc_op, 0xf5, acc, addr, xind, val, sr)
    def test_sbc_abs(acc, addr, val, sr):
        test_read_op_abs('sbc', sbc_op, 0xed, acc, addr, val, sr)
    def test_sbc_absx(acc, addr, xind, val, sr):
        test_read_op_absx('sbc', sbc_op, 0xfd, acc, addr, xind, val, sr)
    def test_sbc_absy(acc, addr, xind, val, sr):
        test_read_op_absy('sbc', sbc_op, 0xf9, acc, addr, yind, val, sr)
    def test_sbc_pindx(acc, addr, xind, addr2, val, sr):
        test_read_op_pindx('sbc', sbc_op, 0xe1, acc, addr, xind, addr2, val, sr)
    def test_sbc_pindy(acc, addr, addr2, yind, val, sr):
        test_read_op_pindy('sbc', sbc_op, 0xf1, acc, addr, addr2, yind, val, sr)
    
    def test_bit_zpg(acc, addr, val, sr):
        test_read_op_zpg('bit', bit_op, 0x24, acc, addr, val, sr)
    def test_bit_abs(acc, addr, val, sr):
        test_read_op_abs('bit', bit_op, 0x2c, acc, addr, val, sr)
    
    def test_dec_zpg(addr, val, sr):
        test_read_write_op_zpg('dec', dec_op, 0xc6, addr, val, sr)
    def test_dec_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('dec', dec_op, 0xd6, addr, xind, val, sr)
    def test_dec_abs(addr, val, sr):
        test_read_write_op_abs('dec', dec_op, 0xce, addr, val, sr)
    def test_dec_absx(addr, xind, val, sr):
        test_read_write_op_absx('dec', dec_op, 0xde, addr, xind, val, sr)
    
    def test_inc_zpg(addr, val, sr):
        test_read_write_op_zpg('inc', inc_op, 0xe6, addr, val, sr)
    def test_inc_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('inc', inc_op, 0xf6, addr, xind, val, sr)
    def test_inc_abs(addr, val, sr):
        test_read_write_op_abs('inc', inc_op, 0xee, addr, val, sr)
    def test_inc_absx(addr, xind, val, sr):
        test_read_write_op_absx('inc', inc_op, 0xfe, addr, xind, val, sr)
    
    def test_asl_imp(val, sr):
        test_acc_op_imp('asl', asl_op, 0x0a, val, sr)
    def test_asl_zpg(addr, val, sr):
        test_read_write_op_zpg('asl', asl_op, 0x06, addr, val, sr)
    def test_asl_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('asl', asl_op, 0x16, addr, xind, val, sr)
    def test_asl_abs(addr, val, sr):
        test_read_write_op_abs('asl', asl_op, 0x0e, addr, val, sr)
    def test_asl_absx(addr, xind, val, sr):
        test_read_write_op_absx('asl', asl_op, 0x1e, addr, xind, val, sr)
    
    def test_lsr_imp(val, sr):
        test_acc_op_imp('lsr', lsr_op, 0x4a, val, sr)
    def test_lsr_zpg(addr, val, sr):
        test_read_write_op_zpg('lsr', lsr_op, 0x46, addr, val, sr)
    def test_lsr_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('lsr', lsr_op, 0x56, addr, xind, val, sr)
    def test_lsr_abs(addr, val, sr):
        test_read_write_op_abs('lsr', lsr_op, 0x4e, addr, val, sr)
    def test_lsr_absx(addr, xind, val, sr):
        test_read_write_op_absx('lsr', lsr_op, 0x5e, addr, xind, val, sr)
    
    def test_rol_imp(val, sr):
        test_acc_op_imp('rol', rol_op, 0x2a, val, sr)
    def test_rol_zpg(addr, val, sr):
        test_read_write_op_zpg('rol', rol_op, 0x26, addr, val, sr)
    def test_rol_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('rol', rol_op, 0x36, addr, xind, val, sr)
    def test_rol_abs(addr, val, sr):
        test_read_write_op_abs('rol', rol_op, 0x2e, addr, val, sr)
    def test_rol_absx(addr, xind, val, sr):
        test_read_write_op_absx('rol', rol_op, 0x3e, addr, xind, val, sr)
    
    def test_ror_imp(val, sr):
        test_acc_op_imp('ror', ror_op, 0x6a, val, sr)
    def test_ror_zpg(addr, val, sr):
        test_read_write_op_zpg('ror', ror_op, 0x66, addr, val, sr)
    def test_ror_zpgx(addr, xind, val, sr):
        test_read_write_op_zpgx('ror', ror_op, 0x76, addr, xind, val, sr)
    def test_ror_abs(addr, val, sr):
        test_read_write_op_abs('ror', ror_op, 0x6e, addr, val, sr)
    def test_ror_absx(addr, xind, val, sr):
        test_read_write_op_absx('ror', ror_op, 0x7e, addr, xind, val, sr)
    
    def test_bcc_rel(start, rel, sr):
        test_op_branch('bcc', False, 1, 0x90, start, rel, sr)
    def test_bcs_rel(start, rel, sr):
        test_op_branch('bcs', True, 1, 0xb0, start, rel, sr)
    def test_beq_rel(start, rel, sr):
        test_op_branch('beq', True, 2, 0xf0, start, rel, sr)
    def test_bmi_rel(start, rel, sr):
        test_op_branch('bmi', True, 0x80, 0x30, start, rel, sr)
    def test_bne_rel(start, rel, sr):
        test_op_branch('bne', False, 2, 0xd0, start, rel, sr)
    def test_bpl_rel(start, rel, sr):
        test_op_branch('bpl', False, 0x80, 0x10, start, rel, sr)
    def test_bvc_rel(start, rel, sr):
        test_op_branch('bvc', False, 0x40, 0x50, start, rel, sr)
    def test_bvs_rel(start, rel, sr):
        test_op_branch('bvs', True, 0x40, 0x70, start, rel, sr)
    
    ###############################
    # testsuite
    
    sr_flags_values = [0, 1, 2, 3, 4, 6, 8, 16, 24, 32, 49, 64, 128, 129, 136, 192, 255]
    transfer_values = [0, 3, 5, 35, 127, 128, 44, 196, 255, 251,
                       136, 138, 139, 160, 161, 162, 163]
    zpg_addr_values = [0, 12, 1, 55, 128, 64, 195, 231, 255]
    zpgx_xind_values = [0, 3, 66, 12, 145, 255, 197, 217, 191]
    abs_addr_values = [0x1316, 0xffff, 0xfe11, 0xffe, 0x0451, 0xb5a1, 0x2988]
    pindx_addr_values = [(0, 42), (54, 76), (187, 68), (200, 55), (178, 121)]
    pindy_addr2_values = [(0x34dd, 11), (0x828b, 141), (0xbd20, 55), (0x6b92, 0x6e)]
    small_nz_values = [0, 31, 128, 55]
    small_sr_nz_values = [ 0x11, 0x13, 0x91, 0x93, 0x10, 0x18 ]
    small_sr_nzvc_values = [ 0x11, 0x13, 0x91, 0x93, 0x10, 0x50, 0x41, 0x51, 0x18 ]
    rel_jump_values = [(0x341, 0x31), (0x33b, 0xc3), (0x33b, 0xc2), (0x33b, 0xba),
                       (0x3ba, 0x2d), (0x3ba, 0x43), (0x3ba, 0x44), (0x3ba, 0x47)]
    small_cmp_values = [0, 11, 22, 93, 233, 252]
    sp_values = [255, 154, 31, 0, 3]
    sp2_values = [255, 254, 154, 31, 61, 0, 3]
    jmp_ind_addr = [(0x3314, 0x42ba), (0x4bff, 0x5b11), (0xffff, 0x1ad5), (0x21, 0x241)]
    vecfffe_values = [0x1316, 0xfffc, 0xfe11, 0xffe, 0x0451, 0xb5a1, 0x2988]
    
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
        for sr in small_sr_nz_values:
            test_dex(i, sr)
            test_dey(i, sr)
            test_inx(i, sr)
            test_iny(i, sr)
    
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
    
    for addr in zpg_addr_values:
        for v in transfer_values:
            for sr in small_sr_nz_values:
                test_dec_zpg(addr, v, sr)
                test_inc_zpg(addr, v, sr)
                test_asl_zpg(addr, v, sr)
                test_lsr_zpg(addr, v, sr)
                test_rol_zpg(addr, v, sr)
                test_ror_zpg(addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in transfer_values:
                for sr in small_sr_nz_values:
                    test_dec_zpgx(addr, xind, v, sr)
                    test_inc_zpgx(addr, xind, v, sr)
                    test_asl_zpgx(addr, xind, v, sr)
                    test_lsr_zpgx(addr, xind, v, sr)
                    test_rol_zpgx(addr, xind, v, sr)
                    test_ror_zpgx(addr, xind, v, sr)
    
    for addr in abs_addr_values:
        for v in transfer_values:
            for sr in small_sr_nz_values:
                test_dec_abs(addr, v, sr)
                test_inc_abs(addr, v, sr)
                test_asl_abs(addr, v, sr)
                test_lsr_abs(addr, v, sr)
                test_rol_abs(addr, v, sr)
                test_ror_abs(addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in transfer_values:
                for sr in small_sr_nz_values:
                    test_dec_absx(addr, xind, v, sr)
                    test_inc_absx(addr, xind, v, sr)
                    test_asl_absx(addr, xind, v, sr)
                    test_lsr_absx(addr, xind, v, sr)
                    test_rol_absx(addr, xind, v, sr)
                    test_ror_absx(addr, xind, v, sr)
    
    for v in transfer_values:
        for sr in small_sr_nz_values:
            test_asl_imp(v, sr)
            test_lsr_imp(v, sr)
            test_rol_imp(v, sr)
            test_ror_imp(v, sr)
    
    for (start, rel) in rel_jump_values:
        for sr in sr_flags_values:
            test_bcc_rel(start, rel, sr)
            test_bcs_rel(start, rel, sr)
            test_beq_rel(start, rel, sr)
            test_bmi_rel(start, rel, sr)
            test_bne_rel(start, rel, sr)
            test_bpl_rel(start, rel, sr)
            test_bvc_rel(start, rel, sr)
            test_bvs_rel(start, rel, sr)
    
    for i in transfer_values:
        for j in transfer_values:
            for sr in small_sr_nz_values:
                test_and_imm(i, j, sr)
                test_ora_imm(i, j, sr)
                test_eor_imm(i, j, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_zpg(i, addr, v, sr)
                    test_ora_zpg(i, addr, v, sr)
                    test_eor_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_zpgx(0xba, addr, xind, v, sr)
                    test_ora_zpgx(0x1c, addr, xind, v, sr)
                    test_eor_zpgx(0x1c, addr, xind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_abs(i, addr, v, sr)
                    test_ora_abs(i, addr, v, sr)
                    test_eor_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_absx(0xba, addr, xind, v, sr)
                    test_ora_absx(0x1c, addr, xind, v, sr)
                    test_eor_absx(0x1c, addr, xind, v, sr)
    
    for addr in abs_addr_values:
        for yind in zpgx_xind_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_absy(0xba, addr, yind, v, sr)
                    test_ora_absy(0x1c, addr, yind, v, sr)
                    test_eor_absy(0x1c, addr, yind, v, sr)
    
    for (addr, xind) in pindx_addr_values:
        for addr2 in abs_addr_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_pindx(0xba, addr, xind, addr2, v, sr)
                    test_ora_pindx(0x1c, addr, xind, addr2, v, sr)
                    test_eor_pindx(0x1c, addr, xind, addr2, v, sr)
    
    for addr in zpg_addr_values:
        for (addr2, yind) in pindy_addr2_values:
            for v in small_nz_values:
                for sr in small_sr_nz_values:
                    test_and_pindy(0xba, addr, addr2, yind, v, sr)
                    test_ora_pindy(0x1c, addr, addr2, yind, v, sr)
                    test_eor_pindy(0x1c, addr, addr2, yind, v, sr)
    
    for i in transfer_values:
        for j in transfer_values:
            for sr in small_sr_nz_values:
                test_cmp_imm(i, j, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_zpgx(0x1c, addr, xind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_absx(0x1c, addr, xind, v, sr)
    
    for addr in abs_addr_values:
        for yind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_absy(0x1c, addr, yind, v, sr)
    
    for (addr, xind) in pindx_addr_values:
        for addr2 in abs_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_pindx(0x1c, addr, xind, addr2, v, sr)
    
    for addr in zpg_addr_values:
        for (addr2, yind) in pindy_addr2_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cmp_pindy(0x1c, addr, addr2, yind, v, sr)
    
    for i in transfer_values:
        for j in transfer_values:
            for sr in small_sr_nz_values:
                test_cpx_imm(i, j, sr)
                test_cpy_imm(i, j, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cpx_zpg(i, addr, v, sr)
                    test_cpy_zpg(i, addr, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nz_values:
                    test_cpx_abs(i, addr, v, sr)
                    test_cpy_abs(i, addr, v, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in transfer_values:
                for sr in small_sr_nz_values:
                    test_bit_zpg(i, addr, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in transfer_values:
                for sr in small_sr_nz_values:
                    test_bit_abs(i, addr, v, sr)
    
    for i in small_nz_values:
        for j in small_nz_values:
            for k in small_nz_values:
                for sr in small_sr_nz_values:
                    test_nop(i, j, k, sr)
    
    for acc in transfer_values:
        for sp in sp_values:
            for sr in small_sr_nz_values:
                test_pha(acc, sp, sr)
    
    for val in transfer_values:
        for sp in sp_values:
            for sr in small_sr_nz_values:
                test_pla(val, sp, sr)
    
    for sp in sp_values:
        for sr in transfer_values:
            test_php(sp, sr)
    
    for val in transfer_values:
        for sp in sp_values:
            for sr in transfer_values:
                test_plp(val, sp, sr)
    
    for addr in abs_addr_values:
        for acc in small_nz_values:
            for xind in small_nz_values:
                for yind in small_nz_values:
                    for sr in small_sr_nz_values:
                        test_jmp(addr, acc, xind, yind, sr)
    
    for (addr, addr2) in jmp_ind_addr:
        for acc in small_nz_values:
            for xind in small_nz_values:
                for yind in small_nz_values:
                    for sr in small_sr_nz_values:
                        test_jmp_ind(addr, addr2, acc, xind, yind, sr)
    
    for start in [0x2b5, 0x2ff, 0x2fe]:
        for addr in abs_addr_values:
            for sp in sp_values:
                for sr in small_sr_nz_values:
                    test_jsr(start, addr, sp, sr)
    
    for val in abs_addr_values:
        for sp in sp2_values:
            for sr in small_sr_nz_values:
                test_rts(val, sp, sr)
    
    for start in [0x2b5, 0x2ff, 0x2fe]:
        for vecfffe in vecfffe_values:
            for sp in sp_values:
                for sr in sr_flags_values:
                    test_brk(start, vecfffe, sp, sr)
    
    for val in abs_addr_values:
        for ret_sr in sr_flags_values:
            for sp in sp2_values:
                for sr in small_sr_nz_values:
                    test_rti(val, ret_sr, sp, sr)
    
    for i in transfer_values:
        for j in transfer_values:
            for sr in small_sr_nzvc_values:
                test_adc_imm(i, j, sr)
                test_sbc_imm(i, j, sr)
    
    for i in transfer_values:
        for addr in zpg_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_zpg(i, addr, v, sr)
                    test_sbc_zpg(i, addr, v, sr)
    
    for addr in zpg_addr_values:
        for xind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_zpgx(0x1c, addr, xind, v, sr)
                    test_sbc_zpgx(0x1c, addr, xind, v, sr)
    
    for i in transfer_values:
        for addr in abs_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_abs(i, addr, v, sr)
                    test_sbc_abs(i, addr, v, sr)
    
    for addr in abs_addr_values:
        for xind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_absx(0x1c, addr, xind, v, sr)
                    test_sbc_absx(0x1c, addr, xind, v, sr)
    
    for addr in abs_addr_values:
        for yind in zpgx_xind_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_absy(0x1c, addr, yind, v, sr)
                    test_sbc_absy(0x1c, addr, yind, v, sr)
    
    for (addr, xind) in pindx_addr_values:
        for addr2 in abs_addr_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_pindx(0x1c, addr, xind, addr2, v, sr)
                    test_sbc_pindx(0x1c, addr, xind, addr2, v, sr)
    
    for addr in zpg_addr_values:
        for (addr2, yind) in pindy_addr2_values:
            for v in small_cmp_values:
                for sr in small_sr_nzvc_values:
                    test_adc_pindy(0x1c, addr, addr2, yind, v, sr)
                    test_sbc_pindy(0x1c, addr, addr2, yind, v, sr)
    
    for a in range(0,256):
        for b in range(0,256):
            for sr in range(8,10):
                test_adc_imm(a, b, sr)
    
    for a in range(0,256):
        for b in range(0,256):
            for sr in range(8,10):
                test_sbc_imm(a, b, sr)
    
    #########################
    # Commodore 64 native
    
    #########################
    
    cp = subprocess.run([PYTHON, CG6502, '-N', '-C', '--create=0xcf'], capture_output=True)
    if cp.returncode != 0:
        raise(RuntimeError('Error while running code generation of 6502'))
    with open('6502progbase.raw','wb') as f:
        f.write(cp.stdout)

    with open('6502membase.raw','wb') as f:
        f.write(b'\x00'*(0x16000))
        with open(C64KERNAL,'rb') as kernal:
            f.write(kernal.read())
        f.write(b'\x00'*(0x2000))   # skip empty
        with open(C64BASIC,'rb') as basic:
            f.write(basic.read())
        with open(C64CHARGEN,'rb') as chargen:
            f.write(chargen.read())
        f.write(b'\x00'*(0x3000))   # devio and kernal
    ####################################
    
    def test_lda_rom(memconfig, addr, val, romaddr, romval):
        new_acc, new_sr = lda_op(0, val, 0)
        run_testcase('lda (rom) mc={} addr={} val={}'.format(memconfig, addr, val),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, val),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, 1),
                (0, (romaddr&0xffff)|0x10000, romval),
            ],
            [
                (0, [0x2f, 0x30|(memconfig&7)]),
                (addr&0xffff, [1]),
                # instructions. last is undefined (stop)
                (0x200, [0xad, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=0, sr=0, xind=2, yind=1)
    
    ####################################
    # basic and kernal
    test_lda_rom(7, 0xa280, 0x4e, 0xa280, 0x4e)
    test_lda_rom(7, 0xe580, 0x27, 0x6580, 0x27)
    test_lda_rom(3, 0xa280, 0x4e, 0xa280, 0x4e)
    test_lda_rom(3, 0xe580, 0x27, 0x6580, 0x27)
    # only kernal
    test_lda_rom(6, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(6, 0xe580, 0x27, 0x6580, 0x27)
    test_lda_rom(2, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(2, 0xe580, 0x27, 0x6580, 0x27)
    # no basic no kernal
    test_lda_rom(5, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(5, 0xe580, 0x1, 0x6580, 0x27)
    test_lda_rom(4, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(4, 0xe580, 0x1, 0x6580, 0x27)
    test_lda_rom(1, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(1, 0xe580, 0x1, 0x6580, 0x27)
    test_lda_rom(0, 0xa280, 0x1, 0xa280, 0x4e)
    test_lda_rom(0, 0xe580, 0x1, 0x6580, 0x27)
    # chargen
    test_lda_rom(3, 0xd4e0, 0xf3, 0xc4e0, 0xf3)
    test_lda_rom(2, 0xd4e0, 0xf3, 0xc4e0, 0xf3)
    test_lda_rom(1, 0xd4e0, 0xf3, 0xc4e0, 0xf3)
    test_lda_rom(0, 0xd4e0, 0x1, 0xc4e0, 0xf3)
    # devio
    test_lda_rom(7, 0xd4e0, 0x0, 0xd4e0, 0x0)   # devio
    test_lda_rom(6, 0xd4e0, 0x0, 0xd4e0, 0x0)   # devio
    test_lda_rom(5, 0xd4e0, 0x0, 0xd4e0, 0x0)   # devio
    test_lda_rom(4, 0xd4e0, 0x1, 0xd4e0, 0x0)   # ram
    # only ram
    for mc in range(0,8):
        test_lda_rom(mc, 0x2280, 0x1, 0x2280, 0x0)
    
    # store
    def test_sta_rom(memconfig, acc, addr, val, val2):
        opcode = 0x8d
        run_testcase('sta (rom) mc={} acc={} addr={} val={} val2={}' \
                .format(memconfig, acc, addr, val, val2),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, 1),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, val),
                (0, (addr&0xffff)|0x10000, val2),
            ],
            [
                (0, [0x2f, 0x30|(memconfig&7)]),
                (addr&0xffff, [0]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=1, xind=2, yind=1)
    
    for mc in range(0, 8):
        test_sta_rom(mc, 0xca, 0xa332, 0xca, 226)
        test_sta_rom(mc, 0xca, 0xe332, 0xca, 0) # this is not kernal! in 16000
    test_sta_rom(7, 0x4d, 0xd176, 0, 0x4d)
    test_sta_rom(6, 0x4d, 0xd176, 0, 0x4d)
    test_sta_rom(5, 0x4d, 0xd176, 0, 0x4d)
    for mc in range(0, 5):
        test_sta_rom(mc, 0x4d, 0xd176, 0x4d, 0)
    
    # modify
    def test_inc_rom(memconfig, addr, val, destval, romaddr, romval):
        run_testcase('inc (rom) mc={} addr={} val={} destval={}' \
                .format(memconfig, addr, val, destval),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, set_sr_nz(destval, 0)),
                (1, acc_offset, 3),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, addr&0xffff, destval),
                (0, (romaddr&0xffff)|0x10000, romval),
            ],
            [
                (0, [0x2f, 0x30|(memconfig&7)]),
                (addr&0xffff, [1]),
                # instructions. last is undefined (stop)
                (0x200, [0xee, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=0, xind=2, yind=1)
    
    # basic and kernal
    test_inc_rom(7, 0xa280, 0x4e, 0x4f, 0xa280, 0x4e)
    test_inc_rom(7, 0xe580, 0x27, 0x28, 0x6580, 0x27)
    test_inc_rom(3, 0xa280, 0x4e, 0x4f, 0xa280, 0x4e)
    test_inc_rom(3, 0xe580, 0x27, 0x28, 0x6580, 0x27)
    # only kernal
    test_inc_rom(6, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(6, 0xe580, 0x27, 0x28, 0x6580, 0x27)
    test_inc_rom(2, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(2, 0xe580, 0x27, 0x28, 0x6580, 0x27)
    # no basic no kernal
    test_inc_rom(5, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(5, 0xe580, 0x27, 0x2, 0x6580, 0x27)
    test_inc_rom(4, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(4, 0xe580, 0x27, 0x2, 0x6580, 0x27)
    test_inc_rom(1, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(1, 0xe580, 0x27, 0x2, 0x6580, 0x27)
    test_inc_rom(0, 0xa280, 0x4e, 0x2, 0xa280, 0x4e)
    test_inc_rom(0, 0xe580, 0x27, 0x2, 0x6580, 0x27)
    # chargen
    test_inc_rom(3, 0xd4e0, 0xf3, 0xf4, 0xc4e0, 0xf3)
    test_inc_rom(2, 0xd4e0, 0xf3, 0xf4, 0xc4e0, 0xf3)
    test_inc_rom(1, 0xd4e0, 0xf3, 0xf4, 0xc4e0, 0xf3)
    test_inc_rom(0, 0xd4e0, 0xf3, 0x2, 0xc4e0, 0xf3)
    
    # load last page
    def test_lda_last(addr, val, lastval):
        new_acc, new_sr = lda_op(0, val, 0)
        run_testcase('lda (last) addr={} val={} lastval={}'.format(addr, val, lastval),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, new_sr),
                (1, acc_offset, val),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, 1),
                (0, addr|0x1ff00, lastval),
            ],
            [
                (addr&0xffff, [1]),
                (addr|0x1ff00, [lastval]),
                # instructions. last is undefined (stop)
                (0x200, [0xad, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=0, sr=0, xind=2, yind=1)
    
    test_lda_last(0xcf23, 0x54, 0x54)
    test_lda_last(0xce23, 1, 0x54)
    
    def test_sta_last(acc, addr, val, lastval):
        opcode = 0x8d
        run_testcase('sta (last) acc={} addr={} val={} lastval={}' \
                .format(acc, addr, val, lastval),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, 1),
                (1, acc_offset, acc),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 4),
                (0, addr&0xffff, val),
                (0, addr|0x1ff00, lastval),
            ],
            [
                (addr&0xffff, [0]),
                # instructions. last is undefined (stop)
                (0x200, [opcode&0xff, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=acc, sr=1, xind=2, yind=1)
    
    test_sta_last(0x4b, 0xcf23, 0, 0x4b)
    test_sta_last(0x4b, 0xce23, 0x4b, 0)
    
    def test_inc_last(addr, val, lastval):
        run_testcase('inc (last) addr={} val={} destval={}'.format(addr, val, lastval),
            [
                (1, pc_offset, (0x204)&0xff),
                (1, pc_offset+1, ((0x204)>>8)&0xff),
                (1, sr_offset, set_sr_nz(2, 0)),
                (1, acc_offset, 3),
                (1, xind_offset, 2),
                (1, yind_offset, 1),
                (1, sp_offset, 0xff),
                (1, instr_cycles_offset, 6),
                (0, addr&0xffff, val),
                (0, addr|0x1ff00, lastval),
            ],
            [
                (addr&0xffff, [1]),
                (addr|0x1ff00, [1]),
                # instructions. last is undefined (stop)
                (0x200, [0xee, addr&0xff, (addr>>8)&0xff, 0x04])
            ],
            pc=0x200, acc=3, sr=0, xind=2, yind=1)
    
    test_inc_last(0xcf3a, 1, 2)
    test_inc_last(0xce3a, 2, 1)
    
    
    cp = subprocess.run([PYTHON, CG6502, '--no-interrupt=1'], capture_output=True)
    if cp.returncode != 0:
        raise(RuntimeError('Error while running code generation of 6502'))
    with open('6502progbase.raw','wb') as f:
        f.write(cp.stdout)

    with open('6502membase.raw','wb') as f:
        f.write(b'\x00'*(1<<16))
    
    def test_chsr_unsat(name, opcode, bit, clr, sr):
        run_testcase('{} unsat sr={}'.format(name, sr),
            [],
            [ (0x200, [opcode&0xff, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_brk_unsat(sr):
        run_testcase('brk unat sr={}'.format(sr),
            [],
            [ (0x200, [0x00, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_brk_unsat(sr):
        run_testcase('rti unsat sr={}'.format(sr),
            [],
            [ (0x200, [0x40, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_cli_unsat(sr): test_chsr_unsat('cli', 0x58, 2, True, sr)
    def test_sei_unsat(sr): test_chsr_unsat('sei', 0x78, 2, False, sr)
    def test_plp_unsat(val, sp, sr):
        run_testcase('plp unsat val={} sp={} sr={}'.format(val, sp, sr),
            [],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [val]),
                # instructions. last is undefined (stop)
                (0x200, [0x28, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp, unsat=True)
    
    for i in sr_flags_values:
        test_cli_unsat(i)
        test_sei_unsat(i)
        test_brk_unsat(i)
    test_plp(0x15, 0xdd, 0x06)
    test_plp_unsat(0x11, 0xdd, 0x06)
    
    cp = subprocess.run([PYTHON, CG6502, '--no-interrupt=2'], capture_output=True)
    if cp.returncode != 0:
        raise(RuntimeError('Error while running code generation of 6502'))
    with open('6502progbase.raw','wb') as f:
        f.write(cp.stdout)

    with open('6502membase.raw','wb') as f:
        f.write(b'\x00'*(1<<16))
    
    def test_chsr_unsat(name, opcode, bit, clr, sr):
        run_testcase('{} unsat sr={}'.format(name, sr),
            [],
            [ (0x200, [opcode&0xff, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_brk_unsat(sr):
        run_testcase('brk unat sr={}'.format(sr),
            [],
            [ (0x200, [0x00, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_brk_unsat(sr):
        run_testcase('rti unsat sr={}'.format(sr),
            [],
            [ (0x200, [0x40, 0x04]) ],   # instructions. last is undefined (stop)
            pc=0x200, acc=0, sr=sr, unsat=True)
    
    def test_cli_unsat(sr): test_chsr_unsat('cli', 0x58, 2, True, sr)
    def test_sei_unsat(sr): test_chsr_unsat('sei', 0x78, 2, False, sr)
    def test_plp_unsat(val, sp, sr):
        run_testcase('plp unsat val={} sp={} sr={}'.format(val, sp, sr),
            [],
            [
                # stack
                (0x100 + ((sp+1)&0xff), [val]),
                # instructions. last is undefined (stop)
                (0x200, [0x28, 0x04])
            ],
            pc=0x200, acc=3, sr=sr, xind=1, yind=2, sp=sp, unsat=True)
    
    for i in sr_flags_values:
        test_cli_unsat(i)
        test_sei_unsat(i)
        test_brk_unsat(i)
    test_plp(0x11, 0xdd, 0x06)
    test_plp_unsat(0x15, 0xdd, 0x06)
    
    #########################
    # Summary
    print("Tests passed: {}, Tests failed: {}, Total: {}" \
            .format(tests_passed, tests_failed, tests_passed+tests_failed))
finally:
    #cleanup()
    pass
