# Implementation Plan: Scrabble Engine Fixes

## Overview

This implementation plan addresses critical issues in the Scrabble engine by fixing negative scores, preventing move repetition, and validating cross-words. The approach is incremental, with each task building on previous work and including validation through tests.

**Execution Environment**: All commands must be run in WSL:

```bash
wsl
source /venv/lib/activate
```

## Tasks

- [x] 1. Implement score floor constraints

  - Modify `apply_penalty` to use `max(0.0, score - penalty)`
  - Update all score modification points to enforce non-negative constraint
  - Add `adjust_final_scores` method for end-game score calculation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.5_

- [ ]\* 1.1 Write property test for score non-negativity

  - **Property 1: Score Non-Negativity**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 6.5**
  - Generate random game states and penalties
  - Assert scores always >= 0 after any operation

- [ ]\* 1.2 Write unit tests for score floor edge cases

  - Test penalty with score at 0
  - Test multiple penalties in sequence
  - Test final score calculation with negative intermediates
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement cross-word validation

  - [x] 2.1 Add `find_cross_words` method to identify perpendicular words

    - For each placed tile, scan perpendicular direction
    - Extract full cross-word including new tile
    - Return list of (word, row, col, direction) tuples
    - _Requirements: 4.1_

  - [x] 2.2 Add `validate_cross_words` method using GADDAG

    - Use `_fast_word_check` for each cross-word
    - Return True only if all cross-words are valid
    - _Requirements: 4.2, 4.3_

  - [x] 2.3 Integrate cross-word validation into `_validate_move`

    - Call `find_cross_words` for each move
    - Call `validate_cross_words` before accepting move
    - Reject move if any cross-word is invalid
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 2.4 Update `_score_move` to include cross-word scores
    - Calculate score for each cross-word
    - Apply premium squares to cross-words correctly
    - Add cross-word scores to total
    - _Requirements: 4.4, 5.5_

- [ ]\* 2.5 Write property test for cross-word validity

  - **Property 10: Cross-Word Validity**
  - **Validates: Requirements 4.1, 4.2, 4.3**
  - Generate random moves that form cross-words
  - Assert all cross-words are valid or move is rejected

- [ ]\* 2.6 Write unit tests for cross-word scenarios

  - Test single cross-word formation
  - Test multiple cross-words in one move
  - Test cross-word with premium squares
  - Test invalid cross-word rejection
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 3. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance move repetition prevention

  - [x] 4.1 Improve banned actions tracking

    - Ensure `banned_actions` is properly maintained per turn
    - Add check for 3 failed attempts before forcing pass
    - Clear `banned_actions` on successful move or turn change
    - _Requirements: 2.1, 2.5, 2.6_

  - [x] 4.2 Add consecutive pass tracking

    - Track consecutive passes across both players
    - Terminate game after 4 consecutive passes
    - Reset counter on any successful move
    - _Requirements: 2.3, 6.4_

  - [x] 4.3 Implement mercy rule termination

    - Check if turn_count > 20 and sum(scores) == 0
    - Terminate game if condition met
    - _Requirements: 2.2_

  - [x] 4.4 Add hard turn limit
    - Check if turn_count > 100
    - Terminate game if exceeded
    - _Requirements: 2.4_

- [ ]\* 4.5 Write property test for move repetition prevention

  - **Property 2: Move Repetition Prevention**
  - **Validates: Requirements 2.1, 2.5, 2.6**
  - Simulate repeated invalid move attempts
  - Assert pass is forced after 3 attempts
  - Assert banned actions are cleared on turn change

- [ ]\* 4.6 Write property test for game termination bounds

  - **Property 3: Game Termination Bounds**
  - **Validates: Requirements 2.2, 2.4**
  - Generate games with various turn counts
  - Assert termination at turn 100
  - Assert mercy rule at turn 20 with zero score

- [ ]\* 4.7 Write unit tests for termination conditions

  - Test consecutive pass termination
  - Test mercy rule activation
  - Test hard turn limit
  - Test six consecutive zero scores
  - _Requirements: 2.2, 2.3, 2.4, 6.4_

- [x] 5. Implement deterministic move generation

  - [x] 5.1 Sort candidates in GADDAG traversal

    - Modify `_go_left` to sort candidates alphabetically
    - Modify `_go_right` to sort candidates alphabetically
    - Ensure consistent ordering across runs
    - _Requirements: 8.4_

  - [x] 5.2 Implement deterministic move selection

    - Sort moves by (-length, word) before deduplication
    - Ensure consistent action ID mapping
    - _Requirements: 8.2, 8.3_

  - [x] 5.3 Add move generation consistency checks
    - Verify same board/rack produces same moves
    - Verify move order is consistent
    - _Requirements: 8.1, 8.5_

- [ ]\* 5.4 Write property test for deterministic move generation

  - **Property 17: Deterministic Move Generation**
  - **Validates: Requirements 8.1, 8.5**
  - Generate random board and rack states
  - Generate moves twice
  - Assert move lists are identical

- [ ]\* 5.5 Write property test for deterministic move selection

  - **Property 18: Deterministic Move Selection**
  - **Validates: Requirements 8.2, 8.3, 8.4**
  - Generate positions with multiple possible words
  - Assert same word is selected consistently

- [ ] 6. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement proper end-game handling

  - [x] 7.1 Add end-game detection

    - Check if player used last tile and bag is empty
    - Check for six consecutive zero scores
    - Set `_game_over` flag appropriately
    - _Requirements: 6.1, 6.4_

  - [x] 7.2 Implement final score adjustment

    - Subtract unplayed tile values from each player
    - Add opponent's unplayed tiles to player who went out
    - Ensure final scores are non-negative
    - _Requirements: 6.2, 6.3, 6.5_
    - _Note: Already implemented in Task 1 via `adjust_final_scores()` method_

  - [x] 7.3 Update `returns()` method
    - Return actual final scores instead of [0.0, 0.0]
    - Apply end-game adjustments
    - _Requirements: 6.2, 6.3_
    - _Note: Already implemented in Task 1_

- [ ]\* 7.4 Write property test for end-game tile adjustment

  - **Property 19: End-Game Tile Adjustment**
  - **Validates: Requirements 6.2**
  - Generate random end-game states
  - Assert unplayed tiles are subtracted correctly

- [ ]\* 7.5 Write property test for out bonus

  - **Property 20: Out Bonus**
  - **Validates: Requirements 6.3**
  - Generate games where one player goes out
  - Assert opponent's tiles are added to winner's score

- [ ]\* 7.6 Write unit tests for end-game scenarios

  - Test last tile played with empty bag
  - Test six consecutive zero scores
  - Test final score calculation
  - Test out bonus calculation
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 8. Add comprehensive game state tracking

  - [x] 8.1 Add move attempt logging

    - Log each move attempt with details
    - Log validation failure reasons
    - Log banned actions accumulation
    - _Requirements: 9.1, 9.2, 9.4_

  - [x] 8.2 Add game termination logging

    - Log termination condition
    - Log final scores and turn count
    - Log game state at termination
    - _Requirements: 9.3_

  - [x] 8.3 Enhance `__str__` method
    - Include scores, turn count, consecutive passes
    - Include bag count and rack sizes
    - Include current player and game over status
    - _Requirements: 9.5_

- [ ]\* 8.4 Write unit tests for logging functionality

  - Test move attempt logging
  - Test validation failure logging
  - Test termination logging
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 9. Implement remaining validation properties

  - [x] 9.1 Add board connectivity validation

    - Verify first move covers center square
    - Verify subsequent moves connect to existing tiles
    - _Requirements: 3.1, 3.2_

  - [x] 9.2 Add boundary validation

    - Check all coordinates are in range [0, 14]
    - Reject moves that go off board
    - _Requirements: 3.3_

  - [x] 9.3 Add rack availability validation

    - Verify player has required tiles
    - Handle blank tiles as wildcards
    - _Requirements: 3.4_

  - [x] 9.4 Add tile matching validation
    - Verify word matches existing board tiles
    - _Requirements: 3.5_

- [ ]\* 9.5 Write property tests for validation rules

  - **Property 5: Board Connectivity**
  - **Property 6: First Move Center Coverage**
  - **Property 7: Boundary Compliance**
  - **Property 8: Rack Availability**
  - **Property 9: Tile Matching**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 10. Implement scoring properties

  - [x] 10.1 Verify premium square application order

    - Apply letter multipliers before word multipliers
    - _Requirements: 5.2, 5.3_

  - [x] 10.2 Implement bingo bonus

    - Add 50 points when all 7 tiles used
    - _Requirements: 5.4_

  - [x] 10.3 Ensure premium squares used once
    - Track which squares have been used
    - Only apply multiplier on first use
    - _Requirements: 5.7_

- [ ]\* 10.4 Write property tests for scoring rules

  - **Property 12: Premium Square Application**
  - **Property 13: Bingo Bonus**
  - **Property 14: Premium Square Single Use**
  - **Validates: Requirements 5.2, 5.3, 5.4, 5.7**

- [x] 11. Implement tile management properties

  - [x] 11.1 Verify rack refill behavior

    - Refill to 7 tiles after each turn
    - Draw all remaining if fewer than 7 in bag
    - _Requirements: 7.1, 7.2_

  - [x] 11.2 Validate exchange rules
    - Require at least 7 tiles in bag
    - Reject and penalize invalid exchanges
    - _Requirements: 7.3, 7.4_

- [ ]\* 11.3 Write property tests for tile management

  - **Property 15: Rack Refill**
  - **Property 16: Exchange Validation**
  - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 12. Final checkpoint - Integration testing

  - [x] 12.1 Run full game simulations

    - Play 10 complete games with random agents
    - Verify no negative scores occur
    - Verify games terminate properly
    - Verify no infinite loops or stuck states
    - _Requirements: All_

  - [x] 12.2 Test with AlphaZero training

    - Run short training session (10 iterations)
    - Verify no crashes
    - Verify game logs show proper progression
    - Verify score distributions are reasonable
    - _Requirements: All_

  - [x] 12.3 Analyze game logs
    - Review `data/results/` for new game outputs
    - Verify scores are non-negative
    - Verify no repeated move patterns
    - Verify games progress normally
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All commands must be executed in WSL with virtual environment activated
- Integration tests verify end-to-end functionality with AlphaZero training
