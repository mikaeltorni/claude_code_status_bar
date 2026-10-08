//! Claude Code status bar. Reads one JSON object on stdin and prints one line.

mod format;
mod render;

use render::{build_status_line, parse_payload, selection_from_config, Selection, SEGMENT_IDS};
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

fn resolve_selection() -> Selection {
    if let Ok(explicit) = env::var("CLAUDE_STATUS_BAR_SEGMENTS") {
        let ids = explicit
            .split(',')
            .map(str::trim)
            .filter(|token| SEGMENT_IDS.contains(token))
            .map(str::to_string)
            .collect();
        return Selection::Only(ids);
    }
    let config = env::var_os("CLAUDE_STATUS_BAR_CONFIG")
        .map(PathBuf::from)
        .or_else(|| {
            env::current_exe()
                .ok()
                .and_then(|path| path.parent().map(|dir| dir.join("claude-status-bar.conf")))
        });
    match config {
        Some(path) => selection_from_config(&path),
        None => Selection::All,
    }
}
