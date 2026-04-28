mod actions;
mod cli;
mod es;
mod formatters;
mod fuzzy;
mod grammar;
mod models;
mod selector;
mod util;

use std::process::ExitCode;

fn main() -> ExitCode {
    match cli::run() {
        Ok(code) => ExitCode::from(code),
        Err(err) => {
            eprintln!("ERROR: {err}");
            ExitCode::from(2)
        }
    }
}
