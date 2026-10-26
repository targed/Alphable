import React from 'react';
import { PlayerConfig } from '../types';

interface ArenaControlsProps {
  player1: PlayerConfig;
  player2: PlayerConfig;
  onPlayer1Change: (cfg: PlayerConfig) => void;
  onPlayer2Change: (cfg: PlayerConfig) => void;
  isAutoPlaying: boolean;
  onToggleAutoPlay: () => void;
  onStepMove: () => void;
  onUndoMove: () => void;
  canUndo: boolean;
  onDuplicateSwap: () => void;
  onOpenBagModal: () => void;
  onResetMatch: () => void;
  autoPlaySpeed: number;
  onSpeedChange: (speed: number) => void;
  activePlayer: number;
  isThinking: boolean;
  isGameOver?: boolean;
  gameOverReason?: string | null;
}

const ENGINE_LABELS: Record<string, string> = {
  v4: 'Alphable V4',
  v3: 'Alphable V3',
  magpie: 'Base MAGPIE',
  greedy: 'Score Greedy',
  human: 'Human'
};

export const ArenaControls: React.FC<ArenaControlsProps> = ({
  player1,
  player2,
  onPlayer1Change,
  onPlayer2Change,
  isAutoPlaying,
  onToggleAutoPlay,
  onStepMove,
  onUndoMove,
  canUndo,
  onDuplicateSwap,
  onOpenBagModal,
  onResetMatch,
  autoPlaySpeed,
  onSpeedChange,
  activePlayer,
  isThinking,
  isGameOver = false,
  gameOverReason = null,
}) => {

  return (
    <div className="panel-card" style={{ marginBottom: '1.25rem', padding: '0.9rem 1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Matchup Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          {/* Player 1 Selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#60a5fa', fontWeight: 700 }}>P1:</span>
            <select
              value={player1.type === 'human' ? 'human' : player1.engine}
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'human') {
                  onPlayer1Change({ type: 'human', engine: 'v4', model: 'latest', name: 'Human' });
                } else {
                  onPlayer1Change({ type: 'ai', engine: val, model: 'latest', name: ENGINE_LABELS[val] || val });
                }
              }}
              style={{
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '0.35rem 0.6rem',
                fontSize: '0.8rem',
                fontWeight: 600
              }}
            >
              <option value="human">Human (You)</option>
              <option value="v4">Alphable V4 (BAMS)</option>
              <option value="v3">Alphable V3 (ResNet)</option>
              <option value="magpie">Base MAGPIE</option>
              <option value="greedy">Score Greedy</option>
            </select>
          </div>

          <span style={{ color: 'var(--text-muted)', fontWeight: 800, fontSize: '0.8rem' }}>VS</span>

          {/* Player 2 Selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#c084fc', fontWeight: 700 }}>P2:</span>
            <select
              value={player2.type === 'human' ? 'human' : player2.engine}
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'human') {
                  onPlayer2Change({ type: 'human', engine: 'v4', model: 'latest', name: 'Human' });
                } else {
                  onPlayer2Change({ type: 'ai', engine: val, model: 'latest', name: ENGINE_LABELS[val] || val });
                }
              }}
              style={{
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '0.35rem 0.6rem',
                fontSize: '0.8rem',
                fontWeight: 600
              }}
            >
              <option value="v4">Alphable V4 (BAMS)</option>
              <option value="v3">Alphable V3 (ResNet)</option>
              <option value="magpie">Base MAGPIE</option>
              <option value="greedy">Score Greedy</option>
              <option value="human">Human</option>
            </select>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <button
            className="btn-primary"
            onClick={onStepMove}
            disabled={isGameOver || isAutoPlaying || isThinking}
            title={isGameOver ? "Match completed" : "Execute next AI turn"}
          >
            {isGameOver ? "Game Complete" : (isThinking ? "Thinking..." : "Step Move")}
          </button>

          <button
            className="btn-secondary"
            onClick={onToggleAutoPlay}
            disabled={isGameOver || isThinking}
            style={{
              backgroundColor: isAutoPlaying ? '#b45309' : 'var(--bg-elevated)',
              color: isAutoPlaying ? '#fffbeb' : 'var(--text-primary)'
            }}
          >
            {isAutoPlaying ? "Pause" : "Auto-play"}
          </button>

          <button
            className="btn-secondary"
            onClick={onUndoMove}
            disabled={!canUndo || isAutoPlaying || isThinking}
            title="Rewind to previous turn"
          >
            Undo
          </button>

          <button
            className="btn-secondary"
            onClick={onDuplicateSwap}
            disabled={isGameOver || isAutoPlaying || isThinking}
            title="Evaluate what each player would do in current position"
            style={{ borderColor: '#f59e0b', color: '#fef3c7' }}
          >
            Duplicate Swap
          </button>

          <button
            className="btn-secondary"
            onClick={onOpenBagModal}
            title="View remaining tile distribution"
          >
            Bag
          </button>

          <button
            className={isGameOver ? "btn-primary" : "btn-secondary"}
            onClick={onResetMatch}
            disabled={isAutoPlaying}
            title="Reset match to turn 1"
          >
            {isGameOver ? "New Match" : "Reset"}
          </button>

          {/* Speed Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', marginLeft: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Delay:</span>
            {[0.5, 1.0, 2.0].map(s => (
              <button
                key={s}
                className={`studio-tab-btn ${autoPlaySpeed === s ? 'active' : ''}`}
                onClick={() => onSpeedChange(s)}
                style={{ padding: '0.2rem 0.45rem', fontSize: '0.75rem' }}
              >
                {s}s
              </button>
            ))}
          </div>
        </div>
      </div>

      {isGameOver && (
        <div style={{
          marginTop: '0.85rem',
          padding: '0.65rem 1rem',
          borderRadius: '4px',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.85rem'
        }}>
          <div>
            <span style={{ fontWeight: 800, color: '#34d399', textTransform: 'uppercase', marginRight: '0.5rem', letterSpacing: '0.05em' }}>
              MATCH COMPLETE
            </span>
            <span style={{ color: '#fef3c7', fontWeight: 600 }}>
              {gameOverReason || "Game has concluded."}
            </span>
          </div>
          <button
            className="btn-primary"
            onClick={onResetMatch}
            style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
          >
            New Match
          </button>
        </div>
      )}
    </div>
  );
};

