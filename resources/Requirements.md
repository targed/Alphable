This Requirements Document outlines the functional and technical specifications for the `ScrabbleGame` and `ScrabbleState` engine. It serves as a checklist to verify that the engine correctly implements the official rules and supports the geometric complexities of the game required for AlphaZero training.

---

# Scrabble Engine Requirements Specification (v2.0)

## 1. Board and Component Definitions

### REQ-101: The Grid
*   The board **must** consist of a 15x15 grid.
*   The coordinate system **must** be zero-indexed (0,0 to 14,14).
*   The center square (7,7) **must** be identified as the starting point.

### REQ-102: Premium Squares
The engine **must** correctly map and apply the following premium squares:
*   **DL (Double Letter):** Doubles the value of the tile placed on it.
*   **TL (Triple Letter):** Triples the value of the tile placed on it.
*   **DW (Double Word):** Doubles the total score of the word.
*   **TW (Triple Word):** Triples the total score of the word.
*   *Note:* The center square (7,7) acts as a Double Word score.

### REQ-103: Tile Distribution and Values
*   The engine **must** initialize a bag with exactly 100 tiles following standard North American distribution (e.g., 9 'A's, 2 Blanks).
*   Each tile **must** correspond to its standard point value (e.g., A=1, Z=10, Blank=0).

### REQ-104: The Rack
*   Each player **must** maintain a private rack of up to 7 tiles.
*   Tiles used in a move **must** be removed from the rack.
*   The rack **must** be refilled from the bag immediately after a move, up to 7 tiles (or until the bag is empty).

---

## 2. Move Validation (Geometry & Rules)

### REQ-201: Placement Validity (The "Frontier" Rule)
*   **First Move:** The first word played **must** cover the center star (7,7).
*   **Subsequent Moves:** Any new word **must** connect to at least one existing tile on the board.
*   **Connectivity:** Disconnected islands of words are **forbidden**.

### REQ-202: Directionality
*   Words **must** be placed either Horizontally (Across) or Vertically (Down).
*   Diagonal plays are **forbidden**.

### REQ-203: Intersection Types
The engine **must** support and validate the following placement types:
1.  **Through-Placement (Intersection):** Playing a word perpendicular to an existing word, utilizing an existing tile as one of its letters (e.g., playing `AND` vertically through the `N` in `PANDA`).
2.  **Hooks (Extension):** Adding tiles to the beginning or end of an existing word (e.g., adding `S` to `TRAIN` to make `STRAIN`).
3.  **Parallel Play (Overlapping):** Placing a word parallel to an existing word such that adjacent tiles form valid 2-letter or 3-letter cross-words (e.g., playing `HI` under `GO` to form `GO`, `HE`, `OI`).
4.  **Bridging:** Placing a word that connects two previously separated clusters of tiles (e.g., filling the gap between two words).

### REQ-204: Boundary Limits
*   No word may extend beyond the 0-14 grid indices.

### REQ-205: Dictionary Validation
*   **Primary Word:** The main word formed by the player **must** exist in the provided lexicon (NWL2023).
*   **Cross-Words:** Every secondary word formed by adjacent tiles **must** also exist in the lexicon.
*   **Invalidity:** If *any* word formed in the turn is invalid, the entire move **must** be rejected.

---

## 3. Scoring Mechanics

### REQ-301: Basic Scoring
*   The score for a turn is the sum of the scores of all new words formed in that turn (Main word + Cross-words).

### REQ-302: Premium Application
*   **Letter Bonuses:** Applied first to the individual tile value.
*   **Word Bonuses:** Applied to the total word score after summing tile values.
*   **Single Use:** Premium squares **must** only apply the first time they are covered. Subsequent uses of that tile count at face value.
*   **Compound Multipliers:** If a word covers two Triple Word squares, the score **must** be multiplied by 9 (3x3).

### REQ-303: The Bingo
*   If a player uses all 7 tiles from their rack in a single turn, a bonus of **50 points** **must** be added to the total score.

### REQ-304: Blank Tiles
*   A blank tile **must** have a score value of 0.
*   When played, the blank **must** assume the identity of a specific letter (A-Z) for dictionary validation.
*   The engine **must** track which letter the blank represents for future cross-word validation.

---

## 4. Game Flow and Special Actions

### REQ-401: Passing
*   A player **must** be able to Pass their turn (Action 450).
*   A Pass results in a score of 0.
*   **Termination:** If there are **4 consecutive passes** (Total across both players), the game **must** end.

### REQ-402: Exchanging
*   A player **must** be able to Exchange tiles (Action 451) instead of playing a word.
*   **Constraint:** Exchange is **forbidden** if the bag has fewer than 7 tiles remaining.
*   **Mechanic:** Selected tiles are returned to the bag, the bag is shuffled, and new tiles are drawn.
*   An Exchange counts as a zero-score turn but resets the "Consecutive Zero Score" counter (depending on specific rule interpretation; standard tournament rules treat it as a zero score).

### REQ-403: Challenges (Verification)
*   *Note: In this AlphaZero implementation, "Challenge" is handled via pre-move verification ("Perfect Adjudication").*
*   The engine **must** reject any move that does not satisfy REQ-205 (Dictionary Validation) and treat it as a forced Pass (or retry), ensuring no invalid words ever remain on the board.

### REQ-404: Early Termination (Mercy Rules)
To facilitate efficient training:
*   The game **must** end if the turn count exceeds 100.
*   The game **must** end if there are 6 consecutive zero-score turns (Passes or Exchanges or Failed Moves).

---

## 5. Endgame Conditions

### REQ-501: "The Out"
The game ends immediately when:
1.  The bag is empty.
2.  One player has emptied their rack.

### REQ-502: Score Adjustment
When the game ends via REQ-501:
*   The sum of the values of unplayed tiles on the opposing player's rack **must** be added to the score of the player who went out.
*   The sum of unplayed tiles **must** be subtracted from the score of the player holding them.

### REQ-503: Normalization (RL Specific)
*   For the Neural Network, the engine **must** return the final game result as `+1` (Win), `-1` (Loss), or `0` (Draw), derived from the final adjusted scores.

---

## 6. AI Interface Requirements

### REQ-601: State Representation
The engine **must** output a Tensor representation (Shape [35, 15, 15]) including:
*   Board configuration (Letters A-Z).
*   Premium squares.
*   **Frontier:** A channel explicitly marking all squares (Empty or Filled) that are valid starting anchors for new words.

### REQ-602: Action Masking
*   The engine **must** provide a mask of legal actions.
*   This mask **must** filter out moves that are geometrically impossible or require tiles the player does not possess.

### REQ-603: Determinism
*   Given a specific Board State and Rack, the Move Generator **must** always return the exact same list of moves in the exact same order.