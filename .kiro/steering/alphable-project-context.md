---
inclusion: always
---

# Alphable Project Context

## Project Overview
Alphable is an AlphaZero-style reinforcement learning system for Scrabble that aims to achieve superhuman performance. The project implements a complete Scrabble engine with neural network training capabilities and includes a comprehensive visualization system for analyzing gameplay.

## Core Architecture

### Game Engine (`scrabble.py`)
- Complete Scrabble rules implementation following NASPA Official Tournament Rules
- 15x15 board with premium squares (TW, DW, TL, DL)
- GADDAG-based move generation for efficient valid word discovery
- Comprehensive move validation including adjacent word checking
- Support for all Scrabble mechanics: scoring, bingo bonus, exchanges, passes

### AI Training System
- **Hybrid Architecture**: Spatial ResNet + GADDAG move generation (NOT token-based)
- **Information Set MCTS (IS-MCTS)**: Handles imperfect information (hidden opponent rack)
- **Opponent Modeling**: Neural network predicts opponent's rack from move patterns
- **Training Pipeline**: Supervised learning on Woogles.io data → Self-play reinforcement learning
- **Bluffing Support**: Mixed strategy policies for optimal deception in tournament rules

### Visualization System
- React/TypeScript frontend with Flask backend
- Complete game replay with interactive controls
- Professional broadcast-quality visualization
- Real-time board state, scores, racks, and statistics

## Key Technical Decisions

### Why Spatial Architecture Over Tokens
The project explicitly rejects token-based (LLM-style) output in favor of spatial board representation because:
- Scrabble is inherently 2D spatial
- Token models struggle with geometric constraints
- High invalid move rate without GADDAG integration
- CNNs have natural inductive bias for grid structures

### Critical Implementation Details
- **Move Validation**: 6-step validation process including adjacent word checking
- **Premium Squares**: Single-use rule correctly implemented
- **Dictionary**: Uses NWL2023 lexicon
- **Scoring**: Handles all edge cases including compound multipliers
- **Endgame**: Perfect information solver when bag is empty

## File Organization

### Core Files
- `scrabble.py` - Main game engine
- `train.py` - Neural network training
- `structure.pyx` - Cython optimizations for performance

### Evaluation & Analysis
- `eval/` - Bot evaluation scripts and analysis tools
- `tests/` - Comprehensive test suite (>20 test files)
- `visualizer/` - Complete replay visualization system

### Data & Resources
- `data/` - Training checkpoints and game results
- `resources/` - Documentation, requirements, and research papers

## Development Standards

### Code Quality
- All game rules must be verified against official NASPA rules
- Comprehensive test coverage for all game mechanics
- Performance-critical code uses Cython extensions
- Type hints and documentation for all public APIs

### AI Training
- Start with supervised learning on expert games
- Use IS-MCTS for handling imperfect information
- Implement opponent modeling for strategic depth
- Support both honest and bluffing strategies based on challenge rules

### Testing Philosophy
- Unit tests for individual game mechanics
- Integration tests for complete game scenarios
- Verification tests against official Scrabble rules
- Performance benchmarks for move generation speed

## Research Foundation
The project is based on extensive research documented in `resources/Alphable.md`, including:
- Analysis of existing Scrabble AI (Maven, Quackle)
- Game theory research on optimal bluffing strategies
- Technical evaluation of different neural architectures
- Implementation roadmap using OpenSpiel framework

## Current Status
- ✅ Complete Scrabble engine with all rules implemented
- ✅ Comprehensive test suite with 100% rule compliance
- ✅ Professional visualization system
- ✅ Cython optimizations for performance
- 🔄 Neural network training in progress
- 📋 Multiple training checkpoints and evaluation results available