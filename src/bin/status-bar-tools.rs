//! Field selection, preview, and config-write commands for the status bar.

fn main() {
    let code = claude_status_bar::tools::run(std::env::args().skip(1).collect());
    std::process::exit(code);
}
