use nom::{
    branch::*, bytes::complete as bc, character::complete as cc, combinator::*, error::*, multi::*,
    sequence::*, IResult,
};

use std::collections::HashMap;

// parser

#[derive(Clone, Debug)]
pub enum Statement {
    Statement {
        output: Vec<String>, // output: output in subcircuit should have name 'oXXX'
        subcircuit: String,  // subcircuit: can be 'nand' or other subcircuit
        input: Vec<String>,  // input of subcircuit should have name 'iXXX
    },
    Alias {
        new_name: String,
        name: String,
    },
}

#[derive(Clone, Debug)]
pub struct ParsedSubcircuit {
    pub name: String, // name of subcircuit: if name is main then main circuit
    pub statements: Vec<Statement>,
}

#[derive(Clone, Debug)]
pub struct ParsedPrimalMachine {
    pub cell_len_bits: u32,
    pub address_len: u32,
    pub circuit: Vec<ParsedSubcircuit>,
}

type VIResult<'a> = IResult<&'a str, &'a str, VerboseError<&'a str>>;
type VOIResult<'a, T> = IResult<&'a str, T, VerboseError<&'a str>>;

fn identifier(input: &str) -> VIResult {
    context(
        "identifier",
        recognize(pair(
            alt((cc::alpha1, bc::tag("_"))),
            many0_count(alt((cc::alphanumeric1, bc::tag("_")))),
        )),
    )(input)
}

pub fn empty_or_comment(input: &str) -> VOIResult<()> {
    value(
        (),
        many0_count(alt((
            value(
                (),
                tuple((
                    cc::space0,
                    cc::char('#'),
                    cc::not_line_ending,
                    cc::line_ending,
                )),
            ),
            value((), pair(cc::space0, cc::line_ending)),
        ))),
    )(input)
}

pub fn parse_names(input: &str) -> VOIResult<Vec<String>> {
    map(
        pair(
            preceded(cc::space0, identifier),
            many0(preceded(cc::space1, identifier)),
        ),
        |(x, vec)| {
            let mut out = vec![x.to_string()];
            out.extend(vec.into_iter().map(|x| x.to_string()));
            out
        },
    )(input)
}

pub fn parse_statement(input: &str) -> VOIResult<Statement> {
    context(
        "statement",
        terminated(
            alt((
                map(
                    tuple((
                        preceded(
                            tuple((cc::space0, bc::tag("alias"), cc::space0)),
                            identifier,
                        ),
                        preceded(cc::space0, identifier),
                    )),
                    |(new_name, name)| Statement::Alias {
                        new_name: new_name.to_string(),
                        name: name.to_string(),
                    },
                ),
                map(
                    tuple((
                        parse_names,
                        preceded(tuple((cc::space0, cc::char('='), cc::space0)), identifier),
                        cut(parse_names),
                    )),
                    |(output, subcircuit, input)| Statement::Statement {
                        output,
                        subcircuit: subcircuit.to_string(),
                        input,
                    },
                ),
            )),
            cut(pair(cc::space0, cc::line_ending)),
        ),
    )(input)
}

pub fn parse_subcircuit(input: &str) -> VOIResult<ParsedSubcircuit> {
    context(
        "subcircuit",
        map(
            pair(
                delimited(
                    cc::space0,
                    terminated(identifier, cut(pair(cc::space0, cc::char(':')))),
                    pair(cc::space0, cc::line_ending),
                ),
                many0(preceded(empty_or_comment, parse_statement)),
            ),
            |(name, statements)| ParsedSubcircuit {
                name: name.to_string(),
                statements,
            },
        ),
    )(input)
}

pub fn parse_circuit(input: &str) -> VOIResult<Vec<ParsedSubcircuit>> {
    context(
        "circuit",
        many0(preceded(empty_or_comment, parse_subcircuit)),
    )(input)
}

pub fn parse_field_u32<'a>(name: &'a str) -> impl FnMut(&'a str) -> VOIResult<u32> {
    delimited(
        tuple((
            empty_or_comment,
            cc::space0,
            bc::tag(name),
            cc::space0,
            cc::char(':'),
            cc::space0,
        )),
        cc::u32,
        pair(cc::space0, cc::line_ending),
    )
}

pub fn parse_primal_machine(input: &str) -> VOIResult<ParsedPrimalMachine> {
    context(
        "primal_machine",
        map(
            tuple((
                parse_field_u32("cell_len_bits"),
                parse_field_u32("address_len"),
                many0(preceded(empty_or_comment, parse_subcircuit)),
            )),
            |(cell_len_bits, address_len, circuit)| ParsedPrimalMachine {
                cell_len_bits,
                address_len,
                circuit,
            },
        ),
    )(input)
}

// parser for testcases
