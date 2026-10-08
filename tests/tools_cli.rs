//! Public checks for the status-bar installer commands.

use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn bin() -> PathBuf {
    PathBuf::from(env!("CARGO_BIN_EXE_status-bar-tools"))
}

fn run(args: &[&str]) -> (i32, String, String) {
    let output = Command::new(bin()).args(args).output().expect("status-bar-tools");
    (
        output.status.code().unwrap_or(1),
        String::from_utf8_lossy(&output.stdout).to_string(),
        String::from_utf8_lossy(&output.stderr).to_string(),
    )
}

#[test]
fn field_init_and_claude_preview_match_the_python_contract() {
    let home = std::env::temp_dir().join(format!("status-tools-{}", std::process::id()));
    let _ = fs::remove_dir_all(&home);
    fs::create_dir_all(&home).unwrap();
    let home_s = home.to_str().unwrap();
    let (code, _, err) = run(&["field", "init", home_s]);
    assert_eq!(code, 0, "{err}");
    let selection = home.join(".config/claude_code_status_bar/field-selections.json");
    let (code, out, err) = run(&["field", "get", "claude", selection.to_str().unwrap()]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(out.trim(), r#"["model", "project", "context", "diff", "tokens", "cost"]"#);
    let (code, out, err) = run(&["preview", "component", "claude_tui", home_s]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(
        out.trim(),
        "Opus · low | claude_code_status_bar | 63.2k/200.0k (31%) | +120/-8 | in:63.2k out:5.1k | $1.42"
    );
    let (code, out, err) = run(&["preview", "component", "codex_tui", home_s]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(
        out.trim(),
        "gpt-5.5 · low · claude_code_status_bar · 69% ctx · +12/-3 · 63.2k used · in:58.1k · out:5.1k"
    );
    let _ = fs::remove_dir_all(home);
}

#[test]
fn tui_write_and_settings_wire_round_trip() {
    let home = std::env::temp_dir().join(format!("status-tools-tui-{}", std::process::id()));
    let _ = fs::remove_dir_all(&home);
    fs::create_dir_all(&home).unwrap();
    let config = home.join("config.toml");
    let (code, _, err) = run(&[
        "tui",
        "write",
        config.to_str().unwrap(),
        r#"["model-with-reasoning","current-dir"]"#,
    ]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(
        fs::read_to_string(&config).unwrap(),
        "[tui]\nstatus_line = [\"model-with-reasoning\",\"current-dir\"]\n"
    );
    let (code, out, err) = run(&["tui", "read", config.to_str().unwrap()]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(out.trim(), r#"["model-with-reasoning", "current-dir"]"#);
    let settings = home.join("settings.json");
    let script = home.join(".claude/claude-status-bar");
    let (code, _, err) = run(&["settings", settings.to_str().unwrap(), script.to_str().unwrap()]);
    assert_eq!(code, 0, "{err}");
    let text = fs::read_to_string(&settings).unwrap();
    assert!(text.contains("\"type\": \"command\""), "{text}");
    assert!(text.contains(&script.display().to_string()), "{text}");
    assert!(text.contains("\"refreshInterval\": 5"), "{text}");
    assert!(!text.contains("python3"), "{text}");
    let conf = home.join("bar.conf");
    let (code, _, err) = run(&["segment", conf.to_str().unwrap(), r#"["model","cost"]"#]);
    assert_eq!(code, 0, "{err}");
    let text = fs::read_to_string(&conf).unwrap();
    assert!(text.contains("model\n"));
    assert!(text.contains("cost\n"));
    assert!(!text.lines().any(|line| line == "project"));
    let _ = fs::remove_dir_all(home);
}
