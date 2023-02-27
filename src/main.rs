use nom::{
    branch::*, bytes::complete as bc, character::complete as cc, combinator::*, error::*, multi::*,
    sequence::*, IResult,
};
use std::collections::HashMap;
use std::env;
use std::fs::read_to_string;
use std::process::ExitCode;

// parser

#[derive(Clone, Debug)]
pub enum Statement {
    Statement {
        output: Vec<String>, // output: output in subcircuit should have name 'oXXX'
        subcircuit: String,  // subcircuit: can be 'nand' or other subcircuit
        input: Vec<String>,  // input of subcircuit should have name 'iXXX
    },
    Alias {
        new_name: String,
        name: String,
    },
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
        terminated(
            alt((
                map(
                    tuple((
                        preceded(
                            tuple((cc::space0, bc::tag("alias"), cc::space0)),
                            identifier,
                        ),
                        preceded(cc::space0, identifier),
                    )),
                    |(new_name, name)| Statement::Alias {
                        new_name: new_name.to_string(),
                        name: name.to_string(),
                    },
                ),
                map(
                    tuple((
                        parse_names,
                        preceded(tuple((cc::space0, cc::char('='), cc::space0)), identifier),
                        cut(parse_names),
                    )),
                    |(output, subcircuit, input)| Statement::Statement {
                        output,
                        subcircuit: subcircuit.to_string(),
                        input,
                    },
                ),
            )),
            cut(pair(cc::space0, cc::line_ending)),
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
            bc::tag(name),
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
#[derive(Clone, Copy, Debug)]
struct SubcircuitInfo {
    location: usize,
    input_len: u8,
    output_len: u8,
}

#[derive(Clone, Debug)]
pub struct Circuit {
    circuit: Vec<u8>,
    // tuple: start, input len, output len
    subcircuits: Vec<SubcircuitInfo>,
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

                    let sc_input_len = self.subcircuits[sc].input_len as usize;
                    let sc_output_len = self.subcircuits[sc].output_len as usize;
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
        self.subcircuits.push(SubcircuitInfo {
            location: start,
            input_len,
            output_len,
        });
    }
}

#[derive(Clone, Debug)]
pub struct CircuitDebug {
    circuit: Circuit,
    subcircuits: HashMap<String, usize>,
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
    #[error("Unknown variable {0} in alias in subcircuit {1}")]
    UnknownVariableInAlias(String, String),
}

impl TryFrom<Vec<ParsedSubcircuit>> for CircuitDebug {
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
                .filter(|(_, subc)| subc.name == "main")
                .next()
                .unwrap()
                .0
        };

        for sc in &parsed {
            if sc.statements.is_empty() {
                return Err(ConvertError::EmptySubcircuit(sc.name.clone()));
            }
            // check whether all subcircuits have any inputs
            if !sc.statements.iter().any(|stmt| match stmt {
                Statement::Statement { input: inputs, .. } => inputs.iter().any(|input| {
                    input.starts_with("i")
                        && input.len() >= 2
                        && input.chars().skip(1).all(|c| c.is_digit(10))
                }),
                Statement::Alias { name: input, .. } => {
                    input.starts_with("i")
                        && input.len() >= 2
                        && input.chars().skip(1).all(|c| c.is_digit(10))
                }
            }) {
                return Err(ConvertError::NoInputsInSubcircuit(sc.name.clone()));
            }

            // check whether all subcircuits have any outputs
            if !sc.statements.iter().any(|stmt| match stmt {
                Statement::Statement {
                    output: outputs, ..
                } => outputs.iter().any(|output| {
                    output.starts_with("o")
                        && output.len() >= 2
                        && output.chars().skip(1).all(|c| c.is_digit(10))
                }),
                _ => false,
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
        sorted_scs[1..].sort_by_key(|(_, ci)| *ci);

        // check whether all subcircuits have parseable inputs (in form: 'iXXX')
        if let Err(e) = parsed
            .iter()
            .map(|sc| {
                sc.statements
                    .iter()
                    .map(|stmt| match stmt {
                        Statement::Statement { input: inputs, .. } => inputs
                            .iter()
                            .filter(|input| {
                                input.starts_with("i")
                                    && input.len() >= 2
                                    && input.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|input| input[1..].parse::<u8>())
                            .collect::<Vec<_>>(),
                        Statement::Alias { name: input, .. } => {
                            if input.starts_with("i")
                                && input.len() >= 2
                                && input.chars().skip(1).all(|c| c.is_digit(10))
                            {
                                vec![input[1..].parse::<u8>()]
                            } else {
                                vec![]
                            }
                        }
                    })
                    .flatten()
            })
            .flatten()
            .collect::<Result<Vec<_>, _>>()
        {
            return Err(ConvertError::SubcircuitInputOutputParseError(e));
        }

        // check whether all subcircuits have parseable outputs (in form: 'oXXX')
        if let Err(e) = parsed
            .iter()
            .map(|sc| {
                sc.statements
                    .iter()
                    .map(|stmt| match stmt {
                        Statement::Statement {
                            output: outputs, ..
                        } => outputs
                            .iter()
                            .filter(|output| {
                                output.starts_with("o")
                                    && output.len() >= 2
                                    && output.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|output| output[1..].parse::<u8>())
                            .collect::<Vec<_>>(),
                        _ => vec![],
                    })
                    .flatten()
            })
            .flatten()
            .collect::<Result<Vec<_>, _>>()
        {
            return Err(ConvertError::SubcircuitInputOutputParseError(e));
        }

        // collect number of inputs and number of outputs for all subcircuits (including main).
        let sc_inputs_outputs = parsed
            .iter()
            .map(|sc| {
                // get number of inputs through parsing number from inputs in form 'iXX'
                let input_count = sc
                    .statements
                    .iter()
                    .map(|stmt| match stmt {
                        Statement::Statement { input: inputs, .. } => inputs
                            .iter()
                            .filter(|input| {
                                input.starts_with("i")
                                    && input.len() >= 2
                                    && input.chars().skip(1).all(|c| c.is_digit(10))
                            })
                            .map(|input| input[1..].parse::<u8>().unwrap())
                            .collect::<Vec<_>>(),
                        Statement::Alias { name: input, .. } => {
                            if input.starts_with("i")
                                && input.len() >= 2
                                && input.chars().skip(1).all(|c| c.is_digit(10))
                            {
                                vec![input[1..].parse::<u8>().unwrap()]
                            } else {
                                vec![]
                            }
                        }
                    })
                    .flatten()
                    .max()
                    .unwrap()
                    + 1;
                // get number of outputs by getting last output name in last statement.
                let output_count = sc
                    .statements
                    .iter()
                    .rev()
                    .find_map(|stmt| match stmt {
                        Statement::Statement { output, .. } => Some(output),
                        _ => None,
                    })
                    .unwrap()
                    .last()
                    .unwrap()[1..]
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

            let tmp = vec![];
            // check whether all outputs is in correct order.
            if !sc
                .statements
                .iter()
                .map(|stmt| match stmt {
                    Statement::Statement {
                        output: outputs, ..
                    } => outputs.iter(),
                    _ => tmp.iter(),
                })
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
            let mut vars: Vec<Vec<String>> = (0..input_count)
                .map(|i| vec![format!("i{i}")])
                .chain((input_count..128).map(|_| vec!["".to_string()]))
                .collect::<Vec<_>>();
            let mut var_map =
                HashMap::<String, u8>::from_iter((0..input_count).map(|i| (format!("i{i}"), i)));

            for stmt in &sc.statements {
                match stmt {
                    Statement::Statement {
                        input: inputs,
                        output: outputs,
                        subcircuit,
                    } => {
                        if subcircuit.as_str() == "nand" {
                            if inputs.len() != 2 {
                                return Err(ConvertError::WrongInputNumberInSubcircuit(
                                    stmt.clone(),
                                    sc.name.clone(),
                                ));
                            }
                            if outputs.len() != 1 {
                                return Err(ConvertError::WrongOutputNumberInSubcircuit(
                                    stmt.clone(),
                                    sc.name.clone(),
                                ));
                            }
                        } else if let Some((sc_i, sc_ci)) = subcircuits.get(subcircuit) {
                            if inputs.len() != sc_inputs_outputs[*sc_i].0.into() {
                                return Err(ConvertError::WrongInputNumberInSubcircuit(
                                    stmt.clone(),
                                    sc.name.clone(),
                                ));
                            }
                            if outputs.len() != sc_inputs_outputs[*sc_i].1.into() {
                                return Err(ConvertError::WrongOutputNumberInSubcircuit(
                                    stmt.clone(),
                                    sc.name.clone(),
                                ));
                            }
                            body.push((128 + *sc_ci).try_into().unwrap());
                        } else {
                            return Err(ConvertError::UnknownSubcircuitInSubcircuit(
                                subcircuit.clone(),
                                sc.name.clone(),
                            ));
                        }
                        // put stmt inputs
                        for input in inputs {
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
                        for output in outputs {
                            if !vars[var_pos].is_empty() {
                                for var_name in &vars[var_pos] {
                                    var_map.remove(var_name);
                                }
                            }
                            vars[var_pos].push(output.clone());
                            var_map.insert(output.clone(), var_pos.try_into().unwrap());
                            var_pos = (var_pos + 1) & 127;
                        }
                    }
                    Statement::Alias { new_name, name } => {
                        if let Some(var_pos) = var_map.get(name) {
                            let var_pos = *var_pos as usize;
                            vars[var_pos].push(new_name.clone());
                            var_map.insert(new_name.clone(), var_pos.try_into().unwrap());
                        } else {
                            return Err(ConvertError::UnknownVariableInAlias(
                                name.clone(),
                                sc.name.clone(),
                            ));
                        }
                    }
                }
            }

            if let Some(ci) = ci_opt {
                assert_eq!(ci, circuit.subcircuits.len());
                circuit.push_subcircuit(body, input_count, output_count);
            } else {
                circuit.push_main(body, input_count, output_count);
            }
        }

        Ok(CircuitDebug {
            circuit,
            subcircuits: HashMap::from_iter(subcircuits.into_iter().map(|(k, (_, ci))| (k, ci))),
        })
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
        assert!((1 << cell_len_bits) <= circuit.input_len);
        assert_eq!(
            circuit.output_len as u32,
            // state len in bits, rest is address_len and special bits
            (circuit.input_len - (1 << cell_len_bits)) as u32 + address_len + 3
        );
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

pub struct PrimalMachineDebug {
    machine: PrimalMachine,
    subcircuits: HashMap<String, usize>,
}

impl TryFrom<ParsedPrimalMachine> for PrimalMachineDebug {
    type Error = ConvertError;

    fn try_from(parsed: ParsedPrimalMachine) -> Result<Self, Self::Error> {
        let cd = CircuitDebug::try_from(parsed.circuit)?;
        Ok(PrimalMachineDebug {
            machine: PrimalMachine::new(cd.circuit, parsed.cell_len_bits, parsed.address_len),
            subcircuits: cd.subcircuits,
        })
    }
}

fn main() -> ExitCode {
    let mut args = env::args();
    args.next().unwrap();
    let input = read_to_string(&args.next().unwrap()).unwrap();

    match parse_circuit(&input) {
        Ok((_, parsed)) => {
            println!("{parsed:?}");
            match CircuitDebug::try_from(parsed) {
                Ok(circuit) => {
                    println!("Circuit: {:?}", circuit.circuit);
                    println!("Subcircuit: {:?}", circuit.subcircuits);
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
                    eprintln!("Error: {}", convert_error(input.as_str(), e))
                }
                e => eprintln!("Error: {}", e),
            }
            ExitCode::FAILURE
        }
    }
}
