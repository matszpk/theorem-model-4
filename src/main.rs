pub mod parser;
use parser::*;
pub mod sim;
use sim::*;
pub mod convert;
use convert::*;

use clap::{Parser, Subcommand};

use nom::error::convert_error;

use std::fs::read_to_string;
use std::io::{self, Read};
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
    testsuite: Option<PathBuf>,
    #[clap(short, long, help = "Set trace mode")]
    trace: bool,
}

#[derive(Parser)]
struct DumpCircuitArgs {
    #[clap(help = "Set circuit filename")]
    circuit: PathBuf,
    #[clap(help = "Set output filename")]
    output: PathBuf,
}

#[derive(Parser)]
struct RunMachineArgs {
    #[clap(help = "Set circuit filename")]
    circuit: PathBuf,
    #[clap(help = "Set machine cell len bits")]
    cell_len_bits: u8,
    #[clap(help = "Initial state")]
    initial_state: String,
    #[clap(help = "Initial memory file")]
    memory: PathBuf,
    #[clap(short, long, help = "Set trace mode")]
    trace: bool,
    #[clap(short, long, help = "Set circuit trace mode")]
    circuit_trace: bool,
    #[clap(short, long, help = "Set memory dump")]
    dump: bool,
}

#[derive(Subcommand)]
enum Commands {
    #[clap(about = "Check cicrcuit file syntax")]
    Check(CheckCircuitArgs),
    #[clap(about = "Run circuit")]
    Run(RunCircuitArgs),
    #[clap(about = "Test circuit")]
    Test(TestCircuitArgs),
    #[clap(about = "Dump circuit into raw file")]
    Dump(DumpCircuitArgs),
    #[clap(about = "Run machine")]
    RunMachine(RunMachineArgs),
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let circuit_file_name = match cli.command {
        Commands::Check(ref r) => r.circuit.clone(),
        Commands::Run(ref r) => r.circuit.clone(),
        Commands::Test(ref r) => r.circuit.clone(),
        Commands::Dump(ref r) => r.circuit.clone(),
        Commands::RunMachine(ref r) => r.circuit.clone(),
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
            println!(
                "Length: {}, Subcircuits: {}",
                circuit.circuit.circuit.len(),
                circuit.circuit.subcircuits.len()
            );
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
            let input = divide_lines(&if let Some(testsuite) = r.testsuite {
                read_to_string(testsuite).unwrap()
            } else {
                let mut out = String::new();
                io::stdin().read_to_string(&mut out).unwrap();
                out
            });
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
        Commands::Dump(r) => {
            if let Err(e) = circuit.circuit.dump(r.output) {
                eprintln!("Error while dumping: {:?}", e);
                return ExitCode::FAILURE;
            }
        }
        Commands::RunMachine(r) => {
            let mut pm = PrimalMachine::new(circuit.circuit, r.cell_len_bits as u32);
            let mem = match std::fs::read(r.memory) {
                Ok(mem) => mem,
                Err(e) => {
                    eprintln!("Error reading memory: {:?}", e);
                    return ExitCode::FAILURE;
                }
            };
            pm.memory.copy_from_slice(mem.as_slice());
            let mut initial_state: [u8; 128 >> 3] =
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
            for (i, c) in r.initial_state.chars().enumerate() {
                set_bit(&mut initial_state[..], i, c == '1');
            }
            let initial_state = &initial_state[0..((pm.state_len() + 7) >> 3)];
            pm.run(initial_state, r.trace, r.circuit_trace);

            if r.dump {
                for (i, chunk) in pm.memory.chunks(16).enumerate() {
                    println!(
                        "{:016x} {}",
                        i * 16,
                        chunk
                            .iter()
                            .map(|x| format!("{x:02x}"))
                            .collect::<Vec<_>>()
                            .join(" ")
                    );
                }
            }
        }
    }

    ExitCode::SUCCESS
}
