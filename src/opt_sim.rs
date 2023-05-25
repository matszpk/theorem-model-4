use crate::sim::*;
use std::cmp::min;

#[derive(Clone, Debug, PartialEq)]
pub struct OptCircuit {
    pub circuit: Vec<(u32, u32)>,
    pub input_len: u8,
    pub outputs: Vec<u32>,
}

impl OptCircuit {
    pub fn new(circuit: Circuit, sc_index: Option<usize>) -> Self {
        let (input_len, output_len) = sc_index
            .map(|x| {
                (
                    circuit.subcircuits[x].input_len,
                    circuit.subcircuits[x].output_len,
                )
            })
            .unwrap_or((circuit.input_len, circuit.output_len));
        let mut new_circuit = Self {
            circuit: vec![],
            input_len,
            outputs: vec![0; output_len.into()],
        };
        let input = (0..input_len)
            .map(|x| u32::try_from(x).unwrap())
            .collect::<Vec<_>>();
        let (output, oi) =
            new_circuit.create_circuit(&circuit, sc_index, &input, input_len as usize, 0);
        let shift = (128 + oi - output_len as usize) & 127;
        new_circuit.outputs = (0..output_len)
            .map(|x| output[(shift + x as usize) & 127])
            .collect::<Vec<_>>();
        new_circuit
    }

    fn create_circuit(
        &mut self,
        circ_object: &Circuit,
        circuit: Option<usize>,
        input: &[u32],
        input_len: usize,
        level: u8,
    ) -> (Vec<u32>, usize) {
        assert!(level < 8);
        assert!(input_len <= 128);
        // input_len value is zero in memory
        let mut step_mem: Vec<u32> = vec![self.input_len as u32; 128];

        // initialize input
        step_mem[0..input_len].copy_from_slice(&input[0..input_len]);
        let base = (self.input_len as u32) + 1;

        let mut step_index = circuit
            .map(|x| circ_object.subcircuits[x].location)
            .unwrap_or_default();
        // circuit end: if given - then end at start subcircuit sc+1 or end of whole circuit.
        // if not given: then end starts at start of first subcircuit or  end of whole circuit.
        let circuit_end = circuit
            .map(|x| {
                if x + 1 < circ_object.subcircuits.len() {
                    circ_object.subcircuits[x + 1].location
                } else {
                    circ_object.circuit.len()
                }
            })
            .unwrap_or(if circ_object.subcircuits.is_empty() {
                circ_object.circuit.len()
            } else {
                circ_object.subcircuits[0].location
            });

        let mut oi = input_len; // output index
        while step_index < circuit_end {
            let mut nand_arg1: Option<u32> = None;
            while step_index < circuit_end {
                let lv = circ_object.circuit[step_index];
                if lv < 128 {
                    // input value
                    let ii = lv as usize;
                    let v = step_mem[ii];
                    if let Some(v1) = nand_arg1 {
                        step_mem[oi] = base + u32::try_from(self.circuit.len()).unwrap();
                        self.circuit.push((v1, v));
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
                    } else {
                        nand_arg1 = Some(v);
                    }
                    step_index += 1;
                } else {
                    if let Some(v1) = nand_arg1 {
                        // if next argument not found then flush with 1
                        step_mem[oi] = base + u32::try_from(self.circuit.len()).unwrap();
                        self.circuit.push((v1, v1));
                        nand_arg1 = None;
                        oi = (oi + 1) & 127;
                    }
                    // subcircuit call
                    let sc = (lv - 128) as usize;
                    step_index += 1;
                    let mut sc_input = vec![self.input_len as u32; 128];

                    let sc_input_len = circ_object.subcircuits[sc].input_len as usize;
                    let sc_output_len = circ_object.subcircuits[sc].output_len as usize;
                    {
                        let mut i = 0;
                        while i < sc_input_len {
                            let ii = circ_object.circuit[step_index] as usize;
                            if ii < 128 {
                                sc_input[i] = step_mem[ii];
                                i += 1;
                                step_index += 1;
                            } else if ii >= 128 {
                                // repeat input: 128+rep_count base_output
                                // repeats: base_output + i
                                let inc = usize::from(ii < 192);
                                let rep_count = std::cmp::min(ii & 0x3f, sc_input_len - i);
                                step_index += 1;
                                if step_index < circuit_end {
                                    let ii = circ_object.circuit[step_index] as usize;
                                    step_index += 1;
                                    for j in 0..rep_count {
                                        sc_input[i + j] = step_mem[(ii + j * inc) & 127];
                                    }
                                    i += rep_count;
                                }
                            }
                        }
                    }

                    let (sc_output, sc_oi) = self.create_circuit(
                        circ_object,
                        Some(sc),
                        &sc_input,
                        sc_input_len,
                        level + 1,
                    );
                    let mut sc_oi = (128 + sc_oi - sc_output_len) & 127;

                    for _ in 0..sc_output_len {
                        step_mem[oi] = sc_output[sc_oi];
                        oi = (oi + 1) & 127;
                        sc_oi = (sc_oi + 1) & 127;
                    }
                }
            }
        }

        (step_mem, oi)
    }

    pub fn run_circuit(&self, input: &[u8], input_len: usize) -> [u8; 128 >> 3] {
        let circ_input_len = self.input_len as usize;
        let mut memory = vec![0; (self.circuit.len() + circ_input_len + 1 + 7) >> 3];
        let input_len = min(circ_input_len, input_len);
        memory[0..(input_len + 7) >> 3].copy_from_slice(&input[0..(input_len + 7) >> 3]);
        if input_len & 7 != 0 {
            memory[input_len >> 3] &= ((1u16 << (input_len & 7)) - 1) as u8;
        }
        let base = circ_input_len + 1;
        for (i, (igi1, igi2)) in self.circuit.iter().enumerate() {
            let (gi1, gi2) = (*igi1 as usize, *igi2 as usize);
            let b1 = memory[gi1 >> 3] >> (gi1 & 7);
            let b2 = memory[gi2 >> 3] >> (gi2 & 7);
            let out_idx = base + i;
            let out_bit = out_idx & 7;
            let out = ((!(b1 & b2)) & 1) << out_bit;
            memory[out_idx >> 3] = (memory[out_idx >> 3] & !(1u8 << out_bit)) | out;
        }
        let mut final_output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (i, idx) in self.outputs.iter().enumerate() {
            let idx = *idx as usize;
            final_output[i >> 3] |= ((memory[idx >> 3] >> (idx & 7)) & 1) << (i & 7);
        }
        final_output
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_run_circuit() {
        let circ1 = Circuit {
            circuit: vec![
                0, 0, // not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![],
            input_len: 2,
            output_len: 1,
        };
        let opt_circ1 = OptCircuit::new(circ1.clone(), None);
        assert_eq!(
            OptCircuit {
                circuit: vec![(0, 0), (1, 1), (0, 4), (3, 1), (5, 6)],
                input_len: 2,
                outputs: vec![7]
            },
            opt_circ1
        );
        for i in 0..4 {
            let input = [i];
            let output1 = circ1.run(&input, false);
            let output2 = opt_circ1.run_circuit(&input, 2);
            assert_eq!(output1, output2, "xor0 {}", i);
        }

        let circ1 = Circuit {
            circuit: vec![
                128, 0, 1, 2, 3, 4, 5, 6, 7, // xor bits
                128, 12, 13, 14, 15, 8, 9, 10, 11, // xor next bits
                129, 0, 4, 129, 1, 5, 129, 2, 6, 129, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 18,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 30,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 12,
            output_len: 4,
        };
        let opt_circ1 = OptCircuit::new(circ1.clone(), None);
        assert_eq!(
            OptCircuit {
                circuit: vec![
                    (0, 0),
                    (4, 4),
                    (0, 14),
                    (13, 4),
                    (15, 16),
                    (1, 1),
                    (5, 5),
                    (1, 19),
                    (18, 5),
                    (20, 21),
                    (2, 2),
                    (6, 6),
                    (2, 24),
                    (23, 6),
                    (25, 26),
                    (3, 3),
                    (7, 7),
                    (3, 29),
                    (28, 7),
                    (30, 31),
                    (17, 17),
                    (8, 8),
                    (17, 34),
                    (33, 8),
                    (35, 36),
                    (22, 22),
                    (9, 9),
                    (22, 39),
                    (38, 9),
                    (40, 41),
                    (27, 27),
                    (10, 10),
                    (27, 44),
                    (43, 10),
                    (45, 46),
                    (32, 32),
                    (11, 11),
                    (32, 49),
                    (48, 11),
                    (50, 51)
                ],
                input_len: 12,
                outputs: vec![37, 42, 47, 52]
            },
            opt_circ1
        );
        for i in 0..1 << 12 {
            let input = [(i & 0xff).try_into().unwrap(), (i >> 4).try_into().unwrap()];
            let output1 = circ1.run(&input, false);
            let output2 = opt_circ1.run_circuit(&input, 12);
            assert_eq!(output1, output2, "xor1 {}", i);
        }

        let circ1 = Circuit {
            circuit: vec![
                128, 132, 0, 132, 4, // xor bits
                128, 132, 9, 196, 8, // xor next bits
                129, 0, 4, 129, 1, 5, 129, 2, 6, 129, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 10,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 22,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 9,
            output_len: 4,
        };
        let opt_circ1 = OptCircuit::new(circ1.clone(), None);
        assert_eq!(
            OptCircuit {
                circuit: vec![
                    (0, 0),
                    (4, 4),
                    (0, 11),
                    (10, 4),
                    (12, 13),
                    (1, 1),
                    (5, 5),
                    (1, 16),
                    (15, 5),
                    (17, 18),
                    (2, 2),
                    (6, 6),
                    (2, 21),
                    (20, 6),
                    (22, 23),
                    (3, 3),
                    (7, 7),
                    (3, 26),
                    (25, 7),
                    (27, 28),
                    (14, 14),
                    (8, 8),
                    (14, 31),
                    (30, 8),
                    (32, 33),
                    (19, 19),
                    (8, 8),
                    (19, 36),
                    (35, 8),
                    (37, 38),
                    (24, 24),
                    (8, 8),
                    (24, 41),
                    (40, 8),
                    (42, 43),
                    (29, 29),
                    (8, 8),
                    (29, 46),
                    (45, 8),
                    (47, 48)
                ],
                input_len: 9,
                outputs: vec![34, 39, 44, 49]
            },
            opt_circ1
        );
        for i in 0..1 << 9 {
            let input = [(i & 0xff).try_into().unwrap(), (i >> 4).try_into().unwrap()];
            let output1 = circ1.run(&input, false);
            let output2 = opt_circ1.run_circuit(&input, 9);
            assert_eq!(output1, output2, "xor2 {}", i);
        }

        let circ1 = Circuit {
            circuit: vec![
                128, 132, 4, // copy 4-bits
                129, 132, 0, 132, 4, // xor bits
                129, 132, 12, 132, 8, // xor next bits
                130, 0, 4, 130, 1, 5, 130, 2, 6, 130, 3, 7, // xor-4bit
                0, 0, // xor: not 2=i0
                1, 1, // not 3=i1
                0, 3, // nand i0 noti1
                2, 1, // nand noti0 i1
                4, 5, // nand t0 t1 -> or(and(i0,noti1),and(noti0,i1))
            ],
            subcircuits: vec![
                // xor-4bit
                SubcircuitInfo {
                    location: 13,
                    input_len: 4,
                    output_len: 4,
                },
                // xor-4bit
                SubcircuitInfo {
                    location: 13,
                    input_len: 8,
                    output_len: 4,
                },
                // xor
                SubcircuitInfo {
                    location: 25,
                    input_len: 2,
                    output_len: 1,
                },
            ],
            input_len: 8,
            output_len: 4,
        };
        let opt_circ1 = OptCircuit::new(circ1.clone(), None);
        assert_eq!(
            OptCircuit {
                circuit: vec![
                    (0, 0),
                    (4, 4),
                    (0, 10),
                    (9, 4),
                    (11, 12),
                    (1, 1),
                    (5, 5),
                    (1, 15),
                    (14, 5),
                    (16, 17),
                    (2, 2),
                    (6, 6),
                    (2, 20),
                    (19, 6),
                    (21, 22),
                    (3, 3),
                    (7, 7),
                    (3, 25),
                    (24, 7),
                    (26, 27),
                    (13, 13),
                    (4, 4),
                    (13, 30),
                    (29, 4),
                    (31, 32),
                    (18, 18),
                    (5, 5),
                    (18, 35),
                    (34, 5),
                    (36, 37),
                    (23, 23),
                    (6, 6),
                    (23, 40),
                    (39, 6),
                    (41, 42),
                    (28, 28),
                    (7, 7),
                    (28, 45),
                    (44, 7),
                    (46, 47)
                ],
                input_len: 8,
                outputs: vec![33, 38, 43, 48]
            },
            opt_circ1
        );
        for i in 0..=255 {
            let input = [i];
            let output1 = circ1.run(&input, false);
            let output2 = opt_circ1.run_circuit(&input, 8);
            assert_eq!(output1, output2, "xor3 {}", i);
        }

        // overlapping output in data
        // circuit:
        //      main:
        //     # pos = 0x8
        //     one = nand zero zero
        //     # pos = 0x9
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:i0 one .7:zero
        //     # pos = 0x11
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x19
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x21
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x29
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x31
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x39
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x41
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x49
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x51
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x59
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x61
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x69
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x71
        //     s0 s1 s2 s3 s4 s5 s6 s7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x79
        //     x0 x1 x2 x3 = copy_4bit :4:s4
        //     # pos = 0x7d
        //     o0 o1 o2 o3 o4 o5 o6 o7 = adder_8bit :8:s0 one .7:zero
        //     # pos = 0x5
        // copy:
        //     empty 1
        // copy_4bit:
        //     empty 4
        // xor:
        //     n0 = nand i0 i0
        //     n1 = nand i1 i1
        //     t0 = nand i0 n1
        //     t1 = nand n0 i1
        //     o0 = nand t0 t1
        // full_adder:
        //     s0 = xor i0 i1
        //     a0 = nand i0 i1
        //     a1 = nand s0 i2
        //     o0 = xor s0 i2
        //     # (i0 and i1) or (s0 and i2)
        //     o1 = nand a0 a1
        // # i0 - carry, i1-i4 - 4-bit A, i5-i8 - 4-bit B
        // carry_adder_4bit:
        //     s0 c0 = full_adder i1 i5 i0
        //     s1 c1 = full_adder i2 i6 c0
        //     s2 c2 = full_adder i3 i7 c1
        //     s3 c3 = full_adder i4 i8 c2
        //     o0 o1 o2 o3 = copy_4bit s0 s1 s2 s3
        //     o4 = copy c3
        // adder_8bit:
        //     s0 s1 s2 s3 c4 = carry_adder_4bit zero :4:i0 :4:i8
        //     s4 s5 s6 s7 ign = carry_adder_4bit c4 :4:i4 :4:i12
        //     o0 o1 o2 o3 = copy_4bit :4:s0
        //     o4 o5 o6 o7 = copy_4bit :4:s4
        let circ1 = Circuit {
            circuit: vec![
                0x7f, 0x7f, 0x85, 0x88, 0x00, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x09, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x11, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x19, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x21, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x29, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x31, 0x08,
                0xc7, 0x7f, 0x85, 0x88, 0x39, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x41, 0x08, 0xc7, 0x7f,
                0x85, 0x88, 0x49, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x51, 0x08, 0xc7, 0x7f, 0x85, 0x88,
                0x59, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x61, 0x08, 0xc7, 0x7f, 0x85, 0x88, 0x69, 0x08,
                0xc7, 0x7f, 0x81, 0x84, 0x75, 0x85, 0x88, 0x71, 0x08, 0xc7, 0x7f, 0x00, 0x00, 0x01,
                0x01, 0x00, 0x03, 0x02, 0x01, 0x04, 0x05, 0x82, 0x00, 0x01, 0x00, 0x01, 0x03, 0x02,
                0x82, 0x03, 0x02, 0x04, 0x05, 0x83, 0x01, 0x05, 0x00, 0x83, 0x02, 0x06, 0x0a, 0x83,
                0x03, 0x07, 0x0c, 0x83, 0x04, 0x08, 0x0e, 0x81, 0x09, 0x0b, 0x0d, 0x0f, 0x80, 0x10,
                0x84, 0x7f, 0x84, 0x00, 0x84, 0x08, 0x84, 0x14, 0x84, 0x04, 0x84, 0x0c, 0x81, 0x84,
                0x10, 0x81, 0x84, 0x15,
            ],
            subcircuits: vec![
                SubcircuitInfo {
                    location: 95,
                    input_len: 1,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 95,
                    input_len: 4,
                    output_len: 4,
                },
                SubcircuitInfo {
                    location: 95,
                    input_len: 2,
                    output_len: 1,
                },
                SubcircuitInfo {
                    location: 105,
                    input_len: 3,
                    output_len: 2,
                },
                SubcircuitInfo {
                    location: 117,
                    input_len: 9,
                    output_len: 5,
                },
                SubcircuitInfo {
                    location: 140,
                    input_len: 16,
                    output_len: 8,
                },
            ],
            input_len: 8,
            output_len: 8,
        };
        let opt_circ1 = OptCircuit::new(circ1.clone(), None);
        for i in 0..=255 {
            let input = [i];
            let output1 = circ1.run(&input, false);
            let output2 = opt_circ1.run_circuit(&input, 8);
            assert_eq!(output1, output2, "add0 {}", i);
        }
    }
}
