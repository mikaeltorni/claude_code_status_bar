//! Claude Code status bar. Reads one JSON object on stdin and prints one line.

use claude_status_bar::render::{build_status_line, parse_payload, resolve_selection};
use std::env;
use std::io::{self, Read};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    let mut raw = String::new();
    let _ = io::stdin().read_to_string(&mut raw);
    let data = parse_payload(&raw);
    let selection = resolve_selection();
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs() as i64)
        .unwrap_or(0);
    let state_dir = env::var_os("CLAUDE_STATUS_BAR_STATE_DIR")
        .map(PathBuf::from)
        .or_else(|| env::current_exe().ok().and_then(|path| path.parent().map(|dir| dir.join(".state"))));
    let line = build_status_line(&data, &selection, now, state_dir.as_deref());
    println!("{line}");
}
