pub mod parser;
use parser::*;
pub mod sim;
use sim::*;
pub mod convert;
use convert::*;

use clap::{Parser, Subcommand};

use nom::error::convert_error;

use std::fs::read_to_string;
use std::path::PathBuf;
use std::process::ExitCode;

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
#[clap(propagate_version = true)]
struct Cli {
    #[clap(subcommand)]
    command: Commands,
}

#[derive(Parser)]
struct CheckCircuitArgs {
    #[clap(help = "Set circuit filename")]
    circuit: PathBuf,
}

#[derive(Parser)]
struct RunCircuitArgs {
    #[clap(help = "Set circuit filename")]
    circuit: PathBuf,
    #[clap(help = "Optional subcircuit name")]
    subcircuit: String,
    #[clap(help = "Input string")]
    input: Option<String>,
    #[clap(short, long, help = "Set trace mode")]
    trace: bool,
}

#[derive(Parser)]
struct TestCircuitArgs {
    #[clap(help = "Set circuit filename")]
    circuit: PathBuf,
    #[clap(help = "Set testsuite filename")]
    testsuite: PathBuf,
    #[clap(short, long, help = "Set trace mode")]
    trace: bool,
}

#[derive(Subcommand)]
enum Commands {
    #[clap(about = "Check cicrcuit file syntax")]
    Check(CheckCircuitArgs),
    #[clap(about = "Run circuit")]
    Run(RunCircuitArgs),
    #[clap(about = "Test circuit")]
    Test(TestCircuitArgs),
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let circuit_file_name = match cli.command {
        Commands::Check(ref r) => r.circuit.clone(),
        Commands::Run(ref r) => r.circuit.clone(),
        Commands::Test(ref r) => r.circuit.clone(),
    };

    let input = divide_lines(&read_to_string(circuit_file_name).unwrap());
    let circuit = match parse_circuit_all(&input) {
        Ok((_, parsed)) => match CircuitDebug::try_from(parsed) {
            Ok(circuit) => circuit,
            Err(e) => {
                eprintln!("Convert Error: {}", e);
                return ExitCode::FAILURE;
            }
        },
        Err(e) => {
            match e {
                nom::Err::Error(e) | nom::Err::Failure(e) => {
                    eprintln!("Error: {}", convert_error(input.as_str(), e))
                }
                e => eprintln!("Error: {}", e),
            }
            return ExitCode::FAILURE;
        }
    };

    match cli.command {
        Commands::Check(_) => {
            println!("Ok - Passed.");
        }
        Commands::Run(r) => {
            if let Some(rinput) = r.input {
                if !rinput.chars().all(|c| c == '1' || c == '0') || rinput.len() > 128 {
                    eprintln!("Wrong given input");
                    return ExitCode::FAILURE;
                }
                let mut input: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
                for (i, c) in rinput.chars().enumerate() {
                    set_bit(&mut input[..], i, c == '1');
                }
                let (output, output_len) = if r.subcircuit != "main" {
                    let sc = circuit.subcircuits[&r.subcircuit] as usize;
                    (
                        circuit
                            .circuit
                            .run_subcircuit(sc.try_into().unwrap(), &input[..], r.trace),
                        circuit.circuit.subcircuits[sc].output_len,
                    )
                } else {
                    (
                        circuit.circuit.run(&input[..], r.trace),
                        circuit.circuit.output_len,
                    )
                };
                println!(
                    "Output: {}",
                    (0..output_len as usize)
                        .map(|i| if get_bit(&output[..], i) { "1" } else { "0" })
                        .collect::<String>()
                );
            } else {
                let input_len = if r.subcircuit != "main" {
                    let sc = circuit.subcircuits[&r.subcircuit] as usize;
                    circuit.circuit.subcircuits[sc].input_len
                } else {
                    circuit.circuit.input_len
                };

                for v in 0..(1u128 << input_len) {
                    let mut input: [u8; 128 >> 3] =
                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
                    for i in 0..(input_len as usize) {
                        set_bit(&mut input[..], i, ((v >> i) & 1) != 0);
                    }

                    let (output, output_len) = if r.subcircuit != "main" {
                        let sc = circuit.subcircuits[&r.subcircuit] as usize;
                        (
                            circuit.circuit.run_subcircuit(
                                sc.try_into().unwrap(),
                                &input[..],
                                r.trace,
                            ),
                            circuit.circuit.subcircuits[sc].output_len,
                        )
                    } else {
                        (
                            circuit.circuit.run(&input[..], r.trace),
                            circuit.circuit.output_len,
                        )
                    };

                    println!(
                        "Entry: {}: {}",
                        (0..input_len as usize)
                            .map(|i| if get_bit(&input[..], i) { "1" } else { "0" })
                            .collect::<String>(),
                        (0..output_len as usize)
                            .map(|i| if get_bit(&output[..], i) { "1" } else { "0" })
                            .collect::<String>()
                    );
                }
            }
        }
        Commands::Test(r) => {
            let input = divide_lines(&read_to_string(r.testsuite).unwrap());
            match parse_test_suite(&input) {
                Ok((_, test_suite)) => {
                    if !run_test_suite(&circuit, test_suite, r.trace) {
                        return ExitCode::FAILURE;
                    }
                }
                Err(e) => {
                    match e {
                        nom::Err::Error(e) | nom::Err::Failure(e) => {
                            eprintln!("Error: {}", convert_error(input.as_str(), e))
                        }
                        e => eprintln!("Error: {}", e),
                    }
                    return ExitCode::FAILURE;
                }
            }
        }
    };

    ExitCode::SUCCESS
}
