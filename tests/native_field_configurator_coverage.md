# Native field configurator regression

Runner: `python3 -m pytest -q tests/test_native_field_configurator.py` after
`cargo build --offline --locked --release`.

| Rule | Assertions |
| --- | --- |
| All seven checklists, live preview, first-field toggle, save | `test_checklist_toggles_and_previews_each_agent`: real private terminal, independently expected preview and public field query; every other agent unchanged; private file mode. |
| Arrow movement and clamping | `test_arrow_navigation_clamps_and_ignores_horizontal_arrows`: up at first row, down to second, right ignored, independent persisted fields. `test_downward_navigation_clamps_at_final_field`: beyond final row, correct last-field selection. |
| q / bare Escape / Ctrl+C | `test_cancel_without_toggle_preserves_selection`: nonzero cancellation, immediate public query and byte preservation. Every PTY call asserts restored terminal mode. |
| Original toggle persistence | `test_toggle_then_cancel_retains_original_immediate_persistence`: toggle writes immediately, as original Python does, even when q exits. |
| Non-TTY and component aliases | `test_non_terminal_configure_retains_selection_silently`: alias accepted, twice silent, existing public selections retained. |
| Process interruption | `test_termination_restores_terminal_and_preserves_selection`: SIGINT/SIGTERM/SIGHUP to only the private child, restored mode, immediate public query and byte preservation. |
| Missing/extra argument and unknown agent | `test_bad_configure_arguments_preserve_selection`: expected rejection status, immediate informative public query and byte preservation after each rejection. |

Textual selectors have no numeric conversion contract. Existing Rust tests cover
other command dispatch, config writes and fixture previews. These tests never
open a window or a visible terminal; only their own PTY child may be killed for
cleanup. Test homes contain only synthetic data. Bare Escape and Ctrl+C restore
the terminal and do not block awaiting an incomplete escape sequence.
