use crate::convert::*;
use crate::opt_sim::*;
use crate::parser::*;

use clap::ValueEnum;

use std::fs::File;
use std::io::{self, Read, Write};
use std::path::Path;

// TODO: optimize run of circuit in TheoremModel4.

#[derive(thiserror::Error, Debug)]
pub enum DumpError {
    #[error("IO error: {0}")]
    IO(#[from] io::Error),
    #[error("Numeric error: {0}")]
    Num(#[from] std::num::TryFromIntError),
    #[error("Bad data")]
    Bad,
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
        assert!(input_len <= 128);
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

    pub fn new_from_dump(path: impl AsRef<Path>) -> Result<Circuit, DumpError> {
        let mut file = File::open(path)?;
        let mut main_data: [u8; 3] = [0, 0, 0];
        file.read_exact(main_data.as_mut_slice())?;
        let input_len = main_data[0];
        let output_len = main_data[1];
        let subcircuit_len = main_data[2];
        let mut subcircuits = Vec::<SubcircuitInfo>::new();
        for i in 0..subcircuit_len {
            let sc_location = if i == 0 {
                let mut sc_pos_raw: [u8; 2] = [0, 0];
                file.read_exact(sc_pos_raw.as_mut_slice())?;
                u16::from_le_bytes(sc_pos_raw)
            } else {
                let mut sc_data_raw: [u8; 1] = [0];
                file.read_exact(sc_data_raw.as_mut_slice())?;
                let location: u16 = if sc_data_raw[0] < 128 {
                    sc_data_raw[0] as u16
                } else {
                    let mut sc_data_raw_2: [u8; 1] = [0];
                    file.read_exact(sc_data_raw_2.as_mut_slice())?;
                    ((sc_data_raw[0] & 0x7f) as u16) | ((sc_data_raw_2[0] as u16) << 7)
                };
                location + u16::try_from(subcircuits[0].location).unwrap()
            };

            let mut sc_data_1: [u8; 1] = [0];
            file.read_exact(sc_data_1.as_mut_slice())?;
            let (sc_input_len, sc_output_len) = if sc_data_1[0] < 128 {
                ((sc_data_1[0] & 7) + 1, (sc_data_1[0] >> 3) + 1)
            } else {
                let mut sc_data_2: [u8; 1] = [0];
                file.read_exact(sc_data_2.as_mut_slice())?;
                (sc_data_1[0] & 0x7f, sc_data_2[0])
            };
            subcircuits.push(SubcircuitInfo {
                location: sc_location as usize,
                input_len: sc_input_len,
                output_len: sc_output_len,
            });
        }
        let mut circuit = vec![];
        file.read_to_end(&mut circuit)?;
        Ok(Circuit {
            circuit,
            subcircuits,
            input_len,
            output_len,
        })
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, ValueEnum)]
pub enum RunnerType {
    #[default]
    Normal,
    Optimized,
}

pub struct PrimalMachine {
    circuit: Circuit,
    opt_circuit: Option<OptCircuit>,
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
    pub fn new(circuit: Circuit, cell_len_bits: u32, runner: RunnerType) -> Self {
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
            circuit: circuit.clone(),
            opt_circuit: match runner {
                RunnerType::Normal => None,
                RunnerType::Optimized => Some(OptCircuit::new(circuit.clone(), None)),
            },
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
    // if either create and stop are set - then we have unsatisfied execution.
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
            let output = if let Some(opt_circuit) = self.opt_circuit.as_mut() {
                opt_circuit.run_circuit(&input, input_len)
            } else {
                self.circuit.run(&input, circuit_trace)
            };
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
                if stop {
                    panic!("Unsatisfied execution!");
                }
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
        let mut memory = initial_memory.unwrap_or(vec![0u8; mem_len]);
        memory.resize(mem_len, 0);
        Self {
            cell_len_bits,
            address_len,
            memory,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_set_bit() {
        let bits: [u8; 3] = [0b1010111, 0b110001, 0b0101010];
        assert_eq!(true, get_bit(bits.as_slice(), 2));
        assert_eq!(false, get_bit(bits.as_slice(), 3));
        assert_eq!(true, get_bit(bits.as_slice(), 4));
        assert_eq!(true, get_bit(bits.as_slice(), 8));
        assert_eq!(false, get_bit(bits.as_slice(), 9));
        assert_eq!(true, get_bit(bits.as_slice(), 17));
        assert_eq!(false, get_bit(bits.as_slice(), 18));

        let mut bits: [u8; 3] = [0b1010111, 0b110001, 0b0101010];
        set_bit(bits.as_mut_slice(), 1, false);
        set_bit(bits.as_mut_slice(), 5, true);
        set_bit(bits.as_mut_slice(), 8, false);
        set_bit(bits.as_mut_slice(), 9, true);
        set_bit(bits.as_mut_slice(), 16, true);
        set_bit(bits.as_mut_slice(), 17, false);
        assert_eq!(bits, [0b1110101, 0b110010, 0b0101001]);
    }

    #[test]
    fn test_circuit_run() {
        let circ1 = Circuit {
            circuit: vec![
                0, 0, // not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![],
            input_len: 2,
            output_len: 1,
        };
        for i in 0..4 {
            assert_eq!(circ1.run(&[i], false)[0], ((i >> 1) ^ i) & 1);
        }

        let circ1 = Circuit {
            circuit: vec![
                128, 0, 1, 2, 3, 4, 5, 6, 7, // xor bits
                128, 12, 13, 14, 15, 8, 9, 10, 11, // xor next bits
                129, 0, 4, 129, 1, 5, 129, 2, 6, 129, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 18,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 30,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 12,
            output_len: 4,
        };
        for i in 0..1u16 << 12 {
            assert_eq!(
                circ1.run(&i.to_le_bytes(), false)[0],
                ((i >> 8) ^ ((i >> 4) & 15) ^ (i & 15)).try_into().unwrap()
            );
        }

        let circ1 = Circuit {
            circuit: vec![
                128, 132, 0, 132, 4, // xor bits
                128, 132, 12, 132, 8, // xor next bits
                129, 0, 4, 129, 1, 5, 129, 2, 6, 129, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 10,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 22,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 12,
            output_len: 4,
        };
        for i in 0..1u16 << 12 {
            assert_eq!(
                circ1.run(&i.to_le_bytes(), false)[0],
                ((i >> 8) ^ ((i >> 4) & 15) ^ (i & 15)).try_into().unwrap()
            );
        }
        let circ1 = Circuit {
            circuit: vec![
                128, 132, 0, 132, 4, // xor bits
                128, 132, 9, 196, 8, // xor next bits
                129, 0, 4, 129, 1, 5, 129, 2, 6, 129, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 10,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 22,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 9,
            output_len: 4,
        };
        for i in 0..1u16 << 9 {
            assert_eq!(
                circ1.run(&i.to_le_bytes(), false)[0],
                (((i >> 8) * 15) ^ ((i >> 4) & 15) ^ (i & 15))
                    .try_into()
                    .unwrap()
            );
        }
        // copy
        let circ1 = Circuit {
            circuit: vec![
                128, 132, 4, // copy 4-bits
                129, 132, 0, 132, 4, // xor bits
                129, 132, 12, 132, 8, // xor next bits
                130, 0, 4, 130, 1, 5, 130, 2, 6, 130, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 13,
                    input_len: 4,
                    output_len: 4,
                },
                // xor-4bit
                SubcircuitInfo {
                    location: 13,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 25,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 8,
            output_len: 4,
        };
        for i in 0..=255 {
            assert_eq!(
                circ1.run(&[i], false)[0],
                (((i >> 4) & 15) ^ ((i >> 4) & 15) ^ (i & 15))
            );
        }
        // overlapping output in data
        // circuit:
        //      main:
        //     # pos = 0x8
        //     one = nand zero zero
        //     # pos = 0x9
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:i0 one .7:zero
        //     # pos = 0x11
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x19
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x21
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x29
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x31
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x39
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x41
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x49
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x51
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x59
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x61
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x69
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x71
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x79
        //     x0 x1 x2 x3 = copy_4bit :4:s4
        //     # pos = 0x7d
        //     o0 o1 o2 o3 o4 o5 o6 o7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x5
        // copy:
        //     empty 1
        // copy_4bit:
        //     empty 4
        // xor:
        //     n0 = nand i0 i0
        //     n1 = nand i1 i1
        //     t0 = nand i0 n1
        //     t1 = nand n0 i1
        //     o0 = nand t0 t1
        // full_adder:
        //     s0 = xor i0 i1
        //     a0 = nand i0 i1
        //     a1 = nand s0 i2
        //     o0 = xor s0 i2
        //     # (i0 and i1) or (s0 and i2)
        //     o1 = nand a0 a1
        // # i0 - carry, i1-i4 - 4-bit A, i5-i8 - 4-bit B
        // carry_adder_4bit:
        //     s0 c0 = full_adder i1 i5 i0
        //     s1 c1 = full_adder i2 i6 c0
        //     s2 c2 = full_adder i3 i7 c1
        //     s3 c3 = full_adder i4 i8 c2
        //     o0 o1 o2 o3 = copy_4bit s0 s1 s2 s3
        //     o4 = copy c3
        // adder_8bit:
        //     s0 s1 s2 s3 c4 = carry_adder_4bit zero :4:i0 :4:i8
        //     s4 s5 s6 s7 ign = carry_adder_4bit c4 :4:i4 :4:i12
        //     o0 o1 o2 o3 = copy_4bit :4:s0
        //     o4 o5 o6 o7 = copy_4bit :4:s4
        let circ1 = Circuit {
            circuit: vec![
                0x7f, 0x7f, 0x85, 0x88, 0x00, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x09, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x11, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x19, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x21, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x29, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x31, 0x08,
                0xc7, 0x7f, 0x85, 0x88, 0x39, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x41, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x49, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x51, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x59, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x61, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x69, 0x08,
                0xc7, 0x7f, 0x81, 0x84, 0x75, 0x85, 0x88, 0x71, 0x08, 0xc7, 0x7f, 0x00, 0x00, 0x01,
                0x01, 0x00, 0x03, 0x02, 0x01, 0x04, 0x05, 0x82, 0x00, 0x01, 0x00, 0x01, 0x03, 0x02,
                0x82, 0x03, 0x02, 0x04, 0x05, 0x83, 0x01, 0x05, 0x00, 0x83, 0x02, 0x06, 0x0a, 0x83,
                0x03, 0x07, 0x0c, 0x83, 0x04, 0x08, 0x0e, 0x81, 0x09, 0x0b, 0x0d, 0x0f, 0x80, 0x10,
                0x84, 0x7f, 0x84, 0x00, 0x84, 0x08, 0x84, 0x14, 0x84, 0x04, 0x84, 0x0c, 0x81, 0x84,
                0x10, 0x81, 0x84, 0x15,
            ],
            subcircuits: vec![
                SubcircuitInfo {
                    location: 95,
                    input_len: 1,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 95,
                    input_len: 4,
                    output_len: 4,
                },
                SubcircuitInfo {
                    location: 95,
                    input_len: 2,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 105,
                    input_len: 3,
                    output_len: 2,
                },
                SubcircuitInfo {
                    location: 117,
                    input_len: 9,
                    output_len: 5,
                },
                SubcircuitInfo {
                    location: 140,
                    input_len: 16,
                    output_len: 8,
                },
            ],
            input_len: 8,
            output_len: 8,
        };
        for i in 0..=255 {
            assert_eq!(circ1.run(&[i], false)[0], i.wrapping_add(15));
        }
        // overlapping call input in data
        //     main:
        //     # pos = 0x8
        //     one = nand zero zero
        //     # pos = 0x9
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:i0 one .7:zero
        //     # pos = 0x11
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x19
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x21
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x29
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x31
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x39
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x41
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x49
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x51
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x59
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x61
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x69
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x71
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x79
        //     zero = copy zero
        //     # pos = 0x7a
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x2
        //     o0 o1 o2 o3 o4 o5 o6 o7 = adder_8bit :8:s0 one .7:zero
        // copy:
        //     empty 1
        // copy_4bit:
        //     empty 4
        // xor:
        //     n0 = nand i0 i0
        //     n1 = nand i1 i1
        //     t0 = nand i0 n1
        //     t1 = nand n0 i1
        //     o0 = nand t0 t1
        // full_adder:
        //     s0 = xor i0 i1
        //     a0 = nand i0 i1
        //     a1 = nand s0 i2
        //     o0 = xor s0 i2
        //     # (i0 and i1) or (s0 and i2)
        //     o1 = nand a0 a1
        // # i0 - carry, i1-i4 - 4-bit A, i5-i8 - 4-bit B
        // carry_adder_4bit:
        //     s0 c0 = full_adder i1 i5 i0
        //     s1 c1 = full_adder i2 i6 c0
        //     s2 c2 = full_adder i3 i7 c1
        //     s3 c3 = full_adder i4 i8 c2
        //     o0 o1 o2 o3 = copy_4bit s0 s1 s2 s3
        //     o4 = copy c3
        // adder_8bit:
        //     s0 s1 s2 s3 c4 = carry_adder_4bit zero :4:i0 :4:i8
        //     s4 s5 s6 s7 ign = carry_adder_4bit c4 :4:i4 :4:i12
        //     o0 o1 o2 o3 = copy_4bit :4:s0
        //     o4 o5 o6 o7 = copy_4bit :4:s4
        let circ1 = Circuit {
            circuit: vec![
                0x7f, 0x7f, 0x85, 0x88, 0x00, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x09, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x11, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x19, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x21, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x29, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x31, 0x08,
                0xc7, 0x7f, 0x85, 0x88, 0x39, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x41, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x49, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x51, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x59, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x61, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x69, 0x08,
                0xc7, 0x7f, 0x80, 0x7f, 0x85, 0x88, 0x71, 0x08, 0xc7, 0x79, 0x85, 0x88, 0x7a, 0x08,
                0xc7, 0x79, 0x00, 0x00, 0x01, 0x01, 0x00, 0x03, 0x02, 0x01, 0x04, 0x05, 0x82, 0x00,
                0x01, 0x00, 0x01, 0x03, 0x02, 0x82, 0x03, 0x02, 0x04, 0x05, 0x83, 0x01, 0x05, 0x00,
                0x83, 0x02, 0x06, 0x0a, 0x83, 0x03, 0x07, 0x0c, 0x83, 0x04, 0x08, 0x0e, 0x81, 0x09,
                0x0b, 0x0d, 0x0f, 0x80, 0x10, 0x84, 0x7f, 0x84, 0x00, 0x84, 0x08, 0x84, 0x14, 0x84,
                0x04, 0x84, 0x0c, 0x81, 0x84, 0x10, 0x81, 0x84, 0x15,
            ],
            subcircuits: vec![
                SubcircuitInfo {
                    location: 100,
                    input_len: 1,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 100,
                    input_len: 4,
                    output_len: 4,
                },
                SubcircuitInfo {
                    location: 100,
                    input_len: 2,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 110,
                    input_len: 3,
                    output_len: 2,
                },
                SubcircuitInfo {
                    location: 122,
                    input_len: 9,
                    output_len: 5,
                },
                SubcircuitInfo {
                    location: 145,
                    input_len: 16,
                    output_len: 8,
                },
            ],
            input_len: 8,
            output_len: 8,
        };
        for i in 0..=255 {
            assert_eq!(circ1.run(&[i], false)[0], i.wrapping_add(16));
        }
    }

    fn set_cell_val1(pm: &mut PrimalMachine, addr0: usize, val: u16) {
        for i in 0..4 {
            let v = (val >> (i * 4)) & 0xf;
            pm.set_cell_mem(addr0 + i, |j| ((v >> j) & 1) != 0);
        }
    }

    fn set_cell_val2(pm: &mut PrimalMachine, addr1: usize, val: u32) {
        set_cell_val1(pm, 0xfc, addr1.try_into().unwrap());
        set_cell_val1(pm, 0xf8, (val & 0xffff).try_into().unwrap());
        set_cell_val1(pm, 0xfc, (addr1 + 1).try_into().unwrap());
        set_cell_val1(pm, 0xf8, (val >> 16).try_into().unwrap());
    }

    #[test]
    fn test_get_set_cell_mem() {
        let circ1 = Circuit {
            circuit: vec![
                0, 0, // not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![],
            // define cell_len_bits=2, address_len=8
            input_len: 6,
            output_len: 6 + 3 + 8,
        };
        let mut pm = PrimalMachine::new(circ1, 2);
        pm.set_cell_mem(112, |i| ((11 >> i) & 1) != 0);
        assert_eq!(pm.memory[112 >> 1], 11);
        pm.get_cell_mem(112, |i, v| assert_eq!((11 >> i) & 1 != 0, v));
        pm.set_cell_mem(173, |i| ((5 >> i) & 1) != 0);
        assert_eq!(pm.memory[173 >> 1], 5 << 4);
        pm.get_cell_mem(173, |i, v| assert_eq!((5 >> i) & 1 != 0, v));

        // create new machine: address_len=16, cell_len_bits=4
        set_cell_val1(&mut pm, 0xfc, 0x0410);
        pm.create(true);
        set_cell_val1(&mut pm, 0xfc, 0x2341);
        set_cell_val1(&mut pm, 0xf8, 0xacca);
        let sm = pm.machine.as_mut().unwrap();
        assert_eq!(sm.memory[0x2341 << 1], 0xca);
        assert_eq!(sm.memory[(0x2341 << 1) + 1], 0xac);
        sm.memory[0xd4b7 << 1] = 0x1a;
        sm.memory[(0xd4b7 << 1) + 1] = 0xb5;
        set_cell_val1(&mut pm, 0xfc, 0xd4b7);
        for i in 0..4 {
            let memval = 0xb51a >> (i * 4);
            pm.get_cell_mem(248 + i, |j, v| assert_eq!((memval >> j) & 1 != 0, v));
        }

        // create new second machine: address_len=20, cell_len_bits=5
        set_cell_val1(&mut pm, 0xfc, 0xfffe);
        set_cell_val1(&mut pm, 0xf8, 20);
        set_cell_val1(&mut pm, 0xfc, 0xffff);
        set_cell_val1(&mut pm, 0xf8, 5);
        pm.create(true);

        set_cell_val2(&mut pm, 0xfffe, 0x14523);
        set_cell_val2(&mut pm, 0xfffc, 0x12345678);
        let sm2 = pm.machine.as_mut().unwrap().machine.as_mut().unwrap();
        for (i, v) in [0x78, 0x56, 0x34, 0x12].iter().enumerate() {
            assert_eq!(sm2.memory[(0x14523 << 2) + i], *v);
        }
        set_cell_val1(&mut pm, 0xfc, 0xfffe);
        set_cell_val1(&mut pm, 0xf8, 0x4523);
        set_cell_val1(&mut pm, 0xfc, 0xffff);
        set_cell_val1(&mut pm, 0xf8, 0x1);
        for i in 0..2 {
            set_cell_val1(&mut pm, 0xfc, 0xfffc + i);
            for j in 0..4 {
                let memval = (0x12345678 >> (i * 16)) >> (j * 4);
                pm.get_cell_mem(248 + j, |k, v| assert_eq!((memval >> k) & 1 != 0, v));
            }
        }
    }
}
