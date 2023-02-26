use nom::{
    branch::*, bytes::complete as bc, character::complete as cc, combinator::*, error::*, multi::*,
    sequence::*, IResult,
};

// parser

pub struct Statement {
    output: Vec<String>, // output: output in subcircuit should have name 'oXXX'
    subcircuit: String,  // subcircuit: can be 'nand' or other subcircuit
    input: Vec<String>,  // input of subcircuit should have name 'iXXX
}

pub struct ParsedSubcircuit {
    name: String, // name of subcircuit: if name is main then main circuit
    statements: Vec<Statement>,
}

type VIResult<'a> = IResult<&'a str, &'a str, VerboseError<&'a str>>;
type VOIResult<'a, T> = IResult<&'a str, T, VerboseError<&'a str>>;

fn identifier(input: &str) -> VIResult {
    context(
        "identifier",
        recognize(pair(
            alt((cc::alpha1, bc::tag("_"))),
            many0_count(alt((cc::alphanumeric1, bc::tag("_")))),
        )),
    )(input)
}

pub fn parse_names(input: &str) -> VOIResult<Vec<String>> {
    many0(preceded(
        cc::multispace0,
        map(identifier, |x| x.to_string()),
    ))(input)
}

pub fn parse_statement(input: &str) -> VOIResult<Statement> {
    context(
        "statement",
        map(
            terminated(
                tuple((parse_names, cc::char('='), identifier, parse_names)),
                cut(pair(cc::multispace0, cc::char('\n'))),
            ),
            |(output, _, subcircuit, input)| Statement {
                output,
                subcircuit: subcircuit.to_string(),
                input,
            },
        ),
    )(input)
}

pub fn parse_subcircuit(input: &str) -> VOIResult<ParsedSubcircuit> {
    context(
        "subcircuit",
        map(
            pair(
                delimited(
                    cc::multispace0,
                    identifier,
                    cut(pair(cc::multispace0, cc::char('\n'))),
                ),
                many0(parse_statement),
            ),
            |(name, statements)| ParsedSubcircuit {
                name: name.to_string(),
                statements,
            },
        ),
    )(input)
}
pub fn parse_circuit(input: &str) -> VOIResult<Vec<ParsedSubcircuit>> {
    many0(parse_subcircuit)(input)
}

// runtime environment

pub struct Circuit {
    circuit: Vec<u8>,
    // tuple: start, input len, output len
    subcircuits: Vec<(usize, u8, u8)>,
    input_len: u8,
    output_len: u8,
}

fn get_bit(slice: &[u8], i: usize) -> bool {
    (slice[i >> 3] >> (i & 7)) & 1 != 0
}

fn set_bit(slice: &mut [u8], i: usize, v: bool) {
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
    ) -> ([u8; 128 >> 3], usize) {
        assert!(level < 8);
        assert!(input.len() < 128);
        let mut step_mem: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

        // initialize input
        for i in 0..input_len {
            set_bit(&mut step_mem, i, get_bit(input, i));
        }

        let mut step_index = circuit.map(|x| self.subcircuits[x].0).unwrap_or_default();
        // circuit end: if given - then end at start subcircuit sc+1 or end of whole circuit.
        // if not given: then end starts at start of first subcircuit or  end of whole circuit.
        let circuit_end = circuit
            .map(|x| {
                if x + 1 < self.subcircuits.len() {
                    self.subcircuits[x + 1].0
                } else {
                    self.circuit.len()
                }
            })
            .unwrap_or(if self.subcircuits.is_empty() {
                self.circuit.len()
            } else {
                self.subcircuits[0].0
            });

        let mut oi = input_len; // output index
        while step_index < circuit_end {
            let mut nand_arg1: Option<bool> = None;
            while step_index < circuit_end {
                let lv = self.circuit[step_index];
                println!("Step cell: {} {}: {}", step_index, oi, lv);
                if lv < 128 {
                    // input value
                    let ii = lv as usize;
                    let v = get_bit(&step_mem[..], ii);
                    if let Some(v1) = nand_arg1 {
                        println!("Step: {} {}: {} {} {}", step_index, oi, v1, v, !(v1 & v));
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
                        println!("Step: {} {}: {} {} {}", step_index, oi, v1, true, !v1);
                        set_bit(&mut step_mem[..], oi, !v1);
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
                    }
                    // subcircuit call
                    let sc = (lv - 128) as usize;
                    println!("Call: {} {}: {}", step_index, oi, sc);
                    step_index += 1;
                    let mut sc_input: [u8; 128 >> 3] =
                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

                    let sc_input_len = self.subcircuits[sc].1 as usize;
                    let sc_output_len = self.subcircuits[sc].2 as usize;
                    for i in 0..sc_input_len {
                        let ii = self.circuit[step_index + i] as usize;
                        let v = get_bit(&step_mem[..], ii);
                        println!("Call input: {} {}: {} {}", step_index, oi, i, v);
                        set_bit(&mut sc_input[..], i, v);
                    }
                    step_index += sc_input_len;

                    let (sc_output, sc_oi) =
                        self.run_circuit(Some(sc), &sc_input, sc_input_len, level + 1);
                    let mut sc_oi = (128 + sc_oi - sc_output_len) & 127;

                    for _ in 0..sc_output_len {
                        let v = get_bit(&sc_output[..], sc_oi);
                        println!("Call input: {} {} {}: {}", step_index, oi, sc_oi, v);
                        set_bit(&mut step_mem[..], oi, v);
                        oi = (oi + 1) & 127;
                        sc_oi = (sc_oi + 1) & 127;
                    }
                }
            }
        }

        (step_mem, oi)
    }

    pub fn run(&self, prim_input: &[u8]) -> [u8; 128 >> 3] {
        let mut input: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for i in 0..(self.input_len as usize) {
            set_bit(&mut input[..], i, get_bit(&prim_input[..], i));
        }
        let mut output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        let (temp, shift) = self.run_circuit(None, &input[..], self.input_len as usize, 0);
        let shift = (128 + shift - (self.output_len as usize)) & 127;
        for i in 0..(self.output_len as usize) {
            set_bit(&mut output[..], i, get_bit(&temp[..], (i + shift) & 127));
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
        self.subcircuits.push((start, input_len, output_len));
    }
}

pub struct PrimalMachine {
    circuit: Circuit,
    cell_len_bits: u32, // in bits
    address_len: u32,   // in bits
    pub memory: Vec<u8>,
}

impl PrimalMachine {
    pub fn new(circuit: Circuit, cell_len_bits: u32, address_len: u32) -> Self {
        assert!(cell_len_bits + address_len < usize::BITS + 3);
        let mem_len = if cell_len_bits + address_len >= 3 {
            1 << (cell_len_bits + address_len)
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

    // input: [state, mem_value]
    // output: [state, mem_value, mem_rw:1bit, mem_address, create:1bit, stop:1bit]
}

fn main() {
    let mut circuit = Circuit::new();
    circuit.push_main(
        [
            129, 1, 5, 0, // FullAdder(1,5,0) -> (s=9,c=10)
            129, 2, 6, 10, // FullAdder(2,6,9+1) -> (s=11,c=12)
            129, 3, 7, 12, // FullAdder(3,7,11+1) -> (s=13,c=14)
            129, 4, 8, 14, // FullAdder(4,8,13+1) -> (s=15,c=16)
            128, 9, 128, 11, 128, 13, 128, 15, 128, 16,
        ],
        9,
        5,
    );
    circuit.push_subcircuit([0, 0, 1, 1], 1, 1);
    circuit.push_subcircuit(
        [
            // a0 [0], a1 [1], a2 [2]
            // machine.put_nand(t0 [3], a2 [2], a1 [1]);
            // machine.put_nand(t1 [4], a1 [1], a0 [0]);
            // machine.put_nand(t2 [5], a0 [0], a2 [2]);
            2, 1, 1, 0, 0, 2,
            // a0 [0], a1 [1], a2 [2], t0 [3], t1 [4], t2 [5]
            // machine.put_nand(t3 [6], t0 [3], t1 [4]);
            // machine.put_nand(t4 [7], t1 [4], a0 [0]);
            // machine.put_nand(t5 [8], t0 [3], a2 [2]);
            3, 4, 4, 0, 3, 2,
            // a0 [0], a1 [1], a2 [2], t0 [3], t1 [4], t2 [5], t3 [6], t4 [7], t5 [8]
            // machine.put_nand(t6 [9], t2 [5], t3 [6]);
            // machine.put_nand(t7 [10], t5 [8], t4 [7]);
            5, 6, 8, 7,
            // a0 [0], a1 [1], a2 [2], t0 [3], t1 [4], t2 [5], t3 [6], t4 [7], t5 [8],
            // t6 [9], t7 [10]
            // machine.put_nand(t9 [11], a1 [1], t6 [9]);
            1, 9,
            // a0 [0], a1 [1], a2 [2], t0 [3], t1 [4], t2 [5], t3 [6], t4 [7], t5 [8],
            // t6 [9], t7 [10], t9 [11]
            // machine.put_nand(t10 [12], t2 [5], t7 [10]);
            5, 10,
            // a0 [0], a1 [1], a2 [2], t0 [3], t1 [4], t2 [5], t3 [6], t4 [7], t5 [8],
            // t6 [9], t7 [10], t9 [11], t10 [12]
            // machine.put_nand(r0 [13], t9 [11], t10 [12]);
            // machine.put_nand(t8 [14], t2 [5], t6 [9]);
            11, 12, 5, 9,
        ],
        3,
        2,
    );
    for i in 0..512 {
        println!("-------------");
        let input = [(i & 255) as u8, (i >> 8) as u8];
        let output = circuit.run(&input);
        let sum = output[0];
        let (a, b, c) = ((i >> 1) & 15, (i >> 5) & 15, i & 1);
        assert_eq!((a + b + c) as u8, sum);
        println!("Output: {:04b}+{:04b}+{:04b} : {:05b}", a, b, c, sum);
    }
}
