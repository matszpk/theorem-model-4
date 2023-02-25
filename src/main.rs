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
                            let v = (sc_output[i >> 3] >> (i & 7)) & 1 != 0;
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
            println!("OI {}", oi);
            println!(
                "  OldValues: {:?}",
                (0..16)
                    .map(|i| { format!("{}:{}", i, (next_step_mem[i >> 3] >> (i & 7)) & 1) })
                    .collect::<Vec<_>>()
                    .join(" ")
            );
            println!(
                "  OldValues: {:?}",
                (0..16)
                    .map(|i| { format!("{}:{}", i, (step_mem[i >> 3] >> (i & 7)) & 1) })
                    .collect::<Vec<_>>()
                    .join(" ")
            );
            // copy previous to next step
            for i in 0..128 - oi {
                let v = (step_mem[i >> 3] >> (i & 7)) & 1 != 0;
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
        // machine.put_nand(t0 [0], a2 [2], a1 [1]);
        // machine.put_nand(t1 [1], a1 [1], a0 [0]);
        // machine.put_nand(t2 [2], a0 [0], a2 [2]);
        2, 1, 1, 0, 0, 2, 0xff,
        // a0 [3], a1 [4], a2 [5]
        // machine.put_nand(t3 [0], t0 [0], t1 [1]);
        // machine.put_nand(t4 [1], t1 [1], a0 [3]);
        // machine.put_nand(t5 [2], t0 [0], a2 [5]);
        0, 1, 1, 3, 0, 5, 0xff,
        // t0 [3], t1 [4], t2 [5], a0 [6], a1 [7], a2 [8]
        // machine.put_nand(t6 [0], t2 [5], t3 [0]);
        // machine.put_nand(t7 [1], t5 [2], t4 [1]);
        5, 0, 2, 1, 0xff,
        // t3 [2], t4 [3], t5 [4], t0 [5], t1 [6], t2 [7], a0 [8], a1 [9], a2 [10]
        // machine.put_nand(t8 [0], t2 [7], t6 [0]);
        // machine.put_nand(t9 [1], a1 [9], t6 [0]);
        7, 0, 9, 0, 0xff,
        // t6 [2], t7 [3], t3 [4], t4 [5], t5 [6], t0 [7], t1 [8], t2 [9],
        // a0 [10], a1 [11], a2 [12]
        // machine.put_nand(t10 [0], t2 [9], t7 [3]);
        9, 3, 0xff,
        // t8 [1], t9 [2], t6 [3], t7 [4], t3 [5], t4 [6], t5 [7], t0 [8], t1 [9], t2 [10],
        // a0 [11], a1 [12], a2 [13]
        // machine.put_nand(r0 [0], t9 [2], t10 [0]);
        2,
        0, // t10 [1] t8 [2], t9 [3], t6 [4], t7 [5], t3 [6], t4 [7], t5 [8], t0 [9],
           // t1 [10], t2 [11], a0 [12], a1 [13], a2 [14]
    ]);
    for i in 0..8 {
        println!("-------------");
        println!("Output: {:b}: {:08b}", i, pm.run(&[i])[0].reverse_bits());
    }
}
