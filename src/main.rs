use nom::{
    branch::*, bytes::complete as bc, character::complete as cc, combinator::*, error::*, multi::*,
    sequence::*, IResult,
};
use std::collections::HashMap;
use std::fs::read_to_string;
use std::process::ExitCode;

// parser

#[derive(Clone, Debug)]
pub struct Statement {
    output: Vec<String>, // output: output in subcircuit should have name 'oXXX'
    subcircuit: String,  // subcircuit: can be 'nand' or other subcircuit
    input: Vec<String>,  // input of subcircuit should have name 'iXXX
}

#[derive(Clone, Debug)]
pub struct ParsedSubcircuit {
    name: String, // name of subcircuit: if name is main then main circuit
    statements: Vec<Statement>,
}

#[derive(Clone, Debug)]
pub struct ParsedPrimalMachine {
    cell_len_bits: u32,
    address_len: u32,
    circuit: Vec<ParsedSubcircuit>,
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

pub fn empty_or_comment(input: &str) -> VOIResult<()> {
    value(
        (),
        many0_count(alt((
            value(
                (),
                tuple((
                    cc::space0,
                    cc::char('#'),
                    cc::not_line_ending,
                    cc::line_ending,
                )),
            ),
            value((), pair(cc::space0, cc::line_ending)),
        ))),
    )(input)
}

pub fn parse_names(input: &str) -> VOIResult<Vec<String>> {
    map(
        pair(
            preceded(cc::space0, identifier),
            many0(preceded(cc::space1, identifier)),
        ),
        |(x, vec)| {
            let mut out = vec![x.to_string()];
            out.extend(vec.into_iter().map(|x| x.to_string()));
            out
        },
    )(input)
}

pub fn parse_statement(input: &str) -> VOIResult<Statement> {
    context(
        "statement",
        map(
            terminated(
                tuple((
                    parse_names,
                    preceded(tuple((cc::space0, cc::char('='), cc::space0)), identifier),
                    cut(parse_names),
                )),
                cut(pair(cc::space0, cc::line_ending)),
            ),
            |(output, subcircuit, input)| Statement {
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
                    cc::space0,
                    terminated(identifier, cut(pair(cc::space0, cc::char(':')))),
                    pair(cc::space0, cc::line_ending),
                ),
                many0(preceded(empty_or_comment, parse_statement)),
            ),
            |(name, statements)| ParsedSubcircuit {
                name: name.to_string(),
                statements,
            },
        ),
    )(input)
}

pub fn parse_circuit(input: &str) -> VOIResult<Vec<ParsedSubcircuit>> {
    context(
        "circuit",
        many0(preceded(empty_or_comment, parse_subcircuit)),
    )(input)
}

pub fn parse_field_u32<'a>(name: &'a str) -> impl FnMut(&'a str) -> VOIResult<u32> {
    delimited(
        tuple((
            empty_or_comment,
            cc::space0,
            bc::tag("cell_len_bits"),
            cc::space0,
            cc::char(':'),
            cc::space0,
        )),
        cc::u32,
        pair(cc::space0, cc::line_ending),
    )
}

pub fn parse_primal_machine(input: &str) -> VOIResult<ParsedPrimalMachine> {
    context(
        "primal_machine",
        map(
            tuple((
                parse_field_u32("cell_len_bits"),
                parse_field_u32("address_len"),
                many0(preceded(empty_or_comment, parse_subcircuit)),
            )),
            |(cell_len_bits, address_len, circuit)| ParsedPrimalMachine {
                cell_len_bits,
                address_len,
                circuit,
            },
        ),
    )(input)
}

// runtime environment

#[derive(Clone, Debug)]
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

#[derive(thiserror::Error, Debug)]
pub enum ConvertError {
    #[error("No main circuit")]
    NoMainCircuit,
    #[error("Subcircuit {0} duplicated")]
    DuplicatedSubcircuit(String),
    #[error("Subcircuit {0} is empty")]
    EmptySubcircuit(String),
    #[error("Subcircuit {0} doesn't have inputs")]
    NoInputsInSubcircuit(String),
    #[error("Subcircuit {0} doesn't have outputs")]
    NoOutputsInSubcircuit(String),
    #[error("Variable {0} in {1:?} is not available in subcircuit {2}")]
    VariableUnvailableInSubcircuit(String, Statement, String),
    #[error("Used subcircuit {0} is not available in subcircuit {1}")]
    UnknownSubcircuitInSubcircuit(String, String),
    #[error("Subcircuit {0} have wrong names of outputs")]
    WrongLastOutputInSubcircuit(String),
    #[error("Too many inputs in subcircuit {0}")]
    TooManyInputsInSubcircuit(String),
    #[error("Too many outputs in subcircuit {0}")]
    TooManyOutputsInSubcircuit(String),
    #[error("Too many subcircuits")]
    TooManySubcircuits,
    #[error("Wrong input number {0:?} in subcircuit {1}")]
    WrongInputNumberInSubcircuit(Statement, String),
    #[error("Wrong output number {0:?} in subcircuit {1}")]
    WrongOutputNumberInSubcircuit(Statement, String),
    #[error("Parse error of input/output of subcircuit")]
    SubcircuitInputOutputParseError(#[from] std::num::ParseIntError),
}

impl TryFrom<Vec<ParsedSubcircuit>> for Circuit {
    type Error = ConvertError;

    fn try_from(parsed: Vec<ParsedSubcircuit>) -> Result<Self, Self::Error> {
        let mut circuit = Circuit::new();

        let main_number = {
            let main_count = parsed.iter().filter(|subc| subc.name == "main").count();
            if main_count == 0 {
                return Err(ConvertError::NoMainCircuit);
            } else if main_count != 1 {
                return Err(ConvertError::DuplicatedSubcircuit("main".to_string()));
            }
            parsed
                .iter()
                .enumerate()
                .filter(|(i, subc)| subc.name == "main")
                .next()
                .unwrap()
                .0
        };

        for sc in &parsed {
            if sc.statements.is_empty() {
                return Err(ConvertError::EmptySubcircuit(sc.name.clone()));
            }
            if !sc.statements.iter().any(|stmt| {
                stmt.input.iter().any(|input| {
                    input.starts_with("i")
                        && input.len() >= 2
                        && input.chars().skip(1).all(|c| c.is_digit(10))
                })
            }) {
                return Err(ConvertError::NoInputsInSubcircuit(sc.name.clone()));
            }

            if !sc.statements.iter().any(|stmt| {
                stmt.output.iter().any(|output| {
                    output.starts_with("o")
                        && output.len() >= 2
                        && output.chars().skip(1).all(|c| c.is_digit(10))
                })
            }) {
                return Err(ConvertError::NoOutputsInSubcircuit(sc.name.clone()));
            }
        }

        // key - subcircuit name, value - (order in parsed, number in circuit)
        let mut subcircuits = HashMap::<String, (usize, usize)>::new();
        for (k, v) in parsed
            .iter()
            .enumerate()
            .filter(|(_, subc)| subc.name != "main")
            .enumerate()
            .map(|(ci, (i, subc))| (subc.name.clone(), (i, ci)))
        {
            if v.0 >= 128 {
                return Err(ConvertError::TooManySubcircuits);
            }
            if subcircuits.contains_key(&k) {
                return Err(ConvertError::DuplicatedSubcircuit(k.clone()));
            }
            subcircuits.insert(k, v);
        }

        let mut sorted_scs = vec![(main_number, None)];
        sorted_scs.extend(subcircuits.values().map(|(i, ci)| (*i, Some(*ci))));
        sorted_scs[1..].sort_by_key(|(i, ci)| *ci);

        if let Err(e) = parsed
            .iter()
            .map(|sc| {
                sc.statements
                    .iter()
                    .map(|stmt| {
                        stmt.input
                            .iter()
                            .filter(|input| {
                                input.starts_with("i")
                                    && input.len() >= 2
                                    && input.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|input| input[1..].parse::<u8>())
                    })
                    .flatten()
            })
            .flatten()
            .collect::<Result<Vec<_>, _>>()
        {
            return Err(ConvertError::SubcircuitInputOutputParseError(e));
        }

        if let Err(e) = parsed
            .iter()
            .map(|sc| {
                sc.statements
                    .iter()
                    .map(|stmt| {
                        stmt.output
                            .iter()
                            .filter(|output| {
                                output.starts_with("o")
                                    && output.len() >= 2
                                    && output.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|output| output[1..].parse::<u8>())
                    })
                    .flatten()
            })
            .flatten()
            .collect::<Result<Vec<_>, _>>()
        {
            return Err(ConvertError::SubcircuitInputOutputParseError(e));
        }

        let sc_inputs_outputs = parsed
            .iter()
            .map(|sc| {
                let input_count = sc
                    .statements
                    .iter()
                    .map(|stmt| {
                        stmt.input
                            .iter()
                            .filter(|input| {
                                input.starts_with("i")
                                    && input.len() >= 2
                                    && input.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|input| input[1..].parse::<u8>().unwrap())
                    })
                    .flatten()
                    .max()
                    .unwrap()
                    + 1;
                let output_count = sc.statements.last().unwrap().output.last().unwrap()[1..]
                    .parse::<u8>()
                    .unwrap()
                    + 1;
                (input_count, output_count)
            })
            .collect::<Vec<_>>();

        for (i, ci_opt) in sorted_scs {
            let sc = &parsed[i];
            // statements

            let (input_count, output_count) = sc_inputs_outputs[i];

            if input_count >= 128 {
                return Err(ConvertError::TooManyInputsInSubcircuit(sc.name.clone()));
            }
            if output_count >= 128 {
                return Err(ConvertError::TooManyOutputsInSubcircuit(sc.name.clone()));
            }

            if !sc
                .statements
                .iter()
                .map(|stmt| stmt.output.iter())
                .flatten()
                .skip_while(|output| {
                    !(output.starts_with("o")
                        && output.len() >= 2
                        && output.chars().skip(1).all(|c| c.is_digit(10)))
                })
                .enumerate()
                .all(|(i, output)| *output == format!("o{i}"))
            {
                return Err(ConvertError::WrongLastOutputInSubcircuit(sc.name.clone()));
            }

            let mut body: Vec<u8> = vec![];
            let mut var_pos = input_count as usize;
            let mut vars: Vec<String> = (0..input_count)
                .map(|i| format!("i{i}"))
                .chain((input_count..128).map(|_| "".to_string()))
                .collect::<Vec<_>>();
            let mut var_map =
                HashMap::<String, u8>::from_iter((0..input_count).map(|i| (format!("i{i}"), i)));

            for stmt in &sc.statements {
                if stmt.subcircuit.as_str() == "nand" {
                    if stmt.input.len() != 2 {
                        return Err(ConvertError::WrongInputNumberInSubcircuit(
                            stmt.clone(),
                            sc.name.clone(),
                        ));
                    }
                    if stmt.output.len() != 1 {
                        return Err(ConvertError::WrongOutputNumberInSubcircuit(
                            stmt.clone(),
                            sc.name.clone(),
                        ));
                    }
                } else if let Some((sc_i, sc_ci)) = subcircuits.get(&stmt.subcircuit) {
                    if stmt.input.len() != sc_inputs_outputs[*sc_i].0.into() {
                        return Err(ConvertError::WrongInputNumberInSubcircuit(
                            stmt.clone(),
                            sc.name.clone(),
                        ));
                    }
                    if stmt.output.len() != sc_inputs_outputs[*sc_i].1.into() {
                        return Err(ConvertError::WrongOutputNumberInSubcircuit(
                            stmt.clone(),
                            sc.name.clone(),
                        ));
                    }
                    body.push((128 + *sc_ci).try_into().unwrap());
                } else {
                    return Err(ConvertError::UnknownSubcircuitInSubcircuit(
                        stmt.subcircuit.clone(),
                        sc.name.clone(),
                    ));
                }
                // put stmt inputs
                for input in &stmt.input {
                    if let Some(var) = var_map.get(input.as_str()) {
                        body.push(u8::try_from(*var).unwrap());
                    } else {
                        return Err(ConvertError::VariableUnvailableInSubcircuit(
                            input.clone(),
                            stmt.clone(),
                            sc.name.clone(),
                        ));
                    }
                }
                // put stmt outputs
                for output in &stmt.output {
                    if !vars[var_pos].is_empty() {
                        var_map.remove(&vars[var_pos]);
                    }
                    vars[var_pos] = output.clone();
                    var_map.insert(output.clone(), var_pos.try_into().unwrap());
                    var_pos = (var_pos + 1) & 127;
                }
            }

            if let Some(ci) = ci_opt {
                circuit.push_subcircuit(body, input_count, output_count);
            } else {
                circuit.push_main(body, input_count, output_count);
            }
        }

        Ok(circuit)
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

fn simple_circuit() {
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

fn main() -> ExitCode {
    let input = concat!(
        "main:\n",
        "  s0 c0 = full_adder i1 i5 i0\n",
        "  s1 c1 = full_adder i2 i6 c0\n",
        "  s2 c2 = full_adder i3 i7 c1\n",
        "  s3 c3 = full_adder i4 i8 c2\n",
        "  o0 = copy s0\n",
        "  o1 = copy s1\n",
        "  o2 = copy s2\n",
        "  o3 = copy s3\n",
        "  o4 = copy c3\n",
        "copy:\n",
        "  t = nand i0 i0\n",
        "  o0 = nand t t\n",
        "full_adder:\n",
        "  t0 = nand i2 i1\n",
        "  t1 = nand i1 i0\n",
        "  t2 = nand i0 i2\n",
        "  t3 = nand t0 t1\n",
        "  t4 = nand t1 i0\n",
        "  t5 = nand t0 i2\n",
        "  t6 = nand t2 t3\n",
        "  t7 = nand t5 t4\n",
        "  t8 = nand i1 t6\n",
        "  t9 = nand t2 t7\n",
        "  o0 = nand t8 t9\n",
        "  o1 = nand t2 t6\n",
        // "# test simple  \n",
        // "simple  :   \n",
        // "  \n",
        // "  o1 o2 o3 = nand i1 i2 i3  \n",
        // "  # ddd \n",
        // "  ox oy oz = nand ix iy iz  \n",
        // "simple2 :   \n",
        // "  \n",
        // "  zo1 zo2 zo3 = nand zi1 zi2 zi3  \n",
        // "  \n",
        // "  zox zoy zoz = nand zix ziy ziz  \n",
        // "  simple3 :   \n",
        // "  ao1 ao2 ao3 = nand ai1 ai2 ai3  \n",
        // "  aox aoy aoz = nand aix aiy aiz  \n",
        // "# end comment\n",
    );
    match parse_circuit(input) {
        Ok((_, parsed)) => {
            println!("{parsed:?}");
            match Circuit::try_from(parsed) {
                Ok(circuit) => {
                    println!("Circuit: {:?}", circuit);
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("Convert Error: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        Err(e) => {
            match e {
                nom::Err::Error(e) | nom::Err::Failure(e) => {
                    eprintln!("Error: {}", convert_error(input, e))
                }
                e => eprintln!("Error: {}", e),
            }
            ExitCode::FAILURE
        }
    }
}
