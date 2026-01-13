import React, { useState, useEffect } from 'react';
import { GameData, BoardSquare, PremiumSquareType } from '../types';
import Board from './Board';
import PlayerHUD from './PlayerHUD';
import PlaybackControls from './PlaybackControls';
import MoveLog from './MoveLog';
import MoveValidity from './MoveValidity';
import WordDefinition from './WordDefinition';
import './GameViewer.css';

interface GameViewerProps {
  game: GameData;
  onBack: () => void;
}

// Premium square layout for standard Scrabble
const PREMIUM_SQUARES: PremiumSquareType[][] = [
  ['TW', null, null, 'DL', null, null, null, 'TW', null, null, null, 'DL', null, null, 'TW'],
  [null, 'DW', null, null, null, 'TL', null, null, null, 'TL', null, null, null, 'DW', null],
  [null, null, 'DW', null, null, null, 'DL', null, 'DL', null, null, null, 'DW', null, null],
  ['DL', null, null, 'DW', null, null, null, 'DL', null, null, null, 'DW', null, null, 'DL'],
  [null, null, null, null, 'DW', null, null, null, null, null, 'DW', null, null, null, null],
  [null, 'TL', null, null, null, 'TL', null, null, null, 'TL', null, null, null, 'TL', null],
  [null, null, 'DL', null, null, null, 'DL', null, 'DL', null, null, null, 'DL', null, null],
  ['TW', null, null, 'DL', null, null, null, 'DW', null, null, null, 'DL', null, null, 'TW'],
  [null, null, 'DL', null, null, null, 'DL', null, 'DL', null, null, null, 'DL', null, null],
  [null, 'TL', null, null, null, 'TL', null, null, null, 'TL', null, null, null, 'TL', null],
  [null, null, null, null, 'DW', null, null, null, null, null, 'DW', null, null, null, null],
  ['DL', null, null, 'DW', null, null, null, 'DL', null, null, null, 'DW', null, null, 'DL'],
  [null, null, 'DW', null, null, null, 'DL', null, 'DL', null, null, null, 'DW', null, null],
  [null, 'DW', null, null, null, 'TL', null, null, null, 'TL', null, null, null, 'DW', null],
  ['TW', null, null, 'DL', null, null, null, 'TW', null, null, null, 'DL', null, null, 'TW']
];

const GameViewer: React.FC<GameViewerProps> = ({ game, onBack }) => {
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [board, setBoard] = useState<BoardSquare[][]>([]);
  const [currentWord, setCurrentWord] = useState<string | null>(null);
  const [isMoveValid, setIsMoveValid] = useState(true);

  // Initialize board
  useEffect(() => {
    const initialBoard: BoardSquare[][] = Array(15).fill(null).map((_, row) =>
      Array(15).fill(null).map((_, col) => ({
        row,
        col,
        letter: null,
        premium: PREMIUM_SQUARES[row][col],
        isNew: false
      }))
    );
    setBoard(initialBoard);
  }, [game]);

  // Update board when turn changes
  useEffect(() => {
    if (currentTurnIndex < 0 || currentTurnIndex > game.turns.length) return;

    // Parse board state from the turn
    const turn = game.turns[currentTurnIndex];
    if (!turn?.board_state) return;

    const lines = turn.board_state.split('\n');
    const newBoard: BoardSquare[][] = Array(15).fill(null).map((_, row) =>
      Array(15).fill(null).map((_, col) => ({
        row,
        col,
        letter: null,
        premium: PREMIUM_SQUARES[row][col],
        isNew: false
      }))
    );

    // Parse the board state
    // Format: " 0 . . . T I L E . . . . . . . "
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Match lines that start with a row number (0-14) followed by spaces and letters/dots
      const match = line.match(/^\s*(\d+)\s+(.*)/);
      if (!match) continue;

      const rowNum = parseInt(match[1]);
      if (rowNum < 0 || rowNum >= 15) continue;

      const rowData = match[2].trim().split(/\s+/);

      for (let col = 0; col < Math.min(15, rowData.length); col++) {
        const cell = rowData[col];
        if (cell && cell !== '.' && cell !== '') {
          newBoard[rowNum][col].letter = cell;
          newBoard[rowNum][col].premium = null;
        }
      }
    }

    // Mark newly placed tiles
    if (turn.action_type === 'PLAY' && turn.position && turn.word) {
      const [row, col] = turn.position;
      const isAcross = turn.direction === 'Across';
      
      for (let i = 0; i < turn.word.length; i++) {
        const r = isAcross ? row : row + i;
        const c = isAcross ? col + i : col;
        if (r >= 0 && r < 15 && c >= 0 && c < 15) {
          newBoard[r][c].isNew = true;
        }
      }
      
      // Update current word for definition lookup
      setCurrentWord(turn.word);
      // A move with a word and score > 0 is valid
      setIsMoveValid(turn.score > 0);
    } else if (turn.action_type === 'PASS') {
      setCurrentWord(null);
      setIsMoveValid(true); // Pass is valid
    } else if (turn.action_type === 'EXCHANGE') {
      setCurrentWord(null);
      setIsMoveValid(true); // Exchange is valid
    } else {
      setCurrentWord(null);
      setIsMoveValid(false); // Invalid move
    }

    setBoard(newBoard);
  }, [currentTurnIndex, game.turns]);

  // Auto-play functionality
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTurnIndex((prev) => {
        if (prev >= game.turns.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, game.turns.length]);

  const currentTurn = game.turns[currentTurnIndex];
  const currentPlayer = currentTurn?.player ?? 0;

  return (
    <div className="game-viewer">
      <div className="game-viewer-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Games
        </button>
        <h2>{game.player_names[0]} vs {game.player_names[1]}</h2>
        <div className="game-info">
          Turn {currentTurnIndex + 1} / {game.turns.length}
        </div>
      </div>

      <div className="game-layout">
        <div className="left-panel">
          <PlayerHUD
            playerName={game.player_names[0]}
            playerId={0}
            currentPlayer={currentPlayer}
            score={currentTurnIndex >= 0 ? 
              game.turns.slice(0, currentTurnIndex + 1)
                .filter(t => t.player === 0)
                .reduce((sum, t) => sum + t.score, 0) : 0
            }
            rack={currentTurn?.rack_after && currentTurn.player === 0 ? 
              currentTurn.rack_after : 
              (currentTurnIndex > 0 ? 
                game.turns.slice(0, currentTurnIndex)
                  .reverse()
                  .find(t => t.player === 0)?.rack_after || [] : []
              )
            }
            lastScore={currentTurn?.player === 0 ? currentTurn.score : undefined}
          />
          
          <WordDefinition word={currentWord} />
        </div>

        <div className="center-panel">
          <Board board={board} />
          <PlaybackControls
            currentTurn={currentTurnIndex}
            totalTurns={game.turns.length}
            isPlaying={isPlaying}
            playbackSpeed={playbackSpeed}
            onJumpToStart={() => setCurrentTurnIndex(0)}
            onPrevious={() => setCurrentTurnIndex(Math.max(0, currentTurnIndex - 1))}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onNext={() => setCurrentTurnIndex(Math.min(game.turns.length - 1, currentTurnIndex + 1))}
            onJumpToEnd={() => setCurrentTurnIndex(game.turns.length - 1)}
            onSeek={(turn) => setCurrentTurnIndex(turn)}
            onSpeedChange={setPlaybackSpeed}
          />
        </div>

        <div className="right-panel">
          <PlayerHUD
            playerName={game.player_names[1]}
            playerId={1}
            currentPlayer={currentPlayer}
            score={currentTurnIndex >= 0 ? 
              game.turns.slice(0, currentTurnIndex + 1)
                .filter(t => t.player === 1)
                .reduce((sum, t) => sum + t.score, 0) : 0
            }
            rack={currentTurn?.rack_after && currentTurn.player === 1 ? 
              currentTurn.rack_after : 
              (currentTurnIndex > 0 ? 
                game.turns.slice(0, currentTurnIndex)
                  .reverse()
                  .find(t => t.player === 1)?.rack_after || [] : []
              )
            }
            lastScore={currentTurn?.player === 1 ? currentTurn.score : undefined}
          />
          
          <div className="bag-tracker">
            <h3>📦 Bag</h3>
            <div className="bag-count">
              {currentTurn?.tiles_in_bag ?? 0} tiles
            </div>
          </div>
          
          <MoveValidity 
            isValid={isMoveValid}
            moveDescription={currentTurn?.action_type === 'PLAY' ? currentWord || undefined : currentTurn?.action_type}
          />
        </div>
      </div>

      <div className="bottom-panel">
        <MoveLog
          turns={game.turns}
          currentTurnIndex={currentTurnIndex}
          onSelectTurn={setCurrentTurnIndex}
        />
      </div>
    </div>
  );
};

export default GameViewer;
