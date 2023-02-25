pub struct PrimalMachine {
    pub circuit: Vec<u8>,
    // tuple: start, input len, output len
    pub subcircuits: Vec<(usize, u8, u8)>,
}

impl PrimalMachine {
    pub fn new() -> Self {
        Self {
            circuit: vec![],
            subcircuits: vec![],
        }
    }

    fn run_circuit(&self, circuit: Option<usize>, input: &[u8], level: u8) -> [u8; 128 >> 3] {
        assert!(level < 8);
        assert!(input.len() < 128);
        let mut step_mem: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        let mut next_step_mem: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

        // initialize input
        step_mem[0..input.len()].copy_from_slice(input);

        let mut step_index = circuit.map(|x| self.subcircuits[x].0).unwrap_or_default();
        // circuit end
        let circuit_end = circuit
            .map(|x| {
                if x < self.subcircuits.len() {
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

        while step_index < circuit_end {
            let mut oi = 0; // output index

            let mut nand_arg1: Option<bool> = None;
            while step_index < circuit_end {
                let lv = self.circuit[step_index];
                println!("Step cell: {} {}: {}", step_index, oi, lv);
                if lv < 128 {
                    // input value
                    let ii = lv as usize;
                    let v = (step_mem[ii >> 3] >> (ii & 7)) & 1 != 0;
                    if let Some(v1) = nand_arg1 {
                        println!("Step: {} {}: {} {} {}", step_index, oi, v1, v, !(v1 & v));
                        next_step_mem[oi >> 3] |= u8::from(!(v1 & v)) << (oi & 7);
                        nand_arg1 = None;
                        oi += 1;
                    } else {
                        nand_arg1 = Some(v);
                    }
                    step_index += 1;
                } else {
                    if let Some(v1) = nand_arg1 {
                        // if next argument not found then flush with 1
                        println!(
                            "Step: {} {}: {} {} {}",
                            step_index,
                            oi,
                            v1,
                            true,
                            !(v1 & true)
                        );
                        next_step_mem[oi >> 3] |= u8::from(!(v1 & true)) << (oi & 7);
                        nand_arg1 = None;
                        oi += 1;
                    }
                    if lv < 255 {
                        // subcircuit call
                        let sc = (lv - 128) as usize;
                        let mut sc_input: [u8; 128 >> 3] =
                            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

                        let sc_input_len = self.subcircuits[sc].1 as usize;
                        let sc_output_len = self.subcircuits[sc].2 as usize;
                        for i in 0..sc_input_len {
                            let ii = self.circuit[step_index + i] as usize;
                            let v = (step_mem[ii >> 3] >> (ii & 7)) & 1 != 0;
                            sc_input[i >> 3] |= u8::from(v) << (i & 7);
                        }
                        step_index += sc_input_len;

                        let sc_output = self.run_circuit(Some(sc), &sc_input, level + 1);

                        for i in 0..sc_output_len {
                            let v = sc_output[i >> 3] >> (i & 7) != 0;
                            next_step_mem[(oi + i) >> 3] |= u8::from(v) << ((oi + i) & 7);
                        }

                        oi += sc_output_len;
                    } else {
                        step_index += 1;
                        // 255: end of list
                        break;
                    }
                }
            }
            // copy previous to next step
            for i in 0..128 - oi {
                let v = step_mem[i >> 3] >> (i & 7) != 0;
                next_step_mem[(oi + i) >> 3] |= u8::from(v) << ((oi + i) & 7);
            }

            step_mem = next_step_mem;
            next_step_mem.fill(0);
            println!("Next step");
            println!(
                "  Values: {:?}",
                (0..16)
                    .map(|i| { format!("{}:{}", i, (step_mem[i >> 3] >> (i & 7)) & 1) })
                    .collect::<Vec<_>>()
                    .join(" ")
            );
        }

        step_mem
    }

    pub fn run(&self, input: &[u8]) -> [u8; 128 >> 3] {
        self.run_circuit(None, input, 0)
    }
}

fn main() {
    let mut pm = PrimalMachine::new();
    pm.circuit.extend([
        2, 1, 1, 0, 0, 2, 0xff, 0, 1, 1, 3, 0, 5, 0xff, 5, 0, 2, 1, 0xff, 7, 0, 9, 0, 0xff, 11, 3,
        0xff, 1, 0, 0xff,
    ]);
    for i in 0..8 {
        println!("Output: {:?}", pm.run(&[i]));
    }
}
