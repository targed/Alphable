import React, { useState, useEffect, useRef } from 'react';
import './InteractiveGame.css';
import Board from './Board';
import PlayerHUD from './PlayerHUD';
import { BoardSquare, PremiumSquareType } from '../types';
import { InteractiveGameConfig, PlayerType } from './NewInteractiveGame';

const API_URL = 'http://localhost:5000/api';

interface Props {
  config: InteractiveGameConfig;
  onBack: () => void;
}

interface Move {
  word: string;
  row: number;
  col: number;
  direction: "Across" | "Down";
}

interface EvaluatedMove extends Move {
  points: number;
  value: number;
  new_rack: string[];
}

interface GameState {
  board: string[][];
  p1Rack: string[];
  p2Rack: string[];
  p1Score: number;
  p2Score: number;
  bagRemaining: number;
  isP1Turn: boolean;
  history: GameState[]; // Stores previous states for undo
  redoHistory: GameState[]; // Stores next states for redo
  bagHistory: string[][]; // Stores previous bags
  redoBagHistory: string[][]; // Stores next bags
}

// Scrabble letter distribution for initial bag
const INITIAL_BAG_COUNTS: Record<string, number> = {
  'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
  'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
  'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
  'Y': 2, 'Z': 1, '?': 2
};

const PREMIUM_SQUARES: Record<string, PremiumSquareType> = {
  "0,0": "TW", "0,7": "TW", "0,14": "TW",
  "7,0": "TW", "7,14": "TW", "14,0": "TW", "14,7": "TW", "14,14": "TW",
  "1,1": "DW", "2,2": "DW", "3,3": "DW", "4,4": "DW",
  "10,10": "DW", "11,11": "DW", "12,12": "DW", "13,13": "DW",
  "1,13": "DW", "2,12": "DW", "3,11": "DW", "4,10": "DW",
  "10,4": "DW", "11,3": "DW", "12,2": "DW", "13,1": "DW",
  "7,7": "DW",
  "1,5": "TL", "1,9": "TL", "5,1": "TL", "5,5": "TL",
  "5,9": "TL", "5,13": "TL", "9,1": "TL", "9,5": "TL",
  "9,9": "TL", "9,13": "TL", "13,5": "TL", "13,9": "TL",
  "0,3": "DL", "0,11": "DL", "2,6": "DL", "2,8": "DL",
  "3,0": "DL", "3,7": "DL", "3,14": "DL", "6,2": "DL",
  "6,6": "DL", "6,8": "DL", "6,12": "DL", "7,3": "DL",
  "7,11": "DL", "8,2": "DL", "8,6": "DL", "8,8": "DL",
  "8,12": "DL", "11,0": "DL", "11,7": "DL", "11,14": "DL",
  "12,6": "DL", "12,8": "DL", "14,3": "DL", "14,11": "DL"
};

const InteractiveGame: React.FC<Props> = ({ config, onBack }) => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Player move input state
  const [moveWord, setMoveWord] = useState('');
  const [moveRow, setMoveRow] = useState(7);
  const [moveCol, setMoveCol] = useState(7);
  const [moveDir, setMoveDir] = useState<"Across" | "Down">("Across");

  // Developer/Test controls
  const [temperature, setTemperature] = useState(0.0);
  const [topK, setTopK] = useState(3);
  const [showDevPanel, setShowDevPanel] = useState(false);
  const [evaluatedMoves, setEvaluatedMoves] = useState<EvaluatedMove[]>([]);
  const [customP1Rack, setCustomP1Rack] = useState('');
  const [customP2Rack, setCustomP2Rack] = useState('');
  const [autoPlayAI, setAutoPlayAI] = useState(config.autoPlayAI);
  const [forceAiType, setForceAiType] = useState<PlayerType>('alphable');

  // Internal full bag
  const bagRef = useRef<string[]>([]);

  useEffect(() => {
    initGame();
  }, []);

  const buildInitialBag = () => {
    const bag: string[] = [];
    for (const [letter, count] of Object.entries(INITIAL_BAG_COUNTS)) {
      for (let i = 0; i < count; i++) {
        bag.push(letter);
      }
    }
    // Shuffle
    for (let i = bag.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [bag[i], bag[j]] = [bag[j], bag[i]];
    }
    return bag;
  };

  const drawTiles = (bag: string[], count: number) => {
    const drawn: string[] = [];
    for (let i = 0; i < count; i++) {
      if (bag.length > 0) {
        drawn.push(bag.pop()!);
      }
    }
    return drawn;
  };

  const initGame = () => {
    const newBag = buildInitialBag();
    bagRef.current = newBag;

    const initialBoard = Array(15).fill(null).map(() => Array(15).fill('.'));
    const p1Rack = drawTiles(bagRef.current, 7);
    const p2Rack = drawTiles(bagRef.current, 7);

    setGameState({
      board: initialBoard,
      p1Rack,
      p2Rack,
      p1Score: 0,
      p2Score: 0,
      bagRemaining: bagRef.current.length,
      isP1Turn: true,
      history: [],
      redoHistory: [],
      bagHistory: [],
      redoBagHistory: []
    });
    setLoading(false);
  };

  const getCurrentPlayerType = () => {
    return gameState?.isP1Turn ? config.p1Type : config.p2Type;
  };

  const isHumanTurn = () => {
    return getCurrentPlayerType() === 'human';
  };

  // Trigger AI move if it's AI's turn
  useEffect(() => {
    if (gameState && !isHumanTurn() && !loading && autoPlayAI) {
      if (gameState.redoHistory.length === 0) {
        makeAIMove(getCurrentPlayerType());
      }
    }
  }, [gameState?.isP1Turn, loading, autoPlayAI]);

  const applyMoveToBoard = (board: string[][], move: Move) => {
    const newBoard = board.map(row => [...row]);
    const word = move.word;
    for (let i = 0; i < word.length; i++) {
      const r = move.direction === 'Across' ? move.row : move.row + i;
      const c = move.direction === 'Across' ? move.col + i : move.col;
      if (newBoard[r][c] === '.') {
        newBoard[r][c] = word[i]; // uppercase
      }
    }
    return newBoard;
  };

  const makeAIMove = async (aiTypeToUse: PlayerType) => {
    if (!gameState) return;
    setLoading(true);
    setError(null);
    setEvaluatedMoves([]);

    const currentRack = gameState.isP1Turn ? gameState.p1Rack : gameState.p2Rack;
    const currentScore = gameState.isP1Turn ? gameState.p1Score : gameState.p2Score;
    const oppScore = gameState.isP1Turn ? gameState.p2Score : gameState.p1Score;

    try {
      const response = await fetch(`${API_URL}/interactive/ai_move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board: gameState.board,
          rack: currentRack,
          score_diff: currentScore - oppScore,
          bag_remaining: gameState.bagRemaining,
          ai_type: aiTypeToUse,
          temperature,
          top_k: topK,
          dictionary: config.dictionary
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to get AI move');

      if (data.evaluated_moves) {
          setEvaluatedMoves(data.evaluated_moves);
      }

      if (data.action === 'PLAY') {
        const move = data.move;
        const newBoard = applyMoveToBoard(gameState.board, move);

        // Draw new tiles to replace used ones
        const tilesNeeded = 7 - data.new_rack.length;
        const drawnTiles = drawTiles(bagRef.current, tilesNeeded);
        const finalRack = [...data.new_rack, ...drawnTiles];

        setGameState(prev => {
          if (!prev) return prev;
          const isP1 = prev.isP1Turn;
          return {
            ...prev,
            board: newBoard,
            p1Rack: isP1 ? finalRack : prev.p1Rack,
            p2Rack: !isP1 ? finalRack : prev.p2Rack,
            p1Score: isP1 ? prev.p1Score + data.points : prev.p1Score,
            p2Score: !isP1 ? prev.p2Score + data.points : prev.p2Score,
            bagRemaining: bagRef.current.length,
            isP1Turn: !prev.isP1Turn,
            history: [...prev.history, JSON.parse(JSON.stringify(prev))],
            redoHistory: [],
            bagHistory: [...prev.bagHistory, [...bagRef.current]],
            redoBagHistory: []
          };
        });
      } else {
        // AI passed
        setGameState(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            isP1Turn: !prev.isP1Turn,
            history: [...prev.history, JSON.parse(JSON.stringify(prev))],
            redoHistory: [],
            bagHistory: [...prev.bagHistory, [...bagRef.current]],
            redoBagHistory: []
          };
        });
      }

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePlayerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gameState || !moveWord) return;
    setLoading(true);
    setError(null);

    const move: Move = {
      word: moveWord.toUpperCase(),
      row: moveRow,
      col: moveCol,
      direction: moveDir
    };

    try {
      const currentRack = gameState.isP1Turn ? gameState.p1Rack : gameState.p2Rack;

      const response = await fetch(`${API_URL}/interactive/validate_user_move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board: gameState.board,
          rack: currentRack,
          move,
          dictionary: config.dictionary
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to validate move');

      if (data.valid) {
        const newBoard = applyMoveToBoard(gameState.board, move);

        // Draw new tiles
        const tilesNeeded = 7 - data.new_rack.length;
        const drawnTiles = drawTiles(bagRef.current, tilesNeeded);
        const finalRack = [...data.new_rack, ...drawnTiles];

        setGameState(prev => {
          if (!prev) return prev;
          const isP1 = prev.isP1Turn;
          return {
            ...prev,
            board: newBoard,
            p1Rack: isP1 ? finalRack : prev.p1Rack,
            p2Rack: !isP1 ? finalRack : prev.p2Rack,
            p1Score: isP1 ? prev.p1Score + data.points : prev.p1Score,
            p2Score: !isP1 ? prev.p2Score + data.points : prev.p2Score,
            bagRemaining: bagRef.current.length,
            isP1Turn: !prev.isP1Turn,
            history: [...prev.history, JSON.parse(JSON.stringify(prev))],
            redoHistory: [],
            bagHistory: [...prev.bagHistory, [...bagRef.current]],
            redoBagHistory: []
          };
        });
        setMoveWord('');
      } else {
        setError('Invalid move according to rules/dictionary.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePass = () => {
      if (!gameState) return;
      setGameState(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            isP1Turn: !prev.isP1Turn,
            history: [...prev.history, JSON.parse(JSON.stringify(prev))],
            redoHistory: [],
            bagHistory: [...prev.bagHistory, [...bagRef.current]],
            redoBagHistory: []
          };
      });
  };

  const handleUndo = () => {
    if (!gameState || gameState.history.length === 0) return;
    const previousState = gameState.history[gameState.history.length - 1];
    const previousBag = gameState.bagHistory[gameState.bagHistory.length - 1];

    // Restore bag array
    if (previousBag) {
        bagRef.current = [...previousBag];
    }

    setGameState(prev => {
        if (!prev) return prev;
        const newHistory = [...prev.history];
        newHistory.pop();
        const newBagHistory = [...prev.bagHistory];
        newBagHistory.pop();

        return {
            ...previousState,
            history: newHistory,
            bagHistory: newBagHistory,
            redoHistory: [...prev.redoHistory, JSON.parse(JSON.stringify(prev))],
            redoBagHistory: [...prev.redoBagHistory, [...bagRef.current]]
        };
    });
  };

  const handleRedo = () => {
    if (!gameState || gameState.redoHistory.length === 0) return;
    const nextState = gameState.redoHistory[gameState.redoHistory.length - 1];
    const nextBag = gameState.redoBagHistory[gameState.redoBagHistory.length - 1];

    if (nextBag) {
        bagRef.current = [...nextBag];
    }

    setGameState(prev => {
        if (!prev) return prev;
        const newRedoHistory = [...prev.redoHistory];
        newRedoHistory.pop();
        const newRedoBagHistory = [...prev.redoBagHistory];
        newRedoBagHistory.pop();

        return {
            ...nextState,
            history: [...prev.history, JSON.parse(JSON.stringify(prev))],
            bagHistory: [...prev.bagHistory, [...bagRef.current]],
            redoHistory: newRedoHistory,
            redoBagHistory: newRedoBagHistory
        };
    });
  };

  const handleForceP1Rack = () => {
      if (!gameState || !customP1Rack) return;
      const tiles = customP1Rack.toUpperCase().split('');
      if (tiles.length > 7) {
          setError("Rack can have at most 7 tiles");
          return;
      }
      setGameState(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            p1Rack: tiles,
          };
      });
      setCustomP1Rack('');
  };

  const handleForceP2Rack = () => {
      if (!gameState || !customP2Rack) return;
      const tiles = customP2Rack.toUpperCase().split('');
      if (tiles.length > 7) {
          setError("Rack can have at most 7 tiles");
          return;
      }
      setGameState(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            p2Rack: tiles,
          };
      });
      setCustomP2Rack('');
  };

  const applyEvaluatedMove = (moveEval: EvaluatedMove) => {
    if (!gameState) return;
    const newBoard = applyMoveToBoard(gameState.board, moveEval);
    const tilesNeeded = 7 - moveEval.new_rack.length;
    const drawnTiles = drawTiles(bagRef.current, tilesNeeded);
    const finalRack = [...moveEval.new_rack, ...drawnTiles];

    setGameState(prev => {
      if (!prev) return prev;
      const isP1 = prev.isP1Turn;
      return {
        ...prev,
        board: newBoard,
        p1Rack: isP1 ? finalRack : prev.p1Rack,
        p2Rack: !isP1 ? finalRack : prev.p2Rack,
        p1Score: isP1 ? prev.p1Score + moveEval.points : prev.p1Score,
        p2Score: !isP1 ? prev.p2Score + moveEval.points : prev.p2Score,
        bagRemaining: bagRef.current.length,
        isP1Turn: !prev.isP1Turn,
        history: [...prev.history, JSON.parse(JSON.stringify(prev))],
        redoHistory: [],
        bagHistory: [...prev.bagHistory, [...bagRef.current]],
        redoBagHistory: []
      };
    });
    setEvaluatedMoves([]);
  };

  const handleExchangeP1Tiles = () => {
      if (!gameState) return;
      const numTiles = gameState.p1Rack.length;
      const currentRack = [...gameState.p1Rack];

      // Put rack back into bag
      bagRef.current.push(...currentRack);
      // Shuffle bag
      for (let i = bagRef.current.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [bagRef.current[i], bagRef.current[j]] = [bagRef.current[j], bagRef.current[i]];
      }

      // Draw new
      const newRack = drawTiles(bagRef.current, numTiles);

      setGameState(prev => {
          if (!prev) return prev;
          return {
              ...prev,
              p1Rack: newRack,
              bagRemaining: bagRef.current.length,
              isP1Turn: false, // passes turn
              history: [...prev.history, JSON.parse(JSON.stringify(prev))],
              redoHistory: [],
              bagHistory: [...prev.bagHistory, [...bagRef.current]],
              redoBagHistory: []
          };
      });
  };

  const handleExchangeP2Tiles = () => {
      if (!gameState) return;
      const numTiles = gameState.p2Rack.length;
      const currentRack = [...gameState.p2Rack];

      bagRef.current.push(...currentRack);
      for (let i = bagRef.current.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [bagRef.current[i], bagRef.current[j]] = [bagRef.current[j], bagRef.current[i]];
      }

      const newRack = drawTiles(bagRef.current, numTiles);

      setGameState(prev => {
          if (!prev) return prev;
          return {
              ...prev,
              p2Rack: newRack,
              bagRemaining: bagRef.current.length,
              isP1Turn: true, // passes turn
              history: [...prev.history, JSON.parse(JSON.stringify(prev))],
              redoHistory: [],
              bagHistory: [...prev.bagHistory, [...bagRef.current]],
              redoBagHistory: []
          };
      });
  };

  if (loading && !gameState) {
    return <div>Loading Game...</div>;
  }

  if (!gameState) return null;

  // Convert string[][] board to BoardSquare[][]
  const renderBoard: BoardSquare[][] = gameState.board.map((row, r) =>
    row.map((cell, c) => ({
      row: r,
      col: c,
      letter: cell === '.' ? null : cell,
      premium: PREMIUM_SQUARES[`${r},${c}`] || null,
      isNew: false
    }))
  );

  return (
    <div className="interactive-game">
      <div className="header-actions">
        <button className="btn-back" onClick={onBack}>&larr; Exit Match</button>
        <button className="btn-toggle-dev" onClick={() => setShowDevPanel(!showDevPanel)}>
          {showDevPanel ? 'Hide Dev Panel' : 'Show Dev Panel'}
        </button>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      <div className="game-layout">
        <div className="main-play-area">
          <div className="huds-container">
            <PlayerHUD
              playerName={`Player 1 (${config.p1Type})`}
              playerId={1}
              currentPlayer={gameState.isP1Turn ? 1 : 2}
              score={gameState.p1Score}
              rack={gameState.p1Rack}
            />
            <div className="turn-indicator">
              <h3>{gameState.isP1Turn ? "Player 1's Turn" : "Player 2's Turn"}</h3>
              {(!isHumanTurn() && autoPlayAI && !loading) && <p>Thinking...</p>}
              <p>Bag: {gameState.bagRemaining} tiles</p>
            </div>
            <PlayerHUD
              playerName={`Player 2 (${config.p2Type})`}
              playerId={2}
              currentPlayer={gameState.isP1Turn ? 1 : 2}
              score={gameState.p2Score}
              rack={gameState.p2Rack}
            />
          </div>

          <div className="board-wrapper">
            <Board board={renderBoard} />
          </div>

          {isHumanTurn() && (
            <div className="player-controls">
              <h3>Play a Move</h3>
              <form onSubmit={handlePlayerSubmit} className="move-form">
                <input
                  type="text"
                  placeholder="Word"
                  value={moveWord}
                  onChange={(e) => setMoveWord(e.target.value)}
                  maxLength={15}
                  required
                />
                <div className="coords">
                  <label>Row (0-14):
                    <input type="number" min="0" max="14" value={moveRow} onChange={(e) => setMoveRow(Number(e.target.value))} required />
                  </label>
                  <label>Col (0-14):
                    <input type="number" min="0" max="14" value={moveCol} onChange={(e) => setMoveCol(Number(e.target.value))} required />
                  </label>
                  <select value={moveDir} onChange={(e) => setMoveDir(e.target.value as any)}>
                    <option value="Across">Across</option>
                    <option value="Down">Down</option>
                  </select>
                </div>
                <button type="submit" disabled={loading}>Play Word</button>
                <button type="button" onClick={handlePass} disabled={loading} className="btn-pass">Pass</button>
              </form>
            </div>
          )}
        </div>

        {showDevPanel && (
          <div className="dev-panel">
            <h3>Developer Controls</h3>

            <div className="dev-section">
              <h4>Game State</h4>
              <div style={{display: 'flex', gap: '5px', marginBottom: '5px'}}>
                <button onClick={handleUndo} disabled={gameState.history.length === 0}>Undo</button>
                <button onClick={handleRedo} disabled={gameState.redoHistory.length === 0}>Redo</button>
              </div>
              <div style={{display: 'flex', gap: '5px', marginTop: '10px'}}>
                <button onClick={handleExchangeP1Tiles} disabled={bagRef.current.length === 0}>Exchange P1</button>
                <button onClick={handleExchangeP2Tiles} disabled={bagRef.current.length === 0}>Exchange P2</button>
              </div>
            </div>

            <div className="dev-section">
              <h4>AI Settings & Overrides</h4>
              <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <input type="checkbox" checked={autoPlayAI} onChange={e => setAutoPlayAI(e.target.checked)} />
                Auto-play AI turns
              </label>

              <div style={{ marginTop: '10px', display: 'flex', gap: '5px', alignItems: 'center' }}>
                <select value={forceAiType} onChange={(e) => setForceAiType(e.target.value as PlayerType)}>
                  <option value="alphable">Alphable</option>
                  <option value="greedy">Greedy</option>
                  <option value="random">Random</option>
                </select>
                <button onClick={() => makeAIMove(forceAiType)}>Force Evaluate</button>
              </div>
              <hr style={{ margin: '10px 0', border: 'none', borderTop: '1px solid #ddd' }} />
              <label>
                Temperature: {temperature}
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                />
              </label>
              <label>
                Top-K: {topK}
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="dev-section">
                <h4>Set Custom Racks</h4>
                <div style={{display: 'flex', gap: '5px', marginBottom: '10px'}}>
                    <input
                        type="text"
                        placeholder="P1 Rack (e.g. ABCDEFG)"
                        value={customP1Rack}
                        onChange={(e) => setCustomP1Rack(e.target.value)}
                        maxLength={7}
                    />
                    <button onClick={handleForceP1Rack}>Set</button>
                </div>
                <div style={{display: 'flex', gap: '5px'}}>
                    <input
                        type="text"
                        placeholder="P2 Rack (e.g. ABCDEFG)"
                        value={customP2Rack}
                        onChange={(e) => setCustomP2Rack(e.target.value)}
                        maxLength={7}
                    />
                    <button onClick={handleForceP2Rack}>Set</button>
                </div>
            </div>

            <div className="dev-section">
              <h4>Bag Contents</h4>
              <details>
                <summary>View Tiles ({gameState.bagRemaining})</summary>
                <div style={{ wordBreak: 'break-all', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  {bagRef.current.join(', ')}
                </div>
              </details>
            </div>

            <div className="dev-section">
              <h4>Evaluated AI Moves (Top 10)</h4>
              {evaluatedMoves.length === 0 ? (
                <p>No moves evaluated yet.</p>
              ) : (
                <div className="table-wrapper">
                  <table className="moves-table">
                    <thead>
                      <tr>
                        <th>Word</th>
                        <th>Pos</th>
                        <th>Pts</th>
                        <th>Val</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluatedMoves.slice(0, 10).map((m, i) => (
                        <tr key={i}>
                          <td>{m.word}</td>
                          <td>{m.row},{m.col} {m.direction[0]}</td>
                          <td>{m.points}</td>
                          <td>{m.value.toFixed(3)}</td>
                          <td>
                            <button onClick={() => applyEvaluatedMove(m)} style={{fontSize: '0.7rem'}}>Play</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InteractiveGame;
