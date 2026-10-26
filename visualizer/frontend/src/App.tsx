import React, { useState, useEffect, useRef } from 'react';
import { BoardState, CandidateMove, GameSnapshot, PlayerConfig, EngineStats } from './types';
import { Board, TILE_POINTS } from './components/Board';
import { TileRack } from './components/TileRack';
import { PlayerHUD } from './components/PlayerHUD';
import { CandidateTable } from './components/CandidateTable';
import { ArenaControls } from './components/ArenaControls';
import { BagModal } from './components/BagModal';
import { DuplicateModal } from './components/DuplicateModal';
import { GameReplayView } from './components/GameReplayView';
import { PositionAnalyzer } from './components/PositionAnalyzer';
import { WordInspector } from './components/WordInspector';
import { EngineStatsView } from './components/EngineStatsView';

const INITIAL_BOARD = (): BoardState => Array(15).fill(null).map(() => Array(15).fill(null));

const DEFAULT_BAG = (
  'E'.repeat(12) + 'A'.repeat(9) + 'I'.repeat(9) + 'O'.repeat(8) +
  'N'.repeat(6) + 'R'.repeat(6) + 'T'.repeat(6) + 'L'.repeat(4) +
  'S'.repeat(4) + 'U'.repeat(4) + 'D'.repeat(4) + 'G'.repeat(3) +
  'B'.repeat(2) + 'C'.repeat(2) + 'M'.repeat(2) + 'P'.repeat(2) +
  'F'.repeat(2) + 'H'.repeat(2) + 'V'.repeat(2) + 'W'.repeat(2) +
  'Y'.repeat(2) + 'K' + 'J' + 'X' + 'Q' + 'Z' + '??'
).split('');

// Tile drawing utility function
const drawTiles = (count: number, currentBag: string[]): [string[], string[]] => {
  const copy = [...currentBag];
  const drawn: string[] = [];
  for (let i = 0; i < count && copy.length > 0; i++) {
    const idx = Math.floor(Math.random() * copy.length);
    drawn.push(copy.splice(idx, 1)[0]);
  }
  return [drawn, copy];
};

// Generates an initial deal where P1 (7 tiles) and P2 (7 tiles) are drawn from DEFAULT_BAG, leaving 86 tiles in bag
const createInitialGameRacks = (): { p1: string[]; p2: string[]; bag: string[] } => {
  const [p1, b1] = drawTiles(7, DEFAULT_BAG);
  const [p2, b2] = drawTiles(7, b1);
  return { p1, p2, bag: b2 };
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'arena' | 'replays' | 'compare'>('arena');
  const [lexicon, setLexicon] = useState<string>('CSW24');

  // Player 1 & Player 2 Configurations
  const [player1, setPlayer1] = useState<PlayerConfig>({
    type: 'human',
    engine: 'v4',
    model: 'latest',
    name: 'Human'
  });

  const [player2, setPlayer2] = useState<PlayerConfig>({
    type: 'ai',
    engine: 'v4',
    model: 'latest',
    name: 'Alphable V4'
  });

  // Game Arena State - initialized with exact 100-tile conservation
  const [initialTiles] = useState(createInitialGameRacks);
  const [board, setBoard] = useState<BoardState>(INITIAL_BOARD);
  const [p1Rack, setP1Rack] = useState<string[]>(initialTiles.p1);
  const [p2Rack, setP2Rack] = useState<string[]>(initialTiles.p2);
  const [p1Score, setP1Score] = useState<number>(0);
  const [p2Score, setP2Score] = useState<number>(0);
  const [bag, setBag] = useState<string[]>(initialTiles.bag);
  const [activePlayer, setActivePlayer] = useState<number>(0); // 0 = P1, 1 = P2
  const [turnNumber, setTurnNumber] = useState<number>(1);
  const [candidates, setCandidates] = useState<CandidateMove[]>([]);
  const [lastScoreDelta, setLastScoreDelta] = useState<{ player: number; delta: number } | null>(null);
  const [highlightCells, setHighlightCells] = useState<Array<[number, number]>>([]);

  // Game End & Over States
  const [isGameOver, setIsGameOver] = useState<boolean>(false);
  const [gameOverReason, setGameOverReason] = useState<string | null>(null);
  const [consecutivePasses, setConsecutivePasses] = useState<number>(0);

  // Snapshot History Stack for Undo/Rewind
  const [historyStack, setHistoryStack] = useState<GameSnapshot[]>([]);

  // Execution & Auto-play State
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(false);
  const [autoPlaySpeed, setAutoPlaySpeed] = useState<number>(1.0);
  const [statusMessage, setStatusMessage] = useState<string>('Match ready. Play a move or start AI match.');

  // Modals & Panels
  const [isBagModalOpen, setIsBagModalOpen] = useState<boolean>(false);
  const [isDuplicateModalOpen, setIsDuplicateModalOpen] = useState<boolean>(false);
  const [duplicateP1Decision, setDuplicateP1Decision] = useState<any>(null);
  const [duplicateP2Decision, setDuplicateP2Decision] = useState<any>(null);
  const [isDuplicateLoading, setIsDuplicateLoading] = useState<boolean>(false);

  // Engine Stats & Lexicon Word Inspector
  const [engineStats, setEngineStats] = useState<EngineStats | null>(null);
  const [activeRightTab, setActiveRightTab] = useState<'candidates' | 'stats' | 'dictionary'>('candidates');
  const [inspectedWord, setInspectedWord] = useState<string>('');
  const [isWordModalOpen, setIsWordModalOpen] = useState<boolean>(false);
  const [autoDefineWord, setAutoDefineWord] = useState<boolean>(true);

  // Inspect word in Lexicon Word Inspector without modifying game state
  const handleInspectWord = (word: string | undefined | null) => {
    if (!word) return;
    const clean = word.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
    if (!clean) return;
    setInspectedWord(clean);
    setActiveRightTab('dictionary');
  };

  // Human Move Input
  const [playWord, setPlayWord] = useState<string>('');
  const [playRow, setPlayRow] = useState<number>(7);
  const [playCol, setPlayCol] = useState<number>(7);
  const [playDir, setPlayDir] = useState<'Across' | 'Down'>('Across');

  const autoPlayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Push current state to undo history
  const recordSnapshot = (lastMoveInfo: any = null) => {
    const snapshot: GameSnapshot = {
      board: board.map(r => [...r]),
      p1Rack: [...p1Rack],
      p2Rack: [...p2Rack],
      p1Score,
      p2Score,
      bag: [...bag],
      activePlayer,
      lastMove: lastMoveInfo,
      turnNumber,
      isGameOver,
      gameOverReason,
      consecutivePasses,
    };
    setHistoryStack(prev => [...prev, snapshot]);
  };

  // Undo / Rewind
  const handleUndoMove = () => {
    if (historyStack.length === 0) return;

    setIsAutoPlaying(false);
    const prev = historyStack[historyStack.length - 1];
    setHistoryStack(historyStack.slice(0, -1));

    setBoard(prev.board);
    setP1Rack(prev.p1Rack);
    setP2Rack(prev.p2Rack);
    setP1Score(prev.p1Score);
    setP2Score(prev.p2Score);
    setBag(prev.bag);
    setActivePlayer(prev.activePlayer);
    setTurnNumber(prev.turnNumber);
    setIsGameOver(prev.isGameOver ?? false);
    setGameOverReason(prev.gameOverReason ?? null);
    setConsecutivePasses(prev.consecutivePasses ?? 0);
    setCandidates([]);
    setHighlightCells([]);
    setStatusMessage(`Rewound to Turn ${prev.turnNumber}.`);
  };

  // Reset Match
  const handleResetMatch = () => {
    setIsAutoPlaying(false);
    const { p1, p2, bag: nextBag } = createInitialGameRacks();

    setBoard(INITIAL_BOARD());
    setP1Rack(p1);
    setP2Rack(p2);
    setP1Score(0);
    setP2Score(0);
    setBag(nextBag);
    setActivePlayer(0);
    setTurnNumber(1);
    setIsGameOver(false);
    setGameOverReason(null);
    setConsecutivePasses(0);
    setHistoryStack([]);
    setCandidates([]);
    setHighlightCells([]);
    setStatusMessage('Match reset with fresh 100-tile set.');
  };


  // Execute an AI Turn
  const executeAiTurn = (playerIdx: number) => {
    if (isGameOver) {
      setIsAutoPlaying(false);
      return;
    }
    const activeCfg = playerIdx === 0 ? player1 : player2;
    if (activeCfg.type === 'human') return;

    const activeRack = playerIdx === 0 ? p1Rack : p2Rack;
    if (activeRack.length === 0) {
      setIsAutoPlaying(false);
      setIsGameOver(true);
      return;
    }

    setIsThinking(true);
    const scoreDiff = playerIdx === 0 ? (p1Score - p2Score) : (p2Score - p1Score);

    fetch('/api/interactive/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        board,
        rack: activeRack,
        engine: activeCfg.engine,
        model: activeCfg.model,
        score_diff: scoreDiff,
        bag_remaining: bag.length,
        lexicon
      })
    })
      .then(res => {
        if (!res.ok) {
          throw new Error(`Server returned HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        setIsThinking(false);
        if (data.error) {
          setIsAutoPlaying(false);
          setStatusMessage(`Engine error: ${data.error}`);
          return;
        }

        if (data.candidates) setCandidates(data.candidates);

        if (data.metadata) {
          setEngineStats({
            engine: activeCfg.engine,
            model: activeCfg.model,
            method: data.metadata.method || 'bams_search',
            latency_ms: data.metadata.latency_ms || 0,
            stage: data.metadata.stage || 'Midgame',
            num_candidates_evaluated: data.metadata.num_candidates_evaluated || (data.candidates ? data.candidates.length : 0),
            num_samples: data.metadata.num_samples,
            best_bams_score: data.metadata.best_bams_score,
            static_equity: data.metadata.static_equity,
            volatility_used: data.metadata.volatility_used,
            sampled_racks: data.metadata.sampled_racks,
            evaluations: data.metadata.evaluations,
          });
        }

        if (data.action === 'PLAY' && data.move) {
          recordSnapshot({
            player: playerIdx,
            word: data.move.word,
            coord: data.move.coord,
            points: data.points,
            action: 'PLAY'
          });

          if (autoDefineWord && data.move.word) {
            const clean = data.move.word.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
            if (clean) setInspectedWord(clean);
          }

          // Apply move to board
          const nextBoard = board.map(r => [...r]);
          const isAcross = (data.move.direction || 'Across').toLowerCase().startsWith('a');
          const newHighlights: Array<[number, number]> = [];

          for (let i = 0; i < data.move.word.length; i++) {
            const r = isAcross ? data.move.row : data.move.row + i;
            const c = isAcross ? data.move.col + i : data.move.col;
            nextBoard[r][c] = data.move.word[i];
            newHighlights.push([r, c]);
          }

          setBoard(nextBoard);
          setHighlightCells(newHighlights);

          const pts = data.points || 0;
          const currentP1 = playerIdx === 0 ? p1Score + pts : p1Score;
          const currentP2 = playerIdx === 1 ? p2Score + pts : p2Score;
          if (playerIdx === 0) setP1Score(currentP1);
          else setP2Score(currentP2);
          setLastScoreDelta({ player: playerIdx, delta: pts });

          // Replenish rack
          const remainingTiles = data.new_rack || [];
          const [drawn, nextBag] = drawTiles(7 - remainingTiles.length, bag);
          const nextRack = [...remainingTiles, ...drawn];
          if (playerIdx === 0) setP1Rack(nextRack);
          else setP2Rack(nextRack);
          setBag(nextBag);

          setConsecutivePasses(0);

          // Check if player played out and bag is empty
          if (nextRack.length === 0 && nextBag.length === 0) {
            const oppRack = playerIdx === 0 ? p2Rack : p1Rack;
            const oppBonus = oppRack.reduce((sum, t) => sum + (TILE_POINTS[t.toUpperCase()] || 0), 0);
            const finalP1 = playerIdx === 0 ? currentP1 + oppBonus : currentP1 - oppBonus;
            const finalP2 = playerIdx === 1 ? currentP2 + oppBonus : currentP2 - oppBonus;
            setP1Score(finalP1);
            setP2Score(finalP2);

            setIsAutoPlaying(false);
            setIsGameOver(true);
            const winner = finalP1 > finalP2 ? player1.name : (finalP2 > finalP1 ? player2.name : 'Tie');
            const summary = `${activeCfg.name} played out! Final: ${player1.name} ${finalP1} - ${finalP2} ${player2.name}. ${winner === 'Tie' ? "Draw!" : winner + " wins!"}`;
            setGameOverReason(summary);
            setStatusMessage(summary);
            return;
          }

          setStatusMessage(`${activeCfg.name} played ${data.move.word} (${data.move.coord}) for +${pts} pts!`);
        } else {
          recordSnapshot({
            player: playerIdx,
            word: '',
            coord: '',
            points: 0,
            action: data.action || 'PASS'
          });
          const nextPasses = consecutivePasses + 1;
          setConsecutivePasses(nextPasses);
          setStatusMessage(`${activeCfg.name} ${data.action || 'PASS'}ed.`);

          // 6 consecutive scoreless turns ends the game
          if (nextPasses >= 6) {
            const p1Pen = p1Rack.reduce((sum, t) => sum + (TILE_POINTS[t.toUpperCase()] || 0), 0);
            const p2Pen = p2Rack.reduce((sum, t) => sum + (TILE_POINTS[t.toUpperCase()] || 0), 0);
            const finalP1 = p1Score - p1Pen;
            const finalP2 = p2Score - p2Pen;
            setP1Score(finalP1);
            setP2Score(finalP2);

            setIsAutoPlaying(false);
            setIsGameOver(true);
            const winner = finalP1 > finalP2 ? player1.name : (finalP2 > finalP1 ? player2.name : 'Tie');
            const summary = `Game ended (consecutive passes). Final: ${player1.name} ${finalP1} - ${finalP2} ${player2.name}. ${winner === 'Tie' ? "Draw!" : winner + " wins!"}`;
            setGameOverReason(summary);
            setStatusMessage(summary);
            return;
          }
        }

        setActivePlayer(playerIdx === 0 ? 1 : 0);
        setTurnNumber(prev => prev + 1);
      })
      .catch(err => {
        setIsThinking(false);
        setIsAutoPlaying(false);
        setStatusMessage(`Error during AI turn: ${err}`);
      });
  };

  // Step Move Handler
  const handleStepMove = () => {
    if (isGameOver) return;
    executeAiTurn(activePlayer);
  };

  // Auto-play Loop
  useEffect(() => {
    if (isGameOver) {
      if (isAutoPlaying) setIsAutoPlaying(false);
      return;
    }
    const currentCfg = activePlayer === 0 ? player1 : player2;
    if (isAutoPlaying && currentCfg.type === 'ai' && !isThinking) {
      const delay = autoPlaySpeed === 0 ? 15 : autoPlaySpeed * 1000;
      autoPlayTimerRef.current = setTimeout(() => {
        executeAiTurn(activePlayer);
      }, delay);
    } else if (isAutoPlaying && currentCfg.type === 'human') {
      // Pause if waiting on human
      setIsAutoPlaying(false);
      setStatusMessage("Auto-play paused: Human turn. Enter your play.");
    }

    return () => {
      if (autoPlayTimerRef.current) clearTimeout(autoPlayTimerRef.current);
    };
  }, [isAutoPlaying, activePlayer, isThinking, autoPlaySpeed, isGameOver]);


  // Human Move Placement
  const handleHumanPlay = () => {
    if (!playWord.trim()) return;

    const moveObj = {
      word: playWord.toUpperCase().trim(),
      row: playRow,
      col: playCol,
      direction: playDir
    };

    fetch('/api/interactive/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        board,
        rack: p1Rack,
        move: moveObj,
        engine: 'v4',
        lexicon
      })
    })
      .then(res => res.json())
      .then(data => {
        if (!data.valid) {
          setStatusMessage(`Illegal Play: ${data.error || "Not permitted under official rules."}`);
          return;
        }

        recordSnapshot({
          player: 0,
          word: moveObj.word,
          coord: `${moveObj.row+1}${String.fromCharCode(65+moveObj.col)}`,
          points: data.points,
          action: 'PLAY'
        });

        if (autoDefineWord && moveObj.word) {
          const clean = moveObj.word.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
          if (clean) setInspectedWord(clean);
        }

        const nextBoard = board.map(r => [...r]);
        const isAcross = playDir === 'Across';
        const newHighlights: Array<[number, number]> = [];

        for (let i = 0; i < moveObj.word.length; i++) {
          const r = isAcross ? playRow : playRow + i;
          const c = isAcross ? playCol + i : playCol;
          nextBoard[r][c] = moveObj.word[i];
          newHighlights.push([r, c]);
        }

        setBoard(nextBoard);
        setHighlightCells(newHighlights);

        const pts = data.points || 0;
        setP1Score(prev => prev + pts);
        setLastScoreDelta({ player: 0, delta: pts });

        const remainingRack = data.new_rack || [];
        const [drawn, remainingBag] = drawTiles(7 - remainingRack.length, bag);
        const nextRack = [...remainingRack, ...drawn];
        setP1Rack(nextRack);
        setBag(remainingBag);
        setPlayWord('');
        setCandidates([]);
        setConsecutivePasses(0);

        if (nextRack.length === 0 && remainingBag.length === 0) {
          const oppBonus = p2Rack.reduce((sum, t) => sum + (TILE_POINTS[t.toUpperCase()] || 0), 0);
          const finalP1 = p1Score + pts + oppBonus;
          const finalP2 = p2Score - oppBonus;
          setP1Score(finalP1);
          setP2Score(finalP2);
          setIsGameOver(true);
          setIsAutoPlaying(false);
          const winner = finalP1 > finalP2 ? player1.name : (finalP2 > finalP1 ? player2.name : 'Tie');
          const summary = `You played out! Final: ${player1.name} ${finalP1} - ${finalP2} ${player2.name}. ${winner === 'Tie' ? "Draw!" : winner + " wins!"}`;
          setGameOverReason(summary);
          setStatusMessage(summary);
          return;
        }

        setStatusMessage(`You played ${moveObj.word} for +${pts} pts.`);
        setActivePlayer(1);
        setTurnNumber(prev => prev + 1);
      })
      .catch(err => setStatusMessage(`Validation error: ${err}`));
  };


  // Request AI Hint
  const handleRequestHint = () => {
    setIsThinking(true);
    setStatusMessage("Calculating top candidate moves...");
    const activeRack = activePlayer === 0 ? p1Rack : p2Rack;

    fetch('/api/interactive/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        board,
        rack: activeRack,
        engine: 'v4',
        model: 'latest',
        score_diff: p1Score - p2Score,
        bag_remaining: bag.length,
        lexicon
      })
    })
      .then(res => res.json())
      .then(data => {
        setIsThinking(false);
        if (data.candidates) setCandidates(data.candidates);
        if (data.move) {
          setStatusMessage(`Hint: Consider ${data.move.coord} ${data.move.word} for +${data.points} pts (Equity: ${data.equity})`);
        }
      })
      .catch(err => {
        setIsThinking(false);
        setStatusMessage(`Error getting hint: ${err}`);
      });
  };

  // Duplicate Swap Position
  const handleOpenDuplicateSwap = () => {
    setIsDuplicateModalOpen(true);
    setIsDuplicateLoading(true);
    const activeRack = activePlayer === 0 ? p1Rack : p2Rack;
    const scoreDiff = activePlayer === 0 ? (p1Score - p2Score) : (p2Score - p1Score);

    Promise.all([
      fetch('/api/interactive/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board,
          rack: activeRack,
          engine: player1.engine,
          model: player1.model,
          score_diff: scoreDiff,
          bag_remaining: bag.length,
          lexicon
        })
      }).then(r => r.json()),
      fetch('/api/interactive/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board,
          rack: activeRack,
          engine: player2.engine,
          model: player2.model,
          score_diff: scoreDiff,
          bag_remaining: bag.length,
          lexicon
        })
      }).then(r => r.json())
    ])
      .then(([p1Res, p2Res]) => {
        setDuplicateP1Decision({
          name: player1.name,
          action: p1Res.action,
          move: p1Res.move || {},
          points: p1Res.points || 0,
          equity: p1Res.equity || 0,
          new_rack: p1Res.new_rack || [],
          candidates: p1Res.candidates || []
        });
        setDuplicateP2Decision({
          name: player2.name,
          action: p2Res.action,
          move: p2Res.move || {},
          points: p2Res.points || 0,
          equity: p2Res.equity || 0,
          new_rack: p2Res.new_rack || [],
          candidates: p2Res.candidates || []
        });
        setIsDuplicateLoading(false);
      })
      .catch(err => {
        console.error("Duplicate comparison error:", err);
        setIsDuplicateLoading(false);
      });
  };

  // Apply a decision from the duplicate comparison modal
  const handleApplyDuplicateDecision = (decision: any) => {
    setIsDuplicateModalOpen(false);
    if (!decision || decision.action !== 'PLAY') return;

    recordSnapshot({
      player: activePlayer,
      word: decision.move.word,
      coord: decision.move.coord,
      points: decision.points,
      action: 'PLAY (Duplicate Branch)'
    });

    if (autoDefineWord && decision.move.word) {
      const clean = decision.move.word.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
      if (clean) setInspectedWord(clean);
    }

    const nextBoard = board.map(r => [...r]);
    const isAcross = (decision.move.direction || 'Across').toLowerCase().startsWith('a');
    const newHighlights: Array<[number, number]> = [];

    for (let i = 0; i < decision.move.word.length; i++) {
      const r = isAcross ? decision.move.row : decision.move.row + i;
      const c = isAcross ? decision.move.col + i : decision.move.col;
      nextBoard[r][c] = decision.move.word[i];
      newHighlights.push([r, c]);
    }

    setBoard(nextBoard);
    setHighlightCells(newHighlights);

    const pts = decision.points || 0;
    if (activePlayer === 0) setP1Score(prev => prev + pts);
    else setP2Score(prev => prev + pts);

    const leave = decision.new_rack ?? (decision.candidates?.[0]?.leave?.split('') || []);
    const [drawn, nextBag] = drawTiles(7 - leave.length, bag);

    if (activePlayer === 0) setP1Rack([...leave, ...drawn]);
    else setP2Rack([...leave, ...drawn]);
    setBag(nextBag);

    setActivePlayer(activePlayer === 0 ? 1 : 0);
    setTurnNumber(prev => prev + 1);
    setStatusMessage(`Applied duplicate play: ${decision.move.word} for +${pts} pts.`);
  };


  return (
    <div>
      {/* Studio Top Navigation */}
      <nav className="studio-navbar">
        <div className="studio-logo">
          <span>ALPHABLE</span>
          <span className="badge">STUDIO 2.5</span>
        </div>

        <div className="studio-tabs">
          <button
            className={`studio-tab-btn ${activeTab === 'arena' ? 'active' : ''}`}
            onClick={() => setActiveTab('arena')}
          >
            Match Arena
          </button>
          <button
            className={`studio-tab-btn ${activeTab === 'replays' ? 'active' : ''}`}
            onClick={() => setActiveTab('replays')}
          >
            Replay & Tournaments
          </button>
          <button
            className={`studio-tab-btn ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            Position Lab
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <select
            value={lexicon}
            onChange={(e) => setLexicon(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-elevated)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '0.35rem 0.6rem',
              fontSize: '0.8rem',
              fontWeight: 700
            }}
          >
            <option value="CSW24">CSW24 (Collins)</option>
            <option value="NWL23">NWL23 (North American)</option>
          </select>
          <button
            className="btn-secondary"
            onClick={() => setIsWordModalOpen(true)}
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
            title="Open Lexicon & Word Definition Inspector"
          >
            Word Lookup
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: '#10b981' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }}></span>
            <span>Online</span>
          </div>
        </div>
      </nav>

      {/* Main Studio Viewport */}
      <main className="studio-container">
        {activeTab === 'arena' && (
          <div>
            <ArenaControls
              player1={player1}
              player2={player2}
              onPlayer1Change={setPlayer1}
              onPlayer2Change={setPlayer2}
              isAutoPlaying={isAutoPlaying}
              onToggleAutoPlay={() => setIsAutoPlaying(!isAutoPlaying)}
              onStepMove={handleStepMove}
              onUndoMove={handleUndoMove}
              canUndo={historyStack.length > 0}
              onDuplicateSwap={handleOpenDuplicateSwap}
              onOpenBagModal={() => setIsBagModalOpen(true)}
              onResetMatch={handleResetMatch}
              autoPlaySpeed={autoPlaySpeed}
              onSpeedChange={setAutoPlaySpeed}
              activePlayer={activePlayer}
              isThinking={isThinking}
              isGameOver={isGameOver}
              gameOverReason={gameOverReason}
            />


            <PlayerHUD
              p1Name={player1.name}
              p2Name={player2.name}
              p1Score={p1Score}
              p2Score={p2Score}
              bagCount={bag.length}
              activePlayer={activePlayer}
              scoreDelta={lastScoreDelta}
              onOpenBag={() => setIsBagModalOpen(true)}
            />

            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2rem' }}>
              {/* Board and Player Rack */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                <Board
                  board={board}
                  highlightCells={highlightCells}
                  onCellClick={(r, c) => { setPlayRow(r); setPlayCol(c); }}
                />

                <TileRack rack={activePlayer === 0 ? p1Rack : p2Rack} />

                {/* Human Placement Panel (Active when activePlayer is Human) */}
                {((activePlayer === 0 && player1.type === 'human') || (activePlayer === 1 && player2.type === 'human')) && (
                  <div className="panel-card" style={{ width: '100%', maxWidth: '590px' }}>
                    <div style={{ fontSize: '0.85rem', color: '#f59e0b', fontWeight: 600, marginBottom: '0.65rem' }}>
                      {statusMessage}
                    </div>

                    <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <input
                        type="text"
                        value={playWord}
                        onChange={(e) => setPlayWord(e.target.value.toUpperCase())}
                        placeholder="ENTER WORD"
                        style={{
                          flex: 1,
                          padding: '0.5rem 0.8rem',
                          backgroundColor: 'var(--bg-elevated)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '4px',
                          color: 'white',
                          fontWeight: 700,
                          letterSpacing: '0.1em'
                        }}
                      />

                      <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center', fontSize: '0.8rem' }}>
                        <span>R:</span>
                        <input
                          type="number"
                          min={0}
                          max={14}
                          value={playRow}
                          onChange={(e) => setPlayRow(Number(e.target.value))}
                          style={{ width: '42px', padding: '0.35rem', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: 'white' }}
                        />
                        <span>C:</span>
                        <input
                          type="number"
                          min={0}
                          max={14}
                          value={playCol}
                          onChange={(e) => setPlayCol(Number(e.target.value))}
                          style={{ width: '42px', padding: '0.35rem', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: 'white' }}
                        />
                      </div>

                      <select
                        value={playDir}
                        onChange={(e) => setPlayDir(e.target.value as any)}
                        style={{ padding: '0.45rem', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: 'white' }}
                      >
                        <option value="Across">Across</option>
                        <option value="Down">Down</option>
                      </select>

                      <button className="btn-primary" onClick={handleHumanPlay} disabled={isThinking}>
                        Play
                      </button>

                      <button className="btn-secondary" onClick={handleRequestHint} disabled={isThinking}>
                        Hint
                      </button>

                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Move Evaluations, Engine Stats, and Word Inspector */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Right Column Navigation Tabs */}
                <div style={{ display: 'flex', gap: '0.35rem', backgroundColor: 'var(--bg-elevated)', padding: '0.3rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  <button
                    className={`studio-tab-btn ${activeRightTab === 'candidates' ? 'active' : ''}`}
                    onClick={() => setActiveRightTab('candidates')}
                    style={{ flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem' }}
                  >
                    Evaluations ({candidates.length})
                  </button>
                  <button
                    className={`studio-tab-btn ${activeRightTab === 'stats' ? 'active' : ''}`}
                    onClick={() => setActiveRightTab('stats')}
                    style={{ flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem' }}
                  >
                    Engine Thoughts
                  </button>
                  <button
                    className={`studio-tab-btn ${activeRightTab === 'dictionary' ? 'active' : ''}`}
                    onClick={() => setActiveRightTab('dictionary')}
                    style={{ flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem' }}
                  >
                    Word Inspector
                  </button>
                </div>

                {activeRightTab === 'candidates' && (
                  <CandidateTable
                    candidates={candidates}
                    title="Live Strategic Evaluations"
                    onInspectWord={(w) => {
                      setInspectedWord(w);
                      setActiveRightTab('dictionary');
                    }}
                    onHoverCandidate={(c) => {
                      if (c && c.word && c.row !== undefined && c.col !== undefined) {
                        const isAcross = (c.direction || 'Across').toLowerCase().startsWith('a');
                        const h: Array<[number, number]> = [];
                        for (let i = 0; i < c.word.length; i++) {
                          h.push([isAcross ? c.row : c.row + i, isAcross ? c.col + i : c.col]);
                        }
                        setHighlightCells(h);
                      } else {
                        setHighlightCells([]);
                      }
                    }}
                  />
                )}

                {activeRightTab === 'stats' && (
                  <EngineStatsView
                    stats={engineStats}
                    currentCandidates={candidates}
                    onSelectWord={(w) => {
                      setInspectedWord(w);
                      setActiveRightTab('dictionary');
                    }}
                  />
                )}

                {activeRightTab === 'dictionary' && (
                  <WordInspector
                    initialWord={inspectedWord}
                    lexicon={lexicon}
                    isInline={true}
                    autoDefine={autoDefineWord}
                    onToggleAutoDefine={setAutoDefineWord}
                  />
                )}

                {/* Turn Snapshot History List */}
                <div className="panel-card" style={{ flex: 1, minHeight: '200px', maxHeight: '340px', overflowY: 'auto' }}>
                  <div className="panel-title">
                    <span>Game Timeline ({historyStack.length} turns)</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Click word to define &bull; Rewind jumps</span>
                  </div>
                  {historyStack.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
                      Game started at Turn 1. Moves will appear here.
                    </div>
                  ) : (
                    <table className="candidate-table">
                      <thead>
                        <tr>
                          <th style={{ width: '45px' }}>Turn</th>
                          <th>Player</th>
                          <th>Move (Click to Define)</th>
                          <th style={{ textAlign: 'right' }}>Pts</th>
                          <th style={{ textAlign: 'center', width: '70px' }}>Rewind</th>
                        </tr>
                      </thead>
                      <tbody>
                        {historyStack.map((snap, idx) => (
                          <tr key={idx} style={{ backgroundColor: 'transparent' }}>
                            <td style={{ color: 'var(--text-muted)' }}>{snap.turnNumber}</td>
                            <td style={{ color: snap.lastMove?.player === 0 ? '#60a5fa' : '#c084fc', fontWeight: 600 }}>
                              {snap.lastMove?.player === 0 ? player1.name : player2.name}
                            </td>
                            <td style={{ fontWeight: 700 }}>
                              {snap.lastMove?.word ? (
                                <span
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleInspectWord(snap.lastMove?.word);
                                  }}
                                  style={{
                                    color: '#38bdf8',
                                    cursor: 'pointer',
                                    textDecoration: 'underline',
                                    textUnderlineOffset: '3px'
                                  }}
                                  title="Click to view definition in Lexicon Word Inspector"
                                >
                                  {snap.lastMove.word} {snap.lastMove.coord ? `(${snap.lastMove.coord})` : ''}
                                </span>
                              ) : (
                                <span style={{ color: 'var(--text-muted)' }}>{snap.lastMove?.action || 'MOVE'}</span>
                              )}
                            </td>
                            <td style={{ textAlign: 'right', fontWeight: 700, color: '#10b981' }}>
                              +{snap.lastMove?.points || 0}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              <button
                                className="btn-secondary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setIsAutoPlaying(false);
                                  setBoard(snap.board);
                                  setP1Rack(snap.p1Rack);
                                  setP2Rack(snap.p2Rack);
                                  setP1Score(snap.p1Score);
                                  setP2Score(snap.p2Score);
                                  setBag(snap.bag);
                                  setActivePlayer(snap.activePlayer);
                                  setTurnNumber(snap.turnNumber);
                                  setHistoryStack(historyStack.slice(0, idx));
                                  setStatusMessage(`Rewound to Turn ${snap.turnNumber}.`);
                                }}
                                style={{ padding: '0.18rem 0.45rem', fontSize: '0.7rem' }}
                                title="Rewind match to this turn"
                              >
                                Rewind
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'replays' && <GameReplayView />}
        {activeTab === 'compare' && <PositionAnalyzer />}
      </main>

      {/* Bag Inspector Modal */}
      {isBagModalOpen && (
        <BagModal bag={bag} onClose={() => setIsBagModalOpen(false)} />
      )}

      {/* Duplicate Position Decision Modal */}
      {isDuplicateModalOpen && (
        <DuplicateModal
          rack={activePlayer === 0 ? p1Rack : p2Rack}
          p1Name={player1.name}
          p2Name={player2.name}
          p1Decision={duplicateP1Decision}
          p2Decision={duplicateP2Decision}
          isLoading={isDuplicateLoading}
          onApplyDecision={handleApplyDuplicateDecision}
          onClose={() => setIsDuplicateModalOpen(false)}
        />
      )}

      {/* Standalone Word Definition Inspector Modal */}
      {isWordModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(4px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem'
          }}
          onClick={() => setIsWordModalOpen(false)}
        >
          <div style={{ width: '100%', maxWidth: '580px' }} onClick={(e) => e.stopPropagation()}>
            <WordInspector
              initialWord={inspectedWord}
              lexicon={lexicon}
              onClose={() => setIsWordModalOpen(false)}
              autoDefine={autoDefineWord}
              onToggleAutoDefine={setAutoDefineWord}
            />
          </div>
        </div>
      )}
    </div>
  );
};
