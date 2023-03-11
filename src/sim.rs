use crate::convert::*;
use crate::parser::*;

use std::fs::File;
use std::io::{self, Write};
use std::path::Path;

#[derive(thiserror::Error, Debug)]
pub enum DumpError {
    #[error("IO error: {0}")]
    IO(#[from] io::Error),
    #[error("Numeric error: {0}")]
    Num(#[from] std::num::TryFromIntError),
}

// runtime environment
#[derive(Clone, Copy, Debug)]
pub struct SubcircuitInfo {
    pub location: usize,
    pub input_len: u8,
    pub output_len: u8,
}

#[derive(Clone, Debug)]
pub struct Circuit {
    pub circuit: Vec<u8>,
    // tuple: start, input len, output len
    pub subcircuits: Vec<SubcircuitInfo>,
    pub input_len: u8,
    pub output_len: u8,
}

pub fn get_bit(slice: &[u8], i: usize) -> bool {
    (slice[i >> 3] >> (i & 7)) & 1 != 0
}

pub fn set_bit(slice: &mut [u8], i: usize, v: bool) {
    let mask = 1 << (i & 7);
    slice[i >> 3] = (slice[i >> 3] & !mask) | (if v { mask } else { 0 });
}

impl Circuit {
    pub fn new() -> Self {
        Self {
            circuit: vec![],
            subcircuits: vec![],
            input_len: 0,
            output_len: 0,
        }
    }

    fn run_circuit(
        &self,
        circuit: Option<usize>,
        input: &[u8],
        input_len: usize,
        level: u8,
        trace: bool,
    ) -> ([u8; 128 >> 3], usize) {
        assert!(level < 8);
        assert!(input.len() < 128);
        if trace {
            println!(
                "Input {}",
                (0..input_len)
                    .map(|i| if get_bit(input, i) { "1" } else { "0" })
                    .collect::<String>()
            );
        }
        let mut step_mem: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

        // initialize input
        for i in 0..input_len {
            set_bit(&mut step_mem, i, get_bit(input, i));
        }

        let mut step_index = circuit
            .map(|x| self.subcircuits[x].location)
            .unwrap_or_default();
        // circuit end: if given - then end at start subcircuit sc+1 or end of whole circuit.
        // if not given: then end starts at start of first subcircuit or  end of whole circuit.
        let circuit_end = circuit
            .map(|x| {
                if x + 1 < self.subcircuits.len() {
                    self.subcircuits[x + 1].location
                } else {
                    self.circuit.len()
                }
            })
            .unwrap_or(if self.subcircuits.is_empty() {
                self.circuit.len()
            } else {
                self.subcircuits[0].location
            });

        let mut oi = input_len; // output index
        while step_index < circuit_end {
            let mut nand_arg1: Option<bool> = None;
            while step_index < circuit_end {
                let lv = self.circuit[step_index];
                if trace {
                    println!("Step cell: {} {}: {}", step_index, oi, lv);
                }
                if lv < 128 {
                    // input value
                    let ii = lv as usize;
                    let v = get_bit(&step_mem[..], ii);
                    if let Some(v1) = nand_arg1 {
                        if trace {
                            println!("Step: {} {}: {} {} {}", step_index, oi, v1, v, !(v1 & v));
                        }
                        set_bit(&mut step_mem[..], oi, !(v1 & v));
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
                    } else {
                        nand_arg1 = Some(v);
                    }
                    step_index += 1;
                } else {
                    if let Some(v1) = nand_arg1 {
                        // if next argument not found then flush with 1
                        if trace {
                            println!("Step: {} {}: {} {} {}", step_index, oi, v1, true, !v1);
                        }
                        set_bit(&mut step_mem[..], oi, !v1);
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
                    }
                    // subcircuit call
                    let sc = (lv - 128) as usize;
                    if trace {
                        println!("Call: {} {}: {}", step_index, oi, sc);
                    }
                    step_index += 1;
                    let mut sc_input: [u8; 128 >> 3] =
                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

                    let sc_input_len = self.subcircuits[sc].input_len as usize;
                    let sc_output_len = self.subcircuits[sc].output_len as usize;
                    {
                        let mut i = 0;
                        while i < sc_input_len {
                            let ii = self.circuit[step_index] as usize;
                            if ii < 128 {
                                let v = get_bit(&step_mem[..], ii);
                                set_bit(&mut sc_input[..], i, v);
                                i += 1;
                                step_index += 1;
                            } else if ii >= 128 {
                                // repeat input: 128+rep_count base_output
                                // repeats: base_output + i
                                let inc = usize::from(ii < 192);
                                let rep_count = std::cmp::min(ii & 0x3f, sc_input_len - i);
                                step_index += 1;
                                if step_index < circuit_end {
                                    let ii = self.circuit[step_index] as usize;
                                    step_index += 1;
                                    for j in 0..rep_count {
                                        let v = get_bit(&step_mem[..], (ii + j * inc) & 127);
                                        set_bit(&mut sc_input[..], i + j, v);
                                    }
                                    i += rep_count;
                                }
                            }
                        }
                    }

                    let (sc_output, sc_oi) =
                        self.run_circuit(Some(sc), &sc_input, sc_input_len, level + 1, trace);
                    let mut sc_oi = (128 + sc_oi - sc_output_len) & 127;

                    if trace {
                        println!(
                            "Output {}",
                            (0..sc_output_len)
                                .map(|i| if get_bit(&sc_output[..], (sc_oi + i) & 127) {
                                    "1"
                                } else {
                                    "0"
                                })
                                .collect::<String>()
                        );
                    }

                    for _ in 0..sc_output_len {
                        let v = get_bit(&sc_output[..], sc_oi);
                        set_bit(&mut step_mem[..], oi, v);
                        oi = (oi + 1) & 127;
                        sc_oi = (sc_oi + 1) & 127;
                    }
                }
            }
        }

        (step_mem, oi)
    }

    pub fn run_subcircuit(&self, subcircuit: u8, prim_input: &[u8], trace: bool) -> [u8; 128 >> 3] {
        let mut input: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        let sc_info = self.subcircuits[subcircuit as usize];

        for i in 0..(sc_info.input_len as usize) {
            set_bit(&mut input[..], i, get_bit(&prim_input[..], i));
        }
        let mut output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

        let (temp, shift) = self.run_circuit(
            Some(subcircuit as usize),
            &input[..],
            sc_info.input_len as usize,
            1,
            trace,
        );

        let shift = (128 + shift - (sc_info.output_len as usize)) & 127;
        for i in 0..(sc_info.output_len as usize) {
            set_bit(&mut output[..], i, get_bit(&temp[..], (i + shift) & 127));
        }
        if trace {
            println!(
                "Output {}",
                (0..sc_info.output_len as usize)
                    .map(|i| if get_bit(&output[..], i) { "1" } else { "0" })
                    .collect::<String>()
            );
        }
        output
    }

    pub fn run(&self, prim_input: &[u8], trace: bool) -> [u8; 128 >> 3] {
        let mut input: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for i in 0..(self.input_len as usize) {
            set_bit(&mut input[..], i, get_bit(&prim_input[..], i));
        }
        let mut output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        let (temp, shift) = self.run_circuit(None, &input[..], self.input_len as usize, 0, trace);
        let shift = (128 + shift - (self.output_len as usize)) & 127;
        for i in 0..(self.output_len as usize) {
            set_bit(&mut output[..], i, get_bit(&temp[..], (i + shift) & 127));
        }
        if trace {
            println!(
                "Output {}",
                (0..self.output_len as usize)
                    .map(|i| if get_bit(&output[..], i) { "1" } else { "0" })
                    .collect::<String>()
            );
        }
        output
    }

    pub fn push_main(&mut self, i: impl IntoIterator<Item = u8>, input_len: u8, output_len: u8) {
        assert!(self.circuit.is_empty());
        self.circuit.extend(i);
        self.input_len = input_len.try_into().unwrap();
        self.output_len = output_len.try_into().unwrap();
    }

    pub fn push_subcircuit(
        &mut self,
        i: impl IntoIterator<Item = u8>,
        input_len: u8,
        output_len: u8,
    ) {
        assert!(!self.circuit.is_empty());
        let start = self.circuit.len();
        self.circuit.extend(i);
        self.subcircuits.push(SubcircuitInfo {
            location: start,
            input_len,
            output_len,
        });
    }

    pub fn dump(&self, path: impl AsRef<Path>) -> Result<(), DumpError> {
        let mut file = File::create(path)?;
        let main_data = [
            self.input_len,
            self.output_len,
            u8::try_from(self.subcircuits.len())?,
        ];
        file.write_all(main_data.as_slice())?;
        for (i, c) in self.subcircuits.iter().enumerate() {
            if i == 0 {
                let sc_pos = u16::try_from(c.location)?.to_le_bytes();
                let sc_data = [sc_pos[0], sc_pos[1]];
                file.write_all(sc_data.as_slice())?;
            } else {
                let sc_pos = c.location - self.subcircuits[0].location;
                if sc_pos < 128 {
                    let sc_pos = sc_pos.try_into().unwrap();
                    let sc_data = [sc_pos];
                    file.write_all(sc_data.as_slice())?;
                } else {
                    let sc_data = [
                        u8::try_from(sc_pos & 0x7f)? | 0x80,
                        u8::try_from(sc_pos >> 7)?,
                    ];
                    file.write_all(sc_data.as_slice())?;
                }
            }

            if c.input_len <= 8 && c.output_len <= 8 {
                let sc_data = [c.input_len - 1 | ((c.output_len - 1) << 3)];
                file.write_all(sc_data.as_slice())?;
            } else {
                let sc_data = [c.input_len | 0x80, c.output_len];
                file.write_all(sc_data.as_slice())?;
            }
        }
        file.write_all(&self.circuit)?;
        Ok(())
    }
}

pub struct PrimalMachine {
    circuit: Circuit,
    cell_len_bits: u32, // in bits
    address_len: u32,   // in bits
    pub memory: Vec<u8>,
    pub extra_memories: Vec<Vec<u8>>,
    pub machine: Option<Box<SecondMachine>>,
}

pub struct SecondMachine {
    cell_len_bits: u32, // in bits
    address_len: u32,   // in bits
    pub memory: Vec<u8>,
    pub machine: Option<Box<SecondMachine>>,
}

impl PrimalMachine {
    pub fn new(circuit: Circuit, cell_len_bits: u32) -> Self {
        assert!(circuit.output_len > circuit.input_len + 4);
        let address_len = (circuit.output_len - (circuit.input_len) - 3) as u32;
        assert!(cell_len_bits + address_len < usize::BITS + 3);
        assert!((1 << cell_len_bits) <= circuit.input_len);
        assert_eq!(
            circuit.output_len as u32,
            // state len in bits, rest is address_len and special bits
            circuit.input_len as u32 + address_len + 3
        );
        let mem_len = if cell_len_bits + address_len >= 3 {
            1 << (cell_len_bits + address_len - 3)
        } else {
            1
        };
        Self {
            circuit,
            cell_len_bits,
            address_len,
            memory: vec![0; mem_len],
            extra_memories: vec![],
            machine: None,
        }
    }

    pub fn state_len(&self) -> usize {
        self.circuit.input_len as usize - (1 << self.cell_len_bits)
    }

    fn get_cell_mem(&self, cell_index: usize, mut f: impl FnMut(usize, bool)) {
        let index = cell_index << self.cell_len_bits;
        if let Some(machine) = &self.machine {
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mach_cell_len_bits = machine.cell_len_bits as usize;
            let mach_address_len = machine.address_len as usize;
            let align_mach_address_len =
                (mach_address_len + ((1 << cell_len_bits) - 1)) & !((1 << cell_len_bits) - 1);
            let cell_addr = (1 << (address_len + cell_len_bits))
                - align_mach_address_len
                - (1 << mach_cell_len_bits);
            let addr_addr = (1 << (address_len + cell_len_bits)) - align_mach_address_len;
            if (cell_addr..addr_addr).contains(&index) {
                let mut mach_cell_addr = 0usize;
                for i in 0..mach_address_len {
                    mach_cell_addr |= usize::from(get_bit(&self.memory, addr_addr + i)) << i;
                }
                machine.get_cell_mem(
                    mach_cell_addr,
                    f,
                    index - cell_addr,
                    1usize << cell_len_bits,
                );
            } else {
                for (i, x) in (index..index + (1usize << self.cell_len_bits)).enumerate() {
                    f(i, get_bit(&self.memory, x));
                }
            }
        } else {
            for (i, x) in (index..index + (1usize << self.cell_len_bits)).enumerate() {
                f(i, get_bit(&self.memory, x));
            }
        }
    }

    fn set_cell_mem(&mut self, cell_index: usize, mut f: impl FnMut(usize) -> bool) {
        let index = cell_index << self.cell_len_bits;
        if let Some(machine) = &mut self.machine {
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mach_cell_len_bits = machine.cell_len_bits as usize;
            let mach_address_len = machine.address_len as usize;
            let align_mach_address_len =
                (mach_address_len + ((1 << cell_len_bits) - 1)) & !((1 << cell_len_bits) - 1);
            let cell_addr = (1 << (address_len + cell_len_bits))
                - align_mach_address_len
                - (1 << mach_cell_len_bits);
            let addr_addr = (1 << (address_len + cell_len_bits)) - align_mach_address_len;
            if (cell_addr..addr_addr).contains(&index) {
                let mut mach_cell_addr = 0usize;
                for i in 0..mach_address_len {
                    mach_cell_addr |= usize::from(get_bit(&self.memory, addr_addr + i)) << i;
                }
                machine.set_cell_mem(
                    mach_cell_addr,
                    f,
                    index - cell_addr,
                    1usize << cell_len_bits,
                )
            } else {
                for (i, x) in (index..index + (1usize << self.cell_len_bits)).enumerate() {
                    set_bit(&mut self.memory, x, f(i));
                }
            }
        } else {
            for (i, x) in (index..index + (1usize << self.cell_len_bits)).enumerate() {
                set_bit(&mut self.memory, x, f(i));
            }
        }
    }

    // input: [state, mem_value]
    // output: [state, mem_value, mem_rw:1bit, mem_address, create:1bit, stop:1bit]
    pub fn run(&mut self, initial_state: &[u8], trace: bool, circuit_trace: bool) -> u64 {
        let input_len = self.circuit.input_len as usize;
        let output_len = self.circuit.output_len as usize;
        let cell_len = 1 << self.cell_len_bits;
        let address_len = self.address_len as usize;
        assert_eq!(input_len + 1 + address_len + 1 + 1, output_len);
        let state_len = input_len - cell_len;
        assert_eq!(initial_state.len(), (state_len + 7) >> 3);

        let mut step_count = 0u64;
        let mut stop = false;
        let mut input = vec![0; ((input_len + 7) >> 3) as usize];
        for i in 0..state_len {
            set_bit(&mut input, i, get_bit(initial_state, i));
        }
        while !stop {
            // put state into input
            if trace {
                println!(
                    "State {}",
                    (0..state_len)
                        .map(|i| if get_bit(&input[..], i) { "1" } else { "0" })
                        .collect::<String>()
                );
            }
            let output = self.circuit.run(&input, circuit_trace);
            // put back to state
            for i in 0..state_len {
                set_bit(&mut input, i, get_bit(&output, i));
            }

            stop = get_bit(&output, output_len - 1);
            // memory access
            // address
            let mut address = 0;
            for i in 0..address_len {
                address |= usize::from(get_bit(&output, state_len + cell_len + 1 + i)) << i;
            }
            // get mem_rw
            if get_bit(&output, state_len + cell_len) {
                if trace {
                    let mut value = 0;
                    for i in 0..cell_len {
                        value |= usize::from(get_bit(&output, state_len + i)) << i;
                    }
                    println!("Write {:#016x} {:#016x}", address, value);
                }
                // write
                self.set_cell_mem(address, |i| get_bit(&output, state_len + i));
            } else {
                self.get_cell_mem(address, |i, v| set_bit(&mut input, state_len + i, v));
                if trace {
                    let mut value = 0;
                    for i in 0..cell_len {
                        value |= usize::from(get_bit(&input, state_len + i)) << i;
                    }
                    println!("Read {:#016x} {:#016x}", address, value);
                }
            }

            if get_bit(&output, output_len - 2) {
                self.create(trace);
            }

            step_count += 1;
        }
        if trace {
            println!(
                "State {}",
                (0..state_len)
                    .map(|i| if get_bit(&input[..], i) { "1" } else { "0" })
                    .collect::<String>()
            );
        }
        step_count
    }

    pub fn create(&mut self, trace: bool) {
        if let Some(machine) = &mut self.machine {
            machine.create(self.extra_memories.pop(), trace);
        } else {
            // create here
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mut new_address_len: u32 = 0;
            let mut new_cell_len_bits: u32 = 0;

            let addr = (1 << (address_len + cell_len_bits)) - (address_len << 1);
            for i in 0..address_len {
                new_address_len |= u32::from(get_bit(&self.memory, addr + i)) << i;
            }
            let addr = (1 << (address_len + cell_len_bits)) - address_len;
            for i in 0..address_len {
                new_cell_len_bits |= u32::from(get_bit(&self.memory, addr + i)) << i;
            }

            assert!(self.cell_len_bits <= new_cell_len_bits);

            if trace {
                println!(
                    "Create machine with address_len {} and cell_len_bits {}",
                    new_address_len, new_cell_len_bits
                );
            }

            self.machine = Some(Box::new(SecondMachine::new(
                new_address_len,
                new_cell_len_bits,
                self.extra_memories.pop(),
            )));
        }
    }
}

impl SecondMachine {
    pub fn new(address_len: u32, cell_len_bits: u32, initial_memory: Option<Vec<u8>>) -> Self {
        assert!(cell_len_bits + address_len < usize::BITS + 3);
        let mem_len = if cell_len_bits + address_len >= 3 {
            1 << (cell_len_bits + address_len - 3)
        } else {
            1
        };
        Self {
            cell_len_bits,
            address_len,
            memory: initial_memory.unwrap_or(vec![0u8; mem_len]),
            machine: None,
        }
    }

    fn get_cell_mem(
        &self,
        cell_index: usize,
        mut f: impl FnMut(usize, bool),
        pri: usize,
        pclen: usize,
    ) {
        let index = cell_index << self.cell_len_bits;
        if let Some(machine) = &self.machine {
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mach_cell_len_bits = machine.cell_len_bits as usize;
            let mach_address_len = machine.address_len as usize;
            let align_mach_address_len =
                (mach_address_len + ((1 << cell_len_bits) - 1)) & !((1 << cell_len_bits) - 1);
            let cell_addr = (1 << (address_len + cell_len_bits))
                - align_mach_address_len
                - (1 << mach_cell_len_bits);
            let addr_addr = (1 << (address_len + cell_len_bits)) - align_mach_address_len;
            if (cell_addr..addr_addr).contains(&index) {
                let mut mach_cell_addr = 0usize;
                for i in 0..mach_address_len {
                    mach_cell_addr |= usize::from(get_bit(&self.memory, addr_addr + i)) << i;
                }
                machine.get_cell_mem(mach_cell_addr, f, pri + index - cell_addr, pclen);
            } else {
                for (i, x) in (index + pri..index + pri + pclen).enumerate() {
                    f(i, get_bit(&self.memory, x));
                }
            }
        } else {
            for (i, x) in (index + pri..index + pri + pclen).enumerate() {
                f(i, get_bit(&self.memory, x));
            }
        }
    }

    fn set_cell_mem(
        &mut self,
        cell_index: usize,
        mut f: impl FnMut(usize) -> bool,
        pri: usize,
        pclen: usize,
    ) {
        let index = cell_index << self.cell_len_bits;
        if let Some(machine) = &mut self.machine {
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mach_cell_len_bits = machine.cell_len_bits as usize;
            let mach_address_len = machine.address_len as usize;
            let align_mach_address_len =
                (mach_address_len + ((1 << cell_len_bits) - 1)) & !((1 << cell_len_bits) - 1);
            let cell_addr = (1 << (address_len + cell_len_bits))
                - align_mach_address_len
                - (1 << mach_cell_len_bits);
            let addr_addr = (1 << (address_len + cell_len_bits)) - align_mach_address_len;
            if (cell_addr..addr_addr).contains(&index) {
                let mut mach_cell_addr = 0usize;
                for i in 0..mach_address_len {
                    mach_cell_addr |= usize::from(get_bit(&self.memory, addr_addr + i)) << i;
                }
                machine.set_cell_mem(mach_cell_addr, f, pri + index - cell_addr, pclen);
            } else {
                for (i, x) in (index + pri..index + pri + pclen).enumerate() {
                    set_bit(&mut self.memory, x, f(i));
                }
            }
        } else {
            for (i, x) in (index + pri..index + pri + pclen).enumerate() {
                set_bit(&mut self.memory, x, f(i));
            }
        }
    }

    pub fn create(&mut self, initial_memory: Option<Vec<u8>>, trace: bool) {
        if let Some(machine) = &mut self.machine {
            machine.create(initial_memory, trace);
        } else {
            // create here
            let cell_len_bits = self.cell_len_bits as usize;
            let address_len = self.address_len as usize;
            let mut new_address_len: u32 = 0;
            let mut new_cell_len_bits: u32 = 0;

            let addr = (1 << (address_len + cell_len_bits)) - (address_len << 1);
            for i in 0..address_len {
                new_address_len |= u32::from(get_bit(&self.memory, addr + i)) << i;
            }
            let addr = (1 << (address_len + cell_len_bits)) - address_len;
            for i in 0..address_len {
                new_cell_len_bits |= u32::from(get_bit(&self.memory, addr + i)) << i;
            }

            assert!(self.cell_len_bits < new_cell_len_bits);

            if trace {
                println!(
                    "Create machine with address_len {} and cell_len_bits {}",
                    new_address_len, new_cell_len_bits
                );
            }

            self.machine = Some(Box::new(SecondMachine::new(
                new_address_len,
                new_cell_len_bits,
                initial_memory,
            )));
        }
    }
}

pub fn run_test_suite(
    circuit: &CircuitDebug,
    testsuite: impl IntoIterator<Item = TestCase>,
    trace: bool,
) -> bool {
    let mut passed = true;
    let mut passed_count = 0;
    let mut failed_count = 0;
    for (i, tc) in testsuite.into_iter().enumerate() {
        println!("Testcase {}: {}", i, tc.name);

        let mut input: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        let mut exp_output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (i, v) in tc.input.iter().enumerate() {
            set_bit(&mut input[..], i, *v);
        }
        for (i, v) in tc.exp_output.iter().enumerate() {
            set_bit(&mut exp_output[..], i, *v);
        }

        let (output, output_len) = if tc.subcircuit != "main" {
            let sc = circuit.subcircuits[&tc.subcircuit] as usize;
            (
                circuit
                    .circuit
                    .run_subcircuit(sc.try_into().unwrap(), &input[..], trace),
                circuit.circuit.subcircuits[sc].output_len as usize,
            )
        } else {
            (
                circuit.circuit.run(&input[..], trace),
                circuit.circuit.output_len as usize,
            )
        };

        if exp_output != output {
            println!("Testcase {}: {} FAILURE!", i, tc.name);
            println!(
                "  Difference: {}!={}",
                (0..output_len)
                    .map(|i| if get_bit(&exp_output[..], i) {
                        '1'
                    } else {
                        '0'
                    })
                    .collect::<String>(),
                (0..output_len)
                    .map(|i| if get_bit(&output[..], i) { '1' } else { '0' })
                    .collect::<String>()
            );
            passed = false;
            failed_count += 1;
        } else {
            println!("Testcase {}: {} PASSED", i, tc.name);
            passed_count += 1;
        }
    }
    println!(
        "Total passed: {}, Total failed: {}, Total: {}",
        passed_count,
        failed_count,
        passed_count + failed_count
    );
    passed
}
