# AI vs Base MAGPIE: Search and Valuation Mechanics

This document explains how the AI evaluation layers in Alphable V4 interact with and modify the base MAGPIE engine during move selection.

---

## 1. Architectural Division of Labor

Game engines often separate move processing into two components:
1. Move Generator: Finds legal moves and applies basic static filters.
2. Search and Valuation: Performs lookahead, opponent modeling, and board evaluation.

In Alphable V4:
- MAGPIE acts as the generator: It runs in native C, finds legal dictionary words in ~0.7 ms, and computes static KLV leave equity.
- BAMS and ResNet-18 provide evaluation: BAMS samples opponent racks, simulates counter-plays, and the ResNet-18 network evaluates resulting board positions.

---

## 2. What MAGPIE Computes Alone vs What BAMS Computes

### Base MAGPIE (Without AI)
When Base MAGPIE chooses a move, it uses this formula:
$$\text{Static Equity}(c) = \text{Score}(c) + \text{KLV\_Leave}(c)$$
- $\text{Score}(c)$: Points on the current turn.
- $\text{KLV\_Leave}(c)$: A pre-computed static lookup of the remaining letters on your rack (e.g. keeping an `S` is +8.2 pts, keeping `Q` is -7.1 pts).

Base MAGPIE evaluates each candidate in isolation. It does not simulate opponent responses to that specific board layout or model the opponent's rack.

---

### Alphable V4 (BAMS AI)
When BAMS evaluates candidate $c$, it replaces the static score with a dynamic 1-ply Monte Carlo simulation and a deep neural value prediction:
$$\text{BAMS\_Score}(c) = \text{Static Equity}(c) - \beta \cdot \frac{1}{N} \sum_{i=1}^N \text{Score}(\text{OppReply}(c, r_i)) + \gamma \cdot \frac{1}{N} \sum_{i=1}^N V_{\theta}(S'_{c, i})$$

Where:
1. $r_i \sim \text{DirichletMultinomial}(\text{UnseenPool}, 7)$: $N$ opponent racks sampled with Common Random Numbers (CRN).
2. $\text{OppReply}(c, r_i)$: The opponent's best response against candidate $c$ given sampled rack $r_i$.
3. $S'_{c, i}$: The game state after candidate $c$ and the opponent reply.
4. $V_{\theta}(S')$: The ResNet-18 Value Network prediction in $[-1.0, 1.0]$.

---

## 3. Concrete Example: Move Divergence

Consider an opening rack with `AQRTUYZ`:
Both `8D QUARTZY` and `8G QUARTZY` score 126 points.

### Base MAGPIE View
- `8D QUARTZY`: Score 126, Leave empty, Equity: 126.00
- `8G QUARTZY`: Score 126, Leave empty, Equity: 125.30 (a 0.7 pt difference)

### BAMS Calculation
1. Draws $N=32$ opponent racks from the 93 unseen tiles in the bag.
2. Simulates the opponent's best reply to both board positions:
   - After `8D QUARTZY`: Opponent average reply is 45.2 points.
   - After `8G QUARTZY`: Opponent average reply is 52.4 points.
   `8G` places the `Z` and `Y` tiles adjacent to high-multiplier lanes that provide higher-scoring counter-attacks for the opponent.
3. The Value Network evaluates board control after both plays:
   - After `8D`: $V = +0.3061$.
   - After `8G`: $V = +0.2779$.
4. Final BAMS scores:
   - `8D QUARTZY`: $126.00 - (0.25 \times 45.2) + (12.0 \times 0.3061) = 118.37$
   - `8G QUARTZY`: $125.30 - (0.25 \times 52.4) + (12.0 \times 0.2779) = 115.54$

BAMS identifies that `8D` is 2.83 points safer, where Base MAGPIE evaluated them as nearly identical.

---

## 4. Tournament Results

In a 20-game tournament between Alphable V4 (BAMS) and Base MAGPIE (KLV static top move):
- BAMS Mean Score: 476.1 points
- Base MAGPIE Mean Score: 437.0 points
- Margin: +39.1 points per game in favor of Alphable V4

If BAMS selected identical plays to Base MAGPIE, the average scores would match. The +39.1 point advantage reflects the impact of opponent counter-play modeling and neural board valuation across the game sample.

---

## 5. Real-Time Position Inspection

Run the analyzer command on any position:
```bash
python cli.py analyze --rack AQRTUYZ
```

Output columns:
- `Opp Threat`: Output of the Bayesian Monte Carlo rollout.
- `Neural Val`: Output of the ResNet-18 Value Network.
- Status flags:
  - `[AGREED #1]`: MAGPIE and the AI agree.
  - `[AI CHOSEN #1]`: The AI selected a different move than Base MAGPIE's top static choice.
