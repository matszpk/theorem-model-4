use crate::sim::*;

use std::cmp::{max, min};
use std::collections::{HashMap, HashSet};

#[cfg(test)]
macro_rules! test_println {
    () => { println!(); };
    ($($arg:tt)*) => { println!($($arg)*); };
}

#[cfg(not(test))]
macro_rules! test_println {
    () => {};
    ($($arg:tt)*) => {};
}

#[derive(Clone, Debug, Default, PartialEq)]
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
        let mut memory = vec![false; self.circuit.len() + circ_input_len + 1];
        let input_len = min(circ_input_len, input_len);
        for i in 0..input_len {
            memory[i] = ((input[i >> 3] >> (i & 7)) & 1) != 0;
        }
        let base = circ_input_len + 1;
        for (i, (igi1, igi2)) in self.circuit.iter().enumerate() {
            let (gi1, gi2) = (*igi1 as usize, *igi2 as usize);
            let out_idx = base + i;
            memory[out_idx] = !(memory[gi1] & memory[gi2]);
        }
        let mut final_output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (i, idx) in self.outputs.iter().enumerate() {
            let idx = *idx as usize;
            final_output[i >> 3] |= u8::from(memory[idx]) << (i & 7);
        }
        final_output
    }
}

#[cfg(feature = "opt2_func9")]
const FUNC_BITS: usize = 9;
#[cfg(not(feature = "opt2_func9"))]
const FUNC_BITS: usize = 6;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct FuncEntry {
    input_len: u8,
    inputs: [u32; 9],
    #[cfg(feature = "opt2_func9")]
    outputs: [u64; 8],
    #[cfg(not(feature = "opt2_func9"))]
    outputs: u64,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct OptCircuit2 {
    circuit: Vec<FuncEntry>,
    pub input_len: u8,
    pub outputs: Vec<u32>,
}

#[cfg(feature = "opt2_func9")]
fn opt2_calc_func(
    opt_circuit: &OptCircuit,
    cur_tree: &[u32],
    base: u32,
    input_len: usize,
) -> [u64; 8] {
    // if not greater input than can be handled by function
    // then create new function and replace
    let mut rev_curtree_map = HashMap::<u32, u32>::new();
    for (i, j) in cur_tree[cur_tree.len() - input_len..].iter().enumerate() {
        rev_curtree_map.insert(*j, u32::try_from(i).unwrap());
    }
    for (i, j) in cur_tree.iter().rev().enumerate() {
        if !rev_curtree_map.contains_key(j) {
            rev_curtree_map.insert(*j, u32::try_from(i).unwrap());
        }
    }
    test_println!("      rev_cur_tree: {:?}", rev_curtree_map);

    let func_circuit = cur_tree
        .iter()
        .rev()
        .copied()
        .skip(input_len)
        .collect::<Vec<_>>();
    test_println!("      Func circuit: {:?}", func_circuit);

    let mut calcs =
        vec![[0u64, 0u64, 0u64, 0u64, 0u64, 0u64, 0u64, 0u64]; input_len + func_circuit.len()];
    // for value in 0..(1u128.overflowing_shl(input_len.try_into().unwrap()).0) {
    //     for i in 0..input_len {
    //         calcs[i] |= ((value >> i) & 1) << value;
    //     }
    // }
    for value in 0..(1u64 << input_len) {
        for i in 0..input_len {
            calcs[i][usize::try_from(value >> 6).unwrap()] |= ((value >> i) & 1) << (value & 63);
        }
    }
    let mut not_mask = [0u64, 0u64, 0u64, 0u64, 0u64, 0u64, 0u64, 0u64];
    // let not_mask = 1u128
    //     .checked_shl(1 << input_len)
    //     .unwrap_or_default()
    //     .overflowing_sub(1)
    //     .0;
    for i in 0..(1 << input_len) {
        not_mask[i >> 6] |= 1u64 << (i & 63);
    }

    for (i, gi) in func_circuit.iter().enumerate() {
        test_println!("        calc func {} {} {}", i, gi, *gi - base);
        if *gi < base {
            continue;
        }
        let (ogi0, ogi1) = opt_circuit.circuit[(*gi - base) as usize];
        test_println!("        calc inputs: {:?}", (ogi0, ogi1));
        if !rev_curtree_map.contains_key(&ogi0) || !rev_curtree_map.contains_key(&ogi1) {
            continue;
        }
        let gi = (
            rev_curtree_map[&ogi0] as usize,
            rev_curtree_map[&ogi1] as usize,
        );
        test_println!("        calc convinputs {:?} to {}", gi, input_len + i);
        //calcs[input_len + i] = not_mask ^ (calcs[gi.0] & calcs[gi.1]);
        for k in 0..(1 << (9 - 6)) {
            calcs[input_len + i][k] = not_mask[k] ^ (calcs[gi.0][k] & calcs[gi.1][k]);
        }
    }
    *calcs.last().unwrap()
}

#[cfg(not(feature = "opt2_func9"))]
fn opt2_calc_func(opt_circuit: &OptCircuit, cur_tree: &[u32], base: u32, input_len: usize) -> u64 {
    // if not greater input than can be handled by function
    // then create new function and replace
    let mut rev_curtree_map = HashMap::<u32, u32>::new();
    for (i, j) in cur_tree[cur_tree.len() - input_len..].iter().enumerate() {
        rev_curtree_map.insert(*j, u32::try_from(i).unwrap());
    }
    for (i, j) in cur_tree.iter().rev().enumerate() {
        if !rev_curtree_map.contains_key(j) {
            rev_curtree_map.insert(*j, u32::try_from(i).unwrap());
        }
    }
    test_println!("      rev_cur_tree: {:?}", rev_curtree_map);

    let func_circuit = cur_tree
        .iter()
        .rev()
        .copied()
        .skip(input_len)
        .collect::<Vec<_>>();
    test_println!("      Func circuit: {:?}", func_circuit);

    let mut calcs = vec![0u64; input_len + func_circuit.len()];
    for value in 0..(1u64.overflowing_shl(input_len.try_into().unwrap()).0) {
        for i in 0..input_len {
            calcs[i] |= ((value >> i) & 1) << value;
        }
    }

    let not_mask = 1u64
        .checked_shl(1 << input_len)
        .unwrap_or_default()
        .overflowing_sub(1)
        .0;

    for (i, gi) in func_circuit.iter().enumerate() {
        test_println!("        calc func {} {} {}", i, gi, *gi - base);
        if *gi < base {
            continue;
        }
        let (ogi0, ogi1) = opt_circuit.circuit[(*gi - base) as usize];
        test_println!("        calc inputs: {:?}", (ogi0, ogi1));
        if !rev_curtree_map.contains_key(&ogi0) || !rev_curtree_map.contains_key(&ogi1) {
            continue;
        }
        let gi = (
            rev_curtree_map[&ogi0] as usize,
            rev_curtree_map[&ogi1] as usize,
        );
        test_println!("        calc convinputs {:?} to {}", gi, input_len + i);
        //calcs[input_len + i] = not_mask ^ (calcs[gi.0] & calcs[gi.1]);
        calcs[input_len + i] = not_mask ^ (calcs[gi.0] & calcs[gi.1]);
    }
    *calcs.last().unwrap()
}

fn opt2_get_g(
    opt_circuit: &OptCircuit,
    cur_tree: &mut Vec<u32>,
    rev_ordering: &[u32],
    base: u32,
    orig_g1: u32,
) -> (u32, u32) {
    let g1 = if orig_g1 < base {
        orig_g1
    } else {
        base + rev_ordering[(orig_g1 - base) as usize]
    };

    let (mut old_g1, mut old_orig_g1) = (g1, orig_g1);
    let (mut g1, mut orig_g1) = (g1, orig_g1);
    loop {
        test_println!("Xy: {:?}", (g1, orig_g1));
        (g1, orig_g1) = if orig_g1 >= base {
            let (orig_g1x, orig_g2x) = opt_circuit.circuit[(orig_g1 - base) as usize];
            // same inputs then not - put not gate and get its input
            if orig_g1x == orig_g2x {
                let g1x = if orig_g1x < base {
                    orig_g1x
                } else {
                    base + rev_ordering[(orig_g1x - base) as usize]
                };
                cur_tree.push(orig_g1);
                (g1x, orig_g1x)
            } else {
                (g1, orig_g1)
            }
        } else {
            (g1, orig_g1)
        };
        if (old_g1, old_orig_g1) == (g1, orig_g1) {
            break;
        }
        (old_g1, old_orig_g1) = (g1, orig_g1);
    }
    (g1, orig_g1)
}

impl OptCircuit2 {
    pub fn new(opt_circuit: OptCircuit) -> Self {
        test_println!("opt_circuit: {:?}", opt_circuit.circuit);
        // ordering - lowest is input, greater output of gates, ..., greatest - last outputs
        // ordering - determine step's number of calculation
        let circ_input_len = opt_circuit.input_len as usize;
        let circ_len = opt_circuit.circuit.len();
        // ordering: value: first - step, second - original order
        let mut ordering = vec![(0u32, 0u32); circ_len];
        // to next ordering: index - original ordering, value - next ordering
        let mut rev_ordering = vec![0; circ_len];

        let base = u32::try_from(circ_input_len + 1).unwrap();
        for (i, (igi1, igi2)) in opt_circuit.circuit.iter().enumerate() {
            // get step of calculation for inputs
            let gs1 = if *igi1 < base {
                0
            } else {
                ordering[(*igi1 - base) as usize].0
            };
            let gs2 = if *igi2 < base {
                0
            } else {
                ordering[(*igi2 - base) as usize].0
            };
            ordering[i] = (max(gs1, gs2) + 1, u32::try_from(i).unwrap());
        }
        ordering.sort(); // more important is order, less important index
        test_println!("Ordering: {:?}", ordering);
        for (i, (_, j)) in ordering.iter().enumerate() {
            rev_ordering[*j as usize] = u32::try_from(i).unwrap();
        }
        test_println!("RevOrdering: {:?}", rev_ordering);

        #[derive(Clone, Copy, Debug, PartialEq, Eq)]
        enum VisitState {
            NotVisited,
            Visited,
            UsedAsInput,
        }
        use VisitState::*;

        // collect and filter functions and build function tree
        let mut final_funcs: Vec<FuncEntry> = vec![];
        let mut final_func_out_idxs = vec![];
        let mut visited = vec![NotVisited; circ_len];

        // outputs must be always calculated as used as final outputs
        for v in opt_circuit
            .outputs
            .iter()
            .filter(|x| **x >= base)
            .map(|x| rev_ordering[(x - base) as usize])
        {
            test_println!(" visited as output {}", v);
            visited[v as usize] = UsedAsInput;
        }

        for ri in 0..circ_len {
            let i = circ_len - ri - 1;
            if visited[i] == Visited {
                continue;
            }

            let (func, calced_nodes) = {
                let ord_idx = i;
                let orig_idx = ordering[ord_idx].1;
                test_println!("  Gate: orig={} order={}", orig_idx, ord_idx);
                // determine function and its inputs
                let mut func = FuncEntry::default();
                let mut func_visited = HashSet::new();
                // set to last function choice - length of curtree for after this choice
                //let mut choosen_curtree_len = 0;
                // hold original index of output
                let mut cur_tree: Vec<u32> = vec![base + orig_idx];
                let mut inputs: Vec<u32> = vec![base + u32::try_from(ord_idx).unwrap()];

                // deepening direct input usage
                //while inputs.iter().any(|x| *x >= base) {
                loop {
                    test_println!("    Step:");
                    let mut new_inputs: Vec<u32> = vec![];
                    let mut new_cur_tree_pass: Vec<u32> = vec![];

                    test_println!("      Gen new inputs:");
                    let mut expanded = 0;
                    for ai in &inputs {
                        if *ai < base
                            || (ord_idx != (*ai - base) as usize
                                && visited[(*ai - base) as usize] == UsedAsInput)
                        {
                            test_println!("        Ii {}", ai);
                            if !new_inputs.contains(&ai) {
                                new_inputs.push(*ai);
                                if *ai < base {
                                    new_cur_tree_pass.push(*ai);
                                } else {
                                    let orig_idx = base + ordering[(ai - base) as usize].1;
                                    test_println!("        Ii2 {} {}", ai, orig_idx);
                                    new_cur_tree_pass.push(orig_idx);
                                }
                            }
                        } else {
                            expanded += 1;
                            // deep
                            test_println!("        Gi {}", ai);
                            let orig_idx = ordering[(ai - base) as usize].1 as usize;
                            let (orig_g1, orig_g2) = opt_circuit.circuit[orig_idx];
                            test_println!(
                                "        Gi orig_idx={} {} {}",
                                orig_idx,
                                orig_g1,
                                orig_g2
                            );

                            let (g1, orig_g1) = opt2_get_g(
                                &opt_circuit,
                                &mut cur_tree,
                                &rev_ordering,
                                base,
                                orig_g1,
                            );
                            let (g2, orig_g2) = opt2_get_g(
                                &opt_circuit,
                                &mut cur_tree,
                                &rev_ordering,
                                base,
                                orig_g2,
                            );

                            if !new_inputs.contains(&g1) {
                                new_inputs.push(g1);
                                new_cur_tree_pass.push(orig_g1);
                            }
                            if !new_inputs.contains(&g2) {
                                new_inputs.push(g2);
                                new_cur_tree_pass.push(orig_g2);
                            }
                        }
                    }
                    cur_tree.extend(new_cur_tree_pass);
                    test_println!("      New inputs: {:?}", new_inputs);
                    test_println!("      New cur_tree: {:?}", cur_tree);

                    if new_inputs.len() <= FUNC_BITS {
                        func.input_len = u8::try_from(new_inputs.len()).unwrap();
                        func.inputs[0..new_inputs.len()]
                            .copy_from_slice(&new_inputs[0..new_inputs.len()]);
                        test_println!("      Func inputs: {:?}", &func.inputs[0..new_inputs.len()]);
                        let input_len = func.input_len as usize;

                        func.outputs = opt2_calc_func(&opt_circuit, &cur_tree, base, input_len);

                        func_visited = HashSet::<u32>::from_iter(
                            cur_tree
                                .iter()
                                .rev()
                                .skip(input_len)
                                .filter(|x| **x >= base)
                                .map(|x| rev_ordering[(*x - base) as usize]),
                        );
                        //choosen_curtree_len = cur_tree.len();
                    } else {
                        test_println!("      New inuts over 9: {}", new_inputs.len());
                        // simple heuristics
                        if new_inputs.len() > 30 {
                            break; // end of finding
                        }
                    }
                    test_println!("      Func Nodes: {:?}", func_visited);
                    inputs = new_inputs.clone();
                    if expanded == 0 {
                        break;
                    }
                }

                (func, func_visited)
            };
            test_println!("collect and filter: {} {:?}", i, func);
            final_funcs.push(func);
            final_func_out_idxs.push(i);
            for g in &func.inputs[0..func.input_len as usize] {
                if *g >= base {
                    visited[(*g - base) as usize] = UsedAsInput;
                }
            }
            test_println!("  visited by : {} {:?}", i, calced_nodes);
            for g in calced_nodes.iter() {
                if visited[*g as usize] == NotVisited {
                    visited[*g as usize] = Visited; // set as
                }
            }
            visited[i] = Visited;
        }
        final_funcs.reverse();
        final_func_out_idxs.reverse();
        test_println!(
            "OptCircuit outputs: {:?}",
            opt_circuit
                .outputs
                .iter()
                .map(|x| rev_ordering[(x - base) as usize])
                .collect::<Vec<_>>()
        );
        test_println!("final_func_out_idxs: {:?}", final_func_out_idxs);
        let final_func_out_map = HashMap::<usize, usize>::from_iter(
            final_func_out_idxs
                .into_iter()
                .enumerate()
                .map(|(i, x)| (x, i)),
        );
        // convert function inputs
        for func in &mut final_funcs {
            for v in &mut func.inputs[0..func.input_len as usize] {
                if *v >= base {
                    *v = base + u32::try_from(final_func_out_map[&((*v - base) as usize)]).unwrap();
                }
            }
        }
        test_println!("Final funcs: {:?}", final_funcs);
        test_println!("Optcircuit len: {}", opt_circuit.circuit.len());
        println!("Final funcs len: {}", final_funcs.len());

        OptCircuit2 {
            circuit: final_funcs,
            input_len: opt_circuit.input_len,
            outputs: opt_circuit
                .outputs
                .into_iter()
                .map(|x| {
                    if x < base {
                        x
                    } else {
                        u32::try_from(
                            final_func_out_map[&(rev_ordering[(x - base) as usize] as usize)],
                        )
                        .unwrap()
                            + base
                    }
                })
                .collect::<Vec<_>>(),
        }
    }

    #[cfg(feature = "opt2_func9")]
    pub fn run_circuit(&self, input: &[u8], input_len: usize) -> [u8; 128 >> 3] {
        let circ_input_len = self.input_len as usize;
        let mut memory = vec![false; self.circuit.len() + circ_input_len + 1];
        let input_len = min(circ_input_len, input_len);
        for i in 0..input_len {
            memory[i] = ((input[i >> 3] >> (i & 7)) & 1) != 0;
        }
        let base = circ_input_len + 1;
        for (i, func) in self.circuit.iter().enumerate() {
            let func_input_len = func.input_len as usize;
            let mut input_idx = 0;
            for i in 0..func_input_len {
                let idx = func.inputs[i] as usize;
                input_idx |= usize::from(memory[idx]) << i;
            }
            let out_idx = base + i;
            memory[out_idx] = ((func.outputs[input_idx >> 6] >> (input_idx & 63)) & 1) != 0;
        }
        let mut final_output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (i, idx) in self.outputs.iter().enumerate() {
            let idx = *idx as usize;
            final_output[i >> 3] |= u8::from(memory[idx]) << (i & 7);
        }
        final_output
    }

    #[cfg(not(feature = "opt2_func9"))]
    pub fn run_circuit(&self, input: &[u8], input_len: usize) -> [u8; 128 >> 3] {
        let circ_input_len = self.input_len as usize;
        let mut memory = vec![false; self.circuit.len() + circ_input_len + 1];
        let input_len = min(circ_input_len, input_len);
        for i in 0..input_len {
            memory[i] = ((input[i >> 3] >> (i & 7)) & 1) != 0;
        }
        let base = circ_input_len + 1;
        for (i, func) in self.circuit.iter().enumerate() {
            let func_input_len = func.input_len as usize;
            let mut input_idx = 0;
            for i in 0..func_input_len {
                let idx = func.inputs[i] as usize;
                input_idx |= usize::from(memory[idx]) << i;
            }
            let out_idx = base + i;
            memory[out_idx] = ((func.outputs >> input_idx) & 1) != 0;
        }
        let mut final_output: [u8; 128 >> 3] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (i, idx) in self.outputs.iter().enumerate() {
            let idx = *idx as usize;
            final_output[i >> 3] |= u8::from(memory[idx]) << (i & 7);
        }
        final_output
    }
}

#[cfg(not(feature = "opt2_func9"))]
pub fn aggregate_opt_circuit2(opt_circuit: &OptCircuit2) {
    let base = (opt_circuit.input_len as u32) + 1;
    let mut dep_sets = vec![HashSet::<u32>::new(); opt_circuit.circuit.len()];
    for (i, func) in opt_circuit.circuit.iter().enumerate() {
        for inp in &func.inputs[0..func.input_len as usize] {
            if *inp >= base {
                dep_sets[i].insert(*inp - base);
                dep_sets[i] = &dep_sets[i] | &dep_sets[(*inp - base) as usize];
            }
        }
    }
    for (i, dep_set) in dep_sets.iter().enumerate() {
        println!("dependencies: {} {:?}", i, dep_set);
    }
    // collect
    let mut visited = vec![false; opt_circuit.circuit.len()];
    let mut aggregates = vec![];
    for (i, func) in opt_circuit.circuit.iter().enumerate() {
        if visited[i] {
            continue;
        }
        let mut input_sets = HashSet::<u32>::from_iter(
            func.inputs[0..func.input_len as usize]
                .iter()
                .copied(),
        );
        visited[i] = true;
        for (j, funcj) in opt_circuit.circuit.iter().enumerate() {
            if visited[j] || dep_sets[i].contains(&u32::try_from(j).unwrap()) {
                continue;
            }
            let j_input_sets = HashSet::<u32>::from_iter(
                funcj.inputs[0..funcj.input_len as usize]
                    .iter()
                    .copied(),
            );
            let new_input_sets = &input_sets | &j_input_sets;
            if new_input_sets.len() <= 6 {
                input_sets = new_input_sets;
                visited[j] = true;
            }
        }
        aggregates.push((i, input_sets));
    }
    println!("aggegations: {:?}", aggregates);
    println!("aggegations count: {:?}", aggregates.len());
}

// #[derive(Clone, Copy, Debug, PartialEq, Eq)]
// pub enum Opt2Entry {
//     // range of input to argument 1 to gates: (Start, x), (Start+1,x2),...(end-1, xn)
//     Arg1Range(u32, u32),
//     // range of input to argument 2 to gates: (Start, x), (Start+1,x2),...(end-1, xn)
//     Arg2Range(u32, u32),
// }
//
// // parallelize calculation by bitwise operations
// // aggregate single bit operations into integer bitwise operations
//
// #[derive(Clone, Debug, PartialEq)]
// pub struct OptCircuit2 {
//     pub circuit: Vec<Opt2Entry>,
//     pub input_len: u8,
//     pub outputs: Vec<u32>,
// }
//
// impl OptCircuit2 {
//     pub fn new(opt_circuit: OptCircuit) -> Self {
//         // ordering - lowest is input, greater output of gates, ..., greatest - last outputs
//         // ordering - determine step's number of calculation
//         let circ_input_len = opt_circuit.input_len as usize;
//         let circ_len = opt_circuit.circuit.len();
//         let mut ordering = vec![(0u32, 0u32); circ_len];
//         // to next ordering: index - next ordering, value - prev ordering
//         let mut rev_ordering = vec![0, circ_len];
//         let base = u32::try_from(circ_input_len + 1).unwrap();
//         for (i, (igi1, igi2)) in opt_circuit.circuit.iter().enumerate() {
//             // get step of calculation for inputs
//             let gs1 = if *igi1 < base { 0 }
//             else { ordering[i - (*igi1 as usize)].0 };
//             let gs2 = if *igi2 < base { 0 }
//             else { ordering[i - (*igi2 as usize)].0 };
//             ordering[i] = (max(gs1, gs2) + 1, u32::try_from(i).unwrap());
//         }
//         ordering.sort();    // more important is order, less important index
//         {
//             let mut step = 0;
//             let mut first_in_step = 0;
//             while first_in_step < circ_len {
//                 let first_in_next_step = match ordering.binary_search(&(step + 1, 0)) {
//                     Ok(r) => r,
//                     Err(r) => r
//                 };
//                 // sort ordering for current step
//                 // arg1: 1 2 3 1 4 3 1 5 2 3 5 -> 1 2 3 1 3 4 1 5
//                 first_in_step = first_in_next_step;
//                 step += 1;
//             }
//         }
//
//         // let mut entry: Vec<Opt2Entry> = vec![];
//         // let mut cur_order = ordering.first().copied().unwrap_or_default().1;
//         // let Option<u32>;
//         // for (o, i) in ordering {
//         //     if o == cur_order {
//         //     } else {
//         //         // new phase
//         //         entry.push(Opt2Entry::Arg1Range(i, i+1));
//         //         entry.push(Opt2Entry::Arg2Range(i, i+1));
//         //         cur_order = o;
//         //     }
//         // }
//
//         OptCircuit2 {
//             circuit: vec![],
//             input_len: opt_circuit.circuit.len().try_into().unwrap(),
//             outputs: opt_circuit.outputs.clone()
//         }
//     }
// }

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

    #[test]
    fn test_create_opt_circuit_2() {
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
        let opt_circ2 = OptCircuit2::new(opt_circ1);
        println!("Out opt_circ2: {:?}", opt_circ2);
        for i in 0..4 {
            let input = [i];
            println!("XX {:b}={:?}", i, opt_circ2.run_circuit(&input, 2));
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
        let opt_circ2 = OptCircuit2::new(opt_circ1.clone());
        for i in 0..1 << 12 {
            let input = [(i & 0xff).try_into().unwrap(), (i >> 4).try_into().unwrap()];
            let output2 = opt_circ1.run_circuit(&input, 12);
            let output3 = opt_circ2.run_circuit(&input, 12);
            assert_eq!(output2, output3, "xor1 {}", i);
            // println!("xor1_1 {:b}={:?}", i, output2);
            // println!("xor1_2 {:b}={:?}", i, output3);
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
        let opt_circ2 = OptCircuit2::new(opt_circ1.clone());
        for i in 0..1 << 9 {
            let input = [(i & 0xff).try_into().unwrap(), (i >> 4).try_into().unwrap()];
            let output2 = opt_circ1.run_circuit(&input, 9);
            let output3 = opt_circ2.run_circuit(&input, 9);
            assert_eq!(output2, output3, "xor2 {}", i);
            // println!("xor1_1 {:b}={:?}", i, output2);
            // println!("xor1_2 {:b}={:?}", i, output3);
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
        let opt_circ2 = OptCircuit2::new(opt_circ1.clone());
        for i in 0..1u16 << 8 {
            let input = [(i & 0xff).try_into().unwrap(), (i >> 4).try_into().unwrap()];
            let output2 = opt_circ1.run_circuit(&input, 8);
            let output3 = opt_circ2.run_circuit(&input, 8);
            assert_eq!(output2, output3, "xor3 {}", i);
            // println!("xor1_1 {:b}={:?}", i, output2);
            // println!("xor1_2 {:b}={:?}", i, output3);
        }

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
        let opt_circ2 = OptCircuit2::new(opt_circ1.clone());
        for i in 0..=255 {
            let input = [i];
            let output2 = opt_circ1.run_circuit(&input, 8);
            let output3 = opt_circ2.run_circuit(&input, 8);
            assert_eq!(output2, output3, "add {}", i);
        }
    }
}
