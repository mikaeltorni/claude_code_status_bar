"""Behavioral regression tests for the Claude Code status-bar command."""

import json
from pathlib import Path
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_BAR = REPO_ROOT / "claude-status-bar"


def run_status_bar(payload: str) -> subprocess.CompletedProcess[str]:
    """Run the status-bar executable with raw stdin content."""
    return subprocess.run(
        [str(STATUS_BAR)],
        input=payload,
        capture_output=True,
        check=False,
        text=True,
    )


class StatusBarCommandTests(unittest.TestCase):
    """Verify the command's public stdin-to-stdout behavior."""

    def test_renders_all_status_segments(self):
        payload = {
            "model": {"display_name": "Opus"},
            "effort": {"level": "low"},
            "workspace": {"project_dir": "/work/claude_code_status_bar/"},
            "context_window": {
                "total_input_tokens": 63_249,
                "total_output_tokens": 5_120,
                "context_window_size": 200_000,
                "used_percentage": 31,
            },
            "rate_limits": {
                "five_hour": {"used_percentage": 10},
                "seven_day": {"used_percentage": 40},
            },
            "cost": {
                "total_lines_added": 120,
                "total_lines_removed": 8,
                "total_cost_usd": 1.42,
            },
        }

        result = run_status_bar(json.dumps(payload))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "Opus · low | claude_code_status_bar | 63.2k/200.0k (31%)"
            " | 5h:90% | wk:60% | +120/-8 | in:63.2k out:5.1k | $1.42\n",
        )

    def test_uses_model_and_workspace_fallbacks(self):
        payload = {
            "model": {"id": "claude-test"},
            "workspace": {"current_dir": "/work/fallback-project"},
        }

        result = run_status_bar(json.dumps(payload))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "claude-test | fallback-project\n")

    def test_renders_blank_line_for_empty_or_malformed_input(self):
        for payload in ("{}", "not json"):
            with self.subTest(payload=payload):
                result = run_status_bar(payload)

                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout, "\n")

    def test_omits_malformed_numeric_segments(self):
        payload = {
            "model": {"display_name": "Opus"},
            "context_window": {
                "total_input_tokens": "bad",
                "context_window_size": 200_000,
                "used_percentage": "bad",
            },
            "rate_limits": {
                "five_hour": {"used_percentage": "bad"},
                "seven_day": {"used_percentage": "bad"},
            },
            "cost": {
                "total_lines_added": "bad",
                "total_lines_removed": "also-bad",
                "total_cost_usd": "bad",
            },
        }

        result = run_status_bar(json.dumps(payload))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "Opus\n")


if __name__ == "__main__":
    unittest.main()
