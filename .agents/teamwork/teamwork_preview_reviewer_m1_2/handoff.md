# Milestone M1 Reviewer 2 & Adversarial Audit Report

**Document**: `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_reviewer_m1_2/handoff.md`  
**Reviewer**: M1 Reviewer 2 & Adversarial Critic (`teamwork_preview_reviewer_m1_2`)  
**Parent Orchestrator**: `d0ac5384-dff3-498c-b189-b11d798c2489`  
**Date**: 2026-11-09T22:59:00Z  
**Target Milestone**: Milestone M1 (Code Remediation & Bug Fixes: BUG-01 through BUG-07)  
**Verdict**: **APPROVE**  
**Overall Risk Assessment**: LOW (0 integrity violations, 0 regressions, all 7 bugs genuine and mathematically sound)

---

## 1. Observation

### 1.1 Direct Inspection of Source Modifications
We performed an exhaustive line-by-line code audit of all changes introduced by Worker M1 (`teamwork_preview_worker_m1_1`):

1. **`alphable_v4/engine/magpie_bindings.py` (Lines 94–115, 188–221)**
   - Ctypes function signatures for `magpie_get_last_command_output`, `magpie_get_and_clear_error`, `magpie_get_last_command_status_message` were converted from `ctypes.c_char_p` to `ctypes.c_void_p`.
   - `magpie_free_string.argtypes` set to `[ctypes.c_void_p]`.
   - `MagpieEngine._take_string(ptr: Optional[int]) -> str` implemented:
     ```python
     def _take_string(self, ptr: Optional[int]) -> str:
         """Copies a C string returned by libmagpie and immediately frees the C heap allocation."""
         if not ptr:
             return ""
         val = ctypes.string_at(ptr).decode("utf-8")
         self._ctypes._cdll.magpie_free_string(ptr)
         return val
     ```
   - All C outputs and errors in `__init__` and `run_command` are routed through `_take_string(ptr)`.

2. **`alphable_v4/engine/move.py` (Lines 68–88, 124–157, 212–230)**
   - `Move.get_tiles_played(self, rack_len: int = 7) -> int` implemented with priority handling: pass (0), exchange (`len(word)`), explicit `tiles_placed` (`len(tiles_placed)`), leave calculation (`max(1, rack_len - len(leave))`), and fallback `min(rack_len, len(word))`.
   - `Move.parse_coordinate(cls, coord: str)` validates bounds `1 <= row_num <= 15` and `[A-O]` for both Across and Down coordinates.
   - `Move.from_ucgi_line` catches `ValueError` from invalid coordinates and propagates `tiles_placed`.

3. **`alphable_v4/search/bams.py` (Lines 344–353, 532–564)**
   - Asymmetric volatility control formula replaced with a continuous linear ramp:
     ```python
     clamped_ratio = max(-2.0, min(2.0, float(score_diff) / 40.0))
     lambda_vol = -0.15 * clamped_ratio
     ```
   - In `_evaluate_pre_endgame`: dynamic `rack_size = len(game_state.rack) if game_state.rack else 7`, calling `cand.get_tiles_played(rack_len=rack_size)`, correctly activating the +2.0 tempo bonus when `tiles_played >= bag_count`.

4. **`alphable_v4/platform/woogles_bot.py` (Lines 84–90)**
   - Pass move check updated to:
     ```python
     if move.is_pass or move.word in ("--", "pass"):
         cmd_str = "pass"
     else:
         cmd_str = f"exchange {move.word}"
     ```

5. **`alphable_v4/platform/eval.py` (Lines 91–107, 139–345)**
   - `get_game_phase(turn_num: int, bag_count: int) -> str` implemented:
     - `bag_count == 0`: `"endgame"`
     - `1 <= bag_count <= 14`: `"pre_endgame"`
     - `turn_num <= 5`: `"opening"`
     - else: `"midgame"`
   - `GameSimulator.play_game` records `phase_scores` and `phase_counts`, adds `"phase"` to each entry in `turn_history`, and maps endgame bonuses/penalties to `"endgame"`.

6. **`alphable_v4/cli.py` (Lines 745–752, 805–811, 893–928)**
   - Margin calculation fixed to `margin = s1 - s2` unconditionally.
   - Per-phase score spreads mapped into `pair_records` (duplicate mode) and `game_records` (alternating mode).

7. **Test Suites**
   - `tests/engine/test_bug_fixes.py` (319 lines, 9 tests) and `tests/test_m1_remediation.py` verify all 7 remediations.

### 1.2 Independent Verification Test Execution
All test suites were executed independently under Python 3.11:

```bash
# Core test suite + E2E suite
PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
-m pytest tests/ -v
# Result: 162 passed, 2 skipped in 37.00s

# Visualizer test suite
PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
-m pytest visualizer/tests/ -v
# Result: 20 passed, 1 skipped in 5.43s
```

---

## 2. Logic Chain

1. **Memory Safety (BUG-01)**:
   - Observation: With `c_char_p`, ctypes auto-converts the pointer into a Python `bytes` object, immediately discarding the raw C pointer address and preventing `magpie_free_string(ptr)` from being called.
   - Logic: Switching to `c_void_p` preserves the exact memory address as an integer. `_take_string` uses `ctypes.string_at(ptr)` to copy the null-terminated buffer into Python, then invokes `magpie_free_string(ptr)`.
   - Verification: Spy interceptor in `test_bug01_c_memory_management_and_freeing` confirmed `magpie_free_string` is invoked with valid non-zero pointer addresses on every command and error query. Null pointers (`None`, `0`) return `""` without crashing.

2. **Pre-Endgame Parity Accounting (BUG-02)**:
   - Observation: `cand.tiles_placed` was empty string for standard MAGPIE moves, causing `len(cand.tiles_placed) == 0`. Consequently, `tiles_played >= bag_count` was never satisfied when `bag_count > 0`.
   - Logic: `Move.get_tiles_played(rack_len)` computes rack depletion using `max(1, rack_len - len(leave))` when leave is present. In `BAMSSearch._evaluate_pre_endgame`, `tiles_played` reflects true rack consumption, correctly granting `parity_delta += 2.0` when the play empties the bag.

3. **Protocol Conformance (BUG-03)**:
   - Observation: `Move.make_pass()` creates `Move(is_pass=True, word="pass")`. Previously `woogles_bot.py` checked only `if move.word == "--"`, causing passes to format as `"exchange pass"`.
   - Logic: Checking `move.is_pass or move.word in ("--", "pass")` guarantees `"pass"` is generated.

4. **Mathematical Continuity of Volatility Scaling (BUG-04)**:
   - Observation: The legacy formula branched at `score_diff = ±20.0`, resulting in a jump discontinuity of $\Delta \lambda = 0.075$ (a 50% jump in volatility multiplier).
   - Logic: Let $x = \text{score\_diff}$. The updated formula $\lambda_{\text{vol}}(x) = -0.15 \times \text{clamp}(-2.0, 2.0, \frac{x}{40.0})$:
     - Is $C^0$ continuous everywhere on $\mathbb{R}$.
     - At $x = 0$: $\lambda_{\text{vol}}(0) = 0.0$.
     - At $x = 20$: $\lim_{x \to 20^-} \lambda_{\text{vol}}(x) = \lim_{x \to 20^+} \lambda_{\text{vol}}(x) = -0.075$.
     - At $x = -20$: $\lim_{x \to -20^-} \lambda_{\text{vol}}(x) = \lim_{x \to -20^+} \lambda_{\text{vol}}(x) = +0.075$.
     - At $x = \pm 80$: saturates cleanly at $\mp 0.30$ and remains constant for $|x| \ge 80$.
     - Displays strict odd symmetry: $\lambda_{\text{vol}}(-x) = -\lambda_{\text{vol}}(x)$.
     - Correctly aligns with game theory: penalizes variance when leading ($x > 0 \implies \lambda < 0$), rewards variance when trailing ($x < 0 \implies \lambda > 0$).

5. **Coordinate Validation (BUG-05)**:
   - Observation: Legacy regex allowed arbitrary integers, permitting `"0A"` (evaluating to row index `-1`, indexing the bottom board row in Python) and `"16A"` (`IndexError`).
   - Logic: Adding explicit checks `1 <= row_num <= 15` in both Across and Down branches ensures strict adherence to standard Scrabble coordinate boundaries.

6. **Tournament Margin Sign (BUG-06)**:
   - Observation: In alternating tournament games, `s1` and `s2` are already assigned to Model 1 and Model 2 respectively. Inverting them again on odd games produced inverted margins.
   - Logic: Computing `margin = s1 - s2` unconditionally guarantees positive margins always represent Model 1 advantages.

7. **Game Phase Telemetry (BUG-07)**:
   - Observation: Need per-phase attribution to audit strategic edge across opening, midgame, pre-endgame, and endgame.
   - Logic: Moves are tagged with `get_game_phase`, scores accumulated into `phase_scores`, and the sum of phase scores across all 4 phases exactly matches final game scores: $\sum_{\text{phase}} \text{score}_{\text{phase}} = \text{score}_{\text{total}}$.

8. **Integrity Violations Check**:
   - Zero hardcoded test values, facade methods, or bypass shortcuts were found. All remediations are genuine algorithmic implementations.

---

## 3. Caveats

1. **Python Environment Compatibility**:
   - System `/usr/bin/python3` is Python 3.14, whereas repository dependencies (`numpy 2.4.0`, `torch 2.5.1`) are compiled for CPython 3.11.
   - Commands must specify `PYTHONHOME` pointing to `/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux` and use the 3.11 executable.
2. **Exception Safety in `_take_string`**:
   - In `alphable_v4/engine/magpie_bindings.py`, `_take_string` decodes bytes before calling `magpie_free_string(ptr)` without an explicit `try ... finally` block. While MAGPIE outputs are standard ASCII strings and decode failures do not occur under normal operation, wrapping string decoding in `try ... finally` is recommended for bulletproof exception safety.
3. **Turn Definition vs Ply in Phase Classification**:
   - `turn_num` increments once per ply (half-move). Consequently, `turn_num <= 5` encompasses 3 plies for Player 1 and 2 plies for Player 2. In duplicate tournament matches, because seats swap between Game A and Game B, this asymmetry cancels out symmetrically.

---

## 4. Conclusion

The code remediation for Milestone M1 (BUG-01 through BUG-07) is **fully verified, mathematically sound, robust against edge cases, and completely regression-free**.
All 162 core unit/integration/E2E tests and 20 visualizer tests pass cleanly.

**Final Verdict: APPROVE**

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Execute M1 Dedicated Bug Fix Tests**:
   ```bash
   PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
   CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
   /home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
   -m pytest tests/engine/test_bug_fixes.py -v
   ```
   *Expected: 9 passed in <1.0s.*

2. **Execute Full Core & E2E Test Suite**:
   ```bash
   PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
   CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
   /home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
   -m pytest tests/ -v
   ```
   *Expected: 162 passed, 2 skipped in ~37s.*

3. **Execute Visualizer Test Suite**:
   ```bash
   PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
   CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
   /home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
   -m pytest visualizer/tests/ -v
   ```
   *Expected: 20 passed, 1 skipped in ~5s.*

4. **Adversarial Python Boundary Harness**:
   Verify continuous ramp and boundary handling across extreme inputs:
   ```bash
   PYTHONHOME=/home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux \
   CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. \
   /home/targed/Documents/unreal-engine-bin/Linux_Unreal_Engine_5.6.1/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3.11 \
   -c "
   from alphable_v4.engine.move import Move
   from alphable_v4.platform.eval import get_game_phase
   for c in ['1A', '15O', '8H', 'A1', 'O15', 'H8']: Move.parse_coordinate(c)
   for b in ['0A', '16A', 'A0', 'A16']: 
       try: Move.parse_coordinate(b); assert False
       except ValueError: pass
   assert get_game_phase(1, 86) == 'opening' and get_game_phase(6, 0) == 'endgame'
   print('Verified!')
   "
   ```
   *Expected: 'Verified!' printed.*
