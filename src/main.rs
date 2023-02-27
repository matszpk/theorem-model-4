pub mod parser;
use parser::*;
pub mod sim;
use sim::*;
pub mod convert;
use convert::*;

use nom::error::convert_error;

use std::env;
use std::fs::read_to_string;
use std::process::ExitCode;

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
