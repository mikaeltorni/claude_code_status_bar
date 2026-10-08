//! Assemble the Claude Code status line from a JSON payload.

use crate::format::{format_reset, format_reset_day, format_tokens, token_count};
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};

/// Segment ids in the order they appear on the bar.
pub const SEGMENT_IDS: [&str; 8] = [
    "model",
    "project",
    "context",
    "five_hour",
    "weekly",
    "diff",
    "tokens",
    "cost",
];

/// Which segments may render.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Selection {
    /// No config file: show every segment.
    All,
    /// Config file or explicit list: only these ids.
    Only(Vec<String>),
}

impl Selection {
    fn allows(&self, segment_id: &str) -> bool {
        match self {
            Self::All => true,
            Self::Only(ids) => ids.iter().any(|id| id == segment_id),
        }
    }
}

/// Resolve the segment selection from the environment, then the config file.
///
/// Parameters: none. Reads `CLAUDE_STATUS_BAR_SEGMENTS` and `CLAUDE_STATUS_BAR_CONFIG`.
///
/// Returns: every segment, or the explicit subset.
pub fn resolve_selection() -> Selection {
    if let Ok(explicit) = std::env::var("CLAUDE_STATUS_BAR_SEGMENTS") {
        let ids = explicit
            .split(',')
            .map(str::trim)
            .filter(|token| SEGMENT_IDS.contains(token))
            .map(str::to_string)
            .collect();
        return Selection::Only(ids);
    }
    let config = std::env::var_os("CLAUDE_STATUS_BAR_CONFIG")
        .map(PathBuf::from)
        .or_else(|| {
            std::env::current_exe()
                .ok()
                .and_then(|path| path.parent().map(|dir| dir.join("claude-status-bar.conf")))
        });
    match config {
        Some(path) => selection_from_config(&path),
        None => Selection::All,
    }
}

/// Read a segment config file. A missing file means every segment.
pub fn selection_from_config(path: &Path) -> Selection {
    let raw = match fs::read_to_string(path) {
        Ok(raw) => raw,
        Err(_) => return Selection::All,
    };
    let mut enabled = Vec::new();
    for line in raw.lines() {
        let token = line.split('#').next().unwrap_or("").trim();
        if token.is_empty() {
            continue;
        }
        if SEGMENT_IDS.contains(&token) && !enabled.iter().any(|id: &String| id == token) {
            enabled.push(token.to_string());
        }
    }
    Selection::Only(enabled)
}

/// Build the pipe-delimited status line.
pub fn build_status_line(
    data: &Value,
    selection: &Selection,
    now_secs: i64,
    state_dir: Option<&Path>,
) -> String {
    let mut parts = Vec::new();
    for segment_id in SEGMENT_IDS {
        if !selection.allows(segment_id) {
            continue;
        }
        if let Some(value) = render_segment(segment_id, data, now_secs, state_dir) {
            if !value.is_empty() {
                parts.push(value);
            }
        }
    }
    parts.join(" | ")
}

fn render_segment(
    segment_id: &str,
    data: &Value,
    now_secs: i64,
    state_dir: Option<&Path>,
) -> Option<String> {
    match segment_id {
        "model" => segment_model(data),
        "project" => segment_project(data),
        "context" => segment_context(data),
        "five_hour" => segment_five_hour(data, now_secs),
        "weekly" => segment_weekly(data),
        "diff" => segment_diff(data),
        "tokens" => segment_tokens(data, state_dir),
        "cost" => segment_cost(data),
        _ => None,
    }
}

fn as_object(value: &Value) -> serde_json::Map<String, Value> {
    value.as_object().cloned().unwrap_or_default()
}

fn segment_model(data: &Value) -> Option<String> {
    let model = as_object(&data["model"]);
    let model_name = model
        .get("display_name")
        .and_then(Value::as_str)
        .filter(|text| !text.is_empty())
        .map(str::to_string)
        .or_else(|| {
            model
                .get("id")
                .and_then(Value::as_str)
                .filter(|text| !text.is_empty())
                .map(str::to_string)
        })?;
    let effort = as_object(&data["effort"])
        .get("level")
        .and_then(Value::as_str)
        .filter(|text| !text.is_empty())
        .map(str::to_string);
    Some(match effort {
        Some(effort) => format!("{model_name} · {effort}"),
        None => model_name,
    })
}

fn segment_project(data: &Value) -> Option<String> {
    let workspace = as_object(&data["workspace"]);
    let project_path = workspace
        .get("project_dir")
        .and_then(Value::as_str)
        .filter(|text| !text.is_empty())
        .map(str::to_string)
        .or_else(|| {
            workspace
                .get("current_dir")
                .and_then(Value::as_str)
                .filter(|text| !text.is_empty())
                .map(str::to_string)
        })
        .or_else(|| {
            data.get("cwd")
                .and_then(Value::as_str)
                .filter(|text| !text.is_empty())
                .map(str::to_string)
        })?;
    let trimmed = project_path.trim_end_matches('/');
    Path::new(trimmed)
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .filter(|name| !name.is_empty())
}

fn number(value: &Value) -> Option<f64> {
    match value {
        Value::Number(number) => number.as_f64(),
        Value::String(text) => text.parse::<f64>().ok(),
        _ => None,
    }
}

fn segment_context(data: &Value) -> Option<String> {
    let ctx = as_object(&data["context_window"]);
    let used = number(ctx.get("total_input_tokens").unwrap_or(&Value::Null))?;
    let size = number(ctx.get("context_window_size").unwrap_or(&Value::Null))?;
    if size == 0.0 {
        return None;
    }
    let mut text = format!(
        "{}/{}",
        format_tokens(&json!(used)),
        format_tokens(&json!(size))
    );
    if let Some(pct) = number(ctx.get("used_percentage").unwrap_or(&Value::Null)) {
        text.push_str(&format!(" ({}%)", format_g(pct)));
    }
    Some(text)
}

fn format_g(value: f64) -> String {
    if value.fract() == 0.0 {
        format!("{}", value as i64)
    } else {
        let text = format!("{value}");
        text
    }
}

fn segment_five_hour(data: &Value, now_secs: i64) -> Option<String> {
    let limits = as_object(&data["rate_limits"]);
    let five = as_object(limits.get("five_hour").unwrap_or(&Value::Null));
    let used = number(five.get("used_percentage").unwrap_or(&Value::Null))?;
    let remaining = (100.0 - used).round() as i64;
    let reset = format_reset(five.get("resets_at").unwrap_or(&Value::Null), now_secs);
    let mut text = format!("5h:{remaining}%");
    if !reset.is_empty() {
        text.push_str(&format!(" (~{reset})"));
    }
    Some(text)
}

fn segment_weekly(data: &Value) -> Option<String> {
    let limits = as_object(&data["rate_limits"]);
    let week = as_object(limits.get("seven_day").unwrap_or(&Value::Null));
    let used = number(week.get("used_percentage").unwrap_or(&Value::Null))?;
    let remaining = (100.0 - used).round() as i64;
    let reset_day = format_reset_day(week.get("resets_at").unwrap_or(&Value::Null));
    let mut text = format!("wk:{remaining}%");
    if !reset_day.is_empty() {
        text.push_str(&format!(" ({reset_day})"));
    }
    Some(text)
}

fn segment_diff(data: &Value) -> Option<String> {
    let cost = as_object(&data["cost"]);
    let added = number(cost.get("total_lines_added").unwrap_or(&Value::Null));
    let removed = number(cost.get("total_lines_removed").unwrap_or(&Value::Null));
    if added.is_none() && removed.is_none() {
        return None;
    }
    Some(format!(
        "+{}/-{}",
        added.unwrap_or(0.0) as i64,
        removed.unwrap_or(0.0) as i64
    ))
}

fn segment_tokens(data: &Value, state_dir: Option<&Path>) -> Option<String> {
    let ctx = as_object(&data["context_window"]);
    let tokens_in = number(ctx.get("total_input_tokens").unwrap_or(&Value::Null));
    let tokens_out = number(ctx.get("total_output_tokens").unwrap_or(&Value::Null));
    if tokens_in.is_none() && tokens_out.is_none() {
        return None;
    }
    let mut tokens_in = tokens_in.unwrap_or(0.0) as i64;
    let mut tokens_out = tokens_out.unwrap_or(0.0) as i64;
    let session_id = data
        .get("session_id")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    if let Some(state_dir) = state_dir {
        (tokens_in, tokens_out) = token_high_water(state_dir, &session_id, tokens_in, tokens_out);
    }
    Some(format!(
        "in:{} out:{}",
        format_tokens(&json!(tokens_in)),
        format_tokens(&json!(tokens_out))
    ))
}

fn token_high_water(state_dir: &Path, session_id: &str, mut tokens_in: i64, mut tokens_out: i64) -> (i64, i64) {
    if session_id.is_empty() || session_id.contains('/') || session_id.contains('\\') {
        return (tokens_in, tokens_out);
    }
    let path = state_dir.join(format!("tokens-{session_id}.json"));
    let _ = fs::create_dir_all(state_dir);
    let mut prev_in = 0;
    let mut prev_out = 0;
    if let Ok(raw) = fs::read_to_string(&path) {
        if let Ok(prev) = serde_json::from_str::<Value>(&raw) {
            prev_in = token_count(&prev["in"]).unwrap_or(0);
            prev_out = token_count(&prev["out"]).unwrap_or(0);
        }
    }
    tokens_in = tokens_in.max(prev_in);
    tokens_out = tokens_out.max(prev_out);
    if tokens_in > prev_in || tokens_out > prev_out {
        let tmp = PathBuf::from(format!("{}.tmp", path.display()));
        if fs::write(&tmp, json!({"in": tokens_in, "out": tokens_out}).to_string()).is_ok() {
            let _ = fs::rename(&tmp, &path);
        }
    }
    (tokens_in, tokens_out)
}

fn segment_cost(data: &Value) -> Option<String> {
    let usd = number(as_object(&data["cost"]).get("total_cost_usd").unwrap_or(&Value::Null))?;
    Some(format!("${usd:.2}"))
}

/// Parse stdin text into a payload. Malformed input is an empty object.
pub fn parse_payload(raw: &str) -> Value {
    serde_json::from_str(raw).unwrap_or_else(|_| json!({}))
}

#[cfg(test)]
mod tests {
    use super::{build_status_line, selection_from_config, Selection, SEGMENT_IDS};
    use serde_json::json;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn full_payload() -> serde_json::Value {
        json!({
            "model": {"display_name": "Opus"},
            "effort": {"level": "low"},
            "workspace": {"project_dir": "/home/u/claude_code_status_bar"},
            "context_window": {
                "total_input_tokens": 63249,
                "total_output_tokens": 5120,
                "context_window_size": 200000,
                "used_percentage": 31
            },
            "rate_limits": {
                "five_hour": {"used_percentage": 10, "resets_at": 99999999999i64},
                "seven_day": {"used_percentage": 40, "resets_at": 99999999999i64}
            },
            "cost": {"total_lines_added": 120, "total_lines_removed": 8, "total_cost_usd": 1.42}
        })
    }

    #[test]
    fn none_selection_renders_every_segment() {
        let line = build_status_line(&full_payload(), &Selection::All, 1_000, None);
        assert_eq!(line.matches('|').count(), 7);
        assert!(line.contains("in:63.2k out:5.1k"));
        assert!(line.contains("Opus · low"));
        assert!(line.contains("claude_code_status_bar"));
        assert!(line.contains("$1.42"));
    }

    #[test]
    fn empty_selection_renders_nothing() {
        let line = build_status_line(&full_payload(), &Selection::Only(vec![]), 1_000, None);
        assert_eq!(line, "");
    }

    #[test]
    fn subset_selection_keeps_registry_order() {
        let line = build_status_line(
            &full_payload(),
            &Selection::Only(vec!["cost".into(), "model".into()]),
            1_000,
            None,
        );
        assert_eq!(line, "Opus · low | $1.42");
    }

    #[test]
    fn disabled_project_segment_is_omitted() {
        let enabled = SEGMENT_IDS
            .into_iter()
            .filter(|id| *id != "project")
            .map(str::to_string)
            .collect();
        let line = build_status_line(&full_payload(), &Selection::Only(enabled), 1_000, None);
        assert!(!line.contains("claude_code_status_bar"));
        assert!(line.contains("Opus · low"));
    }

    #[test]
    fn tokens_never_shrink_inside_one_session() {
        let dir = std::env::temp_dir().join(format!(
            "status-bar-tokens-{}",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        let mut payload = full_payload();
        payload["session_id"] = json!("sess-1");
        assert_eq!(
            build_status_line(&payload, &Selection::Only(vec!["tokens".into()]), 1_000, Some(&dir)),
            "in:63.2k out:5.1k"
        );
        payload["context_window"]["total_input_tokens"] = json!(6);
        payload["context_window"]["total_output_tokens"] = json!(1);
        assert_eq!(
            build_status_line(&payload, &Selection::Only(vec!["tokens".into()]), 1_000, Some(&dir)),
            "in:63.2k out:5.1k"
        );
        payload["context_window"]["total_input_tokens"] = json!(70_000);
        assert_eq!(
            build_status_line(&payload, &Selection::Only(vec!["tokens".into()]), 1_000, Some(&dir)),
            "in:70.0k out:5.1k"
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn token_high_water_is_isolated_per_session() {
        let dir = std::env::temp_dir().join(format!(
            "status-bar-sessions-{}",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        let mut big = full_payload();
        big["session_id"] = json!("sess-a");
        assert_eq!(
            build_status_line(&big, &Selection::Only(vec!["tokens".into()]), 1_000, Some(&dir)),
            "in:63.2k out:5.1k"
        );
        let mut small = full_payload();
        small["session_id"] = json!("sess-b");
        small["context_window"]["total_input_tokens"] = json!(6);
        small["context_window"]["total_output_tokens"] = json!(1);
        assert_eq!(
            build_status_line(&small, &Selection::Only(vec!["tokens".into()]), 1_000, Some(&dir)),
            "in:6 out:1"
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn missing_config_enables_every_segment() {
        let missing = std::env::temp_dir().join(format!(
            "missing-status-conf-{}",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
        ));
        assert_eq!(selection_from_config(&missing), Selection::All);
    }

    #[test]
    fn stdin_contract_matches_the_python_bar() {
        let payload = json!({
            "model": {"display_name": "Opus"},
            "effort": {"level": "low"},
            "workspace": {"project_dir": "/work/claude_code_status_bar/"},
            "context_window": {
                "total_input_tokens": 63249,
                "total_output_tokens": 5120,
                "context_window_size": 200000,
                "used_percentage": 31
            },
            "rate_limits": {
                "five_hour": {"used_percentage": 10},
                "seven_day": {"used_percentage": 40}
            },
            "cost": {
                "total_lines_added": 120,
                "total_lines_removed": 8,
                "total_cost_usd": 1.42
            }
        });
        assert_eq!(
            build_status_line(&payload, &Selection::All, 1_000, None),
            "Opus · low | claude_code_status_bar | 63.2k/200.0k (31%) | 5h:90% | wk:60% | +120/-8 | in:63.2k out:5.1k | $1.42"
        );
    }
}
