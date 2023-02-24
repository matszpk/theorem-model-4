pub struct PrimalMachine {
    circuit: Vec<u8>,
    // tuple: start, input len, output len
    subcircuits: Vec<(usize, u8, u8)>,
}

impl PrimalMachine {
    pub fn new() -> Self {
        Self {
            circuit: vec![],
            subcircuits: vec![],
        }
    }

    fn run_circuit(&self, circuit: Option<usize>, input: &[u8]) -> [u8; 128 >> 3] {
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
            .unwrap_or(self.subcircuits[0].0);

        while step_index < circuit_end {
            let mut oi = 0; // output index

            let mut nand_arg1: Option<bool> = None;
            while step_index < circuit_end {
                let lv = self.circuit[step_index];
                if lv < 128 {
                    // input value
                    let ii = lv as usize;
                    let v = (step_mem[ii >> 3] >> (ii & 7)) & 1 != 0;
                    if let Some(v1) = nand_arg1 {
                        next_step_mem[oi >> 3] |= u8::from(!(v1 & v)) << (oi & 7);
                        nand_arg1 = None;
                        oi += 1;
                    } else {
                        nand_arg1 = Some(v);
                    }
                    step_index += 1;
                } else if lv < 255 {
                    if let Some(v1) = nand_arg1 {
                        // if next argument not found then flush with 1
                        next_step_mem[oi >> 3] |= u8::from(!(v1 & true)) << (oi & 7);
                        nand_arg1 = None;
                        oi += 1;
                    }
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

                    let sc_output = self.run_circuit(Some(sc), &sc_input);

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

            step_mem = next_step_mem;
        }

        step_mem
    }

    pub fn run(&self, input: &[u8]) -> [u8; 128 >> 3] {
        self.run_circuit(None, input)
    }
}

fn main() {
    println!("Hello, world!");
}
