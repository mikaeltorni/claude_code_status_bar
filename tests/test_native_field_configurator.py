"""Drive the shipped native field configurator through an isolated terminal."""

import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import termios
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "target/release/status-bar-tools"
AGENTS = ("codex", "qwen", "openrouter", "nvidia", "claude", "grok", "cline")
SELECTED = {agent: ["model-with-reasoning", "current-dir"] for agent in AGENTS[:4]}
SELECTED.update(claude=["model", "cost"], grok=["model", "working-directory"], cline=["model", "workspace"])
AFTER_PREVIEW = {"codex": "claude_code_status_bar", "qwen": "agent_command_center", "openrouter": "agent_command_center", "nvidia": "agent_command_center", "claude": "$1.42", "grok": "installation_scripts", "cline": "linux_programming_setup"}


def selection(home):
    """Populate independently expected nonempty selections for every agent.

    Parameters: home - isolated target home.
    Returns: populated selection path.
    """
    print(f"home={home}")
    path = home / ".config/claude_code_status_bar/field-selections.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(SELECTED))
    print(path)
    return path


def query(agent, path):
    """Read configured fields through the native public query.

    Parameters: agent - agent identifier; path - persisted selection file.
    Returns: decoded field identifiers.
    """
    print(f"agent={agent}, path={path}")
    result = subprocess.run([str(TOOLS), "field", "get", agent, str(path)], capture_output=True, text=True, check=True)
    fields = json.loads(result.stdout)
    print(fields)
    return fields


def terminal_run(home, keys, agent="codex", command=None, stop_signal=None):
    """Run the public configurator in a private PTY and check mode restoration.

    Parameters: home - isolated home; keys - sequential key inputs; agent - chosen agent; command - optional reference CLI; stop_signal - optional termination signal after render.
    Returns: exit code and terminal transcript.
    """
    print(f"home={home}, keys={keys}, agent={agent}, command={command}, stop_signal={stop_signal}")
    master, slave = pty.openpty()
    before = termios.tcgetattr(slave)
    process = subprocess.Popen(command or [str(TOOLS), "field", "configure", agent, str(home)], stdin=slave, stdout=slave, stderr=slave, env=dict(os.environ, TARGET_HOME=str(home)))
    transcript = bytearray()
    try:
        pending = [None, *keys]
        for key in pending:
            if key is not None:
                os.write(master, key)
            if key in (b"\r", b"q", b"\x1b", b"\x03"):
                break
            frame = bytearray()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.02)
                if ready:
                    chunk = os.read(master, 65536)
                    frame.extend(chunk)
                    transcript.extend(chunk)
                if b"[q] cancel" in frame and not (termios.tcgetattr(slave)[3] & termios.ICANON):
                    break
                assert process.poll() is None, "configurator exited before its checklist opened"
            else:
                raise AssertionError("configurator did not render a ready checklist")
        if stop_signal is not None:
            process.send_signal(stop_signal)
        code = process.wait(timeout=3)
        while select.select([master], [], [], 0)[0]:
            transcript.extend(os.read(master, 65536))
        assert termios.tcgetattr(slave) == before, "terminal mode was not restored"
        result = (code, transcript.decode(errors="replace"))
        print(result)
        return result
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)


@pytest.mark.parametrize("agent", AGENTS)
def test_checklist_toggles_and_previews_each_agent(tmp_path, agent):
    """Toggle the first catalog field and save every agent through the real CLI.

    Parameters: tmp_path - isolated target home; agent - parameterized supported agent.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}, agent={agent}")
    path = selection(tmp_path)
    code, transcript = terminal_run(tmp_path, [b" ", b"\r"], agent)
    assert code == 0
    assert "[x] Model" in transcript or "[x] Active model" in transcript
    assert f"Preview: {AFTER_PREVIEW[agent]}" in transcript
    assert query(agent, path) == SELECTED[agent][1:]
    for other in AGENTS:
        if other != agent:
            assert query(other, path) == SELECTED[other]
    assert path.stat().st_mode & 0o777 == 0o600
    print(None)


def test_arrow_navigation_clamps_and_ignores_horizontal_arrows(tmp_path):
    """Clamp upward movement, move down and ignore the unrelated horizontal key.

    Parameters: tmp_path - isolated populated home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    path = selection(tmp_path)
    code, transcript = terminal_run(tmp_path, [b"\x1b[A", b"\x1b[B", b"\x1b[C", b" ", b"\r"])
    assert code == 0
    assert "Current directory (active worktree)" in transcript
    assert query("codex", path) == ["model-with-reasoning"]
    print(None)


def test_downward_navigation_clamps_at_final_field(tmp_path):
    """Keep the final row selected after movement beyond the catalog boundary.

    Parameters: tmp_path - isolated populated home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    path = selection(tmp_path)
    code, _ = terminal_run(tmp_path, [*[b"\x1b[B"] * 20, b" ", b"\r"])
    assert code == 0
    assert query("codex", path) == ["model-with-reasoning", "current-dir", "total-output-tokens"]
    print(None)


@pytest.mark.parametrize("key", [b"q", b"\x1b", b"\x03"])
def test_cancel_without_toggle_preserves_selection(tmp_path, key):
    """Cancel with q, bare Escape or Ctrl+C without changing populated selections.

    Parameters: tmp_path - isolated home; key - cancellation key.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}, key={key}")
    path = selection(tmp_path)
    before = path.read_bytes()
    code, _ = terminal_run(tmp_path, [key])
    assert code == 1
    assert query("codex", path) == SELECTED["codex"]
    assert path.read_bytes() == before
    print(None)


def test_toggle_then_cancel_retains_original_immediate_persistence(tmp_path):
    """Keep the original configurator's persisted toggle even when q ends the menu.

    Parameters: tmp_path - isolated target home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    path = selection(tmp_path)
    code, _ = terminal_run(tmp_path, [b" ", b"q"])
    assert code == 1
    assert query("codex", path) == ["current-dir"]
    print(None)


def test_non_terminal_configure_retains_selection_silently(tmp_path):
    """Preserve the inherited non-TTY behavior without drawing a checklist.

    Parameters: tmp_path - isolated home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    path = selection(tmp_path)
    for _ in range(2):
        result = subprocess.run([str(TOOLS), "field", "configure", "codex_tui", str(tmp_path)], capture_output=True, text=True)
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
        assert query("codex", path) == SELECTED["codex"]
    print(None)


@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_termination_restores_terminal_and_preserves_selection(tmp_path, stop_signal):
    """Handle only the private menu child's termination without leaving raw input.

    Parameters: tmp_path - isolated home; stop_signal - cancellation signal for the private child.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}, stop_signal={stop_signal}")
    path = selection(tmp_path)
    before = path.read_bytes()
    code, _ = terminal_run(tmp_path, [], stop_signal=stop_signal)
    assert code == 1
    assert query("codex", path) == SELECTED["codex"]
    assert path.read_bytes() == before
    print(None)


def test_bad_configure_arguments_preserve_selection(tmp_path):
    """Reject missing, extra or unknown-agent configuration without writing state.

    Parameters: tmp_path - isolated populated home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    path = selection(tmp_path)
    before = path.read_bytes()
    for args, expected in [(["field", "configure"], 2), (["field", "configure", "codex", str(tmp_path), "extra"], 2), (["field", "configure", "unknown", str(tmp_path)], 1)]:
        result = subprocess.run([str(TOOLS), *args], capture_output=True, text=True)
        assert result.returncode == expected
        assert query("codex", path) == SELECTED["codex"]
        assert path.read_bytes() == before
    print(None)
