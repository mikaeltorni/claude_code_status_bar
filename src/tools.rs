//! Installer commands that used to be separate Python scripts.
//!
//! Argument parsing lives in `parse`. Each command's result lives in its own
//! function. `run` only dispatches.

use crate::render::{build_status_line, Selection, SEGMENT_IDS};
use crate::field_terminal::{self, Key, RawTerminal};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{self, IsTerminal, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const AGENTS: [&str; 7] = ["codex", "qwen", "openrouter", "nvidia", "claude", "grok", "cline"];
const CODEX_STYLE: [&str; 4] = ["codex", "qwen", "openrouter", "nvidia"];
const CODEX_FIELDS: [&str; 13] = [
    "model-with-reasoning",
    "current-dir",
    "context-remaining",
    "five-hour-limit",
    "weekly-limit",
    "run-state",
    "context-used",
    "codex-version",
    "pull-request-number",
    "branch-changes",
    "used-tokens",
    "total-input-tokens",
    "total-output-tokens",
];
const CODEX_OFF: [&str; 6] = [
    "five-hour-limit",
    "weekly-limit",
    "run-state",
    "context-used",
    "codex-version",
    "pull-request-number",
];
const LEGACY_CODEX: [&str; 8] = [
    "model-with-reasoning",
    "current-dir",
    "git-branch",
    "context-remaining",
    "branch-changes",
    "used-tokens",
    "total-input-tokens",
    "total-output-tokens",
];
const REMOVED: [&str; 2] = ["project-name", "git-branch"];
const GROK_FIELDS: [&str; 5] = ["model", "working-directory", "session-state", "context-usage", "tool-activity"];
const CLINE_FIELDS: [&str; 5] = ["model", "workspace", "context-window", "session-cost", "diff-stats"];

/// Run one status-bar tool command.
///
/// Parameters: args - arguments after the program name.
///
/// Returns: the process exit code.
pub fn run(args: Vec<String>) -> i32 {
    match parse(&args) {
        Ok(command) => execute(command),
        Err(message) => {
            eprintln!("{message}");
            2
        }
    }
}

enum Command {
    FieldPath { home: Option<String> },
    FieldInit { home: Option<String> },
    FieldGet { agent: String, path: Option<String> },
    FieldMigrate { path: Option<String> },
    FieldConfigure { agent: String, home: Option<String> },
    FieldToml { agent: String, home: Option<String> },
    PreviewComponent { id: String, home: Option<String> },
    PreviewAggregate { home: Option<String> },
    TuiWrite { config: String, tokens: Vec<String> },
    TuiRead { config: String },
    TuiRemove { config: String },
    Segment { config: String, ids: Vec<String> },
    ConfigInit { path: String },
    SettingsWire { settings: String, script: String },
    SettingsRemove { settings: String },
    SettingsTrust { claude_json: String, project: String },
    SettingsKnown { claude_json: String },
}

fn parse(args: &[String]) -> Result<Command, String> {
    let group = args.first().ok_or_else(|| "usage: status-bar-tools COMMAND".to_string())?;
    let rest = &args[1..];
    match group.as_str() {
        "field" => parse_field(rest),
        "preview" => parse_preview(rest),
        "tui" => parse_tui(rest),
        "segment" => {
            if rest.len() < 2 {
                return Err("usage: status-bar-tools segment CONFIG JSON".into());
            }
            Ok(Command::Segment { config: rest[0].clone(), ids: json_strings(&rest[1])? })
        }
        "config" => {
            if rest.first().map(String::as_str) != Some("init") || rest.len() < 2 {
                return Err("usage: status-bar-tools config init PATH".into());
            }
            Ok(Command::ConfigInit { path: rest[1].clone() })
        }
        "settings" => parse_settings(rest),
        other => Err(format!("unknown command: {other}")),
    }
}

/// Parse all field commands before dispatch, including complete configure arity.
/// Parameters: args - raw field subcommand tokens.
/// Returns: parsed field operation or usage error.
fn parse_field(args: &[String]) -> Result<Command, String> {
    let command = args.first().ok_or_else(|| "usage: status-bar-tools field COMMAND".to_string())?;
    match command.as_str() {
        "path" => Ok(Command::FieldPath { home: field_home(args) }),
        "init" => Ok(Command::FieldInit { home: args.get(1).cloned() }),
        "migrate" => Ok(Command::FieldMigrate { path: args.get(1).cloned() }),
        "configure" if (2..=3).contains(&args.len()) => Ok(Command::FieldConfigure {
            agent: args[1].clone(), home: args.get(2).cloned(),
        }),
        "configure" => Err("usage: status-bar-tools field configure AGENT [HOME]".into()),
        "get" => Ok(Command::FieldGet {
            agent: args.get(1).cloned().ok_or_else(|| "field get needs an agent".to_string())?,
            path: path_arg(args),
        }),
        "toml-array" => Ok(Command::FieldToml {
            agent: args.get(1).cloned().ok_or_else(|| "field toml-array needs an agent".to_string())?,
            home: args.get(2).cloned(),
        }),
        other => Err(format!("unknown field command: {other}")),
    }
}

fn parse_preview(args: &[String]) -> Result<Command, String> {
    match args.first().map(String::as_str) {
        Some("component") => Ok(Command::PreviewComponent {
            id: args.get(1).cloned().unwrap_or_default(),
            home: args.get(2).cloned(),
        }),
        Some("aggregate") => Ok(Command::PreviewAggregate { home: args.get(1).cloned() }),
        _ => Err("usage: status-bar-tools preview {component|aggregate}".into()),
    }
}

fn parse_tui(args: &[String]) -> Result<Command, String> {
    let command = args.first().ok_or_else(|| "usage: status-bar-tools tui {write|read|remove}".to_string())?;
    let config = args.get(1).cloned().ok_or_else(|| "tui needs a config path".to_string())?;
    match command.as_str() {
        "write" => {
            let tokens = if args.len() > 2 {
                if args[2].starts_with('[') {
                    json_strings(&args[2])?
                } else {
                    args[2..].to_vec()
                }
            } else {
                codex_defaults()
            };
            Ok(Command::TuiWrite { config, tokens })
        }
        "read" => Ok(Command::TuiRead { config }),
        "remove" => Ok(Command::TuiRemove { config }),
        other => Err(format!("unknown tui command: {other}")),
    }
}

fn parse_settings(args: &[String]) -> Result<Command, String> {
    match args.first().map(String::as_str) {
        Some("--remove") if args.len() == 2 => Ok(Command::SettingsRemove { settings: args[1].clone() }),
        Some("--ensure-trust") if args.len() == 3 => Ok(Command::SettingsTrust {
            claude_json: args[1].clone(),
            project: args[2].clone(),
        }),
        Some("--ensure-known-trust") if args.len() == 2 => Ok(Command::SettingsKnown { claude_json: args[1].clone() }),
        Some(_) if args.len() == 2 => Ok(Command::SettingsWire { settings: args[0].clone(), script: args[1].clone() }),
        _ => Err("usage: status-bar-tools settings SETTINGS SCRIPT".into()),
    }
}

/// Dispatch parsed operations and report their output or failure status.
/// Parameters: command - fully parsed tool operation.
/// Returns: process exit status, including silent checklist cancellation.
fn execute(command: Command) -> i32 {
    let result = match command {
        Command::FieldPath { home } => Ok(format!("{}\n", selection_path(home.as_deref()).display())),
        Command::FieldInit { home } => init_fields(home.as_deref()).map(|_| String::new()),
        Command::FieldGet { agent, path } => Ok(format!("{}\n", json_array(&fields_for(&agent, path.as_deref())))),
        Command::FieldMigrate { path } => migrate(path.as_deref()).map(|_| String::new()),
        Command::FieldConfigure { agent, home } => return match configure_fields(&agent, home.as_deref()) {
            Ok(code) => code,
            Err(message) => { eprintln!("{message}"); 1 },
        },
        Command::FieldToml { agent, home } => Ok(format!("{}\n", toml_array(&fields_for(&agent, home.as_deref().map(selection_file).as_deref())))),
        Command::PreviewComponent { id, home } => Ok(format!("{}\n", preview_component(&id, home.as_deref()))),
        Command::PreviewAggregate { home } => Ok(format!("{}\n", preview_aggregate(home.as_deref()))),
        Command::TuiWrite { config, tokens } => write_tui(Path::new(&config), &tokens).map(|_| String::new()),
        Command::TuiRead { config } => Ok(format!("{}\n", json_array(&read_tui(Path::new(&config)).unwrap_or_default()))),
        Command::TuiRemove { config } => remove_tui(Path::new(&config)).map(|_| String::new()),
        Command::Segment { config, ids } => write_segments(Path::new(&config), &ids).map(|_| String::new()),
        Command::ConfigInit { path } => write_segments(Path::new(&path), &[]).map(|_| String::new()),
        Command::SettingsWire { settings, script } => wire_settings(Path::new(&settings), &script).map(|_| String::new()),
        Command::SettingsRemove { settings } => remove_settings(Path::new(&settings)).map(|_| String::new()),
        Command::SettingsTrust { claude_json, project } => trust_project(Path::new(&claude_json), &project).map(|_| String::new()),
        Command::SettingsKnown { claude_json } => trust_known(Path::new(&claude_json)).map(|_| String::new()),
    };
    match result {
        Ok(text) => {
            print!("{text}");
            0
        }
        Err(message) => {
            eprintln!("{message}");
            1
        }
    }
}

fn field_home(args: &[String]) -> Option<String> {
    if args.len() >= 3 && is_path(&args[args.len() - 1]) {
        return Some(args[args.len() - 1].clone());
    }
    args.get(2).cloned()
}

fn path_arg(args: &[String]) -> Option<String> {
    if args.len() >= 3 && is_path(&args[args.len() - 1]) {
        Some(args[args.len() - 1].clone())
    } else {
        None
    }
}

fn is_path(value: &str) -> bool {
    value.starts_with('/') || value.starts_with('.')
}

fn selection_path(home: Option<&str>) -> PathBuf {
    let home = home
        .map(PathBuf::from)
        .or_else(|| env::var_os("TARGET_HOME").map(PathBuf::from))
        .or_else(|| env::var_os("HOME").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("/"));
    home.join(".config/claude_code_status_bar/field-selections.json")
}

fn selection_file(home: &str) -> String {
    selection_path(Some(home)).display().to_string()
}

fn codex_defaults() -> Vec<String> {
    CODEX_FIELDS.iter().filter(|token| !CODEX_OFF.contains(token)).map(|token| (*token).to_string()).collect()
}

fn claude_defaults() -> Vec<String> {
    SEGMENT_IDS.iter().copied().filter(|id| !matches!(*id, "five_hour" | "weekly")).map(str::to_string).collect()
}

fn defaults_for(agent: &str) -> Vec<String> {
    let agent = component_agent(agent);
    match agent {
        "codex" | "qwen" | "openrouter" | "nvidia" => codex_defaults(),
        "claude" => claude_defaults(),
        "grok" => GROK_FIELDS.iter().map(|id| (*id).to_string()).collect(),
        "cline" => CLINE_FIELDS.iter().map(|id| (*id).to_string()).collect(),
        _ => Vec::new(),
    }
}

fn component_agent(agent: &str) -> &str {
    match agent {
        "codex_tui" => "codex",
        "qwen_tui" => "qwen",
        "openrouter_tui" => "openrouter",
        "nvidia_tui" => "nvidia",
        "claude_tui" => "claude",
        "grok_tui" => "grok",
        "cline_tui" => "cline",
        other => other,
    }
}

fn empty_document() -> Map<String, Value> {
    let mut doc = Map::new();
    for agent in AGENTS {
        doc.insert((*agent).to_string(), json!(defaults_for(agent)));
    }
    doc
}

fn load_document(path: Option<&str>) -> Map<String, Value> {
    let mut doc = empty_document();
    let Some(path) = path else {
        return doc;
    };
    let Ok(text) = fs::read_to_string(path) else {
        return doc;
    };
    let Ok(Value::Object(raw)) = serde_json::from_str::<Value>(&text) else {
        return doc;
    };
    for agent in AGENTS {
        if let Some(Value::Array(values)) = raw.get(agent) {
            doc.insert(
                (*agent).to_string(),
                json!(values.iter().filter_map(Value::as_str).map(str::to_string).collect::<Vec<_>>()),
            );
        }
    }
    doc
}

fn save_document(doc: &Map<String, Value>, path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let text = serde_json::to_string_pretty(&Value::Object(doc.clone())).map_err(|err| err.to_string())?;
    fs::write(path, format!("{text}\n")).map_err(|err| err.to_string())?;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    Ok(())
}

fn init_fields(home: Option<&str>) -> Result<(), String> {
    save_document(&empty_document(), &selection_path(home))
}

fn fields_for(agent: &str, path: Option<&str>) -> Vec<String> {
    let agent = component_agent(agent);
    let doc = load_document(path);
    doc.get(agent)
        .and_then(Value::as_array)
        .map(|values| values.iter().filter_map(Value::as_str).map(str::to_string).collect())
        .unwrap_or_else(|| defaults_for(agent))
}

/// Select the existing canonical field catalog for one supported agent.
/// Parameters: agent - normalized supported agent identifier.
/// Returns: field identifiers in canonical display order.
fn field_catalog(agent: &str) -> &'static [&'static str] {
    match agent {
        "codex" | "qwen" | "openrouter" | "nvidia" => &CODEX_FIELDS,
        "claude" => &SEGMENT_IDS,
        "grok" => &GROK_FIELDS,
        "cline" => &CLINE_FIELDS,
        _ => &[],
    }
}

/// Resolve the original checklist labels from canonical field identifiers.
/// Parameters: field - canonical field identifier.
/// Returns: the human-readable label, or the identifier for an unknown field.
fn field_label(field: &str) -> &str {
    match field {
        "model-with-reasoning" | "model" => "Model + reasoning effort",
        "current-dir" => "Current directory (active worktree)",
        "context-remaining" => "Context remaining",
        "five-hour-limit" | "five_hour" => "5-hour rate limit",
        "weekly-limit" | "weekly" => "Weekly rate limit",
        "run-state" => "Run state",
        "context-used" => "Context used",
        "codex-version" => "Codex version",
        "pull-request-number" => "Pull request number",
        "branch-changes" => "Branch changes",
        "used-tokens" => "Used tokens",
        "total-input-tokens" => "Total input tokens",
        "total-output-tokens" => "Total output tokens",
        "project" => "Repository / workspace",
        "context" => "Context window",
        "diff" => "Diff line count",
        "tokens" => "Token in/out counts",
        "cost" => "Session cost",
        "working-directory" => "Working directory",
        "session-state" => "Session / turn state",
        "context-usage" => "Context usage",
        "tool-activity" => "Tool activity indicator",
        "workspace" => "Workspace / project",
        "context-window" => "Context window usage",
        "session-cost" => "Session cost",
        "diff-stats" => "Diff line statistics",
        other => other,
    }
}

/// Draw the field rows, current preview and footer in their original order.
/// Parameters: agent - normalized agent; row - focused row; fields - current selections.
/// Returns: None on success or a terminal output error.
fn render_field_menu(agent: &str, row: usize, fields: &[String]) -> Result<(), String> {
    let title = match agent {
        "codex" => "Codex status bar fields",
        "qwen" => "Qwen (local Codex) status bar fields",
        "claude" => "Claude Code status bar segments",
        "grok" => "Grok native TUI display (reference)",
        "cline" => "Cline native TUI display (reference)",
        other => other,
    };
    let mut screen = format!("\x1b[2J\x1b[H  {title}\n");
    if matches!(agent, "grok" | "cline") {
        screen.push_str("  Grok/Cline expose no writable status_line keys; toggles affect preview only.\n\n");
    } else {
        screen.push_str("  Toggle fields with SPACE. ENTER saves, q cancels.\n\n");
    }
    for (index, field) in field_catalog(agent).iter().enumerate() {
        let mark = if row == index { "›" } else { " " };
        let box_mark = if fields.iter().any(|selected| selected == field) { "[x]" } else { "[ ]" };
        let label = if *field == "model" && matches!(agent, "grok" | "cline") { "Active model" } else { field_label(field) };
        screen.push_str(&format!("   {mark} {box_mark} {label}\n"));
    }
    let preview = preview_agent(agent, fields);
    let preview = if preview.is_empty() { "(empty)" } else { &preview };
    screen.push_str(&format!("\n  Preview: {preview}\n\n  [↑/↓] move  [space] toggle  [enter] save  [q] cancel\n"));
    // Raw mode disables output newline conversion; emit explicit terminal CRLF.
    io::stdout().write_all(screen.replace('\n', "\r\n").as_bytes()).map_err(|err| err.to_string())?;
    io::stdout().flush().map_err(|err| err.to_string())
}

/// Run the interactive checklist or retain silent non-TTY materialization.
/// Parameters: agent - agent/component selector; home - optional target home.
/// Returns: zero after save, one on cancellation, or an operation error.
fn configure_fields(agent: &str, home: Option<&str>) -> Result<i32, String> {
    let agent = component_agent(agent).to_string();
    if !AGENTS.contains(&agent.as_str()) {
        return Err(format!("unknown field agent: {agent}"));
    }
    let path = selection_path(home);
    let mut fields = fields_for(&agent, Some(&path.display().to_string()));
    let mut doc = load_document(Some(&path.display().to_string()));
    if !io::stdin().is_terminal() || !io::stdout().is_terminal() {
        doc.insert(agent, json!(fields));
        save_document(&doc, &path)?;
        return Ok(0);
    }
    let _terminal = RawTerminal::enter()?;
    let catalog = field_catalog(&agent);
    let mut row = 0_usize;
    loop {
        render_field_menu(&agent, row, &fields)?;
        match field_terminal::read_key()? {
            Key::Up => row = row.saturating_sub(1),
            Key::Down => row = (row + 1).min(catalog.len().saturating_sub(1)),
            Key::Toggle => {
                let field = catalog[row];
                if fields.iter().any(|selected| selected == field) {
                    fields.retain(|selected| selected != field);
                } else {
                    fields.push(field.to_string());
                }
                doc.insert(agent.clone(), json!(fields));
                save_document(&doc, &path)?;
            }
            Key::Save => {
                doc.insert(agent, json!(fields));
                save_document(&doc, &path)?;
                return Ok(0);
            }
            Key::Cancel => return Ok(1),
            Key::Ignore => {},
        }
    }
}

fn migrate(path: Option<&str>) -> Result<(), String> {
    let path = path.map(PathBuf::from).unwrap_or_else(|| selection_path(None));
    if !path.exists() {
        return Ok(());
    }
    let mut doc = load_document(Some(&path.display().to_string()));
    let mut changed = false;
    for agent in CODEX_STYLE {
        let current = fields_for(agent, Some(&path.display().to_string()));
        let next = if current == LEGACY_CODEX.iter().map(|s| (*s).to_string()).collect::<Vec<_>>() {
            codex_defaults()
        } else {
            current.iter().filter(|token| !REMOVED.contains(&token.as_str())).cloned().collect()
        };
        if next != current {
            doc.insert((*agent).to_string(), json!(next));
            changed = true;
        }
    }
    if changed {
        save_document(&doc, &path)?;
    }
    Ok(())
}

fn normalize_codex(tokens: &[String]) -> Vec<String> {
    CODEX_FIELDS.iter().filter(|token| tokens.iter().any(|item| item == *token)).map(|token| (*token).to_string()).collect()
}

fn toml_array(tokens: &[String]) -> String {
    let inner = normalize_codex(tokens).iter().map(|token| format!("\"{token}\"")).collect::<Vec<_>>().join(",");
    format!("[{inner}]")
}

fn json_array(tokens: &[String]) -> String {
    format!("[{}]", tokens.iter().map(|token| format!("\"{token}\"")).collect::<Vec<_>>().join(", "))
}

fn json_strings(raw: &str) -> Result<Vec<String>, String> {
    let value: Value = serde_json::from_str(raw).map_err(|err| err.to_string())?;
    Ok(value.as_array().unwrap_or(&Vec::new()).iter().filter_map(Value::as_str).map(str::to_string).collect())
}

fn write_tui(path: &Path, tokens: &[String]) -> Result<(), String> {
    let status = format!("status_line = {}\n", toml_array(tokens));
    let mut lines: Vec<String> = if path.exists() {
        fs::read_to_string(path).map_err(|err| err.to_string())?.split_inclusive('\n').map(str::to_string).collect()
    } else {
        Vec::new()
    };
    let start = lines.iter().position(|line| line.trim() == "[tui]");
    let text = if let Some(start) = start {
        let end = lines.iter().skip(start + 1).position(|line| line.trim_start().starts_with('[')).map(|offset| start + 1 + offset).unwrap_or(lines.len());
        let item = lines.iter().enumerate().skip(start + 1).take(end.saturating_sub(start + 1)).find(|(_, line)| {
            line.split('#').next().unwrap_or("").split('=').next().unwrap_or("").trim() == "status_line"
        }).map(|(index, _)| index);
        if let Some(item) = item {
            lines[item] = status;
        } else {
            lines.insert(start + 1, status);
        }
        lines.concat()
    } else {
        let mut body = lines.concat();
        body = body.trim_end().to_string();
        if !body.is_empty() {
            body.push_str("\n\n");
        }
        format!("{body}[tui]\n{status}")
    };
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    fs::write(path, text).map_err(|err| err.to_string())?;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    Ok(())
}

fn read_tui(path: &Path) -> Option<Vec<String>> {
    let text = fs::read_to_string(path).ok()?;
    let mut in_tui = false;
    for raw in text.lines() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        if line == "[tui]" {
            in_tui = true;
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            in_tui = false;
            continue;
        }
        if !in_tui {
            continue;
        }
        let (key, value) = line.split_once('=').unwrap_or((line, ""));
        if key.trim() != "status_line" {
            continue;
        }
        let value = value.trim();
        if !(value.starts_with('[') && value.ends_with(']')) {
            continue;
        }
        let body = value[1..value.len() - 1].trim();
        if body.is_empty() {
            return Some(Vec::new());
        }
        let parts = body
            .split(',')
            .map(|item| item.trim().trim_matches('"').trim_matches('\'').to_string())
            .filter(|item| CODEX_FIELDS.contains(&item.as_str()))
            .collect::<Vec<_>>();
        return Some(normalize_codex(&parts));
    }
    None
}

fn remove_tui(path: &Path) -> Result<(), String> {
    if !path.exists() {
        return Ok(());
    }
    let text = fs::read_to_string(path).map_err(|err| err.to_string())?;
    let mut lines: Vec<String> = text.split_inclusive('\n').map(str::to_string).collect();
    let Some(start) = lines.iter().position(|line| line.trim() == "[tui]") else {
        return Ok(());
    };
    let end = lines.iter().skip(start + 1).position(|line| line.trim_start().starts_with('[')).map(|offset| start + 1 + offset).unwrap_or(lines.len());
    let Some(item) = lines.iter().enumerate().skip(start + 1).take(end.saturating_sub(start + 1)).find(|(_, line)| {
        line.split('#').next().unwrap_or("").split('=').next().unwrap_or("").trim() == "status_line"
    }).map(|(index, _)| index) else {
        return Ok(());
    };
    lines.remove(item);
    let end = end - 1;
    if !lines[start + 1..end.saturating_sub(0).min(lines.len())].iter().any(|line| line.trim().len() > 0 && start + 1 < end) {
        let drop_end = end.min(lines.len());
        if drop_end > start {
            lines.drain(start..drop_end.saturating_sub(if lines.get(item).is_some() { 0 } else { 0 }));
        }
    }
    // Recompute emptiness the way the Python writer does: after deletion, a
    // [tui] table with only blank lines is removed.
    let lines = simplify_empty_tui(lines);
    fs::write(path, lines.concat()).map_err(|err| err.to_string())?;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    Ok(())
}

fn simplify_empty_tui(mut lines: Vec<String>) -> Vec<String> {
    let Some(start) = lines.iter().position(|line| line.trim() == "[tui]") else {
        return lines;
    };
    let end = lines.iter().skip(start + 1).position(|line| line.trim_start().starts_with('[')).map(|offset| start + 1 + offset).unwrap_or(lines.len());
    if !lines[start + 1..end].iter().any(|line| !line.trim().is_empty()) {
        lines.drain(start..end);
    }
    lines
}

fn config_header() -> String {
    "# claude-status-bar.conf - status-bar segment selection.\n#\n# Generated by install.sh. One enabled segment id per line; '#' comments\n# and blank lines are ignored. Re-run the installer (optionally with\n# --select id,id,...) to change which segments appear.\n# Known ids, in bar order: model, project, context, five_hour, weekly, diff, tokens, cost.\n".to_string()
}

fn write_segments(path: &Path, ids: &[String]) -> Result<(), String> {
    let body: String = SEGMENT_IDS.iter().filter(|id| ids.iter().any(|item| item == *id)).map(|id| format!("{id}\n")).collect();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    fs::write(path, format!("{}{body}", config_header())).map_err(|err| err.to_string())
}

fn shell_quote(value: &str) -> String {
    if value.is_empty() {
        return "''".to_string();
    }
    if value.chars().all(|ch| ch.is_ascii_alphanumeric() || "@%+=:,./-_".contains(ch)) {
        return value.to_string();
    }
    format!("'{}'", value.replace('\'', "'\"'\"'"))
}

fn wire_settings(path: &Path, script: &str) -> Result<(), String> {
    let mut settings = read_object(path);
    settings.insert(
        "statusLine".to_string(),
        json!({"type": "command", "command": shell_quote(script), "refreshInterval": 5}),
    );
    write_pretty(path, &Value::Object(settings))
}

fn remove_settings(path: &Path) -> Result<(), String> {
    if !path.exists() {
        return Ok(());
    }
    let mut settings = read_object(path);
    if settings.remove("statusLine").is_none() {
        return Ok(());
    }
    write_pretty(path, &Value::Object(settings))
}

fn trust_project(path: &Path, project: &str) -> Result<(), String> {
    let key = Path::new(project).canonicalize().map_err(|err| err.to_string())?;
    let mut data = read_object(path);
    let projects = data.entry("projects".to_string()).or_insert_with(|| json!({}));
    if !projects.is_object() {
        *projects = json!({});
    }
    let projects = projects.as_object_mut().unwrap();
    let entry = projects.entry(key.display().to_string()).or_insert_with(|| json!({}));
    if !entry.is_object() {
        *entry = json!({});
    }
    if entry.get("hasTrustDialogAccepted").and_then(Value::as_bool) == Some(true) {
        return Ok(());
    }
    entry.as_object_mut().unwrap().insert("hasTrustDialogAccepted".to_string(), Value::Bool(true));
    write_compact(path, &Value::Object(data))
}

fn trust_known(path: &Path) -> Result<(), String> {
    let data = read_object(path);
    let Some(projects) = data.get("projects").and_then(Value::as_object).cloned() else {
        return Ok(());
    };
    for (raw, _) in projects {
        let project = PathBuf::from(&raw);
        if project.is_dir() {
            trust_project(path, &raw)?;
        }
    }
    Ok(())
}

fn read_object(path: &Path) -> Map<String, Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|value| match value {
            Value::Object(map) => Some(map),
            _ => None,
        })
        .unwrap_or_default()
}

fn write_pretty(path: &Path, value: &Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let text = serde_json::to_string_pretty(value).map_err(|err| err.to_string())?;
    fs::write(path, format!("{text}\n")).map_err(|err| err.to_string())
}

fn write_compact(path: &Path, value: &Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let text = serde_json::to_string(value).map_err(|err| err.to_string())?;
    fs::write(path, format!("{text}\n")).map_err(|err| err.to_string())
}

fn preview_component(id: &str, home: Option<&str>) -> String {
    let agent = component_agent(id);
    if !AGENTS.contains(&agent) {
        return String::new();
    }
    let path = home.map(selection_file);
    preview_agent(agent, &fields_for(agent, path.as_deref()))
}

fn preview_aggregate(home: Option<&str>) -> String {
    let labels = [
        ("codex", "Codex"),
        ("qwen", "Qwen"),
        ("openrouter", "OpenRouter"),
        ("nvidia", "NVIDIA"),
        ("claude", "Claude"),
        ("grok", "Grok"),
        ("cline", "Cline"),
    ];
    labels
        .iter()
        .filter_map(|(agent, label)| {
            let line = preview_component(agent, home);
            if line.is_empty() { None } else { Some(format!("[{label}] {line}")) }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn preview_agent(agent: &str, fields: &[String]) -> String {
    if agent == "claude" {
        let now = 1_700_000_000_i64;
        let data = json!({
            "model": {"display_name": "Opus"},
            "effort": {"level": "low"},
            "workspace": {"project_dir": "/home/u/claude_code_status_bar"},
            "context_window": {"total_input_tokens": 63249, "total_output_tokens": 5120, "context_window_size": 200000, "used_percentage": 31},
            "rate_limits": {"five_hour": {"used_percentage": 10, "resets_at": 99999999999_i64}, "seven_day": {"used_percentage": 40, "resets_at": 99999999999_i64}},
            "cost": {"total_lines_added": 120, "total_lines_removed": 8, "total_cost_usd": 1.42}
        });
        return build_status_line(&data, &Selection::Only(fields.to_vec()), now, None);
    }
    let fixture = match agent {
        "qwen" => qwen_fixture(),
        "openrouter" => openrouter_fixture(),
        "nvidia" => nvidia_fixture(),
        "grok" => grok_fixture(),
        "cline" => cline_fixture(),
        _ => codex_fixture(),
    };
    fields.iter().filter_map(|token| fixture.get(token).cloned()).collect::<Vec<_>>().join(" · ")
}

fn codex_fixture() -> HashMap<String, String> {
    HashMap::from_iter([
        ("model-with-reasoning", "gpt-5.5 · low"),
        ("current-dir", "claude_code_status_bar"),
        ("context-remaining", "69% ctx"),
        ("five-hour-limit", "5h:90%"),
        ("weekly-limit", "wk:60%"),
        ("run-state", "idle"),
        ("context-used", "63.2k/200.0k"),
        ("codex-version", "codex 0.42"),
        ("pull-request-number", "PR #128"),
        ("branch-changes", "+12/-3"),
        ("used-tokens", "63.2k used"),
        ("total-input-tokens", "in:58.1k"),
        ("total-output-tokens", "out:5.1k"),
    ].into_iter().map(|(key, value)| (key.to_string(), value.to_string())))
}

fn qwen_fixture() -> HashMap<String, String> {
    let mut fixture = codex_fixture();
    fixture.insert("model-with-reasoning".to_string(), "ornstein3.6-35b · high".to_string());
    fixture.insert("current-dir".to_string(), "agent_command_center".to_string());
    fixture.insert("context-remaining".to_string(), "42% ctx".to_string());
    fixture
}

fn openrouter_fixture() -> HashMap<String, String> {
    let mut fixture = qwen_fixture();
    fixture.insert("model-with-reasoning".to_string(), "nvidia/nemotron-3-ultra-550b-a55b:free · high".to_string());
    fixture
}

fn nvidia_fixture() -> HashMap<String, String> {
    let mut fixture = qwen_fixture();
    fixture.insert("model-with-reasoning".to_string(), "deepseek-ai/deepseek-v4-pro · high".to_string());
    fixture
}

fn grok_fixture() -> HashMap<String, String> {
    HashMap::from_iter([
        ("model", "grok-build"),
        ("working-directory", "installation_scripts"),
        ("session-state", "ready"),
        ("context-usage", "18% ctx"),
        ("tool-activity", "2 tools"),
    ].into_iter().map(|(key, value)| (key.to_string(), value.to_string())))
}

fn cline_fixture() -> HashMap<String, String> {
    HashMap::from_iter([
        ("model", "claude-sonnet-4"),
        ("workspace", "linux_programming_setup"),
        ("context-window", "41% ctx"),
        ("session-cost", "$0.84"),
        ("diff-stats", "+45/-6"),
    ].into_iter().map(|(key, value)| (key.to_string(), value.to_string())))
}
