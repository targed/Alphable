# BRIEFING — 2026-11-09T22:41:00Z

## Mission
Formulate exact file-by-file patch specifications, line-level instructions, and verification unit tests for Milestone M1 (Code Remediation & Bug Fixes: BUG-01 through BUG-07).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: /home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1
- Original parent: d0ac5384-dff3-498c-b189-b11d798c2489
- Milestone: M1 (Code Remediation & Bug Fixes)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code changes directly in source tree.
- Produce precise, actionable patch specs and test instructions in handoff.md for workers.
- Ensure all 57 core unit tests and 20 visualizer tests pass under pure CPU mode (`CUDA_VISIBLE_DEVICES=""`).

## Current Parent
- Conversation ID: d0ac5384-dff3-498c-b189-b11d798c2489
- Updated: 2026-11-09T22:41:00Z

## Investigation State
- **Explored paths**:
  - `alphable_v4/engine/magpie_bindings.py` (ctypes bindings, string allocation, memory freeing)
  - `alphable_v4/engine/move.py` (coordinate parser, UCGI line parser, tiles_placed/tiles_used)
  - `alphable_v4/search/bams.py` (volatility formula, pre-endgame parity logic, tempo bonus)
  - `alphable_v4/platform/woogles_bot.py` (Woogles command formatting, pass/exchange handling)
  - `alphable_v4/platform/eval.py` (GameSimulator, turn history, phase tagging, phase scores)
  - `alphable_v4/cli.py` (standard alternating tournament sign handling, duplicate pair phase logging)
  - `tests/` and `visualizer/tests/` (verified baseline 57 core tests and 20 visualizer tests pass in CPU mode)
- **Key findings**:
  - BUG-01: `MagpieCtypes` drops raw C pointers due to `restype = c_char_p`. Must switch to `c_void_p` and wrap in `_take_string(ptr)` invoking `magpie_free_string(ptr)`.
  - BUG-02: `bams.py` checks `len(cand.tiles_placed)` which is `""` for UCGI moves. Need `Move.get_tiles_played(rack_len)` checking `tiles_placed`, `leave`, or `word`.
  - BUG-03: `woogles_bot.py:86` checks `move.word == "--"` while `Move.make_pass()` sets `word="pass"`. Update to `move.is_pass or move.word in ("--", "pass")`.
  - BUG-04: Volatility formula has 50% jump discontinuity at $\pm 20$ pts. Replace with continuous linear ramp `clamped_ratio = max(-2.0, min(2.0, score_diff / 40.0)); lambda_vol = -0.15 * clamped_ratio`.
  - BUG-05: `Move.parse_coordinate` permits row numbers outside 1..15. Add explicit bounds validation `1 <= row_num <= 15`.
  - BUG-06: `cli.py:878-881` re-inverts sign on odd games in alternating tournaments. Replace with `margin = s1 - s2`.
  - BUG-07: Add `get_game_phase()` to `eval.py` and log `phase_scores` in `GameSimulator.play_game()`, and propagate phase score differentials in `cli.py`.
- **Unexplored areas**:
  - Implementation is handed off to worker agent.

## Key Decisions Made
- Confirmed all 7 bugs have localized, non-breaking fixes with zero regression risk to existing 57 core tests and 20 visualizer tests.
- Formulated exact patch specifications with verbatim before-and-after line replacements and dedicated unit test suites for each fix.

## Artifact Index
- DISPATCH.md — Task instructions and updates
- BRIEFING.md — Working memory and identity
- progress.md — Heartbeat and status log
- handoff.md — Comprehensive patch specifications and verification plan
