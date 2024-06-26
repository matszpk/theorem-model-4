## THEOREM-MODEL-4 CIRCUIT CODE:

Any inputs or outputs are single boolean values (bits). TheoremModel4 defines circuits and
machines in that simpliest level. Any circuit is list of call of NAND or other circuits
that can call NAND and other circuits. The noticed NAND is just simple NAND gate that
return 0 if all inputs are 1 and returns 1 if otherwise.

The code of circuit in TheoremModel4 is set of defined circuits. The circuit can have
maximum 128 inputs and 128 outputs. Inputs of circuit treat as previous internal outputs
in circuit. Internal outputs are numbered from 0 to 127. Internal outputs in circuit can be
unlimited. However, Nth internal output just replaces (N-127)th internal output.
Inputs and outputs of circuit defined in circuit definition. The body of circuit contains code
that describe operations done by circuit. The first internal outputs are input of circuits.

A body of circuit defined as list of instructions. A instruction can contains 2 or more bytes.
Type of instructions:

Two bytes value in 0-127 - call NAND function. Two bytes represents previous internal outputs.
Instruction generates one next internal output.

Byte value in 128-255 - call other circuit that get some inputs and generates some
internal outputs. Number of inputs and outputs defined in called circuit.
Next bytes with value in 0-127 are internal outputs that will be used
as inputs for circuit. Additional encoding in this input list includes:
* byte value in 192-255 - repeat internal output (given in next byte) n (byte value - 192)
  times.
* byte value in 128-191 - repeat internal output (given in next byte) n (byte value - 128)
  times with increasing same internal output. For example 132 4: 4 5 6 ... 11.

An empty body of circuit defines empty circuit that just copies inputs to its outputs.
Then number of inputs and ouputs must be same.

## THEOREM-MODEL-4 CIRCUIT LANGUAGE:

The circuit language for model define simple human-readable form to define circuits in
TheoremModel4. This is list of circuits where one circuit must be named 'main'.
Sample circuit definition:

```
xor:
    n0 = nand i0 i0
    n1 = nand i1 i1
    t0 = nand i0 n1
    t1 = nand n0 i1
    o0 = nand t0 t1
```

The first line defines name of circuit. Inputs are called as `iX` where X is number of input
start from 0. Number of inputs get from input with highest number (then number of inputs is 
N+1). Next lines defines body where single lines is single instruction.
In that line first name is name of internal output. Next name in line is name of circuit
(it can be nand as builtin NAND function). Next names are internal outputs passed as
input of called circuit. Last instruction must have interal outputs named as `oX` where
X is number of output. These outputs must be defined in order from 0 to some number.
Number of outputs get from number of last output.
Between circuit outputs must not be other internal outputs.

The comments are defined as lines started from `#`.

Lines of circuit code can be divided by source lines by `\`, like in example:

```
...
cpu_instr_0_n cpu_instr_1_n cpu_instr_2_n cpu_instr_3_n = not_4bit \
        cpu_instr_0 cpu_instr_1 cpu_instr_2 cpu_instr_3
...
```

# EXECUTION MODEL.

Any instruction in any circuit is executed in order (first to last).
Maximal nesting of circuit is 8.

TheoeremModel4 defines machine that have access to memory. The execution of that machine
is execution of main circuit by passing memory value as some inputs to this circuit and
get some outputs as memory address and read/write indicator. The first is primal machine
which execution defined by circuit in TM4 language. Next machines can be defined as
code in primal machine language.

Machine defines two parameters:
* cell_len_bits - number of bits in cell as 2^cell_len_bits.
* address_len - number of bits in memory address.

Inputs for machine circuit:

* state - circuit state that from previous circuit execution or initial state if first execution.
* mem_value - value return from memory if memory read.

Outputs for machine circuit:

* state - returned new circuit state.
* mem_value - new memory value that will be stored into memory cell with given memory address
  if mem_rw is true.
* mem_rw - if true then mem_value will be stored into memory cell.
* mem_address - given memory address from memory will be read or written.
* create - create new nested machine (actually nested memory).
* stop - stop machine. If stop and create are true then we have unsatisfied state.

A memory address is cell address, not bit or byte address.

# CREATION MODEL

If create bit is set then 2*address_len bits in memory defines two parameters of next machine:
* first address_len bits - defines new address_len.
* second address_len bits - defines new cell_len_bits.

After machine creation. Last cells of memory of current machine is memory addres to
memory cell of next machine. The number of these cells with new address to new nachine is
number of cells needed to store memory address to new memory.
Previous cells of current memory is memory cell value - it can have read memory value or
write operation causes writing to new memory in given memory address.
The number of these cells with new address to new nachine is
number of cells needed to store cell of new memory.

For example if current cell_len_bits=3 (cell_len is 8 bits) and current address_len=12
(4096 bytes of memory) then new_cell_bits=4 (cell_len is 16 bits) and new_address_len=18
then cells with address 0xffb and 0xffc is new cell and cells
with addresses 0xffd,0xffe,0xfff holds new memory address.
