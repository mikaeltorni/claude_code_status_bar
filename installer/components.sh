#!/usr/bin/env bash
# components.sh - Five-agent TUI status-bar manifest for claude_code_status_bar.
#
# Entry: id|label|default|install_fn[|detect|uninstall|section|requires|configure_fn|config_status_fn]
# Order: Codex, Qwen (local Codex), Claude Code, Grok, Cline.

ISC_REPO_NAME="claude_code_status_bar"
ISC_REPO_LABEL="Agent TUI status bars"

ISC_COMPONENTS=(
  "codex_tui|Codex TUI status bar|on|status_bar_install_codex|detect_codex_tui|status_bar_uninstall_codex|Codex||status_bar_configure_codex_fields|status_bar_codex_preview_status"
  "qwen_tui|Qwen (local Codex) TUI status bar|on|status_bar_install_qwen|detect_qwen_tui|status_bar_uninstall_qwen|Qwen||status_bar_configure_qwen_fields|status_bar_qwen_preview_status"
  "openrouter_tui|OpenRouter (Codex) TUI status bar|on|status_bar_install_openrouter|detect_openrouter_tui|status_bar_uninstall_openrouter|OpenRouter||status_bar_configure_openrouter_fields|status_bar_openrouter_preview_status"
  "nvidia_tui|NVIDIA (Codex) TUI status bar|on|status_bar_install_nvidia|detect_nvidia_tui|status_bar_uninstall_nvidia|NVIDIA||status_bar_configure_nvidia_fields|status_bar_nvidia_preview_status"
  "claude_tui|Claude Code status bar|on|status_bar_install_claude|detect_claude_tui|status_bar_uninstall_claude|Claude Code||status_bar_configure_claude_fields|status_bar_claude_preview_status"
  "grok_tui|Grok TUI display|on|status_bar_install_grok|detect_grok_tui|status_bar_uninstall_grok|Grok||status_bar_configure_grok_fields|status_bar_grok_preview_status"
  "cline_tui|Cline TUI display|on|status_bar_install_cline|detect_cline_tui|status_bar_uninstall_cline|Cline||status_bar_configure_cline_fields|status_bar_cline_preview_status"
)