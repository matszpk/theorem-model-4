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

        let mut oi = input_len; // output index
        while step_index < circuit_end {
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
                        step_mem[oi >> 3] |= u8::from(!(v1 & v)) << (oi & 7);
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
                        step_mem[oi >> 3] |= u8::from(!(v1 & true)) << (oi & 7);
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
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

                    let (sc_output, sc_oi) =
                        self.run_circuit(Some(sc), &sc_input, sc_input_len, level + 1);
                    let mut sc_oi = (128 + sc_oi - sc_output_len) & 127;

                    for _ in 0..sc_output_len {
                        let v = (sc_output[sc_oi >> 3] >> (sc_oi & 7)) & 1 != 0;
                        step_mem[oi >> 3] |= u8::from(v) << (oi & 7);
                        oi = (oi + 1) & 127;
                        sc_oi = (sc_oi + 1) & 127;
                    }
                }
            }
        }

        (step_mem, oi)
    }

    pub fn run(&self, input: &[u8], input_len: usize) -> ([u8; 128 >> 3], usize) {
        self.run_circuit(None, input, input_len, 0)
    }
}

fn main() {
    let mut pm = PrimalMachine::new();
    pm.circuit.extend([
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
    ]);
    for i in 0..8 {
        println!("-------------");
        let output = pm.run(&[i], 3).0;
        println!(
            "Output: {:03b}: {:08b} {:08b}",
            i,
            output[0].reverse_bits(),
            output[1].reverse_bits(),
        );
    }
}
