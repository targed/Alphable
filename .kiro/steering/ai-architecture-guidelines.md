---
inclusion: fileMatch
fileMatchPattern: "train*.py|*neural*|*network*|*model*|*ai*"
---

# AI Architecture Guidelines for Alphable

## Core Architectural Principles

### Spatial Architecture (Required)
- **Use**: Spatial ResNet with 15x15x32 input tensors
- **Avoid**: Token-based/LLM-style architectures
- **Reason**: Scrabble is inherently 2D spatial; CNNs have natural inductive bias for grid structures

### Input Representation (32 Channels)
```
Channels 0-25:  One-hot encoding of letters A-Z on board
Channel 26:     Blank tiles (distinct from represented letter)
Channel 27:     Double Letter (DL) premium squares
Channel 28:     Triple Letter (TL) premium squares  
Channel 29:     Double Word (DW) premium squares
Channel 30:     Triple Word (TW) premium squares
Channel 31:     Legal anchor positions (from GADDAG)
Channel 32:     Opponent's last move (temporal feature)
```

### Hybrid "Select-and-Rank" Architecture
1. **GADDAG Move Generation**: Generate all valid moves (20-100 typically)
2. **Neural Network Ranking**: ResNet evaluates and ranks these moves
3. **Action Masking**: 100% valid moves, no wasted compute on rule learning
4. **Policy Head**: Outputs probability distribution over valid moves only

## Information Set MCTS (IS-MCTS)

### Handling Imperfect Information
- **Determinization**: Sample opponent racks from probability distribution
- **Belief State**: Maintain probability distribution over opponent holdings
- **Aggregation**: Run MCTS on multiple determinizations, aggregate results

### Opponent Modeling (Critical Innovation)
- **Inference Head**: Parallel output predicting opponent's rack (26x7 matrix)
- **Training Signal**: Use actual opponent rack during self-play
- **Loss Function**: `L_total = L_π + L_v + λ_inference * L_rack_pred`
- **Strategic Advantage**: Learn to infer opponent tiles from move patterns

## Training Pipeline

### Phase 1: Supervised Learning (Cold Start)
- **Dataset**: Woogles.io expert games (Rating >1800)
- **Input**: Board state + player rack
- **Target**: Expert move selection
- **Goal**: Reach ~1600-1800 Elo immediately
- **Duration**: Until convergence on expert move prediction

### Phase 2: Self-Play Reinforcement Learning
- **Algorithm**: IS-MCTS with value network updates
- **Opponent**: Self-play with determinized racks
- **Training Trick**: Value network sees opponent rack, policy network doesn't
- **Goal**: Discover superhuman strategies beyond expert data

### Advanced Training Techniques
- **GAIL**: Generative Adversarial Imitation Learning for human-like play
- **Mixed Strategies**: Support probabilistic bluffing policies
- **Challenge Rules**: Different policies for Double vs Single challenge rules

## Bluffing and Game Theory

### Strategic Depth Requirements
- **Mixed Strategy Support**: Output probability distributions, not single moves
- **Bluffing Logic**: Play invalid words with optimal probability in Double Challenge
- **Phoney Baiting**: Play obscure valid words to induce failed challenges
- **Rule Awareness**: Different strategies for different challenge rule sets

### Implementation Details
- **Obscurity Scoring**: Track word frequency in training data vs dictionary
- **Challenge Modeling**: Predict opponent challenge probability
- **Risk Assessment**: Balance bluff reward vs challenge penalty

## Performance Optimization

### Critical Requirements
- **GADDAG Integration**: C++ implementation with Python bindings
- **Cython Extensions**: Performance-critical code in `structure.pyx`
- **GPU Training**: NVIDIA A100/H100 for ResNet training
- **Inference Speed**: Real-time gameplay on consumer hardware

### Endgame Optimization
- **Perfect Information Switch**: When bag empty, use minimax solver
- **Deterministic Endgame**: Never lose won positions
- **Computational Efficiency**: Endgame solver is fast when few tiles remain

## Code Organization

### Model Architecture Files
- Neural network definitions with proper input/output shapes
- Separate heads for policy, value, and opponent inference
- Modular design for easy experimentation

### Training Scripts
- Clear separation of supervised vs RL phases
- Checkpoint management and resumption
- Evaluation metrics and logging
- Hyperparameter configuration

### Integration Points
- Clean interface between GADDAG and neural network
- Proper action masking implementation
- Efficient tensor operations for board representation