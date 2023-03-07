use nom::{
    branch::*, bytes::complete as bc, character::complete as cc, combinator::*, error::*, multi::*,
    sequence::*, IResult,
};

// parser

#[derive(Clone, Debug)]
pub enum Input {
    Single(String),
    Repeat(u8, String),
}

#[derive(Clone, Debug)]
pub enum Statement {
    Statement {
        output: Vec<String>, // output: output in subcircuit should have name 'oXXX'
        subcircuit: String,  // subcircuit: can be 'nand' or other subcircuit
        input: Vec<Input>,   // input of subcircuit should have name 'iXXX
    },
    Alias {
        new_name: String,
        name: String,
    },
    Empty {
        input_output_len: u8,
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

fn parse_input(input: &str) -> VOIResult<Input> {
    context(
        "input",
        alt((
            map(identifier, |x| Input::Single(x.to_string())),
            map(
                preceded(cc::char(':'), separated_pair(cc::u8, cc::char(':'), identifier)),
                |(count, base)| Input::Repeat(count, base.to_string()),
            ),
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

pub fn parse_inputs(input: &str) -> VOIResult<Vec<Input>> {
    map(
        pair(
            preceded(cc::space0, parse_input),
            many0(preceded(cc::space1, parse_input)),
        ),
        |(x, vec)| {
            let mut out = vec![x];
            out.extend(vec.into_iter());
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
                        cut(parse_inputs),
                    )),
                    |(output, subcircuit, input)| Statement::Statement {
                        output,
                        subcircuit: subcircuit.to_string(),
                        input,
                    },
                ),
                map(
                    preceded(tuple((cc::space0, bc::tag("empty"), cc::space0)), cc::u8),
                    |input_output_len| Statement::Empty { input_output_len },
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

pub fn parse_circuit_all(input: &str) -> VOIResult<Vec<ParsedSubcircuit>> {
    context(
        "circuit",
        all_consuming(terminated(
            many0(preceded(empty_or_comment, parse_subcircuit)),
            cc::multispace0,
        )),
    )(input)
}

// parser for testcases

pub struct TestCase {
    pub name: String,
    pub subcircuit: String,
    pub input: Vec<bool>,
    pub exp_output: Vec<bool>,
}

pub fn parse_test_case(input: &str) -> VOIResult<TestCase> {
    context(
        "testcase",
        map(
            terminated(
                tuple((
                    preceded(cc::space0, identifier),
                    preceded(cc::space0, identifier),
                    preceded(cc::space0, many0(cc::one_of("01"))),
                    preceded(cc::space0, many0(cc::one_of("01"))),
                )),
                pair(cc::space0, cc::line_ending),
            ),
            |(name, subcircuit, input, exp_output)| TestCase {
                name: name.to_string(),
                subcircuit: subcircuit.to_string(),
                input: input.into_iter().map(|c| c == '1').collect(),
                exp_output: exp_output.into_iter().map(|c| c == '1').collect(),
            },
        ),
    )(input)
}

pub fn parse_test_suite(input: &str) -> VOIResult<Vec<TestCase>> {
    context(
        "testsuite",
        all_consuming(terminated(
            many0(preceded(empty_or_comment, parse_test_case)),
            cc::multispace0,
        )),
    )(input)
}

pub fn divide_lines(input: &str) -> String {
    #[derive(Copy, Clone, PartialEq, Debug)]
    enum Divisor {
        Nothing,
        Backslash,
        LineFeed,
    }
    let mut div = Divisor::Nothing;
    let mut out = String::new();
    for c in input.chars() {
        match c {
            '\\' => {
                div = Divisor::Backslash;
            }
            '\r' => {
                if div == Divisor::Nothing {
                    out.push(c);
                } else if div == Divisor::Backslash {
                    div = Divisor::LineFeed;
                }
            }
            '\n' => {
                if div == Divisor::Nothing {
                    out.push(c);
                } else if div == Divisor::Backslash || div == Divisor::LineFeed {
                    div = Divisor::Nothing;
                    // skip newline
                }
            }
            _ => {
                if div == Divisor::Backslash {
                    out.push('\\');
                } else if div == Divisor::LineFeed {
                    out.push('\\');
                    out.push('\r');
                }
                div = Divisor::Nothing;
                out.push(c);
            }
        }
    }
    out
}
