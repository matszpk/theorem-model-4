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
                            } else {
                                // repeat input: 128+rep_count base_output
                                // repeats: base_output + i
                                let rep_count = std::cmp::min(ii - 128, sc_input_len - i);
                                step_index += 1;
                                if step_index < circuit_end {
                                    let ii = self.circuit[step_index] as usize;
                                    step_index += 1;
                                    for j in 0..rep_count {
                                        let v = get_bit(&step_mem[..], (ii + j) & 127);
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
        for c in &self.subcircuits {
            let sc_pos = u16::try_from(c.location)?.to_le_bytes();
            let sc_data = [sc_pos[0], sc_pos[1], c.input_len, c.output_len];
            file.write_all(sc_data.as_slice())?;
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
        }
    }

    pub fn state_len(&self) -> usize {
        self.circuit.input_len as usize - (1 << self.cell_len_bits)
    }

    // input: [state, mem_value]
    // output: [state, mem_value, mem_rw:1bit, mem_address, create:1bit, stop:1bit]
    pub fn run(&mut self, initial_state: &[u8], trace: bool, circuit_trace: bool) {
        let input_len = self.circuit.input_len as usize;
        let output_len = self.circuit.output_len as usize;
        let cell_len = 1 << self.cell_len_bits;
        let address_len = self.address_len as usize;
        assert_eq!(input_len + 1 + address_len + 1 + 1, output_len);
        let state_len = input_len - cell_len;
        assert_eq!(initial_state.len(), (state_len + 7) >> 3);

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
                for i in 0..cell_len {
                    set_bit(
                        &mut self.memory,
                        (address << self.cell_len_bits) + i,
                        get_bit(&output, state_len + i),
                    );
                }
            } else {
                for i in 0..cell_len {
                    set_bit(
                        &mut input,
                        state_len + i,
                        get_bit(&self.memory, (address << self.cell_len_bits) + i),
                    );
                }
                if trace {
                    let mut value = 0;
                    for i in 0..cell_len {
                        value |= usize::from(get_bit(&input, state_len + i)) << i;
                    }
                    println!("Read {:#016x} {:#016x}", address, value);
                }
            }
            stop = get_bit(&output, output_len - 1);
        }
        if trace {
            println!(
                "State {}",
                (0..state_len)
                    .map(|i| if get_bit(&input[..], i) { "1" } else { "0" })
                    .collect::<String>()
            );
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
