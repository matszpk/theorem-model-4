use crate::parser::*;
use crate::sim::*;

use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct CircuitDebug {
    pub circuit: Circuit,
    pub subcircuits: HashMap<String, u8>,
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
                // skip to last outputs as o
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
            let mut vars: Vec<Vec<String>> = (0..128)
                .map(|i| {
                    if i < input_count {
                        vec![format!("i{i}")]
                    } else if i == 127 {
                        vec!["zero".to_string()]
                    } else {
                        vec![]
                    }
                })
                .collect::<Vec<_>>();
            let mut var_map = HashMap::<String, u8>::from_iter(
                vars.iter()
                    .enumerate()
                    .map(|(i, names)| {
                        names
                            .iter()
                            .map(move |name| (name.clone(), i.try_into().unwrap()))
                    })
                    .flatten(),
            );

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
            subcircuits: HashMap::from_iter(
                subcircuits
                    .into_iter()
                    .map(|(k, (_, ci))| (k, ci.try_into().unwrap())),
            ),
        })
    }
}

pub struct PrimalMachineDebug {
    pub machine: PrimalMachine,
    pub subcircuits: HashMap<String, u8>,
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
